"""
Módulo de FinOps, Telemetria de Tokens e Observabilidade de Custos LLM (IDEA-28).

Rastreia e audita chamadas de inferência de IA, contabilizando tokens de entrada,
saída, latência, provedor utilizado e custo financeiro estimado. Oferece controle
de cotas diárias com fallback transparente para o nó LM Studio local.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import logging
from pathlib import Path
import sqlite3
import time
from typing import Any, Dict, List, Optional, Tuple

from config import DB_FILE

logger = logging.getLogger(__name__)

# Preços de referência por 1 milhão de tokens (USD)
PRECOS_MODELOS_1M: Dict[str, Dict[str, float]] = {
    "gemini-1.5-flash": {"input": 0.075, "output": 0.30},
    "gemini-2.0-flash": {"input": 0.10, "output": 0.40},
    "gemini-1.5-pro": {"input": 1.25, "output": 5.00},
    "gemini-2.0-pro": {"input": 1.25, "output": 5.00},
    "gemini-flash": {"input": 0.075, "output": 0.30},
    "gemini-pro": {"input": 1.25, "output": 5.00},
}

# Preço padrão para modelos desconhecidos na nuvem (equivalente ao Gemini Flash)
PRECO_PADRAO_CLOUD = {"input": 0.075, "output": 0.30}

# Cotação base estimada USD -> BRL para relatórios em moeda local
TAXA_CAMBIO_BRL = 5.80

# Cotas diárias padrão de tokens
COTA_DIARIA_USUARIO_PADRAO = 200_000
COTA_DIARIA_BACKGROUND_PADRAO = 500_000


@dataclass
class TokenLogEntry:
    """Entrada estruturada de telemetria de uso de tokens."""
    user_id: str
    channel_id: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    latency_ms: int
    cost_usd: float
    is_local: bool
    origin_type: str = "INTERACTIVE"  # "INTERACTIVE" ou "BACKGROUND"
    is_fallback: bool = False
    created_at: Optional[str] = None


def calcular_custo_tokens(
    model_name: str,
    prompt_tokens: int,
    completion_tokens: int,
    is_local: bool = False,
) -> float:
    """Calcula o custo financeiro estimado em dólares para a chamada."""
    if is_local or not model_name:
        return 0.0

    nome_normalizado = model_name.lower().strip()
    precos = PRECO_PADRAO_CLOUD
    for chave, tabela in PRECOS_MODELOS_1M.items():
        if chave in nome_normalizado:
            precos = tabela
            break

    custo_in = (prompt_tokens / 1_000_000.0) * precos["input"]
    custo_out = (completion_tokens / 1_000_000.0) * precos["output"]
    return round(custo_in + custo_out, 6)


def calcular_economia_local(prompt_tokens: int, completion_tokens: int) -> float:
    """Calcula quanto a inferência teria custado na nuvem (Gemini Flash) em USD."""
    return calcular_custo_tokens("gemini-flash", prompt_tokens, completion_tokens, is_local=False)


def _get_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    caminho = db_path or DB_FILE
    parent = Path(caminho).parent
    if parent and not parent.exists():
        parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(str(caminho), timeout=30.0)


def init_finops_db(db_path: Optional[str] = None) -> None:
    """Inicializa a tabela de telemetria de tokens no SQLite WAL."""
    with _get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA journal_mode = WAL;")
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS llm_token_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                channel_id TEXT NOT NULL,
                model TEXT NOT NULL,
                prompt_tokens INTEGER NOT NULL,
                completion_tokens INTEGER NOT NULL,
                total_tokens INTEGER NOT NULL,
                latency_ms INTEGER NOT NULL,
                cost_usd REAL NOT NULL,
                is_local INTEGER NOT NULL DEFAULT 0,
                origin_type TEXT NOT NULL DEFAULT 'INTERACTIVE',
                is_fallback INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_token_logs_user ON llm_token_logs(user_id, created_at DESC);"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_token_logs_origin ON llm_token_logs(origin_type, created_at DESC);"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_token_logs_created ON llm_token_logs(created_at DESC);"
        )
        conn.commit()


class FinOpsManager:
    """Gerenciador assíncrono de observabilidade FinOps e controle de cotas."""

    def __init__(self, db_path: Optional[str] = None) -> None:
        self.db_path = db_path
        self._queue: asyncio.Queue[TokenLogEntry] = asyncio.Queue()
        self._flush_lock = asyncio.Lock()
        self._worker_task: Optional[asyncio.Task] = None
        self._running = False
        # Cache em memória para cotas diárias: {f"{user_id}:{date}": total_tokens}
        self._cache_consumo_diario: Dict[str, int] = {}

    def _get_today_str(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")

    async def iniciar_worker(self) -> None:
        """Inicia o worker assíncrono de flush em lote a cada 30 segundos."""
        if self._running:
            return
        self._running = True
        self._worker_task = asyncio.create_task(self._loop_flush_periodico())
        logger.info("[FinOpsManager] Worker de telemetria de tokens inicializado.")

    async def parar_worker(self) -> None:
        """Finaliza o worker e força o flush de qualquer métrica remanescente na fila."""
        self._running = False
        if self._worker_task and not self._worker_task.done():
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
        await self.flush()
        logger.info("[FinOpsManager] Worker de telemetria finalizado e fila persistida.")

    async def _loop_flush_periodico(self) -> None:
        """Loop contínuo que descarrega a fila no banco a cada 30 segundos."""
        while self._running:
            try:
                await asyncio.sleep(30.0)
                await self.flush()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("[FinOpsManager] Erro no loop de flush periódico: %s", e)

    async def registrar_uso(
        self,
        user_id: str | int,
        channel_id: str | int,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        latency_ms: int,
        is_local: bool,
        origin_type: str = "INTERACTIVE",
        is_fallback: bool = False,
    ) -> TokenLogEntry:
        """Registra a telemetria de uma chamada de LLM na fila assíncrona."""
        u_str = str(user_id) if user_id else "SYSTEM"
        c_str = str(channel_id) if channel_id else "UNKNOWN"
        p_tok = max(0, int(prompt_tokens))
        c_tok = max(0, int(completion_tokens))
        t_tok = p_tok + c_tok
        custo = calcular_custo_tokens(model, p_tok, c_tok, is_local=is_local)

        entry = TokenLogEntry(
            user_id=u_str,
            channel_id=c_str,
            model=model or "desconhecido",
            prompt_tokens=p_tok,
            completion_tokens=c_tok,
            total_tokens=t_tok,
            latency_ms=max(0, int(latency_ms)),
            cost_usd=custo,
            is_local=is_local,
            origin_type=origin_type or "INTERACTIVE",
            is_fallback=is_fallback,
        )

        # Atualiza cache em memória para resposta rápida de cota
        hoje = self._get_today_str()
        chave_cache = f"{u_str}:{hoje}"
        self._cache_consumo_diario[chave_cache] = self._cache_consumo_diario.get(chave_cache, 0) + t_tok

        await self._queue.put(entry)

        # Se a fila acumular 50 itens ou mais, descarrega imediatamente em background
        if self._queue.qsize() >= 50:
            asyncio.create_task(self.flush())

        return entry

    async def flush(self) -> int:
        """Descarrega todos os itens pendentes da fila para o SQLite WAL via executemany."""
        if self._queue.empty():
            return 0

        async with self._flush_lock:
            itens: List[TokenLogEntry] = []
            while not self._queue.empty():
                try:
                    itens.append(self._queue.get_nowait())
                except asyncio.QueueEmpty:
                    break

            if not itens:
                return 0

            return await asyncio.to_thread(self._persistir_lote_db, itens)

    def _persistir_lote_db(self, itens: List[TokenLogEntry]) -> int:
        """Executa a inserção em lote no SQLite em thread auxiliar."""
        linhas = [
            (
                it.user_id,
                it.channel_id,
                it.model,
                it.prompt_tokens,
                it.completion_tokens,
                it.total_tokens,
                it.latency_ms,
                it.cost_usd,
                1 if it.is_local else 0,
                it.origin_type,
                1 if it.is_fallback else 0,
            )
            for it in itens
        ]
        with _get_connection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.executemany(
                """
                INSERT INTO llm_token_logs (
                    user_id, channel_id, model, prompt_tokens, completion_tokens,
                    total_tokens, latency_ms, cost_usd, is_local, origin_type, is_fallback
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                linhas,
            )
            conn.commit()
        return len(linhas)

    def consultar_consumo_diario(
        self,
        user_id: str | int,
        origin_type: Optional[str] = None,
    ) -> int:
        """Consulta o total de tokens consumidos hoje pelo usuário ou pelo sistema."""
        u_str = str(user_id)
        with _get_connection(self.db_path) as conn:
            cursor = conn.cursor()
            query = """
                SELECT COALESCE(SUM(total_tokens), 0)
                FROM llm_token_logs
                WHERE user_id = ?
                  AND date(created_at, 'localtime') = date('now', 'localtime')
            """
            params: List[Any] = [u_str]
            if origin_type:
                query += " AND origin_type = ?"
                params.append(origin_type)
            cursor.execute(query, tuple(params))
            res = cursor.fetchone()
            banco_tokens = int(res[0]) if res else 0

        # Soma itens que ainda estão na fila assíncrona
        fila_tokens = 0
        hoje = self._get_today_str()
        chave = f"{u_str}:{hoje}"
        if chave in self._cache_consumo_diario:
            # O cache reflete o acumulador do dia nesta sessão
            fila_tokens = max(0, self._cache_consumo_diario[chave] - banco_tokens)

        return banco_tokens + fila_tokens

    def deve_forcar_fallback_local(
        self,
        user_id: str | int,
        origin_type: str = "INTERACTIVE",
    ) -> bool:
        """Verifica se o usuário ou background excedeu a cota diária de nuvem."""
        consumo = self.consultar_consumo_diario(user_id, origin_type)
        limite = COTA_DIARIA_BACKGROUND_PADRAO if origin_type == "BACKGROUND" else COTA_DIARIA_USUARIO_PADRAO
        return consumo >= limite

    def obter_resumo_finops(self, dias: int = 30) -> Dict[str, Any]:
        """Gera o resumo estatístico e financeiro do período informado."""
        with _get_connection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT 
                    COUNT(*) as total_calls,
                    COALESCE(SUM(total_tokens), 0) as total_tokens,
                    COALESCE(SUM(cost_usd), 0.0) as total_cost_usd,
                    COALESCE(AVG(latency_ms), 0) as avg_latency_ms,
                    COALESCE(SUM(CASE WHEN is_local = 1 THEN total_tokens ELSE 0 END), 0) as local_tokens,
                    COALESCE(SUM(CASE WHEN is_local = 0 THEN total_tokens ELSE 0 END), 0) as cloud_tokens,
                    COALESCE(SUM(CASE WHEN origin_type = 'INTERACTIVE' THEN total_tokens ELSE 0 END), 0) as interactive_tokens,
                    COALESCE(SUM(CASE WHEN origin_type = 'BACKGROUND' THEN total_tokens ELSE 0 END), 0) as background_tokens,
                    COALESCE(SUM(is_fallback), 0) as total_fallbacks
                FROM llm_token_logs
                WHERE created_at >= datetime('now', '-' || ? || ' days')
                """,
                (dias,),
            )
            row = cursor.fetchone()

        if not row:
            return {
                "dias": dias,
                "total_calls": 0,
                "total_tokens": 0,
                "total_cost_usd": 0.0,
                "total_cost_brl": 0.0,
                "economia_local_usd": 0.0,
                "economia_local_brl": 0.0,
                "pct_local": 0.0,
            }

        total_calls, total_tokens, total_cost_usd, avg_lat, local_tok, cloud_tok, int_tok, bg_tok, fallbacks = row
        custo_usd = float(total_cost_usd)
        custo_brl = round(custo_usd * TAXA_CAMBIO_BRL, 2)
        pct_local = round((local_tok / total_tokens * 100.0), 1) if total_tokens > 0 else 0.0
        economia_usd = calcular_economia_local(int(local_tok * 0.7), int(local_tok * 0.3))
        economia_brl = round(economia_usd * TAXA_CAMBIO_BRL, 2)

        return {
            "dias": dias,
            "total_calls": total_calls,
            "total_tokens": total_tokens,
            "total_cost_usd": round(custo_usd, 4),
            "total_cost_brl": custo_brl,
            "economia_local_usd": round(economia_usd, 4),
            "economia_local_brl": economia_brl,
            "avg_latency_ms": int(avg_lat),
            "local_tokens": local_tok,
            "cloud_tokens": cloud_tok,
            "interactive_tokens": int_tok,
            "background_tokens": bg_tok,
            "pct_local": pct_local,
            "total_fallbacks": fallbacks,
        }

    def obter_ranking_modelos(self, dias: int = 30) -> List[Dict[str, Any]]:
        """Retorna o ranking de modelos mais utilizados e seus custos."""
        with _get_connection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT 
                    model,
                    COUNT(*) as calls,
                    COALESCE(SUM(total_tokens), 0) as tokens,
                    COALESCE(SUM(cost_usd), 0.0) as cost_usd,
                    is_local
                FROM llm_token_logs
                WHERE created_at >= datetime('now', '-' || ? || ' days')
                GROUP BY model
                ORDER BY tokens DESC
                """,
                (dias,),
            )
            rows = cursor.fetchall()

        ranking = []
        for mod, calls, toks, cost, loc in rows:
            ranking.append({
                "model": mod,
                "calls": calls,
                "tokens": toks,
                "cost_usd": round(float(cost), 4),
                "is_local": bool(loc),
            })
        return ranking

    def obter_saldo_cotas(self, user_id: str | int) -> Dict[str, Any]:
        """Obtém o balanço da cota diária do usuário e do background."""
        u_str = str(user_id)
        user_consumo = self.consultar_consumo_diario(u_str, "INTERACTIVE")
        bg_consumo = self.consultar_consumo_diario("SYSTEM_BACKGROUND", "BACKGROUND")

        pct_user = min(100.0, round((user_consumo / COTA_DIARIA_USUARIO_PADRAO) * 100.0, 1))
        pct_bg = min(100.0, round((bg_consumo / COTA_DIARIA_BACKGROUND_PADRAO) * 100.0, 1))

        return {
            "user_id": u_str,
            "user_consumed": user_consumo,
            "user_limit": COTA_DIARIA_USUARIO_PADRAO,
            "user_pct": pct_user,
            "user_exceeded": user_consumo >= COTA_DIARIA_USUARIO_PADRAO,
            "bg_consumed": bg_consumo,
            "bg_limit": COTA_DIARIA_BACKGROUND_PADRAO,
            "bg_pct": pct_bg,
            "bg_exceeded": bg_consumo >= COTA_DIARIA_BACKGROUND_PADRAO,
        }

    def resetar_cota_usuario(self, user_id: str | int) -> None:
        """Reseta a contagem de cota diária do usuário."""
        u_str = str(user_id)
        hoje = self._get_today_str()
        chave = f"{u_str}:{hoje}"
        self._cache_consumo_diario[chave] = 0
        with _get_connection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE llm_token_logs 
                SET total_tokens = 0, prompt_tokens = 0, completion_tokens = 0
                WHERE user_id = ? AND date(created_at, 'localtime') = date('now', 'localtime')
                """,
                (u_str,),
            )
            conn.commit()


# Instância singleton global de FinOps
finops_manager = FinOpsManager()
