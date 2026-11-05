"""
Módulo de Filtragem Semântica de Ferramentas (Tool RAG / Dynamic Tool Selection).

Reduz a sobrecarga de contexto na LLM computando similaridade vetorial entre
a mensagem do usuário e as descrições das ferramentas registradas, enviando
apenas as ferramentas mais pertinentes para cada requisição.
"""

import asyncio
import logging
import math
from typing import Any, Dict, List, Optional
from config import (
    TOOL_FILTER_ENABLED,
    TOOL_FILTER_MIN_SIMILARITY,
    TOOL_FILTER_TOP_K,
)
from tools.registry import ToolDefinition, registry
from vector_db import gerar_embedding

logger = logging.getLogger(__name__)

# Cache de embeddings das descrições das ferramentas indexado pelo nome da tool
_tool_embeddings_cache: Dict[str, List[float]] = {}
_cache_lock = asyncio.Lock()


def similaridade_cosseno(v1: List[float], v2: List[float]) -> float:
    """Calcula a similaridade de cosseno entre dois vetores densos."""
    dot = sum(a * b for a, b in zip(v1, v2))
    norm1 = math.sqrt(sum(a * a for a in v1))
    norm2 = math.sqrt(sum(b * b for b in v2))
    if norm1 == 0.0 or norm2 == 0.0:
        return 0.0
    return dot / (norm1 * norm2)


def _gerar_texto_descritivo_tool(tool: ToolDefinition) -> str:
    """Gera um texto rico e explicativo da ferramenta para fins de vetorização."""
    partes = [f"Ferramenta '{tool.name}': {tool.description}"]
    
    # Se houver propriedades/parâmetros, inclui nomes para enriquecer o embedding
    params = tool.parameters.get("properties", {})
    if params:
        nomes_params = list(params.keys())
        partes.append(f"Parâmetros: {', '.join(nomes_params)}")
        
    return " ".join(partes)


async def inicializar_cache_ferramentas(force_reload: bool = False) -> None:
    """Pré-computa os embeddings de todas as ferramentas registradas e armazena em cache."""
    async with _cache_lock:
        todas_tools = registry._tools.values()
        novas = 0
        for tool in todas_tools:
            if force_reload or tool.name not in _tool_embeddings_cache:
                texto = _gerar_texto_descritivo_tool(tool)
                vetor = await gerar_embedding(texto)
                if vetor:
                    _tool_embeddings_cache[tool.name] = vetor
                    novas += 1

        if novas > 0:
            logger.info(
                "Cache de embeddings de tools inicializado: %d nova(s) ferramenta(s) vetorizada(s).",
                novas,
            )


async def filtrar_ferramentas_relevantes(
    query: str,
    top_k: Optional[int] = None,
    min_score: Optional[float] = None,
) -> List[Dict[str, Any]]:
    """Seleciona dinamicamente as ferramentas mais pertinentes à consulta do usuário.
    
    1. Compara o embedding da mensagem com os embeddings pré-computados das ferramentas.
    2. Ordena pela similaridade de cosseno.
    3. Retorna apenas as Top-K ferramentas que atingirem o limiar mínimo de similaridade.
    """
    # 1. Se a filtragem estiver desativada nas configurações, repassa o catálogo completo
    if not TOOL_FILTER_ENABLED:
        return registry.get_schemas()

    texto_busca = (query or "").strip()
    if not texto_busca:
        return []

    limite_k = top_k if top_k is not None else TOOL_FILTER_TOP_K
    limite_score = min_score if min_score is not None else TOOL_FILTER_MIN_SIMILARITY

    # 2. Garante que o cache de embeddings das ferramentas está aquecido
    if len(_tool_embeddings_cache) < len(registry._tools):
        await inicializar_cache_ferramentas()

    # 3. Gera embedding da mensagem enviada pelo usuário
    query_vec = await gerar_embedding(texto_busca)
    if not query_vec:
        logger.warning(
            "Não foi possível gerar embedding para a mensagem. "
            "Ativando fallback: todas as ferramentas serão enviadas para a LLM."
        )
        return registry.get_schemas()

    # 4. Calcula a similaridade de cosseno para cada ferramenta registrada
    ranqueamento: List[tuple[ToolDefinition, float]] = []
    for tool_name, tool_defn in registry._tools.items():
        tool_vec = _tool_embeddings_cache.get(tool_name)
        if not tool_vec:
            continue
        score = similaridade_cosseno(query_vec, tool_vec)
        ranqueamento.append((tool_defn, score))

    # 5. Ordena da mais similar para a menos similar
    ranqueamento.sort(key=lambda x: x[1], reverse=True)

    # 6. Filtra as que atingem a pontuação mínima ou até o Top-K
    selecionadas: List[ToolDefinition] = []
    detalhes_log = []

    for tool_defn, score in ranqueamento:
        if len(selecionadas) >= limite_k:
            break
        if score >= limite_score:
            selecionadas.append(tool_defn)
            detalhes_log.append(f"{tool_defn.name} ({score:.2f})")

    # Se a melhor pontuação for muito baixa, assume que é uma conversa geral sem ferramentas
    if not selecionadas:
        logger.info(
            "Tool Filter: Nenhuma ferramenta atingiu similaridade mínima (>= %.2f) para: '%s'. Enviando sem tools.",
            limite_score,
            texto_busca[:35],
        )
        return []

    logger.info(
        "Tool Filter: %d/%d ferramentas selecionadas para: '%s' -> [%s]",
        len(selecionadas),
        len(registry._tools),
        texto_busca[:35],
        ", ".join(detalhes_log),
    )

    # 7. Formata no schema padrão OpenAI/LM Studio
    return [
        {
            "type": "function",
            "function": {
                "name": t.name,
                "description": t.description,
                "parameters": t.parameters,
            },
        }
        for t in selecionadas
    ]
