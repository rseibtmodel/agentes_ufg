"""
Gerenciador do Radar Autônomo de RSS, ArXiv & GitHub (IDEA-29).

Monitora proativamente feeds técnicos (Releases do GitHub via .atom, papers
do ArXiv via API OAI/Atom e feeds RSS padrão), executa filtragem em 2 etapas
(Regex preliminar de keywords seguido de síntese via LLM) e despacha resumos
estruturados em tempo real ou em boletins consolidados nos canais do Discord.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
import hashlib
import logging
from pathlib import Path
import re
import sqlite3
import time
from typing import Any, Dict, List, Optional, Tuple
import xml.etree.ElementTree as ET

import aiohttp

from config import DB_FILE
from context_manager import set_current_origin_type
from message_gateway import message_gateway, MessagePriority

logger = logging.getLogger(__name__)


@dataclass
class FeedItem:
    """Item extraído de um feed RSS ou Atom."""
    item_id: str
    title: str
    link: str
    published: str
    summary: str


@dataclass
class RadarSubscription:
    """Assinatura de monitoramento de feed no banco de dados."""
    id: int
    user_id: str
    channel_id: str
    source_type: str  # 'GITHUB', 'ARXIV', 'RSS'
    source_url: str
    keywords_regex: Optional[str]
    mode: str  # 'REALTIME' ou 'DIGEST'
    digest_time: str
    etag: Optional[str]
    last_modified: Optional[str]
    next_run_at: str
    ativo: bool
    created_at: str


def _get_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    caminho = db_path or DB_FILE
    parent = Path(caminho).parent
    if parent and not parent.exists():
        parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(str(caminho), timeout=30.0)


def init_radar_db(db_path: Optional[str] = None) -> None:
    """Inicializa as tabelas do Radar no SQLite WAL."""
    with _get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA journal_mode = WAL;")
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS radar_subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                channel_id TEXT NOT NULL,
                source_type TEXT NOT NULL,
                source_url TEXT NOT NULL,
                keywords_regex TEXT,
                mode TEXT NOT NULL DEFAULT 'DIGEST',
                digest_time TEXT DEFAULT '18:00',
                etag TEXT,
                last_modified TEXT,
                next_run_at TIMESTAMP NOT NULL,
                ativo INTEGER NOT NULL DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS radar_seen_items (
                item_hash TEXT PRIMARY KEY,
                subscription_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                link TEXT NOT NULL,
                processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (subscription_id) REFERENCES radar_subscriptions(id) ON DELETE CASCADE
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS radar_digest_buffer (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subscription_id INTEGER NOT NULL,
                channel_id TEXT NOT NULL,
                title TEXT NOT NULL,
                link TEXT NOT NULL,
                summary TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_radar_next_run ON radar_subscriptions(next_run_at, ativo);"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_radar_seen_sub ON radar_seen_items(subscription_id);"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_radar_digest_chan ON radar_digest_buffer(channel_id);"
        )
        conn.commit()


def normalizar_url_fonte(url_ou_chave: str) -> Tuple[str, str]:
    """Identifica o tipo de fonte (GITHUB, ARXIV ou RSS) e gera a URL normalizada."""
    alvo = url_ou_chave.strip()

    # Padrão GitHub: 'github.com/dono/repo' ou 'dono/repo'
    gh_match = re.search(r"(?:https?://)?(?:www\.)?github\.com/([\w.-]+)/([\w.-]+)", alvo, re.IGNORECASE)
    if gh_match:
        dono, repo = gh_match.groups()
        # Feed Atom nativo do GitHub (sem necessidade de token ou API REST)
        return "GITHUB", f"https://github.com/{dono}/{repo}/releases.atom"

    if "/" in alvo and not alvo.startswith("http") and not alvo.startswith("arxiv"):
        partes = alvo.split("/")
        if len(partes) == 2 and partes[0] and partes[1]:
            return "GITHUB", f"https://github.com/{partes[0]}/{partes[1]}/releases.atom"

    # Padrão ArXiv: 'arxiv:cs.AI' ou categoria direta
    if alvo.lower().startswith("arxiv:") or "arxiv.org" in alvo.lower():
        cat = alvo.split(":")[-1].strip() if "arxiv:" in alvo.lower() else "cs.AI"
        url_arxiv = f"http://export.arxiv.org/api/query?search_query=cat:{cat}&max_results=15&sortBy=submittedDate&sortOrder=descending"
        return "ARXIV", url_arxiv

    return "RSS", alvo


def fazer_parse_xml_feed(xml_bytes: bytes) -> List[FeedItem]:
    """Faz o parse determinístico de feeds XML (Atom 1.0 ou RSS 2.0) sem dependências externas."""
    itens: List[FeedItem] = []
    if not xml_bytes or not xml_bytes.strip():
        return itens

    try:
        root = ET.fromstring(xml_bytes)
    except Exception as e:
        logger.warning("[RadarManager] Erro no parsing XML do feed: %s", e)
        return itens

    # Remove namespaces para facilitar as buscas
    tag_raiz = root.tag.lower()

    # 1. Parsing de Atom (usado por GitHub Releases e ArXiv)
    if "feed" in tag_raiz:
        # Extrai namespace se existir
        ns_match = re.match(r"\{.*\}", root.tag)
        ns = ns_match.group(0) if ns_match else ""

        for entry in root.findall(f"{ns}entry"):
            title_elem = entry.find(f"{ns}title")
            title = title_elem.text.strip() if title_elem is not None and title_elem.text else "Sem título"

            id_elem = entry.find(f"{ns}id")
            item_id = id_elem.text.strip() if id_elem is not None and id_elem.text else title

            # Busca link (pode ter rel='alternate' ou href direto)
            link = ""
            for l_elem in entry.findall(f"{ns}link"):
                href = l_elem.get("href")
                if href:
                    link = href
                    break

            pub_elem = entry.find(f"{ns}updated")
            if pub_elem is None:
                pub_elem = entry.find(f"{ns}published")
            pub_date = pub_elem.text.strip() if pub_elem is not None and pub_elem.text else ""

            summary_elem = entry.find(f"{ns}summary")
            if summary_elem is None:
                summary_elem = entry.find(f"{ns}content")
            summary = summary_elem.text.strip() if summary_elem is not None and summary_elem.text else ""

            # Remove eventuais tags HTML básicas do resumo
            summary_clean = re.sub(r"<[^>]+>", "", summary).strip()

            itens.append(
                FeedItem(
                    item_id=item_id,
                    title=title,
                    link=link,
                    published=pub_date,
                    summary=summary_clean[:1000],
                )
            )
        return itens

    # 2. Parsing de RSS 2.0 (padrão <rss><channel><item>)
    channel = root.find("channel")
    if channel is None:
        channel = root
    for item in channel.findall("item"):
        title_elem = item.find("title")
        title = title_elem.text.strip() if title_elem is not None and title_elem.text else "Sem título"

        link_elem = item.find("link")
        link = link_elem.text.strip() if link_elem is not None and link_elem.text else ""

        guid_elem = item.find("guid")
        item_id = guid_elem.text.strip() if guid_elem is not None and guid_elem.text else (link or title)

        pub_elem = item.find("pubDate")
        pub_date = pub_elem.text.strip() if pub_elem is not None and pub_elem.text else ""

        desc_elem = item.find("description")
        desc = desc_elem.text.strip() if desc_elem is not None and desc_elem.text else ""
        desc_clean = re.sub(r"<[^>]+>", "", desc).strip()

        itens.append(
            FeedItem(
                item_id=item_id,
                title=title,
                link=link,
                published=pub_date,
                summary=desc_clean[:1000],
            )
        )

    return itens


class RadarManager:
    """Orquestrador assíncrono de feeds técnicos e curadoria automática."""

    def __init__(self, db_path: Optional[str] = None) -> None:
        self.db_path = db_path
        self._semaphore = asyncio.Semaphore(2)
        self._poller_task: Optional[asyncio.Task] = None
        self._running = False

    async def iniciar_poller(self) -> None:
        """Inicia a tarefa contínua de checagem de feeds e envio de boletins."""
        if self._running:
            return
        self._running = True
        self._poller_task = asyncio.create_task(self._loop_poller())
        logger.info("[RadarManager] Poller assíncrono de feeds inicializado.")

    async def parar_poller(self) -> None:
        """Para a tarefa contínua do radar."""
        self._running = False
        if self._poller_task and not self._poller_task.done():
            self._poller_task.cancel()
            try:
                await self._poller_task
            except asyncio.CancelledError:
                pass
        logger.info("[RadarManager] Poller de feeds finalizado.")

    async def _loop_poller(self) -> None:
        """Loop que acorda a cada 60 segundos para processar feeds agendados e boletins."""
        while self._running:
            try:
                await self.processar_ciclo_agendado()
                await self.verificar_envio_boletins()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("[RadarManager] Erro no ciclo do poller: %s", e)

            try:
                await asyncio.sleep(60.0)
            except asyncio.CancelledError:
                break

    def criar_assinatura(
        self,
        user_id: str | int,
        channel_id: str | int,
        url_ou_chave: str,
        keywords_regex: Optional[str] = None,
        mode: str = "DIGEST",
        digest_time: str = "18:00",
    ) -> Dict[str, Any]:
        """Cria ou atualiza uma assinatura de monitoramento no banco."""
        source_type, source_url = normalizar_url_fonte(url_ou_chave)
        u_str = str(user_id)
        c_str = str(channel_id)
        modo_final = "REALTIME" if mode.upper() in ("REALTIME", "TEMPO_REAL", "TEMPO-REAL") else "DIGEST"

        with _get_connection(self.db_path) as conn:
            cursor = conn.cursor()
            # Próxima checagem imediata (now)
            now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute(
                """
                INSERT INTO radar_subscriptions (
                    user_id, channel_id, source_type, source_url,
                    keywords_regex, mode, digest_time, next_run_at, ativo
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
                """,
                (u_str, c_str, source_type, source_url, keywords_regex, modo_final, digest_time, now_str),
            )
            sub_id = cursor.lastrowid
            conn.commit()

        return {
            "id": sub_id,
            "source_type": source_type,
            "source_url": source_url,
            "keywords_regex": keywords_regex,
            "mode": modo_final,
            "digest_time": digest_time,
            "channel_id": c_str,
        }

    def listar_assinaturas(self, user_id: Optional[str | int] = None) -> List[Dict[str, Any]]:
        """Lista as assinaturas cadastradas."""
        with _get_connection(self.db_path) as conn:
            cursor = conn.cursor()
            if user_id:
                cursor.execute(
                    "SELECT id, user_id, channel_id, source_type, source_url, keywords_regex, mode, digest_time, next_run_at, ativo FROM radar_subscriptions WHERE user_id = ? ORDER BY id DESC",
                    (str(user_id),),
                )
            else:
                cursor.execute(
                    "SELECT id, user_id, channel_id, source_type, source_url, keywords_regex, mode, digest_time, next_run_at, ativo FROM radar_subscriptions ORDER BY id DESC"
                )
            rows = cursor.fetchall()

        subs = []
        for r in rows:
            subs.append({
                "id": r[0],
                "user_id": r[1],
                "channel_id": r[2],
                "source_type": r[3],
                "source_url": r[4],
                "keywords_regex": r[5],
                "mode": r[6],
                "digest_time": r[7],
                "next_run_at": r[8],
                "ativo": bool(r[9]),
            })
        return subs

    def remover_assinatura(self, sub_id: int) -> bool:
        """Remove uma assinatura pelo ID."""
        with _get_connection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM radar_subscriptions WHERE id = ?", (sub_id,))
            removido = cursor.rowcount > 0
            conn.commit()
        return removido

    async def processar_ciclo_agendado(self) -> int:
        """Busca todas as assinaturas vencidas e processa as novidades."""
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        with _get_connection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, user_id, channel_id, source_type, source_url, keywords_regex, mode, digest_time, etag, last_modified, next_run_at, ativo, created_at
                FROM radar_subscriptions
                WHERE next_run_at <= ? AND ativo = 1
                LIMIT 5
                """,
                (now_str,),
            )
            rows = cursor.fetchall()

        if not rows:
            return 0

        processados = 0
        for r in rows:
            sub = RadarSubscription(
                id=r[0], user_id=r[1], channel_id=r[2], source_type=r[3],
                source_url=r[4], keywords_regex=r[5], mode=r[6], digest_time=r[7],
                etag=r[8], last_modified=r[9], next_run_at=r[10], ativo=bool(r[11]),
                created_at=r[12]
            )
            try:
                await self._processar_assinatura(sub)
                processados += 1
            except Exception as e:
                logger.error("[RadarManager] Erro ao processar feed ID %d (%s): %s", sub.id, sub.source_url, e)

        return processados

    async def _processar_assinatura(self, sub: RadarSubscription) -> int:
        """Executa a coleta, desduplicação, regex e síntese de uma assinatura."""
        async with self._semaphore:
            headers = {
                "User-Agent": "Antigravity-Radar/1.0 (Discord Bot Assistant; Local-First)",
            }
            if sub.etag:
                headers["If-None-Match"] = sub.etag
            if sub.last_modified:
                headers["If-Modified-Since"] = sub.last_modified

            timeout = aiohttp.ClientTimeout(total=12.0)
            xml_bytes = b""
            novo_etag = sub.etag
            novo_last_mod = sub.last_modified

            try:
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.get(sub.source_url, headers=headers) as resp:
                        if resp.status == 304:
                            # Feed não foi modificado (economia de 100% de banda e processamento)
                            self._agendar_proxima_checagem(sub.id, minutos=30)
                            return 0

                        if resp.status != 200:
                            logger.warning("[RadarManager] Feed %s retornou HTTP %d", sub.source_url, resp.status)
                            self._agendar_proxima_checagem(sub.id, minutos=60)
                            return 0

                        xml_bytes = await resp.read()
                        novo_etag = resp.headers.get("ETag") or sub.etag
                        novo_last_mod = resp.headers.get("Last-Modified") or sub.last_modified
            except Exception as e_net:
                logger.warning("[RadarManager] Falha de conexão ao feed %s: %s", sub.source_url, e_net)
                self._agendar_proxima_checagem(sub.id, minutos=45)
                return 0

            # Atualiza ETag / Last-Modified
            self._atualizar_cache_http(sub.id, novo_etag, novo_last_mod)

            # Parse dos itens do XML
            itens = await asyncio.to_thread(fazer_parse_xml_feed, xml_bytes)
            if not itens:
                self._agendar_proxima_checagem(sub.id, minutos=30)
                return 0

            novos_itens_count = 0
            for item in itens:
                processou = await self._processar_item(sub, item)
                if processou:
                    novos_itens_count += 1

            self._agendar_proxima_checagem(sub.id, minutos=30)
            return novos_itens_count

    async def _processar_item(self, sub: RadarSubscription, item: FeedItem) -> bool:
        """Processa um item individual com desduplicação por hash, regex preliminar e síntese LLM."""
        # Gera hash determinístico para desduplicação no SQLite
        hash_id = hashlib.sha256(f"{sub.source_url}:{item.item_id}".encode()).hexdigest()
        if self._ja_processado(hash_id):
            return False

        # Marca como visto para nunca reprocessar
        self._marcar_como_visto(hash_id, sub.id, item.title, item.link)

        # -------------------------------------------------------------
        # ETAPA 1: FILTRAGEM DETERMINÍSTICA POR REGEX DE KEYWORDS (CUSTO ZERO)
        # -------------------------------------------------------------
        if sub.keywords_regex and sub.keywords_regex.strip():
            texto_busca = f"{item.title} {item.summary}"
            try:
                if not re.search(sub.keywords_regex.strip(), texto_busca, re.IGNORECASE):
                    return False
            except re.error as e_regex:
                logger.warning("[RadarManager] Regex inválido '%s': %s", sub.keywords_regex, e_regex)

        # -------------------------------------------------------------
        # ETAPA 2: SÍNTESE CONCISA DE IMPACTO TÉCNICO VIA LLM
        # -------------------------------------------------------------
        resumo_impacto = await self._sintetizar_impacto_llm(sub.source_type, item)

        if sub.mode == "REALTIME":
            await self._despachar_tempo_real(sub.channel_id, sub.source_type, item, resumo_impacto)
        else:
            self._bufferizar_digest(sub.id, sub.channel_id, item.title, item.link, resumo_impacto)

        return True

    def _ja_processado(self, item_hash: str) -> bool:
        with _get_connection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM radar_seen_items WHERE item_hash = ?", (item_hash,))
            return cursor.fetchone() is not None

    def _marcar_como_visto(self, item_hash: str, sub_id: int, title: str, link: str) -> None:
        with _get_connection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR IGNORE INTO radar_seen_items (item_hash, subscription_id, title, link) VALUES (?, ?, ?, ?)",
                (item_hash, sub_id, title, link),
            )
            conn.commit()

    def _atualizar_cache_http(self, sub_id: int, etag: Optional[str], last_modified: Optional[str]) -> None:
        with _get_connection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE radar_subscriptions SET etag = ?, last_modified = ? WHERE id = ?",
                (etag, last_modified, sub_id),
            )
            conn.commit()

    def _agendar_proxima_checagem(self, sub_id: int, minutos: int = 30) -> None:
        proxima = datetime.now(timezone.utc) + timedelta(minutes=minutos)
        prox_str = proxima.strftime("%Y-%m-%d %H:%M:%S")
        with _get_connection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE radar_subscriptions SET next_run_at = ? WHERE id = ?",
                (prox_str, sub_id),
            )
            conn.commit()

    def _bufferizar_digest(self, sub_id: int, channel_id: str, title: str, link: str, summary: str) -> None:
        with _get_connection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO radar_digest_buffer (subscription_id, channel_id, title, link, summary) VALUES (?, ?, ?, ?, ?)",
                (sub_id, str(channel_id), title, link, summary),
            )
            conn.commit()

    async def _sintetizar_impacto_llm(self, source_type: str, item: FeedItem) -> str:
        """Gera síntese executiva do artigo/release via LLM operando sob contexto de background."""
        set_current_origin_type("BACKGROUND")
        from llm_client import llm_client

        prompt_sistema = (
            "Você é o Radar de Inteligência Técnica do assistente. Analise a novidade técnica abaixo e resuma "
            "em exatamente 2 a 3 bullet points curtos e densos, destacando o impacto prático e a relevância "
            "para desenvolvimento de software em Python e IA. Seja direto e objetivo. Não invente fatos."
        )
        prompt_user = f"Fonte: {source_type}\nTítulo: {item.title}\nConteúdo/Resumo: {item.summary}"

        try:
            resposta = await llm_client.gerar_resposta(
                mensagens=[
                    {"role": "system", "content": prompt_sistema},
                    {"role": "user", "content": prompt_user},
                ],
                temperatura=0.2,
                provider="local",  # Prioriza custo zero no LM Studio
                permitir_failover=True,
            )
            return resposta.strip()
        except Exception as e_llm:
            logger.warning("[RadarManager] Falha ao sintetizar com LLM, usando resumo original: %s", e_llm)
            return item.summary[:300] + ("..." if len(item.summary) > 300 else "")

    async def _despachar_tempo_real(self, channel_id: str, source_type: str, item: FeedItem, resumo: str) -> None:
        """Publica a novidade imediatamente no canal do Discord via outbox."""
        badge_icon = "🐙" if source_type == "GITHUB" else ("🔬" if source_type == "ARXIV" else "📡")
        linhas = [
            f"{badge_icon} **RADAR EM TEMPO REAL: {source_type}**",
            f"📌 **{item.title}**",
            f"🔗 <{item.link}>",
            "──────────────────────────────────────────────",
            f"💡 **Síntese de Impacto:**\n{resumo}",
        ]
        texto_final = "\n".join(linhas)
        await message_gateway.dispatch(
            channel=int(channel_id),
            content=texto_final,
            priority=MessagePriority.LOW,
        )

    def buscar_itens_radar(self, termo: Optional[str] = None, limite: int = 5) -> List[Dict[str, Any]]:
        """Busca itens capturados pelo radar filtrando por termo ou trazendo os mais recentes."""
        with _get_connection(self.db_path) as conn:
            cursor = conn.cursor()
            if termo:
                cursor.execute(
                    """
                    SELECT s.source_type, i.title, i.link, i.processed_at
                    FROM radar_seen_items i
                    JOIN radar_subscriptions s ON i.subscription_id = s.id
                    WHERE i.title LIKE ? OR i.link LIKE ?
                    ORDER BY i.processed_at DESC LIMIT ?
                    """,
                    (f"%{termo}%", f"%{termo}%", limite),
                )
            else:
                cursor.execute(
                    """
                    SELECT s.source_type, i.title, i.link, i.processed_at
                    FROM radar_seen_items i
                    JOIN radar_subscriptions s ON i.subscription_id = s.id
                    ORDER BY i.processed_at DESC LIMIT ?
                    """,
                    (limite,),
                )
            rows = cursor.fetchall()
            return [
                {"fonte": r[0], "titulo": r[1], "link": r[2], "processado_em": r[3]}
                for r in rows
            ]

    async def verificar_envio_boletins(self) -> int:
        """Verifica se há boletins acumulados prontos para envio no horário estipulado."""
        agora_hora = datetime.now().strftime("%H:%M")
        with _get_connection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT DISTINCT channel_id
                FROM radar_subscriptions
                WHERE mode = 'DIGEST' AND digest_time = ? AND ativo = 1
                """,
                (agora_hora,),
            )
            canais = [r[0] for r in cursor.fetchall()]

        if not canais:
            return 0

        boletins_enviados = 0
        for cid in canais:
            enviou = await self.enviar_boletim_canal(cid)
            if enviou:
                boletins_enviados += 1
        return boletins_enviados

    async def enviar_boletim_canal(self, channel_id: str | int) -> bool:
        """Compila e envia os itens acumulados no buffer para um canal específico."""
        c_str = str(channel_id)
        with _get_connection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, title, link, summary FROM radar_digest_buffer WHERE channel_id = ? ORDER BY id ASC LIMIT 8",
                (c_str,),
            )
            rows = cursor.fetchall()
            if not rows:
                return False

            ids_buffer = [r[0] for r in rows]
            cursor.execute(
                f"DELETE FROM radar_digest_buffer WHERE id IN ({','.join('?' for _ in ids_buffer)})",
                tuple(ids_buffer),
            )
            conn.commit()

        linhas = [
            f"📰 **BOLETIM TÉCNICO DO RADAR ({datetime.now().strftime('%d/%m/%Y')})**",
            f"Foram identificados **{len(rows)}** novos destaques curados para este canal:",
            "──────────────────────────────────────────────",
        ]
        for idx, (_, title, link, summary) in enumerate(rows, start=1):
            linhas.append(f"**{idx}. [{title}]({link})**\n{summary}\n")
        linhas.append("──────────────────────────────────────────────")
        linhas.append("💡 *Curadoria autônoma do Radar de Inteligência Técnica.*")

        await message_gateway.dispatch(
            channel=int(c_str),
            content="\n".join(linhas),
            priority=MessagePriority.LOW,
        )
        return True


# Instância global singleton
radar_manager = RadarManager()
