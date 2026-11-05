"""
Ferramentas de Integração com o Google Calendar para a LLM (Function Calling).

Permite que a LLM consulte compromissos futuros, adicione novos eventos
e cancele/remova compromissos da agenda do usuário no Google Calendar.
"""

from google_calendar import (
    adicionar_compromisso,
    listar_compromissos,
    remover_compromisso,
    verificar_status_autenticacao,
)
from tools.registry import register_tool


@register_tool(
    name="listar_agenda_google",
    description="Consulta a agenda do Google Calendar e retorna os próximos compromissos e reuniões agendados. Use sempre que o usuário perguntar o que tem para fazer, compromissos de hoje/amanhã/semana ou pedir para ver a agenda.",
    parameters={
        "type": "object",
        "properties": {
            "dias_a_frente": {
                "type": "integer",
                "description": "Quantidade de dias à frente para consultar a partir de hoje (padrão: 7 dias).",
            },
            "data_inicio": {
                "type": "string",
                "description": "Data ou data/hora inicial da consulta no formato 'YYYY-MM-DD' ou 'YYYY-MM-DD HH:MM' (opcional, padrão: momento atual).",
            },
        },
        "required": [],
    },
)
def tool_listar_agenda_google(dias_a_frente: int = 7, data_inicio: str = "") -> str:
    """Executa a listagem de compromissos no Google Calendar."""
    data_in = data_inicio if data_inicio.strip() else None
    res = listar_compromissos(dias_a_frente=dias_a_frente, data_inicio=data_in)

    if not res.get("sucesso"):
        return f"Não foi possível consultar a agenda do Google: {res.get('erro')}"

    eventos = res.get("eventos", [])
    if not eventos:
        return (
            f"📅 Nenhum compromisso encontrado na sua agenda Google entre "
            f"{res.get('periodo_inicio')} e {res.get('periodo_fim')}."
        )

    linhas = [
        f"📅 Compromissos encontrados na agenda Google ({len(eventos)} evento(s) entre {res.get('periodo_inicio')} e {res.get('periodo_fim')}):"
    ]
    for idx, ev in enumerate(eventos, start=1):
        local_str = f" | Local: {ev['local']}" if ev.get("local") else ""
        desc_str = f" | Descrição: {ev['descricao']}" if ev.get("descricao") else ""
        linhas.append(
            f"{idx}. **{ev['titulo']}** (Início: {ev['inicio']} | Fim: {ev['fim']}{local_str}{desc_str}) [ID: {ev['id']}]"
        )

    return "\n".join(linhas)


@register_tool(
    name="adicionar_evento_google",
    description="Adiciona um novo compromisso ou reunião na agenda do Google Calendar. Use sempre que o usuário pedir para marcar reunião, agendar compromisso, adicionar evento ou salvar na agenda.",
    parameters={
        "type": "object",
        "properties": {
            "titulo": {
                "type": "string",
                "description": "Nome ou resumo do evento/reunião (ex: 'Reunião com Fornecedor', 'Dentista', 'Almoço de Negócios').",
            },
            "data_hora_inicio": {
                "type": "string",
                "description": "Data e horário de início no formato 'YYYY-MM-DD HH:MM' ou 'DD/MM/YYYY HH:MM' ou ISO 8601 (ex: '2026-10-20 14:30').",
            },
            "data_hora_fim": {
                "type": "string",
                "description": "Data e horário de término no formato 'YYYY-MM-DD HH:MM' (opcional, padrão: 1 hora após o início).",
            },
            "descricao": {
                "type": "string",
                "description": "Pauta, detalhes ou anotações adicionais do compromisso (opcional).",
            },
            "localizacao": {
                "type": "string",
                "description": "Local físico ou link da chamada de vídeo (ex: 'Google Meet', 'Sala 4', 'Avenida Paulista, 1000') (opcional).",
            },
        },
        "required": ["titulo", "data_hora_inicio"],
    },
)
def tool_adicionar_evento_google(
    titulo: str,
    data_hora_inicio: str,
    data_hora_fim: str = "",
    descricao: str = "",
    localizacao: str = "",
) -> str:
    """Cria um novo evento no Google Calendar."""
    fim = data_hora_fim if data_hora_fim.strip() else None
    res = adicionar_compromisso(
        titulo=titulo,
        inicio=data_hora_inicio,
        fim=fim,
        descricao=descricao,
        localizacao=localizacao,
    )

    if not res.get("sucesso"):
        return f"Não foi possível agendar o compromisso no Google Calendar: {res.get('erro')}"

    return (
        f"✅ Evento '{res.get('titulo')}' agendado com sucesso no Google Calendar!\n"
        f"• Início: {res.get('inicio')}\n"
        f"• Término: {res.get('fim')}\n"
        f"• Link: {res.get('link')}"
    )


@register_tool(
    name="remover_evento_google",
    description="Remove ou cancela um compromisso da agenda do Google Calendar pelo nome/título ou ID. Use sempre que o usuário pedir para cancelar compromisso, desmarcar reunião ou apagar evento da agenda.",
    parameters={
        "type": "object",
        "properties": {
            "termo_ou_id": {
                "type": "string",
                "description": "Título exato ou parcial do compromisso a remover, ou o ID do evento no Google Calendar (ex: 'Dentista', 'Reunião de Alinhamento').",
            }
        },
        "required": ["termo_ou_id"],
    },
)
def tool_remover_evento_google(termo_ou_id: str) -> str:
    """Cancela ou exclui um evento da agenda Google."""
    res = remover_compromisso(termo_ou_id=termo_ou_id)
    if not res.get("sucesso"):
        return f"Não foi possível remover o compromisso: {res.get('erro')}"

    return f"🗑️ {res.get('mensagem')}"
