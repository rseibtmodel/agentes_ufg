"""
Testes Unitários e Assíncronos para o Barramento de Mensagens (MessageGateway).
"""

from pathlib import Path
import sys
import unittest
from unittest.mock import AsyncMock, MagicMock

# Adiciona o diretório discord ao sys.path
DISCORD_PATH = Path(__file__).resolve().parent.parent / "discord"
if str(DISCORD_PATH) not in sys.path:
    sys.path.insert(0, str(DISCORD_PATH))

from message_gateway import MessageGateway


class TestMessageGateway(unittest.IsolatedAsyncioTestCase):
    """Valida o funcionamento do barramento de mensagens e suas políticas anti-spam/resiliência."""

    def setUp(self):
        # Instancia o gateway padrão e customiza parâmetros para testes velozes
        self.gateway = MessageGateway()
        self.gateway.leaky_interval = 0.01
        self.gateway.debounce_window = 1.0
        self.gateway.max_burst_msgs = 3

    def tearDown(self):
        self.gateway.clear_queue()

    async def test_fast_path_dispatch(self):
        """Valida despacho imediato via fast-path quando o canal está ocioso."""
        mock_channel = MagicMock()
        mock_channel.id = 111
        mock_sent = MagicMock()
        mock_channel.send = AsyncMock(return_value=mock_sent)

        res = await self.gateway.dispatch(
            target=mock_channel,
            content="Mensagem de teste rápida",
        )

        self.assertIsNotNone(res)
        self.assertEqual(res, mock_sent)
        mock_channel.send.assert_called_once()
        self.assertEqual(self.gateway.get_status()["stats"]["fast_path_sent"], 1)

    async def test_anti_spam_deduplication(self):
        """Valida descarte de mensagens duplicadas idênticas no mesmo canal dentro da janela anti-spam."""
        mock_channel = MagicMock()
        mock_channel.id = 222
        mock_channel.send = AsyncMock(return_value=MagicMock())

        # Primeiro envio: deve passar
        sent_1 = await self.gateway.dispatch(
            target=mock_channel,
            content="Mensagem repetida",
        )
        self.assertIsNotNone(sent_1)

        # Segundo envio idêntico imediato: deve ser bloqueado pelo anti-spam
        sent_2 = await self.gateway.dispatch(
            target=mock_channel,
            content="Mensagem repetida",
        )
        self.assertIsNone(sent_2)
        self.assertEqual(self.gateway.get_status()["stats"]["duplicates_dropped"], 1)

    async def test_pause_and_resume_queue(self):
        """Valida que a fila outbox pode ser pausada e retomada."""
        self.assertFalse(self.gateway.get_status()["is_paused"])

        self.gateway.pause()
        self.assertTrue(self.gateway.get_status()["is_paused"])

        self.gateway.resume()
        self.assertFalse(self.gateway.get_status()["is_paused"])

    async def test_tempfile_deletion_after_send(self):
        """Valida que arquivos com delete_after_send=Path são removidos do disco após o envio (BUG-02)."""
        temp_file = Path("/tmp/test_gateway_tempfile.txt")
        temp_file.write_text("conteúdo de teste", encoding="utf-8")
        self.assertTrue(temp_file.exists())

        mock_channel = MagicMock()
        mock_channel.id = 444
        mock_channel.send = AsyncMock(return_value=MagicMock())

        await self.gateway.dispatch(
            target=mock_channel,
            content="Arquivo temporário",
            delete_after_send=temp_file,
        )

        # Verifica se foi deletado após o envio
        self.assertFalse(temp_file.exists())


if __name__ == "__main__":
    unittest.main()
