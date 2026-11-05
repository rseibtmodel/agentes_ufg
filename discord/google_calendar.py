"""
Módulo de Integração com o Google Calendar.

Responsável por:
1. Gerenciar credenciais OAuth 2.0 e token de acesso do usuário.
2. Consultar compromissos futuros na agenda do Google (Primary Calendar).
3. Agendar novos compromissos com data/hora de início e fim.
4. Remover ou cancelar compromissos por ID ou correspondência de título.
"""

from datetime import datetime, timedelta
import logging
from pathlib import Path
import re
from typing import Any, Dict, List, Optional
import zoneinfo
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from config import (
    CALENDAR_DEFAULT_TIMEZONE,
    GOOGLE_CREDENTIALS_FILE,
    GOOGLE_TOKEN_FILE,
)

logger = logging.getLogger(__name__)

# Escopo necessário para leitura, escrita e exclusão de eventos na agenda do usuário
SCOPES = ["https://www.googleapis.com/auth/calendar"]


def verificar_status_autenticacao() -> Dict[str, Any]:
    """Verifica se as credenciais e o token do Google Calendar estão configurados e válidos."""
    caminho_cred = Path(GOOGLE_CREDENTIALS_FILE)
    caminho_token = Path(GOOGLE_TOKEN_FILE)

    tem_cred = caminho_cred.exists()
    tem_token = caminho_token.exists()

    if not tem_token and not tem_cred:
        return {
            "autenticado": False,
            "status": "configuracao_pendente",
            "mensagem": (
                "⚠️ O arquivo 'credentials.json' do Google Cloud não foi encontrado na pasta discord/. "
                "Para ativar a integração com o Google Calendar, baixe o arquivo de credenciais OAuth 2.0 "
                "do Google Cloud Console e execute 'python3 discord/auth_calendar.py'."
            ),
        }

    if not tem_token and tem_cred:
        return {
            "autenticado": False,
            "status": "autorizacao_necessaria",
            "mensagem": (
                "🔑 O arquivo 'credentials.json' foi detectado, mas a autorização ainda não foi concluída. "
                "Por favor, execute 'python3 discord/auth_calendar.py' no terminal para autorizar o acesso à sua agenda."
            ),
        }

    # Verifica validade do token
    try:
        creds = Credentials.from_authorized_user_file(str(caminho_token), SCOPES)
        if creds and creds.valid:
            return {"autenticado": True, "status": "conectado", "mensagem": "Conectado ao Google Calendar."}
        elif creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open(caminho_token, "w", encoding="utf-8") as f:
                f.write(creds.to_json())
            return {"autenticado": True, "status": "conectado", "mensagem": "Token do Google Calendar renovado com sucesso."}
    except Exception as e:
        logger.warning("Falha ao validar token do Google Calendar: %s", e)

    return {
        "autenticado": False,
        "status": "token_invalido",
        "mensagem": "Token do Google Calendar expirado ou inválido. Execute 'python3 discord/auth_calendar.py' para reconectar.",
    }


def obter_servico_calendar():
    """Retorna o cliente autenticado da Google Calendar API v3 ou None caso não esteja autenticado."""
    caminho_token = Path(GOOGLE_TOKEN_FILE)
    if not caminho_token.exists():
        return None

    try:
        creds = Credentials.from_authorized_user_file(str(caminho_token), SCOPES)
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open(caminho_token, "w", encoding="utf-8") as token_file:
                token_file.write(creds.to_json())

        if creds and creds.valid:
            return build("calendar", "v3", credentials=creds, cache_discovery=False)
    except Exception as e:
        logger.exception("Erro ao instanciar serviço do Google Calendar: %s", e)

    return None


def _parse_data_hora(data_str: str, fuso_horario: str = CALENDAR_DEFAULT_TIMEZONE) -> datetime:
    """Interpreta formatos de data e hora comuns e aplica a timezone especificada."""
    texto = data_str.strip()
    tz = zoneinfo.ZoneInfo(fuso_horario)

    formatos = [
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y %H:%M",
        "%Y-%m-%d",
        "%d/%m/%Y",
    ]

    for fmt in formatos:
        try:
            dt = datetime.strptime(texto, fmt)
            return dt.replace(tzinfo=tz)
        except ValueError:
            continue

    # Fallback via regex para ISO 8601 com offset
    try:
        dt_iso = datetime.fromisoformat(texto)
        if dt_iso.tzinfo is None:
            dt_iso = dt_iso.replace(tzinfo=tz)
        return dt_iso
    except Exception:
        pass

    raise ValueError(
        f"Formato de data/hora não reconhecido: '{data_str}'. "
        f"Formatos aceitos: 'YYYY-MM-DD HH:MM', 'DD/MM/YYYY HH:MM' ou ISO 8601 ('2026-10-19T14:00:00')."
    )


def listar_compromissos(
    dias_a_frente: int = 7,
    data_inicio: Optional[str] = None,
    max_resultados: int = 15,
    fuso_horario: str = CALENDAR_DEFAULT_TIMEZONE,
) -> Dict[str, Any]:
    """Lista os próximos compromissos da agenda Google (Primary Calendar)."""
    service = obter_servico_calendar()
    if not service:
        status = verificar_status_autenticacao()
        return {"sucesso": False, "erro": status["mensagem"], "eventos": []}

    tz = zoneinfo.ZoneInfo(fuso_horario)
    agora = datetime.now(tz)

    if data_inicio:
        try:
            dt_inicio = _parse_data_hora(data_inicio, fuso_horario)
        except ValueError as ve:
            return {"sucesso": False, "erro": str(ve), "eventos": []}
    else:
        dt_inicio = agora

    dt_fim = dt_inicio + timedelta(days=dias_a_frente)

    try:
        events_result = (
            service.events()
            .list(
                calendarId="primary",
                timeMin=dt_inicio.isoformat(),
                timeMax=dt_fim.isoformat(),
                maxResults=max_resultados,
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )

        items = events_result.get("items", [])
        eventos = []

        for item in items:
            start_raw = item.get("start", {}).get("dateTime") or item.get("start", {}).get("date")
            end_raw = item.get("end", {}).get("dateTime") or item.get("end", {}).get("date")

            eventos.append({
                "id": item.get("id"),
                "titulo": item.get("summary", "(Sem título)"),
                "inicio": start_raw,
                "fim": end_raw,
                "descricao": item.get("description", ""),
                "local": item.get("location", ""),
                "link": item.get("htmlLink", ""),
            })

        return {
            "sucesso": True,
            "periodo_inicio": dt_inicio.strftime("%d/%m/%Y %H:%M"),
            "periodo_fim": dt_fim.strftime("%d/%m/%Y %H:%M"),
            "total": len(eventos),
            "eventos": eventos,
        }

    except HttpError as error:
        logger.error("Erro na API do Google Calendar: %s", error)
        return {"sucesso": False, "erro": f"Erro retornado pela API do Google: {error}", "eventos": []}
    except Exception as e:
        logger.exception("Erro inesperado ao consultar agenda: %s", e)
        return {"sucesso": False, "erro": str(e), "eventos": []}


def adicionar_compromisso(
    titulo: str,
    inicio: str,
    fim: Optional[str] = None,
    descricao: str = "",
    localizacao: str = "",
    fuso_horario: str = CALENDAR_DEFAULT_TIMEZONE,
) -> Dict[str, Any]:
    """Cria um novo evento no Google Calendar."""
    service = obter_servico_calendar()
    if not service:
        status = verificar_status_autenticacao()
        return {"sucesso": False, "erro": status["mensagem"]}

    try:
        dt_inicio = _parse_data_hora(inicio, fuso_horario)
        if fim and fim.strip():
            dt_fim = _parse_data_hora(fim, fuso_horario)
        else:
            # Duração padrão de 1 hora se não for especificado horário final
            dt_fim = dt_inicio + timedelta(hours=1)

        if dt_fim <= dt_inicio:
            return {"sucesso": False, "erro": "O horário de término deve ser posterior ao horário de início."}

        event_body = {
            "summary": titulo.strip(),
            "description": descricao.strip(),
            "location": localizacao.strip(),
            "start": {
                "dateTime": dt_inicio.isoformat(),
                "timeZone": fuso_horario,
            },
            "end": {
                "dateTime": dt_fim.isoformat(),
                "timeZone": fuso_horario,
            },
        }

        created_event = (
            service.events()
            .insert(calendarId="primary", body=event_body)
            .execute()
        )

        return {
            "sucesso": True,
            "id": created_event.get("id"),
            "titulo": created_event.get("summary"),
            "inicio": dt_inicio.strftime("%d/%m/%Y às %H:%M"),
            "fim": dt_fim.strftime("%d/%m/%Y às %H:%M"),
            "link": created_event.get("htmlLink"),
        }

    except ValueError as ve:
        return {"sucesso": False, "erro": str(ve)}
    except HttpError as error:
        logger.error("Erro ao inserir evento no Google Calendar: %s", error)
        return {"sucesso": False, "erro": f"Erro na API do Google Calendar: {error}"}
    except Exception as e:
        logger.exception("Erro inesperado ao agendar compromisso: %s", e)
        return {"sucesso": False, "erro": str(e)}


def remover_compromisso(
    termo_ou_id: str,
    fuso_horario: str = CALENDAR_DEFAULT_TIMEZONE,
) -> Dict[str, Any]:
    """Remove um compromisso do Google Calendar pelo ID ou buscando por título em eventos futuros."""
    service = obter_servico_calendar()
    if not service:
        status = verificar_status_autenticacao()
        return {"sucesso": False, "erro": status["mensagem"]}

    termo = termo_ou_id.strip()
    if not termo:
        return {"sucesso": False, "erro": "Informe o título ou ID do compromisso a remover."}

    # 1. Tenta remoção direta por ID
    try:
        service.events().delete(calendarId="primary", eventId=termo).execute()
        return {"sucesso": True, "mensagem": f"Evento de ID '{termo}' removido com sucesso."}
    except HttpError:
        pass  # Não era um ID exato, prossegue para busca por título

    # 2. Busca por título nos próximos 60 dias e nos últimos 2 dias
    tz = zoneinfo.ZoneInfo(fuso_horario)
    agora = datetime.now(tz)
    time_min = (agora - timedelta(days=2)).isoformat()
    time_max = (agora + timedelta(days=60)).isoformat()

    try:
        events_result = (
            service.events()
            .list(
                calendarId="primary",
                timeMin=time_min,
                timeMax=time_max,
                q=termo,
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )

        items = events_result.get("items", [])
        if not items:
            return {
                "sucesso": False,
                "erro": f"Nenhum compromisso contendo '{termo}' foi encontrado na agenda.",
            }

        if len(items) == 1:
            alvo = items[0]
            service.events().delete(calendarId="primary", eventId=alvo["id"]).execute()
            titulo = alvo.get("summary", "(Sem título)")
            start = alvo.get("start", {}).get("dateTime", "")
            return {
                "sucesso": True,
                "mensagem": f"Compromisso '{titulo}' ({start}) removido com sucesso da sua agenda!",
                "id_removido": alvo["id"],
                "titulo": titulo,
            }

        # Múltiplos eventos encontrados: lista para o usuário selecionar
        candidatos = []
        for it in items:
            candidatos.append({
                "id": it.get("id"),
                "titulo": it.get("summary"),
                "inicio": it.get("start", {}).get("dateTime") or it.get("start", {}).get("date"),
            })

        return {
            "sucesso": False,
            "erro": (
                f"Mais de um compromisso corresponde a '{termo}'. "
                f"Por favor, seja mais específico ou informe o ID exato. Eventos encontrados: {candidatos}"
            ),
            "multiplos": candidatos,
        }

    except HttpError as error:
        return {"sucesso": False, "erro": f"Erro na API do Google Calendar: {error}"}
    except Exception as e:
        logger.exception("Erro ao remover compromisso: %s", e)
        return {"sucesso": False, "erro": str(e)}
