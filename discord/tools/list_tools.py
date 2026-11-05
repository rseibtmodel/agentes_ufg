"""
Ferramentas de Gerenciamento de Listas (Mercado, Compras, Tarefas) para a LLM.

Permite à LLM adicionar itens, consultar itens, marcar itens como concluídos,
remover itens e excluir itens já finalizados de listas pessoais.
"""

from context_manager import get_current_user
from list_manager import (
    adicionar_item_lista,
    excluir_lista,
    formatar_lista_para_exibicao,
    limpar_itens_concluidos,
    listar_todas_listas,
    obter_itens_lista,
    remover_item_lista,
    ticar_item_lista,
)
from tools.registry import register_tool


@register_tool(
    name="adicionar_item_lista",
    description="Adiciona um novo item a uma lista pessoal (ex: 'mercado', 'compras', 'tarefas'). Cria a lista automaticamente se não existir.",
    parameters={
        "type": "object",
        "properties": {
            "nome_lista": {
                "type": "string",
                "description": "Nome da lista (ex: 'mercado', 'compras', 'tarefas').",
            },
            "item": {
                "type": "string",
                "description": "Texto ou nome do item a ser adicionado (ex: '2L de leite', 'café em pó').",
            },
        },
        "required": ["nome_lista", "item"],
    },
)
def tool_adicionar_item_lista(nome_lista: str, item: str) -> str:
    """Adiciona um item à lista indicada."""
    user = get_current_user()
    res = adicionar_item_lista(user, nome_lista, item)
    if res.get("sucesso"):
        return f"Sucesso: {res['mensagem']}"
    return f"Erro: {res.get('mensagem', 'Falha ao adicionar item.')}"


@register_tool(
    name="ver_itens_lista",
    description="Retorna os itens de uma lista pessoal (ex: 'mercado', 'tarefas'), indicando quais estão pendentes e quais já foram concluídos.",
    parameters={
        "type": "object",
        "properties": {
            "nome_lista": {
                "type": "string",
                "description": "Nome da lista a ser visualizada (ex: 'mercado', 'tarefas').",
            }
        },
        "required": ["nome_lista"],
    },
)
def tool_ver_itens_lista(nome_lista: str) -> str:
    """Visualiza todos os itens de uma lista específica."""
    user = get_current_user()
    dados = obter_itens_lista(user, nome_lista)
    return formatar_lista_para_exibicao(dados)


@register_tool(
    name="listar_minhas_listas",
    description="Lista os nomes de todas as listas pessoais cadastradas do usuário e a contagem de itens de cada uma.",
    parameters={
        "type": "object",
        "properties": {},
        "required": [],
    },
)
def tool_listar_minhas_listas() -> str:
    """Retorna um resumo de todas as listas do usuário."""
    user = get_current_user()
    listas = listar_todas_listas(user)
    if not listas:
        return "Você ainda não possui nenhuma lista criada. Peça para adicionar itens a uma lista (ex: 'adicione leite na lista de mercado')."

    linhas = ["📋 **Suas listas cadastradas:**"]
    for l in listas:
        linhas.append(
            f"• **{l['nome']}**: {l['total_itens']} itens ({l['pendentes']} pendentes, {l['concluidos']} concluídos)"
        )
    return "\n".join(linhas)


@register_tool(
    name="ticar_item_lista",
    description="Marca um item da lista como concluído (ticar) ou reabre como pendente. Aceita o número do item (#ID) ou o nome do item.",
    parameters={
        "type": "object",
        "properties": {
            "nome_lista": {
                "type": "string",
                "description": "Nome da lista onde o item está.",
            },
            "item_ou_id": {
                "type": "string",
                "description": "Número do ID ou texto correspondente ao item.",
            },
            "concluido": {
                "type": "boolean",
                "description": "True para marcar como concluído, False para marcar como pendente.",
                "default": True,
            },
        },
        "required": ["nome_lista", "item_ou_id"],
    },
)
def tool_ticar_item_lista(nome_lista: str, item_ou_id: str, concluido: bool = True) -> str:
    """Marca ou desmarca um item como finalizado."""
    user = get_current_user()
    res = ticar_item_lista(user, nome_lista, item_ou_id, concluido=concluido)
    if res.get("sucesso"):
        return f"Sucesso: {res['mensagem']}"
    return f"Erro: {res.get('mensagem', 'Falha ao atualizar o item.')}"


@register_tool(
    name="remover_item_lista",
    description="Remove um item individual de uma lista pelo número (#ID) ou pelo nome do item.",
    parameters={
        "type": "object",
        "properties": {
            "nome_lista": {
                "type": "string",
                "description": "Nome da lista.",
            },
            "item_ou_id": {
                "type": "string",
                "description": "ID ou texto do item a remover.",
            },
        },
        "required": ["nome_lista", "item_ou_id"],
    },
)
def tool_remover_item_lista(nome_lista: str, item_ou_id: str) -> str:
    """Remove um item da lista."""
    user = get_current_user()
    res = remover_item_lista(user, nome_lista, item_ou_id)
    if res.get("sucesso"):
        return f"Sucesso: {res['mensagem']}"
    return f"Erro: {res.get('mensagem', 'Falha ao remover item.')}"


@register_tool(
    name="limpar_itens_concluidos_lista",
    description="Exclui permanentemente todos os itens ticados/concluídos de uma lista, mantendo apenas os pendentes.",
    parameters={
        "type": "object",
        "properties": {
            "nome_lista": {
                "type": "string",
                "description": "Nome da lista a ter os itens concluídos excluídos.",
            }
        },
        "required": ["nome_lista"],
    },
)
def tool_limpar_itens_concluidos_lista(nome_lista: str) -> str:
    """Apaga os itens concluídos de uma lista."""
    user = get_current_user()
    res = limpar_itens_concluidos(user, nome_lista)
    if res.get("sucesso"):
        return f"Sucesso: {res['mensagem']}"
    return f"Erro: {res.get('mensagem', 'Falha ao limpar itens concluídos.')}"


@register_tool(
    name="excluir_lista",
    description="Exclui uma lista inteira e todos os itens contidos nela.",
    parameters={
        "type": "object",
        "properties": {
            "nome_lista": {
                "type": "string",
                "description": "Nome da lista a ser excluída.",
            }
        },
        "required": ["nome_lista"],
    },
)
def tool_excluir_lista(nome_lista: str) -> str:
    """Exclui a lista inteira."""
    user = get_current_user()
    res = excluir_lista(user, nome_lista)
    if res.get("sucesso"):
        return f"Sucesso: {res['mensagem']}"
    return f"Erro: {res.get('mensagem', 'Falha ao excluir lista.')}"
