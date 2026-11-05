"""
Módulo de Gerenciamento de Lembretes Agendados (Reminders).

Permite ao usuário programar avisos no Discord por tempo relativo (ex: 'em 15 minutos')
ou data/hora absoluta (ex: 'às 09:00 do dia 19/10'). Armazena os lembretes no SQLite
e dispara notificações ativas através de um worker assíncrono em segundo plano.
"""

import asyncio
from datetime import datetime, timedelta
import logging
from pathlib import Path
import re
import sqlite3
from typing import Any, Dict, List, Optional
import zoneinfo
import discord
from config import CALENDAR_DEFAULT_TIMEZONE, DB_FILE

logger = logging.getLogger(__name__)


def _get_db_path(db_path: Optional[str] = None) -> str:
    """Retorna o caminho seguro do banco de dados SQLite."""
    caminho = db_path or DB_FILE
    parent = Path(caminho).parent
    if parent and not parent.exists():
        parent.mkdir(parents=True, exist_ok=True)
    return str(caminho)


def _get_timezone() -> zoneinfo.ZoneInfo:
    """Obtém o fuso horário configurado."""
    try:
        return zoneinfo.ZoneInfo(CALENDAR_DEFAULT_TIMEZONE)
    except Exception:
        return zoneinfo.ZoneInfo("America/Sao_Paulo")


def get_agora() -> datetime:
    """Retorna o datetime atual no fuso horário configurado."""
    return datetime.now(_get_timezone())


def init_reminder_db(db_path: Optional[str] = None) -> None:
    """Inicializa a tabela de lembretes no SQLite."""
    caminho = _get_db_path(db_path)
    with sqlite3.connect(caminho) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                channel_id TEXT NOT NULL,
                message TEXT NOT NULL,
                remind_at TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pendente',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_reminders_status_time 
            ON reminders (status, remind_at)
            """
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_reminders_user 
            ON reminders (user_id, status)
            """
        )
        conn.commit()


def interpretar_expressao_tempo(
    expressao: str,
    agora: Optional[datetime] = None,
) -> Optional[datetime]:
    """Interpreta expressões de tempo relativo ou datas/horários absolutos.
    
    Exemplos suportados:
    - Relativos: '15m', '15 min', '15 minutos', '2h', '2 horas', '30s', '30 segundos', '1d', '1 dia'
    - 'em 15 minutos', 'em 2h'
    - Horários: '09:00', '14:30' (se já passou hoje, agenda para amanhã)
    - Datas e horas: '19/10/2026 09:00', '19/10 09:00', '2026-10-19 09:00', '19-10-2026 09:00'
    """
    if not expressao or not expressao.strip():
        return None

    tz = _get_timezone()
    base = agora or get_agora()
    texto = expressao.strip().lower()

    # Remove prefixos comuns em português
    texto = re.sub(r"^(em|daqui\s+a|para|ás|às|as)\s+", "", texto).strip()

    # 1. Padrões Relativos (dias, horas, minutos, segundos)
    # Exemplos: 15m, 15 min, 15 minutos, 2h, 2 horas, 45 segundos, 1 dia
    rel_match = re.match(
        r"^(\d+)\s*(s|seg|segundos?|m|min|minutos?|h|hrs?|horas?|d|dias?)$",
        texto,
    )
    if rel_match:
        qtd = int(rel_match.group(1))
        unidade = rel_match.group(2)
        if unidade.startswith("s"):
            return base + timedelta(seconds=qtd)
        elif unidade.startswith("m"):
            return base + timedelta(minutes=qtd)
        elif unidade.startswith("h"):
            return base + timedelta(hours=qtd)
        elif unidade.startswith("d"):
            return base + timedelta(days=qtd)

    # 2. Padrões combinados como "1h 30m" ou "1 hora e 20 minutos"
    combinado = re.findall(r"(\d+)\s*(h|hrs?|horas?|m|min|minutos?|s|segundos?)", texto)
    if combinado and len(combinado) > 1:
        delta = timedelta()
        for qtd_str, u in combinado:
            qtd = int(qtd_str)
            if u.startswith("h"):
                delta += timedelta(hours=qtd)
            elif u.startswith("m"):
                delta += timedelta(minutes=qtd)
            elif u.startswith("s"):
                delta += timedelta(seconds=qtd)
        if delta.total_seconds() > 0:
            return base + delta

    # 3. Padrão "amanhã às HH:MM" ou "hoje às HH:MM"
    if "amanhã" in texto:
        hora_match = re.search(r"(\d{1,2}):(\d{2})", texto)
        if hora_match:
            h, m = int(hora_match.group(1)), int(hora_match.group(2))
            alvo = base + timedelta(days=1)
            return alvo.replace(hour=h, minute=m, second=0, microsecond=0)

    # 4. Padrão apenas horário: "HH:MM" ou "HH:MM:SS"
    hora_simples = re.match(r"^(\d{1,2}):(\d{2})(?::(\d{2}))?$", texto)
    if hora_simples:
        h = int(hora_simples.group(1))
        m = int(hora_simples.group(2))
        s = int(hora_simples.group(3) or 0)
        alvo = base.replace(hour=h, minute=m, second=s, microsecond=0)
        # Se o horário já passou hoje, agenda para o dia seguinte
        if alvo <= base:
            alvo += timedelta(days=1)
        return alvo

    # 5. Padrão Data e Hora: DD/MM/YYYY HH:MM ou DD/MM HH:MM
    data_hora_match = re.search(
        r"(\d{1,2})[/-](\d{1,2})(?:[/-](\d{2,4}))?\s+(?:às\s+|as\s+)?(\d{1,2}):(\d{2})(?::(\d{2}))?",
        texto,
    )
    if data_hora_match:
        dia = int(data_hora_match.group(1))
        mes = int(data_hora_match.group(2))
        ano_str = data_hora_match.group(3)
        ano = int(ano_str) if ano_str else base.year
        if ano < 100:
            ano += 2000
        h = int(data_hora_match.group(4))
        m = int(data_hora_match.group(5))
        s = int(data_hora_match.group(6) or 0)
        try:
            return datetime(ano, mes, dia, h, m, s, tzinfo=tz)
        except ValueError:
            return None

    # 6. Formatos ISO padrão (ex: 2026-10-19T09:00:00 ou 2026-10-19 09:00)
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M"):
        try:
            dt = datetime.strptime(texto, fmt)
            return dt.replace(tzinfo=tz)
        except ValueError:
            pass

    return None


def criar_lembrete(
    user_id: str,
    channel_id: str,
    mensagem: str,
    quando_dt: datetime,
    db_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Salva um novo lembrete agendado no banco SQLite."""
    msg = (mensagem or "").strip()
    if not msg:
        return {"sucesso": False, "mensagem": "A mensagem do lembrete não pode estar vazia."}

    agora = get_agora()
    if quando_dt <= agora:
        return {
            "sucesso": False,
            "mensagem": f"O horário agendado ({quando_dt.strftime('%d/%m/%Y %H:%M:%S')}) já passou. Informe uma data/hora no futuro.",
        }

    caminho = _get_db_path(db_path)
    remind_at_iso = quando_dt.isoformat()

    with sqlite3.connect(caminho) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO reminders (user_id, channel_id, message, remind_at, status)
            VALUES (?, ?, ?, ?, 'pendente')
            """,
            (str(user_id), str(channel_id), msg, remind_at_iso),
        )
        lembrete_id = cursor.lastrowid
        conn.commit()

    delta = quando_dt - agora
    minutos_restantes = max(1, int(delta.total_seconds() // 60))

    return {
        "sucesso": True,
        "lembrete_id": lembrete_id,
        "mensagem_texto": msg,
        "remind_at": quando_dt.strftime("%d/%m/%Y às %H:%M"),
        "tempo_estimado": f"em cerca de {minutos_restantes} minuto(s)",
        "resposta_formatada": (
            f"⏰ **Lembrete #{lembrete_id} agendado com sucesso!**\n"
            f"• **Mensagem:** {msg}\n"
            f"• **Data/Hora:** {quando_dt.strftime('%d/%m/%Y às %H:%M')}\n"
            f"• **Previsão:** daqui a aproximadamente {minutos_restantes} minuto(s).\n"
            f"*(Eu avisarei você aqui no canal assim que chegar o momento!)*"
        ),
    }


def obter_lembretes_vencidos(db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Busca no banco todos os lembretes pendentes cujo horário de disparo já chegou."""
    caminho = _get_db_path(db_path)
    agora_iso = get_agora().isoformat()

    with sqlite3.connect(caminho) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, user_id, channel_id, message, remind_at
            FROM reminders
            WHERE status = 'pendente' AND remind_at <= ?
            ORDER BY remind_at ASC
            LIMIT 50
            """,
            (agora_iso,),
        )
        rows = cursor.fetchall()

    return [
        {
            "id": r[0],
            "user_id": r[1],
            "channel_id": r[2],
            "message": r[3],
            "remind_at": r[4],
        }
        for r in rows
    ]


def atualizar_status_lembrete(
    lembrete_id: int,
    novo_status: str,
    db_path: Optional[str] = None,
) -> None:
    """Atualiza o status do lembrete ('disparado', 'cancelado', 'erro')."""
    caminho = _get_db_path(db_path)
    with sqlite3.connect(caminho) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE reminders SET status = ? WHERE id = ?",
            (novo_status, lembrete_id),
        )
        conn.commit()


def listar_lembretes_usuario(
    user_id: str,
    apenas_pendentes: bool = True,
    db_path: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Lista os lembretes de um usuário específico."""
    caminho = _get_db_path(db_path)
    user_str = str(user_id)

    with sqlite3.connect(caminho) as conn:
        cursor = conn.cursor()
        if apenas_pendentes:
            cursor.execute(
                """
                SELECT id, message, remind_at, status, created_at
                FROM reminders
                WHERE user_id = ? AND status = 'pendente'
                ORDER BY remind_at ASC
                """,
                (user_str,),
            )
        else:
            cursor.execute(
                """
                SELECT id, message, remind_at, status, created_at
                FROM reminders
                WHERE user_id = ?
                ORDER BY id DESC
                LIMIT 30
                """,
                (user_str,),
            )
        rows = cursor.fetchall()

    lembretes = []
    for r in rows:
        try:
            dt = datetime.fromisoformat(r[2])
            formatada = dt.strftime("%d/%m/%Y às %H:%M")
        except Exception:
            formatada = r[2]
        lembretes.append({
            "id": r[0],
            "mensagem": r[1],
            "remind_at": formatada,
            "status": r[3],
            "created_at": r[4],
        })
    return lembretes


def cancelar_lembrete(
    user_id: str,
    lembrete_id: int,
    db_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Cancela um lembrete pendente do usuário."""
    caminho = _get_db_path(db_path)
    user_str = str(user_id)

    with sqlite3.connect(caminho) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, message, status 
            FROM reminders 
            WHERE id = ? AND user_id = ?
            """,
            (lembrete_id, user_str),
        )
        row = cursor.fetchone()
        if not row:
            return {
                "sucesso": False,
                "mensagem": f"Lembrete #{lembrete_id} não foi encontrado ou pertence a outro usuário.",
            }

        msg, status = row[1], row[2]
        if status != "pendente":
            return {
                "sucesso": False,
                "mensagem": f"O lembrete #{lembrete_id} já está com status '{status}'.",
            }

        cursor.execute(
            "UPDATE reminders SET status = 'cancelado' WHERE id = ?",
            (lembrete_id,),
        )
        conn.commit()

    return {
        "sucesso": True,
        "mensagem": f"Lembrete #{lembrete_id} ('{msg}') foi cancelado com sucesso.",
    }


def concluir_lembrete(
    lembrete_id: int,
    user_id: Optional[str] = None,
    db_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Marca um lembrete como concluído com sucesso."""
    caminho = _get_db_path(db_path)
    with sqlite3.connect(caminho) as conn:
        cursor = conn.cursor()
        if user_id:
            cursor.execute(
                "SELECT id, message FROM reminders WHERE id = ? AND user_id = ?",
                (lembrete_id, str(user_id)),
            )
        else:
            cursor.execute("SELECT id, message FROM reminders WHERE id = ?", (lembrete_id,))
        row = cursor.fetchone()
        if not row:
            return {"sucesso": False, "mensagem": f"Lembrete #{lembrete_id} não encontrado."}

        cursor.execute(
            "UPDATE reminders SET status = 'concluido' WHERE id = ?",
            (lembrete_id,),
        )
        conn.commit()

    return {
        "sucesso": True,
        "lembrete_id": lembrete_id,
        "mensagem": f"Lembrete #{lembrete_id} ('{row[1]}') marcado como concluído!",
    }


def adiar_lembrete(
    lembrete_id: int,
    minutos: int = 10,
    user_id: Optional[str] = None,
    db_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Adia um lembrete para daqui a N minutos (ou horas) e reabre como pendente."""
    caminho = _get_db_path(db_path)
    agora = get_agora()
    nova_data = agora + timedelta(minutes=minutos)
    nova_data_iso = nova_data.isoformat()

    with sqlite3.connect(caminho) as conn:
        cursor = conn.cursor()
        if user_id:
            cursor.execute(
                "SELECT id, message FROM reminders WHERE id = ? AND user_id = ?",
                (lembrete_id, str(user_id)),
            )
        else:
            cursor.execute("SELECT id, message FROM reminders WHERE id = ?", (lembrete_id,))
        row = cursor.fetchone()
        if not row:
            return {"sucesso": False, "mensagem": f"Lembrete #{lembrete_id} não encontrado."}

        msg = row[1]
        cursor.execute(
            "UPDATE reminders SET remind_at = ?, status = 'pendente' WHERE id = ?",
            (nova_data_iso, lembrete_id),
        )
        conn.commit()

    formatada = nova_data.strftime("%d/%m/%Y às %H:%M")
    return {
        "sucesso": True,
        "lembrete_id": lembrete_id,
        "remind_at": formatada,
        "mensagem": f"Lembrete #{lembrete_id} ('{msg}') adiado para {formatada}!",
    }


# ==============================================================================
# WORKER ASSÍNCRONO DE SEGUNDO PLANO
# ==============================================================================

async def iniciar_worker_lembretes(client: discord.Client, intervalo_segundos: int = 10) -> None:
    """Loop assíncrono contínuo que monitora e dispara lembretes vencidos no Discord."""
    logger.info("⏰ Worker de lembretes iniciado (verificação a cada %ds).", intervalo_segundos)
    
    # Aguarda o bot estar pronto antes de iniciar o loop de envio
    await client.wait_until_ready()

    while not client.is_closed():
        try:
            vencidos = obter_lembretes_vencidos()
            for item in vencidos:
                lembrete_id = item["id"]
                user_id = item["user_id"]
                channel_id = item["channel_id"]
                texto = item["message"]

                # Marca imediatamente como 'processando' para evitar reprocessamento por corridas
                atualizar_status_lembrete(lembrete_id, "processando")

                canal = None
                # Tenta obter o canal em cache ou via API
                try:
                    if channel_id and channel_id.isdigit():
                        canal = client.get_channel(int(channel_id))
                        if not canal:
                            canal = await client.fetch_channel(int(channel_id))
                except Exception as err:
                    logger.warning("Não foi possível acessar o canal %s: %s", channel_id, err)

                from message_gateway import message_gateway, MessagePriority
                from config import DISCORD_UI_COMPONENTS_ENABLED
                from ui_components import ReminderActionView

                view_lembrete = None
                if DISCORD_UI_COMPONENTS_ENABLED:
                    autor_int = int(user_id) if user_id and user_id.isdigit() else 0
                    view_lembrete = ReminderActionView(lembrete_id=lembrete_id, user_id=str(user_id), author_id=autor_int)

                # Se encontrou o canal, envia marcando o usuário
                enviou = False
                if canal and hasattr(canal, "send"):
                    try:
                        mencao = f"<@{user_id}>" if user_id and user_id.isdigit() else f"@{user_id}"
                        conteudo = (
                            f"⏰ 🔔 **LEMBRETE!** {mencao}\n"
                            f"> **{texto}**\n"
                            f"*(Aviso agendado anteriormente)*"
                        )
                        await message_gateway.dispatch(
                            canal,
                            content=conteudo,
                            view=view_lembrete,
                            priority=MessagePriority.BACKGROUND,
                        )
                        enviou = True
                    except Exception as err:
                        logger.error("Falha ao enviar lembrete no canal %s: %s", channel_id, err)

                # Fallback: tenta enviar via Mensagem Direta (DM) para o usuário se o canal falhou
                if not enviou and user_id and user_id.isdigit():
                    try:
                        usuario_discord = client.get_user(int(user_id)) or await client.fetch_user(int(user_id))
                        if usuario_discord:
                            await message_gateway.dispatch(
                                usuario_discord,
                                content=f"⏰ 🔔 **LEMBRETE!**\n> **{texto}**",
                                view=view_lembrete,
                                priority=MessagePriority.BACKGROUND,
                            )
                            enviou = True
                    except Exception as err:
                        logger.error("Falha ao enviar lembrete via DM para %s: %s", user_id, err)

                # Marca como disparado (ou erro se não conseguiu enviar de jeito nenhum)
                status_final = "disparado" if enviou else "falha_envio"
                atualizar_status_lembrete(lembrete_id, status_final)
                logger.info("Lembrete #%d processado com status: %s", lembrete_id, status_final)

        except Exception as e:
            logger.error("Erro no ciclo do worker de lembretes: %s", e, exc_info=True)

        await asyncio.sleep(intervalo_segundos)
