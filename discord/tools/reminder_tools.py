"""
Ferramentas de Gerenciamento de Lembretes Agendados para a LLM.

Permite à LLM interpretar solicitações de aviso ("me avise em 15 minutos",
"às 09:00 do dia 19/10 me lembre de tomar remédio") e registrar o lembrete
no banco para disparo automático no Discord.
"""

from typing import Any, Dict
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
def tool_criar_lembrete(mensagem: str, quando: str) -> Dict[str, Any]:
    """Agenda um lembrete para o usuário no formato canônico."""
    dt_alvo = interpretar_expressao_tempo(quando)
    if not dt_alvo:
        return {
            "sucesso": False,
            "dados": None,
            "erro": (
                f"Não consegui interpretar o momento '{quando}'. "
                "Tente usar expressões como 'em 15 minutos', 'em 2 horas', '09:00' ou '19/10/2026 09:00'."
            ),
        }

    user_id = get_current_user_id() or get_current_user()
    channel_id = get_current_channel_id()

    res = criar_lembrete(
        user_id=user_id,
        channel_id=channel_id,
        mensagem=mensagem,
        quando_dt=dt_alvo,
    )

    if res.get("sucesso"):
        return {
            "sucesso": True,
            "dados": res,
            "erro": None,
        }
    return {
        "sucesso": False,
        "dados": None,
        "erro": res.get("mensagem", "Falha ao agendar lembrete."),
    }


@register_tool(
    name="listar_meus_lembretes",
    description="Consulta e lista todos os lembretes pendentes já programados para o usuário atual.",
)
def tool_listar_meus_lembretes() -> Dict[str, Any]:
    """Retorna os lembretes pendentes no formato canônico."""
    user_id = get_current_user_id() or get_current_user()
    lembretes = listar_lembretes_usuario(user_id, apenas_pendentes=True)

    return {
        "sucesso": True,
        "dados": {
            "total_lembretes": len(lembretes),
            "lembretes": lembretes,
        },
        "erro": None,
    }


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
def tool_cancelar_lembrete(lembrete_id: int) -> Dict[str, Any]:
    """Cancela um lembrete no formato canônico."""
    user_id = get_current_user_id() or get_current_user()
    res = cancelar_lembrete(user_id, int(lembrete_id))
    if res.get("sucesso"):
        return {
            "sucesso": True,
            "dados": res,
            "erro": None,
        }
    return {
        "sucesso": False,
        "dados": None,
        "erro": res.get("mensagem", "Falha ao cancelar lembrete."),
    }
