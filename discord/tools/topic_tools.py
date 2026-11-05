"""
Ferramentas de Gestão do Knowledge Hub e RAG Isolado por Canal — IDEA-25.
"""

from context_manager import get_current_channel_id, get_current_user_id
from topic_manager import adicionar_nota, buscar_notas_rag, listar_notas, obter_topico_canal
from tools.registry import register_tool
from typing import List, Optional


@register_tool(
    name="adicionar_nota_canal",
    description="Registra uma nova nota, ideia ou anotação de conhecimento no banco temático do canal atual e indexa no ChromaDB.",
    parameters={
        "type": "object",
        "properties": {
            "conteudo": {
                "type": "string",
                "description": "Texto completo da anotação, ideia ou fato a ser registrado.",
            },
            "tags": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Lista opcional de tags para classificação (ex: ['#ideia', '#bug', '#cbs']).",
            },
        },
        "required": ["conteudo"],
    },
)
async def tool_adicionar_nota_canal(conteudo: str, tags: Optional[List[str]] = None) -> str:
    """Registra uma nota no tópico do canal ativo."""
    channel_id = get_current_channel_id()
    user_id = get_current_user_id()
    if not channel_id:
        return "Erro: Não foi possível identificar o canal atual para registrar a nota."

    res = await adicionar_nota(channel_id=channel_id, user_id=user_id, content=conteudo, tags=tags)
    return res["mensagem"]


@register_tool(
    name="buscar_notas_canal",
    description="Realiza busca semântica (RAG) estritamente isolada nas notas e conhecimentos salvos no tópico do canal atual, ignorando a memória geral.",
    parameters={
        "type": "object",
        "properties": {
            "consulta_semantica": {
                "type": "string",
                "description": "Pergunta ou termo de busca semântica para resgatar notas relacionadas no canal.",
            },
            "top_k": {
                "type": "integer",
                "description": "Quantidade máxima de fragmentos relevantes a retornar (padrão: 4).",
            },
        },
        "required": ["consulta_semantica"],
    },
)
async def tool_buscar_notas_canal(consulta_semantica: str, top_k: int = 4) -> str:
    """Busca semanticamente nas notas do canal temático atual."""
    channel_id = get_current_channel_id()
    if not channel_id:
        return "Erro: Canal atual não identificado."

    topico = obter_topico_canal(channel_id)
    nome_topico = topico["topic_name"] if topico else f"Canal {channel_id}"

    notas = await buscar_notas_rag(channel_id, consulta_semantica, top_k=top_k)
    if not notas:
        return f"Nenhuma nota relevante encontrada no tópico '{nome_topico}' para a consulta '{consulta_semantica}'."

    linhas = [f"📚 **Notas recuperadas no tópico '{nome_topico}' ({len(notas)} resultado(s)):**"]
    for idx, n in enumerate(notas, start=1):
        tags_str = f" [{n.get('tags')}]" if n.get("tags") else ""
        linhas.append(f"{idx}. (ID: `{n.get('note_id')}`{tags_str}): {n.get('conteudo')} (distância: {n.get('distancia')})")

    return "\n".join(linhas)


@register_tool(
    name="listar_notas_canal",
    description="Lista as notas recentes registradas no tópico do canal atual, com opção de filtro por tag.",
    parameters={
        "type": "object",
        "properties": {
            "tag_filtro": {
                "type": "string",
                "description": "Tag opcional para filtrar as notas (ex: '#cbs', '#bug').",
            },
            "limite": {
                "type": "integer",
                "description": "Quantidade máxima de notas a listar (padrão: 10).",
            },
        },
    },
)
async def tool_listar_notas_canal(tag_filtro: Optional[str] = None, limite: int = 10) -> str:
    """Lista as notas mais recentes do canal atual."""
    channel_id = get_current_channel_id()
    if not channel_id:
        return "Erro: Canal atual não identificado."

    topico = obter_topico_canal(channel_id)
    nome_topico = topico["topic_name"] if topico else f"Canal {channel_id}"

    notas = listar_notas(channel_id, tag=tag_filtro, limite=limite)
    if not notas:
        filtro_txt = f" com a tag '{tag_filtro}'" if tag_filtro else ""
        return f"Nenhuma nota encontrada no tópico '{nome_topico}'{filtro_txt}."

    linhas = [f"📝 **Notas salvas no tópico '{nome_topico}' ({len(notas)} nota(s)):**"]
    for idx, n in enumerate(notas, start=1):
        tags_str = f" `{' '.join(n['tags'])}`" if n["tags"] else ""
        linhas.append(f"{idx}. [`{n['id']}`]{tags_str}: {n['content']}")

    return "\n".join(linhas)
