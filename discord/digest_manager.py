"""
Módulo de Gerenciamento do Resumo Matinal Diário (Morning Digest).

Coleta de forma proativa as informações do dia do usuário:
1. Compromissos agendados no Google Calendar para o dia atual.
2. Lembretes pendentes agendados para hoje no SQLite.
3. Itens pendentes em listas de tarefas e compras (list_manager).
4. Previsão do tempo atual e condição meteorológica via Open-Meteo API.
5. Síntese personalizada via LLM (com fallback em template local).
6. Disparo pontual via worker assíncrono em segundo plano (em texto e/ou áudio Francisca).
"""

import asyncio
from datetime import datetime
import logging
from pathlib import Path
import re
import sqlite3
from typing import Any, Dict, List, Optional
import zoneinfo
import discord
import httpx
from config import CALENDAR_DEFAULT_TIMEZONE, DB_FILE
from database import _get_connection, _get_db_path, obter_modo_resposta
import google_calendar
from list_manager import listar_todas_listas, obter_itens_lista
from reminder_manager import get_agora
from tts_manager import sintetizar_fala_edge
from utils import dividir_mensagem

logger = logging.getLogger(__name__)

# Mapeamento oficial dos códigos WMO de tempo da Open-Meteo para descrições amigáveis em português
WMO_WEATHER_CODES = {
    0: "Céu limpo ☀️",
    1: "Principalmente limpo 🌤️",
    2: "Parcialmente nublado ⛅",
    3: "Nublado ☁️",
    45: "Nevoeiro 🌫️",
    48: "Nevoeiro com geada 🌫️",
    51: "Garoa leve 🌦️",
    53: "Garoa moderada 🌦️",
    55: "Garoa densa 🌧️",
    61: "Chuva fraca 🌧️",
    63: "Chuva moderada 🌧️",
    65: "Chuva forte ⛈️",
    71: "Neve fraca 🌨️",
    73: "Neve moderada 🌨️",
    75: "Neve forte ❄️",
    80: "Pancadas de chuva leves 🌦️",
    81: "Pancadas de chuva moderadas 🌧️",
    82: "Pancadas de chuva violentas ⛈️",
    95: "Tempestade com trovoadas ⛈️",
    96: "Tempestade com granizo leve ⛈️",
    99: "Tempestade com granizo forte ⛈️",
}


def init_digest_db(db_path: Optional[str] = None) -> None:
    """Inicializa a tabela de configurações do Resumo Matinal no SQLite."""
    with _get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS user_digest_settings (
                user_id TEXT PRIMARY KEY,
                enabled INTEGER NOT NULL DEFAULT 1,
                time TEXT NOT NULL DEFAULT '08:00',
                channel_id TEXT DEFAULT NULL,
                city TEXT NOT NULL DEFAULT 'Curitiba',
                last_sent_date TEXT DEFAULT NULL,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.commit()


def obter_configuracao_digest(user_id: str | int, db_path: Optional[str] = None) -> Dict[str, Any]:
    """Recupera a configuração atual do resumo matinal para o usuário."""
    user_str = str(user_id)
    with _get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT enabled, time, channel_id, city, last_sent_date 
            FROM user_digest_settings 
            WHERE user_id = ?
            """,
            (user_str,)
        )
        row = cursor.fetchone()
        if row:
            return {
                "user_id": user_str,
                "enabled": bool(row[0]),
                "time": row[1] or "08:00",
                "channel_id": row[2],
                "city": row[3] or "Curitiba",
                "last_sent_date": row[4],
            }

    # Configuração padrão caso ainda não exista
    return {
        "user_id": user_str,
        "enabled": True,
        "time": "08:00",
        "channel_id": None,
        "city": "Curitiba",
        "last_sent_date": None,
    }


def atualizar_configuracao_digest(
    user_id: str | int,
    enabled: Optional[bool] = None,
    time: Optional[str] = None,
    channel_id: Optional[str | int] = None,
    city: Optional[str] = None,
    db_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Atualiza as preferências do resumo matinal do usuário."""
    atual = obter_configuracao_digest(user_id, db_path)
    novo_enabled = 1 if (enabled if enabled is not None else atual["enabled"]) else 0
    novo_time = str(time).strip() if time else atual["time"]
    novo_channel = str(channel_id).strip() if channel_id is not None else atual["channel_id"]
    nova_city = str(city).strip() if city else atual["city"]

    # Valida formato de hora HH:MM
    if not re.match(r"^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$", novo_time):
        return {
            "sucesso": False,
            "mensagem": f"Horário '{novo_time}' inválido. Utilize o formato 24h `HH:MM` (ex: `08:00`, `07:30`).",
        }

    user_str = str(user_id)
    with _get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO user_digest_settings (user_id, enabled, time, channel_id, city, updated_at)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id) DO UPDATE SET
                enabled = excluded.enabled,
                time = excluded.time,
                channel_id = excluded.channel_id,
                city = excluded.city,
                updated_at = CURRENT_TIMESTAMP
            """,
            (user_str, novo_enabled, novo_time, novo_channel, nova_city)
        )
        conn.commit()

    status_str = "Ativado" if novo_enabled == 1 else "Desativado"
    return {
        "sucesso": True,
        "enabled": bool(novo_enabled),
        "time": novo_time,
        "channel_id": novo_channel,
        "city": nova_city,
        "mensagem": (
            f"⚙️ **Resumo Matinal Configurado com Sucesso!**\n"
            f"• **Status:** {status_str}\n"
            f"• **Horário diário:** `{novo_time}`\n"
            f"• **Cidade (clima):** {nova_city}\n"
            f"• **Canal:** {f'<#{novo_channel}>' if novo_channel else 'Canal da mensagem / DM'}"
        ),
    }


def registrar_envio_digest(user_id: str | int, data_str: str, db_path: Optional[str] = None) -> None:
    """Registra a data do último envio para evitar envios duplicados no mesmo dia."""
    user_str = str(user_id)
    with _get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE user_digest_settings 
            SET last_sent_date = ? 
            WHERE user_id = ?
            """,
            (data_str, user_str)
        )
        conn.commit()


# Siglas dos estados brasileiros para geocodificação e desambiguação
BRAZIL_UFS = {
    "AC": "Acre", "AL": "Alagoas", "AP": "Amapá", "AM": "Amazonas", "BA": "Bahia",
    "CE": "Ceará", "DF": "Distrito Federal", "ES": "Espírito Santo", "GO": "Goiás",
    "MA": "Maranhão", "MT": "Mato Grosso", "MS": "Mato Grosso do Sul", "MG": "Minas Gerais",
    "PA": "Pará", "PB": "Paraíba", "PR": "Paraná", "PE": "Pernambuco", "PI": "Piauí",
    "RJ": "Rio de Janeiro", "RN": "Rio Grande do Norte", "RS": "Rio Grande do Sul",
    "RO": "Rondônia", "RR": "Roraima", "SC": "Santa Catarina", "SP": "São Paulo",
    "SE": "Sergipe", "TO": "Tocantins",
}


def normalizar_cidade_busca(cidade_raw: str) -> tuple[str, Optional[str]]:
    """Separa o nome da cidade de eventual sigla/nome de estado (ex: 'Canela/RS' -> ('Canela', 'RS'))."""
    texto = (cidade_raw or "Curitiba").strip()
    partes = re.split(r"[/,\-–]\s*", texto)
    if len(partes) >= 2:
        return partes[0].strip(), partes[1].strip()
    return texto, None


async def obter_previsao_tempo(cidade: str = "Curitiba") -> Optional[Dict[str, Any]]:
    """Consulta coordenadas e previsão do tempo via API gratuita Open-Meteo."""
    try:
        nome_busca, estado_filtro = normalizar_cidade_busca(cidade)
        async with httpx.AsyncClient(timeout=8.0) as http_client:
            # 1. Geocoding da cidade
            geo_res = await http_client.get(
                "https://geocoding-api.open-meteo.com/v1/search",
                params={"name": nome_busca, "count": 10, "language": "pt", "format": "json"},
            )
            if geo_res.status_code != 200:
                return None
            geo_data = geo_res.json()
            results = geo_data.get("results")
            if not results:
                return None

            # Desambiguação de localidade (filtro por UF/Estado e priorização de cidades brasileiras)
            local = results[0]
            if estado_filtro:
                sigla_upper = estado_filtro.upper()
                nome_estado_completo = BRAZIL_UFS.get(sigla_upper, estado_filtro).lower()
                for r in results:
                    admin1 = (r.get("admin1") or "").lower()
                    country_code = (r.get("country_code") or "").upper()
                    if (sigla_upper in admin1.upper() or nome_estado_completo in admin1) and country_code == "BR":
                        local = r
                        break
            elif any(r.get("country_code") == "BR" for r in results):
                for r in results:
                    if r.get("country_code") == "BR":
                        local = r
                        break

            lat = local["latitude"]
            lon = local["longitude"]
            nome_oficial = local.get("name", nome_busca)
            estado = local.get("admin1", "")

            # 2. Previsão do tempo
            weather_res = await http_client.get(
                "https://api.open-meteo.com/v1/forecast",
                params={
                    "latitude": lat,
                    "longitude": lon,
                    "current": "temperature_2m,relative_humidity_2m,apparent_temperature,weather_code",
                    "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max",
                    "timezone": "auto",
                    "forecast_days": 1,
                },
            )
            if weather_res.status_code != 200:
                return None

            w_data = weather_res.json()
            current = w_data.get("current", {})
            daily = w_data.get("daily", {})

            temp = current.get("temperature_2m", 0.0)
            sensacao = current.get("apparent_temperature", temp)
            w_code = current.get("weather_code", 0)
            condicao = WMO_WEATHER_CODES.get(w_code, "Tempo estável 🌤️")

            temp_max = daily.get("temperature_2m_max", [temp])[0]
            temp_min = daily.get("temperature_2m_min", [temp])[0]
            prob_chuva = daily.get("precipitation_probability_max", [0])[0]

            return {
                "cidade": nome_oficial,
                "estado": estado,
                "temperatura": round(temp, 1),
                "sensacao": round(sensacao, 1),
                "condicao": condicao,
                "temp_max": round(temp_max, 1),
                "temp_min": round(temp_min, 1),
                "prob_chuva": prob_chuva,
                "texto_formatado": (
                    f"{nome_oficial} ({estado}): {round(temp, 1)}°C (Sensação: {round(sensacao, 1)}°C), "
                    f"{condicao}. Mín: {round(temp_min, 1)}°C / Máx: {round(temp_max, 1)}°C, "
                    f"Prob. Chuva: {prob_chuva}%"
                ),
            }
    except Exception as e:
        logger.warning("Falha ao obter previsão do tempo para '%s': %s", cidade, e)
        return None


async def coletar_dados_dia(user_id: str | int, user_name: str, cidade: str = "Curitiba") -> Dict[str, Any]:
    """Coleta e estrutura todos os dados de compromissos, lembretes, listas e clima para o resumo."""
    user_str = str(user_id)
    agora = get_agora()
    hoje_iso = agora.strftime("%Y-%m-%d")
    hoje_formatado = agora.strftime("%d/%m/%Y (%A)")

    # 1. Google Calendar: compromissos do dia
    compromissos = []
    try:
        cal_status = google_calendar.verificar_status_autenticacao()
        if cal_status.get("autenticado"):
            # Consulta compromissos para hoje e amanhã
            eventos_res = await asyncio.to_thread(google_calendar.listar_compromissos, dias_a_frente=1, max_resultados=10)
            if eventos_res.get("sucesso"):
                for ev in eventos_res.get("eventos", []):
                    inicio_str = ev.get("inicio", "")
                    if hoje_iso in inicio_str:
                        # Extrai horário HH:MM
                        try:
                            dt_ini = datetime.fromisoformat(inicio_str)
                            hora_formatada = dt_ini.strftime("%H:%M")
                        except Exception:
                            hora_formatada = inicio_str
                        compromissos.append(f"• `{hora_formatada}` — **{ev.get('titulo', 'Evento')}**")
    except Exception as ex_cal:
        logger.warning("Não foi possível carregar agenda do Google para o digest: %s", ex_cal)

    # 2. Lembretes pendentes para hoje no SQLite
    lembretes = []
    try:
        with _get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, message, remind_at 
                FROM reminders 
                WHERE user_id = ? AND status = 'pendente' AND remind_at LIKE ?
                ORDER BY remind_at ASC
                """,
                (user_str, f"{hoje_iso}%")
            )
            for row in cursor.fetchall():
                lem_id, lem_msg, lem_time = row
                try:
                    hora_lem = datetime.fromisoformat(lem_time).strftime("%H:%M")
                except Exception:
                    hora_lem = lem_time
                lembretes.append(f"• `{hora_lem}` — {lem_msg}")
    except Exception as ex_rem:
        logger.warning("Falha ao coletar lembretes para o digest: %s", ex_rem)

    # 3. Listas e tarefas pendentes
    listas_pendentes = []
    try:
        todas_listas = listar_todas_listas(user_str)
        if isinstance(todas_listas, list):
            for l_info in todas_listas:
                nome_l = l_info["nome"]
                itens_res = obter_itens_lista(user_str, nome_l)
                if itens_res.get("sucesso"):
                    pendentes = [i["texto"] for i in itens_res.get("itens", []) if not i.get("concluido")]
                    if pendentes:
                        amostra = ", ".join(pendentes[:3])
                        if len(pendentes) > 3:
                            amostra += f" (+{len(pendentes) - 3} mais)"
                        listas_pendentes.append(f"• **{nome_l.capitalize()}:** {len(pendentes)} pendente(s) (*{amostra}*)")
    except Exception as ex_lis:
        logger.warning("Falha ao coletar listas para o digest: %s", ex_lis)

    # 4. Previsão do tempo
    clima = await obter_previsao_tempo(cidade)

    return {
        "usuario": user_name,
        "user_id": user_str,
        "data_formatada": hoje_formatado,
        "data_iso": hoje_iso,
        "compromissos": compromissos,
        "lembretes": lembretes,
        "listas": listas_pendentes,
        "clima": clima,
    }


def gerar_texto_fallback_digest(dados: Dict[str, Any]) -> str:
    """Gera o Resumo Matinal estruturado em Markdown caso a LLM esteja offline."""
    user = dados.get("usuario", "Usuário")
    data_str = dados.get("data_formatada", "")
    compromissos = dados.get("compromissos", [])
    lembretes = dados.get("lembretes", [])
    listas = dados.get("listas", [])
    clima = dados.get("clima")

    linhas = [
        f"☀️ **BOM DIA, {user.upper()}!**",
        f"Aqui está o seu **Resumo Matinal Diário** para hoje, *{data_str}*:\n",
    ]

    # Bloco Clima
    if clima:
        linhas.append(f"🌦️ **Previsão do Tempo:**\n{clima.get('texto_formatado', '')}\n")
    else:
        linhas.append("🌦️ **Previsão do Tempo:** Informações climáticas indisponíveis no momento.\n")

    # Bloco Agenda
    linhas.append("📅 **Compromissos na sua Agenda:**")
    if compromissos:
        linhas.extend(compromissos)
    else:
        linhas.append("• *Nenhum compromisso agendado para hoje. Aproveite o dia livre!*")
    linhas.append("")

    # Bloco Lembretes
    linhas.append("⏰ **Lembretes Programados para Hoje:**")
    if lembretes:
        linhas.extend(lembretes)
    else:
        linhas.append("• *Nenhum lembrete programado para hoje.*")
    linhas.append("")

    # Bloco Listas
    linhas.append("🛒 **Listas & Tarefas Pendentes:**")
    if listas:
        linhas.extend(listas)
    else:
        linhas.append("• *Todas as suas listas estão em dia! Nada pendente.*")
    linhas.append("")

    linhas.append("💪 *Tenha um excelente e produtivo dia!*")
    return "\n".join(linhas)


async def gerar_resumo_matinal_texto(dados: Dict[str, Any]) -> str:
    """Utiliza a LLM para redigir o resumo matinal com tom agradável e pessoal (com fallback)."""
    user = dados.get("usuario", "Usuário")
    data_str = dados.get("data_formatada", "")
    compromissos = dados.get("compromissos", [])
    lembretes = dados.get("lembretes", [])
    listas = dados.get("listas", [])
    clima = dados.get("clima")

    prompt_sistema = (
        "Você é o assistente pessoal de IA no Discord (Antigravity). "
        "Sua missão é apresentar o Resumo Matinal Diário do usuário de forma extremamente "
        "agradável, motivadora, elegante e organizada em tópicos. "
        "Use emojis adequados, destaque os horários e mantenha a resposta concisa (máximo 1500 caracteres). "
        "Nunca invente compromissos ou lembretes inexistentes. Atenha-se aos dados fornecidos."
    )

    dados_contexto = [
        f"Usuário: {user}",
        f"Data de hoje: {data_str}",
        f"Clima: {clima.get('texto_formatado') if clima else 'Não disponível'}",
        f"Compromissos da agenda de hoje ({len(compromissos)}): {'; '.join(compromissos) if compromissos else 'Nenhum'}",
        f"Lembretes de hoje ({len(lembretes)}): {'; '.join(lembretes) if lembretes else 'Nenhum'}",
        f"Listas com itens pendentes ({len(listas)}): {'; '.join(listas) if listas else 'Nenhum item pendente'}",
    ]

    mensagens = [
        {"role": "system", "content": prompt_sistema},
        {"role": "user", "content": "Por favor, crie o meu resumo matinal de hoje com base nestes dados:\n" + "\n".join(dados_contexto)},
    ]

    try:
        from llm_client import llm_client
        # Gera via LLM sem necessitar de tools na síntese final
        resposta = await llm_client.gerar_resposta(mensagens, tools=[])
        if resposta and resposta.strip():
            return resposta.strip()
    except Exception as e:
        logger.warning("Falha ao gerar resumo matinal via LLM: %s. Utilizando fallback em template.", e)

    return gerar_texto_fallback_digest(dados)


# Trava em memória para impedir execuções simultâneas do resumo para o mesmo usuário
_digests_em_andamento: set[str] = set()


async def enviar_resumo_matinal(
    client: discord.Client,
    user_id: str | int,
    user_name: Optional[str] = None,
    channel_id: Optional[str | int] = None,
    forcar: bool = False,
) -> Dict[str, Any]:
    """Orquestra a coleta de dados, síntese do resumo e despacho multimodal (texto e/ou áudio)."""
    user_str = str(user_id)

    # Guarda anti-duplicação concorrente em memória
    if not forcar and user_str in _digests_em_andamento:
        logger.warning("Resumo matinal já em andamento para usuário %s. Ignorando disparo concorrente.", user_str)
        return {"sucesso": False, "mensagem": "Resumo matinal já está sendo processado."}

    _digests_em_andamento.add(user_str)
    caminho_audio = None

    try:
        cfg = obter_configuracao_digest(user_id)
        if not cfg["enabled"] and not forcar:
            return {"sucesso": False, "mensagem": "Resumo matinal desativado para este usuário."}

        agora = get_agora()
        hoje_iso = agora.strftime("%Y-%m-%d")

        # Verifica se já foi enviado hoje (a menos que seja forçado pelo comando !digest agora)
        if not forcar and cfg.get("last_sent_date") == hoje_iso:
            return {"sucesso": False, "mensagem": f"O resumo matinal de hoje ({hoje_iso}) já foi enviado."}

        # Resolve nome do usuário
        nome_usuario = user_name
        if not nome_usuario:
            try:
                usr = client.get_user(int(user_str)) or await client.fetch_user(int(user_str))
                nome_usuario = usr.name if usr else "Amigo"
            except Exception:
                nome_usuario = "Amigo"

        cidade = cfg.get("city", "Curitiba")

        # 1. Coleta os dados
        dados = await coletar_dados_dia(user_str, nome_usuario, cidade)

        # 2. Gera o texto do resumo (LLM ou Template)
        texto_resumo = await gerar_resumo_matinal_texto(dados)

        # 3. Resolve o canal de envio
        alvo_channel_id = channel_id or cfg.get("channel_id")
        canal = None
        if alvo_channel_id and str(alvo_channel_id).isdigit():
            try:
                canal = client.get_channel(int(alvo_channel_id))
                if not canal:
                    canal = await client.fetch_channel(int(alvo_channel_id))
            except Exception as e:
                logger.warning("Canal de digest %s inacessível: %s", alvo_channel_id, e)

        # Fallback para DM se não encontrou o canal
        usuario_discord = None
        if not canal and user_str.isdigit():
            try:
                usuario_discord = client.get_user(int(user_str)) or await client.fetch_user(int(user_str))
            except Exception as e:
                logger.warning("Falha ao obter usuário %s para DM de digest: %s", user_str, e)

        destino = canal or usuario_discord
        if not destino:
            # Registra para evitar loop contínuo de tentativas com usuário inválido
            registrar_envio_digest(user_str, hoje_iso)
            return {"sucesso": False, "mensagem": "Não foi possível localizar canal ou usuário para entrega do resumo."}

        # 4. Despacho Multimodal (Texto / Áudio / Ambos conforme preferência do usuário)
        modo_resposta = obter_modo_resposta(user_str)
        chunks = dividir_mensagem(texto_resumo, limite=1900)

        from message_gateway import message_gateway, MessagePriority

        if modo_resposta == "texto":
            for chunk in chunks:
                await message_gateway.dispatch(destino, content=chunk, priority=MessagePriority.BACKGROUND)

        elif modo_resposta == "audio":
            caminho_audio, erro_tts = await sintetizar_fala_edge(texto_resumo)
            if caminho_audio and caminho_audio.exists():
                await message_gateway.dispatch(
                    destino,
                    content="🎙️ **Seu Resumo Matinal em Áudio (Francisca):**",
                    file=discord.File(str(caminho_audio), filename="resumo_matinal.mp3"),
                    priority=MessagePriority.BACKGROUND,
                )
            else:
                for chunk in chunks:
                    await message_gateway.dispatch(destino, content=chunk, priority=MessagePriority.BACKGROUND)

        elif modo_resposta == "ambos":
            for chunk in chunks:
                await message_gateway.dispatch(destino, content=chunk, priority=MessagePriority.BACKGROUND)

            caminho_audio, erro_tts = await sintetizar_fala_edge(texto_resumo)
            if caminho_audio and caminho_audio.exists():
                await message_gateway.dispatch(
                    destino,
                    content="🎙️ **Narração em Áudio do seu Resumo Matinal:**",
                    file=discord.File(str(caminho_audio), filename="resumo_matinal.mp3"),
                    priority=MessagePriority.BACKGROUND,
                )

        # Atualiza a data do último envio no banco para confirmar a entrega
        registrar_envio_digest(user_str, hoje_iso)
        logger.info("Resumo matinal entregue com sucesso para usuário %s (Modo: %s)", user_str, modo_resposta)
        return {"sucesso": True, "texto": texto_resumo, "modo": modo_resposta}

    finally:
        # Remove a trava em memória
        _digests_em_andamento.discard(user_str)
        # REGRA CRÍTICA: Apaga arquivo temporário de áudio gerado
        if caminho_audio and caminho_audio.exists():
            try:
                caminho_audio.unlink()
                logger.info("Áudio temporário de resumo matinal removido: %s", caminho_audio)
            except Exception:
                pass


async def iniciar_worker_digest(client: discord.Client, intervalo_segundos: int = 30) -> None:
    """Loop assíncrono perpétuo que monitora e despacha resumos matinais nos horários agendados."""
    logger.info("☀️ Worker de Resumo Matinal iniciado (verificação a cada %ds).", intervalo_segundos)
    await client.wait_until_ready()

    while not client.is_closed():
        try:
            tz = zoneinfo.ZoneInfo(CALENDAR_DEFAULT_TIMEZONE)
            agora = datetime.now(tz)
            hora_atual = agora.strftime("%H:%M")
            data_atual = agora.strftime("%Y-%m-%d")

            # Consulta todos os usuários com digest ativo
            with _get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT user_id, time, channel_id, city, last_sent_date 
                    FROM user_digest_settings 
                    WHERE enabled = 1
                    """
                )
                usuarios_digest = cursor.fetchall()

            for row in usuarios_digest:
                uid, d_time, ch_id, d_city, last_date = row
                uid_str = str(uid)
                # Dispara se for o horário programado, ainda não enviado hoje e não estiver rodando agora
                if d_time == hora_atual and last_date != data_atual and uid_str not in _digests_em_andamento:
                    logger.info("Disparando Resumo Matinal agendado das %s para usuário %s...", hora_atual, uid_str)
                    # Reserva a data imediatamente e marca em andamento para evitar concorrência
                    _digests_em_andamento.add(uid_str)
                    registrar_envio_digest(uid_str, data_atual)
                    asyncio.create_task(
                        enviar_resumo_matinal(client, uid_str, channel_id=ch_id, forcar=True)
                    )

        except Exception as e:
            logger.error("Erro no ciclo do worker de resumo matinal: %s", e, exc_info=True)

        await asyncio.sleep(intervalo_segundos)
