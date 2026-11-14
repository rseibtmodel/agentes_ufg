"""
Testes unitários de resiliência e catch-up do Resumo Matinal (Morning Digest).
"""

import asyncio
from datetime import datetime
import os
import sys
import tempfile
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
import zoneinfo

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "discord")))

from digest_manager import (
    atualizar_configuracao_digest,
    iniciar_worker_digest,
    init_digest_db,
    obter_configuracao_digest,
    _digests_em_andamento,
)


class TestDigestCatchUp(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "test_digest.db")
        init_digest_db(self.db_path)
        _digests_em_andamento.clear()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()
        _digests_em_andamento.clear()

    async def test_catch_up_resumo_matinal_apos_inicializacao_tardia(self) -> None:
        """Valida que o resumo matinal é despachado se o servidor iniciar após o horário agendado."""
        user_id = "12345"
        # Configura digest para as 08:00
        with patch("digest_manager.DB_FILE", self.db_path):
            atualizar_configuracao_digest(user_id=user_id, time="08:00", enabled=True, db_path=self.db_path)

            mock_client = MagicMock()
            mock_client.wait_until_ready = AsyncMock()
            mock_client.is_closed.side_effect = [False, True]  # Executa 1 iteração e para

            # Simula horário atual como 10:30 (servidor subiu atrasado)
            fake_agora = datetime(2026, 11, 14, 10, 30, tzinfo=zoneinfo.ZoneInfo("America/Sao_Paulo"))

            with patch("digest_manager.datetime") as mock_dt, \
                 patch("digest_manager._get_connection", lambda p=None: __import__("sqlite3").connect(self.db_path)), \
                 patch("digest_manager.enviar_resumo_matinal", new=AsyncMock()) as mock_enviar:

                mock_dt.now.return_value = fake_agora
                mock_dt.strftime = datetime.strftime

                # Executa uma rodada do worker com intervalo simulado 0
                await iniciar_worker_digest(mock_client, intervalo_segundos=0)

                # Verifica se o resumo foi agendado para envio
                mock_enviar.assert_called_once()
                args, kwargs = mock_enviar.call_args
                self.assertEqual(args[1], user_id)
                self.assertTrue(kwargs.get("forcar"))

                # Verifica se last_sent_date foi registrado no banco
                cfg = obter_configuracao_digest(user_id, db_path=self.db_path)
                self.assertEqual(cfg["last_sent_date"], "2026-11-14")


if __name__ == "__main__":
    unittest.main()
