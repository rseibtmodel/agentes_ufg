"""
Ferramentas da LLM para Consulta e Configuração do Resumo Matinal Diário.
"""

from typing import Any, Dict, Optional
from context_manager import get_current_channel_id, get_current_user_id
from digest_manager import (
    atualizar_configuracao_digest,
    coletar_dados_dia,
    gerar_resumo_matinal_texto,
    obter_configuracao_digest,
)
from tools.registry import register_tool


@register_tool(
    name="gerar_resumo_matinal",
    description="Gera e retorna o Resumo Matinal completo do usuário para hoje (compromissos da agenda, lembretes, listas pendentes e previsão do tempo). Use quando o usuário pedir seu resumo diário ou matinal.",
)
async def tool_gerar_resumo_matinal(cidade: Optional[str] = None) -> str:
    """Gera o resumo matinal do dia atual para o usuário ativo."""
    user_id = get_current_user_id()
    if not user_id:
        return "Erro: Identificador de usuário não encontrado no contexto atual."

    cfg = obter_configuracao_digest(user_id)
    cidade_alvo = cidade or cfg.get("city", "Curitiba")

    dados = await coletar_dados_dia(user_id, "Usuário", cidade=cidade_alvo)
    resumo = await gerar_resumo_matinal_texto(dados)
    return resumo


@register_tool(
    name="configurar_resumo_matinal",
    description="Configura as preferências do Resumo Matinal diário: ativar/desativar, horário de envio (ex: '08:00') e cidade para previsão do tempo (ex: 'Curitiba', 'São Paulo').",
)
def tool_configurar_resumo_matinal(
    ativado: Optional[bool] = None,
    horario: Optional[str] = None,
    cidade: Optional[str] = None,
) -> Dict[str, Any]:
    """Atualiza as preferências do resumo matinal diário do usuário."""
    user_id = get_current_user_id()
    channel_id = get_current_channel_id()
    if not user_id:
        return {"sucesso": False, "mensagem": "Usuário não identificado no contexto."}

    return atualizar_configuracao_digest(
        user_id=user_id,
        enabled=ativado,
        time=horario,
        channel_id=channel_id,
        city=cidade,
    )
