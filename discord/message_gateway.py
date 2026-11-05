"""
Módulo de Barramento Centralizado de Mensagens, Fila Outbox e Controle Anti-Spam (Unified Message Gateway).

Implementa a especificação IDEA-24:
1. Canal único de envio de mensagens e arquivos para o Discord.
2. Fila assíncrona Dual-Tier:
   - Prioridade 1 (Alta/Interativa): Fast-Path com latência < 100ms para chat e comandos.
   - Prioridade 2 (Baixa/Background): Leaky Bucket cadenciado (1.5s) para resumos, lembretes e alertas.
3. Deduplicação com janela deslizante e hash SHA-256 (60s) para impedir repetições idênticas.
4. Circuit Breaker Global por canal contra rajadas anômalas (> 8 msgs/10s).
5. Persistência de auditoria e resiliência em SQLite (outbox_queue).
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from enum import IntEnum
import hashlib
import logging
from pathlib import Path
import time
from typing import Any, Dict, List, Optional, Union
import uuid

import discord
from config import (
    GATEWAY_CIRCUIT_BREAKER_COOLDOWN_SEC,
    GATEWAY_CIRCUIT_BREAKER_MAX_MSGS,
    GATEWAY_DEBOUNCE_WINDOW_SEC,
    GATEWAY_LEAKY_BUCKET_INTERVAL_SEC,
    GATEWAY_PERSISTENCE_ENABLED,
    MESSAGE_GATEWAY_ENABLED,
)
from database import _get_connection

logger = logging.getLogger(__name__)


class MessagePriority(IntEnum):
    """Níveis de prioridade para despacho no Message Gateway."""
    HIGH = 1       # Interações diretas, comandos, conversas de chat do usuário
    BACKGROUND = 2 # Resumo matinal, lembretes, alertas de preço, webhooks


@dataclass(order=True)
class OutboxItem:
    """Item a ser despachado na fila prioritária do Outbox."""
    priority: int
    timestamp: float
    msg_id: str = field(compare=False)
    target: Any = field(compare=False)
    channel_id: str = field(compare=False)
    content: Optional[str] = field(default=None, compare=False)
    embed: Optional[discord.Embed] = field(default=None, compare=False)
    file: Optional[discord.File] = field(default=None, compare=False)
    files: Optional[List[discord.File]] = field(default=None, compare=False)
    view: Optional[discord.ui.View] = field(default=None, compare=False)
    content_hash: str = field(default="", compare=False)


class MessageGateway:
    """Barramento centralizado de despacho com proteção anti-spam e controle de vazão."""

    def __init__(self):
        self.enabled = MESSAGE_GATEWAY_ENABLED
        self.leaky_interval = GATEWAY_LEAKY_BUCKET_INTERVAL_SEC
        self.debounce_window = GATEWAY_DEBOUNCE_WINDOW_SEC
        self.max_burst_msgs = GATEWAY_CIRCUIT_BREAKER_MAX_MSGS
        self.breaker_cooldown = GATEWAY_CIRCUIT_BREAKER_COOLDOWN_SEC
        self.persistence_enabled = GATEWAY_PERSISTENCE_ENABLED

        # Fila prioritária assíncrona
        self._queue: asyncio.PriorityQueue[OutboxItem] = asyncio.PriorityQueue()
        self._worker_task: Optional[asyncio.Task] = None
        self._is_paused: bool = False

        # Cache de deduplicação: {f"{channel_id}:{hash}": timestamp}
        self._dedup_cache: Dict[str, float] = {}

        # Histórico de envios para Circuit Breaker: {channel_id: [timestamps]}
        self._send_history: Dict[str, List[float]] = {}
        # Estado do Circuit Breaker por canal: {channel_id: trip_timestamp}
        self._circuit_breakers: Dict[str, float] = {}

        # Rastreamento de último envio por canal para Leaky Bucket
        self._last_send_per_channel: Dict[str, float] = {}

        # Métricas
        self.stats = {
            "total_dispatched": 0,
            "fast_path_sent": 0,
            "queued_sent": 0,
            "duplicates_dropped": 0,
            "circuit_breaker_trips": 0,
            "failed_dispatches": 0,
        }

        # Inicializa tabela SQLite
        if self.persistence_enabled:
            self._init_db()

    def _init_db(self) -> None:
        """Cria tabela SQLite para fila e auditoria outbox."""
        try:
            with _get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS outbox_queue (
                        id TEXT PRIMARY KEY,
                        channel_id TEXT NOT NULL,
                        priority INTEGER NOT NULL DEFAULT 2,
                        content_sample TEXT,
                        content_hash TEXT NOT NULL,
                        status TEXT NOT NULL DEFAULT 'sent',
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )
                conn.commit()
        except Exception as e:
            logger.warning("Falha ao inicializar tabela outbox_queue no SQLite: %s", e)

    def _record_audit(self, msg_id: str, channel_id: str, priority: int, content: Optional[str], c_hash: str, status: str = "sent") -> None:
        """Registra mensagem despachada para fins de auditoria e persistência."""
        if not self.persistence_enabled:
            return
        try:
            with _get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO outbox_queue (id, channel_id, priority, content_sample, content_hash, status)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET status = excluded.status
                    """,
                    (msg_id, str(channel_id), priority, (content or "")[:200], c_hash, status)
                )
                conn.commit()
        except Exception as e:
            logger.debug("Não foi possível persistir auditoria outbox: %s", e)

    def _generate_hash(self, channel_id: str, content: Optional[str], file: Optional[discord.File], files: Optional[List[discord.File]]) -> str:
        """Calcula hash SHA-256 do conteúdo da mensagem para deduplicação."""
        h = hashlib.sha256()
        h.update(str(channel_id).encode("utf-8"))
        if content:
            h.update(content.strip().encode("utf-8"))
        if file and hasattr(file, "filename"):
            h.update(file.filename.encode("utf-8"))
        if files:
            for f in files:
                if hasattr(f, "filename"):
                    h.update(f.filename.encode("utf-8"))
        return h.hexdigest()

    def _is_duplicate(self, channel_id: str, c_hash: str) -> bool:
        """Verifica se mensagem idêntica foi enviada para o mesmo canal na janela de debounce."""
        key = f"{channel_id}:{c_hash}"
        now = time.time()
        last_time = self._dedup_cache.get(key)
        if last_time and (now - last_time) < self.debounce_window:
            return True

        # Registra hash e limpa chaves expiradas
        self._dedup_cache[key] = now
        # Limpeza periódica leve
        if len(self._dedup_cache) > 200:
            self._dedup_cache = {
                k: v for k, v in self._dedup_cache.items() if (now - v) < self.debounce_window
            }
        return False

    def _check_circuit_breaker(self, channel_id: str) -> bool:
        """Retorna True se o Circuit Breaker estiver ABERTO (bloqueando rajadas)."""
        now = time.time()
        trip_time = self._circuit_breakers.get(channel_id)
        if trip_time:
            if (now - trip_time) < self.breaker_cooldown:
                return True
            else:
                # Cooldown encerrado, restabelece para HALF-OPEN/CLOSED
                del self._circuit_breakers[channel_id]
                logger.info("🟢 Circuit Breaker fechado para canal %s (tráfego normalizado).", channel_id)

        # Atualiza histórico de envios
        history = self._send_history.setdefault(channel_id, [])
        history.append(now)
        # Mantém apenas envios dos últimos 10 segundos
        self._send_history[channel_id] = [t for t in history if (now - t) <= 10.0]

        # Verifica se estourou a cota de rajada
        if len(self._send_history[channel_id]) > self.max_burst_msgs:
            self._circuit_breakers[channel_id] = now
            self.stats["circuit_breaker_trips"] += 1
            logger.critical(
                "🚨 CIRCUIT BREAKER DISPARADO para canal %s: %d mensagens em 10s! Represando envios.",
                channel_id,
                len(self._send_history[channel_id]),
            )
            return True

        return False

    async def _send_raw(self, target: Any, content: Optional[str] = None, embed: Optional[discord.Embed] = None, file: Optional[discord.File] = None, files: Optional[List[discord.File]] = None, view: Optional[discord.ui.View] = None) -> Any:
        """Executa a chamada física de envio ao Discord."""
        kwargs: Dict[str, Any] = {}
        if content is not None:
            kwargs["content"] = content
        if embed is not None:
            kwargs["embed"] = embed
        if file is not None:
            kwargs["file"] = file
        if files is not None:
            kwargs["files"] = files
        if view is not None:
            kwargs["view"] = view

        if hasattr(target, "send"):
            return await target.send(**kwargs)
        raise ValueError(f"Objeto de destino '{target}' não suporta método send().")

    async def dispatch(
        self,
        target: Any,
        content: Optional[str] = None,
        embed: Optional[discord.Embed] = None,
        file: Optional[discord.File] = None,
        files: Optional[List[discord.File]] = None,
        view: Optional[discord.ui.View] = None,
        priority: MessagePriority = MessagePriority.HIGH,
        forcar_dedup: bool = False,
    ) -> Optional[Any]:
        """
        Ponto único de despacho de mensagens do bot.
        
        - Prioridade 1 (HIGH): Envio direto e ultrarrápido (Fast-Path < 100ms) se canal ocioso.
        - Prioridade 2 (BACKGROUND): Enfileirado para envio cadenciado via Leaky Bucket.
        """
        if not self.enabled:
            # Bypass de emergência caso o gateway seja desativado em config
            return await self._send_raw(target, content, embed, file, files, view)

        channel_id = str(getattr(target, "id", "global"))
        c_hash = self._generate_hash(channel_id, content, file, files)
        msg_id = str(uuid.uuid4())

        # 1. Guarda Anti-Spam: Deduplicação por SHA-256
        if not forcar_dedup and self._is_duplicate(channel_id, c_hash):
            self.stats["duplicates_dropped"] += 1
            logger.warning(
                "🛡️ [ANTI-SPAM GATEWAY] Mensagem duplicada descartada para canal %s (hash: %s...).",
                channel_id,
                c_hash[:8],
            )
            self._record_audit(msg_id, channel_id, int(priority), content, c_hash, status="discarded_duplicate")
            return None

        # 2. Verificação de Circuit Breaker
        is_breaker_open = self._check_circuit_breaker(channel_id)

        # 3. FAST-PATH: Prioridade 1 (Interativa) sem carga e sem Circuit Breaker
        now = time.time()
        time_since_last = now - self._last_send_per_channel.get(channel_id, 0.0)

        if priority == MessagePriority.HIGH and not is_breaker_open and time_since_last >= 0.2:
            try:
                sent_msg = await self._send_raw(target, content, embed, file, files, view)
                self._last_send_per_channel[channel_id] = time.time()
                self.stats["total_dispatched"] += 1
                self.stats["fast_path_sent"] += 1
                self._record_audit(msg_id, channel_id, int(priority), content, c_hash, status="sent_fastpath")
                return sent_msg
            except discord.HTTPException as err:
                if err.status == 429:
                    logger.warning("Rate limit 429 no Fast-Path. Re-enfileirando para Leaky Bucket...")
                else:
                    logger.error("Erro no Fast-Path do Message Gateway: %s", err)
                    self.stats["failed_dispatches"] += 1
                    return None

        # 4. Enfileiramento na Fila Prioritária (Leaky Bucket)
        item = OutboxItem(
            priority=int(priority),
            timestamp=now,
            msg_id=msg_id,
            target=target,
            channel_id=channel_id,
            content=content,
            embed=embed,
            file=file,
            files=files,
            view=view,
            content_hash=c_hash,
        )
        await self._queue.put(item)
        self._record_audit(msg_id, channel_id, int(priority), content, c_hash, status="enqueued")
        logger.debug("Mensagem %s enfileirada no Outbox (Prioridade %d, Canal %s).", msg_id[:8], priority, channel_id)
        return None

    async def _worker_loop(self) -> None:
        """Loop permanente que processa a fila de saída com cadência controlada."""
        logger.info("🚀 Worker do Message Gateway (Outbox Dispatcher) iniciado com sucesso.")
        while True:
            try:
                item = await self._queue.get()

                # Se estiver pausado, aguarda antes de processar
                while self._is_paused:
                    await asyncio.sleep(1.0)

                channel_id = item.channel_id
                now = time.time()

                # Leaky Bucket: garante intervalo mínimo por canal
                last_send = self._last_send_per_channel.get(channel_id, 0.0)
                elapsed = now - last_send
                if elapsed < self.leaky_interval:
                    wait_time = self.leaky_interval - elapsed
                    await asyncio.sleep(wait_time)

                # Se o Circuit Breaker estiver aberto para este canal e for Prioridade Baixa, descarta ou atrasa
                if self._circuit_breakers.get(channel_id) and item.priority > 1:
                    logger.warning("Circuit Breaker ativo para %s. Descartando mensagem de background %s.", channel_id, item.msg_id[:8])
                    self._record_audit(item.msg_id, channel_id, item.priority, item.content, item.content_hash, status="circuit_breaker_drop")
                    self._queue.task_done()
                    continue

                try:
                    await self._send_raw(
                        item.target,
                        content=item.content,
                        embed=item.embed,
                        file=item.file,
                        files=item.files,
                        view=item.view,
                    )
                    self._last_send_per_channel[channel_id] = time.time()
                    self.stats["total_dispatched"] += 1
                    self.stats["queued_sent"] += 1
                    self._record_audit(item.msg_id, channel_id, item.priority, item.content, item.content_hash, status="sent_queued")
                except discord.HTTPException as err:
                    if err.status == 429:
                        retry_after = getattr(err, "retry_after", 1.0)
                        logger.warning("HTTP 429 Rate Limit detectado. Pausando despacho por %.2fs...", retry_after)
                        await asyncio.sleep(retry_after)
                        # Reinsere com prioridade elevada
                        await self._queue.put(item)
                    else:
                        logger.error("Falha ao despachar mensagem %s da fila: %s", item.msg_id[:8], err)
                        self.stats["failed_dispatches"] += 1
                except Exception as err:
                    logger.error("Erro inesperado ao despachar item %s: %s", item.msg_id[:8], err)
                    self.stats["failed_dispatches"] += 1

                self._queue.task_done()

            except asyncio.CancelledError:
                logger.info("Worker do Message Gateway cancelado.")
                break
            except Exception as e:
                logger.error("Exceção não tratada no loop do Message Gateway: %s", e, exc_info=True)
                await asyncio.sleep(1.0)

    def start_worker(self, client: Optional[Any] = None) -> asyncio.Task:
        """Inicia a tarefa assíncrona consumidora da fila de saída."""
        if self._worker_task is None or self._worker_task.done():
            self._worker_task = asyncio.create_task(self._worker_loop())
        return self._worker_task

    def pause(self) -> None:
        """Pausa o envio de mensagens da fila."""
        self._is_paused = True
        logger.info("⏸️ Message Gateway pausado.")

    def resume(self) -> None:
        """Retoma o envio de mensagens da fila."""
        self._is_paused = False
        logger.info("▶️ Message Gateway retomado.")

    def clear(self) -> int:
        """Purga todas as mensagens pendentes na fila."""
        count = self._queue.qsize()
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
                self._queue.task_done()
            except Exception:
                break
        logger.info("🧹 Message Gateway limpo (%d itens descartados).", count)
        return count

    def get_status(self) -> Dict[str, Any]:
        """Retorna telemetria de funcionamento do barramento."""
        return {
            "enabled": self.enabled,
            "paused": self._is_paused,
            "queue_size": self._queue.qsize(),
            "active_circuit_breakers": len(self._circuit_breakers),
            "stats": self.stats,
            "leaky_interval_sec": self.leaky_interval,
            "debounce_window_sec": self.debounce_window,
        }


# Instância global singleton do Gateway de Mensagens
message_gateway = MessageGateway()
