"""
Ferramentas de Configuração do Usuário para a LLM (Modo de Resposta Texto/Áudio/Ambos).

Permite que a LLM compreenda solicitações em linguagem natural como:
- "A partir de agora me responda em áudio"
- "Quero que você me responda apenas em texto"
- "Me responda com áudio e texto juntos"
e altere a preferência do usuário de forma persistente.
"""

from typing import Any, Dict
from context_manager import get_current_user_id
from database import definir_modo_resposta, obter_modo_resposta
from tools.registry import register_tool


@register_tool(
    name="configurar_modo_resposta",
    description=(
        "Configura a forma como o assistente deve responder ao usuário nas próximas mensagens. "
        "Opções disponíveis: 'texto' (apenas mensagens de texto escritas), "
        "'audio' (apenas mensagens de voz narradas pela Francisca Brasil) ou "
        "'ambos' (envia a mensagem em texto e também o áudio narrado simultaneamente)."
    ),
    parameters={
        "type": "object",
        "properties": {
            "modo": {
                "type": "string",
                "enum": ["texto", "audio", "ambos"],
                "description": (
                    "O modo desejado para as respostas: "
                    "'texto' para somente texto, "
                    "'audio' para somente áudio/voz, ou "
                    "'ambos' para texto e áudio."
                ),
            }
        },
        "required": ["modo"],
    },
)
def tool_configurar_modo_resposta(modo: str) -> Dict[str, Any]:
    """Define a preferência de resposta do usuário atual."""
    user_id = get_current_user_id()
    if not user_id:
        return {"sucesso": False, "mensagem": "ID do usuário não identificado na sessão atual."}

    return definir_modo_resposta(user_id, modo)


@register_tool(
    name="consultar_modo_resposta",
    description="Consulta o modo de resposta atualmente ativo para o usuário ('texto', 'audio' ou 'ambos').",
    parameters={
        "type": "object",
        "properties": {},
    },
)
def tool_consultar_modo_resposta() -> Dict[str, Any]:
    """Informa qual modo de resposta está ativo para o usuário."""
    user_id = get_current_user_id()
    if not user_id:
        return {"sucesso": False, "mensagem": "ID do usuário não identificado na sessão atual."}

    modo = obter_modo_resposta(user_id)
    descricoes = {
        "texto": "Apenas Texto",
        "audio": "Apenas Áudio (voz Francisca pt-BR)",
        "ambos": "Texto e Áudio",
    }
    return {
        "sucesso": True,
        "modo": modo,
        "descricao": descricoes.get(modo, modo),
        "voz": "pt-BR-FranciscaNeural",
    }


@register_tool(
    name="configurar_provedor_modelo",
    description=(
        "Altera o provedor e modelo de IA ativo para o usuário. "
        "Opções: 'local' (LM Studio local para custo zero e privacidade), "
        "'google' (Google Gemini 2.5 Flash para tarefas rápidas em nuvem), "
        "'gemini-pro' (Google Gemini 2.5 Pro para tarefas complexas, livros e raciocínio profundo), "
        "ou 'auto' (roteamento automático inteligente por complexidade)."
    ),
    parameters={
        "type": "object",
        "properties": {
            "provedor": {
                "type": "string",
                "enum": ["local", "google", "gemini", "gemini-pro", "auto"],
                "description": "O provedor desejado: 'local', 'google', 'gemini-pro' ou 'auto'.",
            }
        },
        "required": ["provedor"],
    },
)
def tool_configurar_provedor_modelo(provedor: str) -> Dict[str, Any]:
    """Altera o provedor de IA preferido pelo usuário."""
    from context_manager import get_current_user
    from database import definir_preferencia_modelo
    from llm_client import llm_client

    user_id = get_current_user_id()
    user_name = get_current_user()
    if not user_id:
        return {"sucesso": False, "mensagem": "ID do usuário não identificado na sessão atual."}

    prov_norm = provedor.strip().lower()
    if prov_norm in ("google", "gemini", "gemini-pro") and not llm_client.tem_gemini_disponivel():
        return {
            "sucesso": False,
            "mensagem": (
                "⚠️ A API do Google Gemini ainda não possui uma chave configurada. "
                "Para ativar, use o comando `!modelo key <sua_chave>` no Discord ou configure no `.env`."
            ),
        }

    return definir_preferencia_modelo(user_id, user_name, prov_norm)


@register_tool(
    name="consultar_provedor_modelo",
    description="Consulta o provedor e modelo de IA atualmente ativo para o usuário (LM Studio Local, Google Gemini ou Auto).",
    parameters={
        "type": "object",
        "properties": {},
    },
)
def tool_consultar_provedor_modelo() -> Dict[str, Any]:
    """Informa qual provedor e modelo de IA está ativo para o usuário."""
    from database import obter_preferencia_modelo
    from llm_client import llm_client

    user_id = get_current_user_id()
    if not user_id:
        return {"sucesso": False, "mensagem": "ID do usuário não identificado na sessão atual."}

    pref = obter_preferencia_modelo(user_id)
    gemini_ok = llm_client.tem_gemini_disponivel()

    return {
        "sucesso": True,
        "provedor_ativo": pref["provider"],
        "modelo_ativo": pref["model_name"],
        "auto_failover": pref["auto_failover"],
        "google_gemini_disponivel": gemini_ok,
    }

