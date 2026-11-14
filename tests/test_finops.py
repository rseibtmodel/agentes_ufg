"""
Testes unitários para o subsistema de FinOps e Telemetria de Tokens (IDEA-28).
"""

import asyncio
import os
import tempfile
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "discord")))

from finops_manager import (
    FinOpsManager,
    calcular_custo_tokens,
    calcular_economia_local,
    init_finops_db,
    COTA_DIARIA_USUARIO_PADRAO,
)
from tools.finops_tools import tool_consultar_metricas_finops
from commands.registry import CommandContext


class TestFinOpsManager(unittest.IsolatedAsyncioTestCase):
    """Bateria de testes para cálculo de custos, buffer em lote e cotas."""

    async def asyncSetUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "test_finops.db")
        init_finops_db(self.db_path)
        self.manager = FinOpsManager(db_path=self.db_path)

    async def asyncTearDown(self) -> None:
        await self.manager.parar_worker()
        self.temp_dir.cleanup()

    def test_calculo_custo_tokens(self) -> None:
        """Valida precificação de modelos em nuvem e gratuidade local."""
        # 1M tokens no Gemini Flash input: 0.075, output: 0.30
        custo_flash = calcular_custo_tokens("gemini-1.5-flash", 1_000_000, 1_000_000, is_local=False)
        self.assertAlmostEqual(custo_flash, 0.375, places=4)

        # Modelo local sempre tem custo zero
        custo_local = calcular_custo_tokens("qwen2.5-coder-local", 500_000, 500_000, is_local=True)
        self.assertEqual(custo_local, 0.0)

        # Economia estimada
        econ = calcular_economia_local(1_000_000, 0)
        self.assertAlmostEqual(econ, 0.075, places=4)

    async def test_registro_uso_e_flush_lote(self) -> None:
        """Testa o enfileiramento não-bloqueante e a persistência no SQLite."""
        entry = await self.manager.registrar_uso(
            user_id="user_123",
            channel_id="chan_456",
            model="gemini-1.5-flash",
            prompt_tokens=1000,
            completion_tokens=500,
            latency_ms=120,
            is_local=False,
            origin_type="INTERACTIVE",
        )
        self.assertEqual(entry.total_tokens, 1500)
        self.assertGreater(entry.cost_usd, 0.0)

        # Descarrega a fila no banco de teste
        inseridos = await self.manager.flush()
        self.assertEqual(inseridos, 1)

        # Consulta resumo
        resumo = self.manager.obter_resumo_finops(dias=1)
        self.assertEqual(resumo["total_calls"], 1)
        self.assertEqual(resumo["total_tokens"], 1500)
        self.assertEqual(resumo["cloud_tokens"], 1500)

    async def test_circuit_breaker_cota_e_fallback(self) -> None:
        """Testa gatilho de estouro de cota e ativação de fallback."""
        u_id = "user_heavy"
        # Inicialmente não deve forçar fallback
        self.assertFalse(self.manager.deve_forcar_fallback_local(u_id, "INTERACTIVE"))

        # Registra uso acima do teto de 200k tokens
        await self.manager.registrar_uso(
            user_id=u_id,
            channel_id="c1",
            model="gemini-1.5-flash",
            prompt_tokens=150_000,
            completion_tokens=60_000,
            latency_ms=800,
            is_local=False,
        )
        await self.manager.flush()

        # Agora deve forçar fallback
        self.assertTrue(self.manager.deve_forcar_fallback_local(u_id, "INTERACTIVE"))

        saldo = self.manager.obter_saldo_cotas(u_id)
        self.assertTrue(saldo["user_exceeded"])
        self.assertGreaterEqual(saldo["user_consumed"], COTA_DIARIA_USUARIO_PADRAO)

        # Reset de cota
        self.manager.resetar_cota_usuario(u_id)
        self.assertFalse(self.manager.deve_forcar_fallback_local(u_id, "INTERACTIVE"))

    async def test_tool_consultar_metricas(self) -> None:
        """Valida que a tool registrada para a IA retorna o contrato padrão."""
        with patch("tools.finops_tools.finops_manager", self.manager):
            res = tool_consultar_metricas_finops(dias=7)
            self.assertTrue(res["sucesso"])
            self.assertIn("resumo_periodo", res["dados"])
            self.assertIn("cotas_usuario", res["dados"])
            self.assertIn("top_modelos", res["dados"])

    async def test_comando_finops_execucao(self) -> None:
        """Valida que o comando !finops responde sem lançar exceções."""
        from commands.system_commands import cmd_finops

        mock_author = MagicMock()
        mock_author.id = 9999
        mock_author.display_name = "DevTester"

        ctx = MagicMock(spec=CommandContext)
        ctx.author = mock_author
        ctx.args = ["status"]
        ctx.reply = AsyncMock()

        with patch("commands.system_commands.finops_manager", self.manager):
            await cmd_finops(ctx)
            ctx.reply.assert_called_once()
            resposta = ctx.reply.call_args[0][0]
            self.assertIn("PAINEL FINOPS", resposta)


if __name__ == "__main__":
    unittest.main()
