"""
Ferramentas de Pesquisa na Web e Leitura de Páginas para a LLM.

Disponibiliza as tools 'buscar_na_web' e 'ler_pagina_web' para permitir
que o assistente acesse informações em tempo real na internet.
"""

from typing import Optional
from tools.registry import register_tool
from web_search_manager import web_search_manager


@register_tool(
    name="buscar_na_web",
    description=(
        "Pesquisa na internet fatos em tempo real, notícias recentes, cotações de moedas, "
        "previsão do tempo, documentações técnicas e artigos. Retorna uma lista com títulos, links e resumos."
    ),
    parameters={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Termo ou pergunta a ser pesquisada na internet (ex: 'previsão do tempo são paulo amanhã', 'cotação do euro hoje').",
            },
            "max_resultados": {
                "type": "integer",
                "description": "Quantidade máxima de resultados desejados (padrão: 4, máximo: 6).",
                "default": 4,
            },
        },
        "required": ["query"],
    },
)
async def tool_buscar_na_web(query: str, max_resultados: Optional[int] = 4) -> str:
    """Executa a busca na web e retorna os resultados estruturados para a LLM."""
    limite = min(max(1, max_resultados or 4), 6)
    resultados = await web_search_manager.buscar_na_web(query=query, max_resultados=limite)
    return web_search_manager.formatar_para_llm(resultados, query)


@register_tool(
    name="ler_pagina_web",
    description=(
        "Acessa uma URL na internet e extrai o conteúdo textual limpo da página ou matéria "
        "(removendo menus, scripts e anúncios). Use para aprofundar a leitura de links encontrados em buscas."
    ),
    parameters={
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "URL completa da página ou artigo (ex: 'https://exemplo.com/noticia-123'). Deve começar com http:// ou https://.",
            },
        },
        "required": ["url"],
    },
)
async def tool_ler_pagina_web(url: str) -> str:
    """Extrai o texto limpo de uma página web."""
    res = await web_search_manager.ler_pagina_web(url=url, max_caracteres=3500)
    if not res.get("sucesso"):
        return f"Erro ao acessar {url}: {res.get('erro', 'Falha desconhecida ao ler página.')}"

    titulo = res.get("titulo", "Sem título")
    conteudo = res.get("conteudo", "")
    return (
        f"--- CONTEÚDO EXTRAÍDO DE: {url} ---\n"
        f"Título: {titulo}\n\n"
        f"{conteudo}\n"
        f"--- FIM DO CONTEÚDO ---"
    )
