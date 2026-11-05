"""
Ferramentas de Gerenciamento de Lembretes Agendados para a LLM.

Permite à LLM interpretar solicitações de aviso ("me avise em 15 minutos",
"às 09:00 do dia 19/10 me lembre de tomar remédio") e registrar o lembrete
no banco para disparo automático no Discord.
"""

from context_manager import (
    get_current_channel_id,
    get_current_user,
    get_current_user_id,
)
from reminder_manager import (
    cancelar_lembrete,
    criar_lembrete,
    get_agora,
    interpretar_expressao_tempo,
    listar_lembretes_usuario,
)
from tools.registry import register_tool


@register_tool(
    name="criar_lembrete",
    description=(
        "Agenda um aviso/lembrete no Discord para o usuário. "
        "O parâmetro 'quando' aceita tempo relativo (ex: '15 minutos', '15m', '2 horas', '30 segundos') "
        "ou data/hora absoluta (ex: '09:00', '19/10/2026 09:00', '19/10 14:30', 'amanhã às 10:00'). "
        "O bot avisará o usuário no canal automaticamente quando o horário chegar."
    ),
    parameters={
        "type": "object",
        "properties": {
            "mensagem": {
                "type": "string",
                "description": "Texto do lembrete (o que o usuário precisa ser avisado para fazer ou lembrar).",
            },
            "quando": {
                "type": "string",
                "description": "Quando disparar o aviso. Ex: 'em 15 minutos', 'em 2 horas', '09:00', '19/10/2026 09:00'.",
            },
        },
        "required": ["mensagem", "quando"],
    },
)
def tool_criar_lembrete(mensagem: str, quando: str) -> str:
    """Agenda um lembrete para o usuário."""
    dt_alvo = interpretar_expressao_tempo(quando)
    if not dt_alvo:
        return (
            f"Erro: Não consegui interpretar o momento '{quando}'. "
            "Tente usar expressões como 'em 15 minutos', 'em 2 horas', '09:00' ou '19/10/2026 09:00'."
        )

    user_id = get_current_user_id() or get_current_user()
    channel_id = get_current_channel_id()

    res = criar_lembrete(
        user_id=user_id,
        channel_id=channel_id,
        mensagem=mensagem,
        quando_dt=dt_alvo,
    )

    if res.get("sucesso"):
        return res["resposta_formatada"]
    return f"Erro: {res.get('mensagem', 'Falha ao agendar lembrete.')}"


@register_tool(
    name="listar_meus_lembretes",
    description="Consulta e lista todos os lembretes pendentes já programados para o usuário atual.",
)
def tool_listar_meus_lembretes() -> str:
    """Retorna os lembretes pendentes."""
    user_id = get_current_user_id() or get_current_user()
    lembretes = listar_lembretes_usuario(user_id, apenas_pendentes=True)

    if not lembretes:
        return "Você não tem nenhum lembrete pendente programado no momento."

    linhas = ["⏰ **Seus lembretes pendentes:**"]
    for l in lembretes:
        linhas.append(f"• `#{l['id']}` **{l['remind_at']}**: {l['mensagem']}")
    linhas.append("💡 *Para cancelar: peça 'cancele o lembrete #ID' ou use `!cancelar_lembrete <id>`.*")
    return "\n".join(linhas)


@register_tool(
    name="cancelar_lembrete",
    description="Cancela um lembrete pendente utilizando o número do identificador (ID) do lembrete.",
    parameters={
        "type": "object",
        "properties": {
            "lembrete_id": {
                "type": "integer",
                "description": "ID numérico do lembrete a ser cancelado.",
            }
        },
        "required": ["lembrete_id"],
    },
)
def tool_cancelar_lembrete(lembrete_id: int) -> str:
    """Cancela um lembrete."""
    user_id = get_current_user_id() or get_current_user()
    res = cancelar_lembrete(user_id, int(lembrete_id))
    if res.get("sucesso"):
        return f"Sucesso: {res['mensagem']}"
    return f"Erro: {res.get('mensagem', 'Falha ao cancelar lembrete.')}"
