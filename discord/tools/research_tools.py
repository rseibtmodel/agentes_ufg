"""
Ferramentas de Pesquisa Profunda (Deep Research) para a LLM — IDEA-17.

Permite à LLM acionar investigações aprofundadas com varredura paralela da web,
análise de múltiplas fontes e geração de dossiês estruturados.
"""

from typing import Any, Dict, Optional
from context_manager import add_pending_file, get_current_user_id
from deep_research_manager import deep_research_manager
from radar_manager import radar_manager
from tools.registry import register_tool


@register_tool(
    name="executar_pesquisa_profunda",
    description=(
        "Conduz uma investigação e pesquisa profunda autônoma (Deep Research) na internet sobre um tema complexo, "
        "técnico ou de mercado. A IA decompõe a dúvida em múltiplos eixos de busca, lê dezenas de páginas da web, "
        "cruza dados e redige um dossiê técnico detalhado com citações e referências. "
        "Use sempre que o usuário pedir uma análise minuciosa, pesquisa aprofundada, relatório comparativo ou dossiê."
    ),
    parameters={
        "type": "object",
        "properties": {
            "tema": {
                "type": "string",
                "description": "O tema, tecnologia, pergunta ou problema complexo a ser investigado minuciosamente na web.",
            }
        },
        "required": ["tema"],
    },
)
async def tool_executar_pesquisa_profunda(tema: str) -> Dict[str, Any]:
    """Executa o ciclo de pesquisa profunda e agenda o envio do dossiê."""
    user_id = get_current_user_id() or "usuario_padrao"

    res = await deep_research_manager.executar_pesquisa_completa(tema=tema, user_id=user_id)
    if not res.get("sucesso"):
        return res

    dados = res["dados"]
    caminho_arquivo = dados.get("file_path")
    if caminho_arquivo:
        # Registra o arquivo Markdown para envio como anexo no Discord
        from pathlib import Path
        add_pending_file(Path(caminho_arquivo))

    return {
        "sucesso": True,
        "dados": {
            "report_id": dados["report_id"],
            "tema": dados["tema"],
            "resumo_executivo": dados["resumo_executivo"],
            "total_fontes_consultadas": dados["total_fontes"],
            "mensagem": (
                f"✅ Dossiê de Pesquisa Profunda concluído com sucesso (ID: `{dados['report_id']}`). "
                f"Foram consultadas e analisadas `{dados['total_fontes']}` fontes na web. "
                f"O arquivo completo em Markdown foi anexado ao chat."
            ),
        },
        "erro": None,
    }


@register_tool(
    name="listar_relatorios_pesquisa",
    description="Lista os relatórios e dossiês de pesquisa profunda (Deep Research) já elaborados anteriormente para o usuário.",
    parameters={
        "type": "object",
        "properties": {
            "limite": {
                "type": "integer",
                "description": "Quantidade máxima de relatórios a listar (padrão: 5).",
            }
        },
    },
)
def tool_listar_relatorios_pesquisa(limite: int = 5) -> Dict[str, Any]:
    """Lista as pesquisas profundas já salvas do usuário."""
    user_id = get_current_user_id() or "usuario_padrao"

    relatorios = deep_research_manager.listar_relatorios(user_id=user_id, limite=limite)
    if not relatorios:
        return {
            "sucesso": True,
            "dados": {
                "total": 0,
                "relatorios": [],
                "mensagem": "Nenhum relatório de pesquisa profunda encontrado.",
            },
            "erro": None,
        }

    linhas = [f"📚 **Relatórios de Pesquisa Profunda ({len(relatorios)}):**\n"]
    for idx, r in enumerate(relatorios, start=1):
        linhas.append(f"{idx}. `[{r['id']}]` **{r['topic']}** ({r['total_sources']} fontes) — *{r['created_at']}*")

    return {
        "sucesso": True,
        "dados": {
            "total": len(relatorios),
            "relatorios": relatorios,
            "texto_formatado": "\n".join(linhas),
        },
        "erro": None,
    }


@register_tool(
    name="pesquisar_novidades_radar",
    description="Consulta novidades técnicas, releases do GitHub e artigos do ArXiv capturados e curados pelo Radar de Feeds.",
    parameters={
        "type": "object",
        "properties": {
            "termo": {
                "type": "string",
                "description": "Palavra-chave ou termo para filtrar os itens capturados no radar (opcional).",
            },
            "limite": {
                "type": "integer",
                "description": "Quantidade máxima de novidades a retornar (padrão: 5).",
            },
        },
    },
)
def tool_pesquisar_novidades_radar(termo: Optional[str] = None, limite: int = 5) -> Dict[str, Any]:
    """Consulta itens capturados pelo radar."""
    itens = radar_manager.buscar_itens_radar(termo=termo, limite=limite)
    if not itens:
        return {
            "sucesso": True,
            "dados": {
                "total": 0,
                "itens": [],
                "mensagem": "Nenhuma novidade encontrada no Radar para o filtro informado.",
            },
            "erro": None,
        }

    linhas = [f"📡 **Novidades do Radar de Feeds ({len(itens)}):**\n"]
    for idx, item in enumerate(itens, start=1):
        linhas.append(f"{idx}. `[{item['fonte']}]` **{item['titulo']}**\n🔗 <{item['link']}> ({item['processado_em']})")

    return {
        "sucesso": True,
        "dados": {
            "total": len(itens),
            "itens": itens,
            "texto_formatado": "\n".join(linhas),
        },
        "erro": None,
    }

