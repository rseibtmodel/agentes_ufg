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

    async def test_embed_chunking_distinct_hashes(self):
        """Valida que múltiplos chunks enviados como Embed (content=None) não sofrem colisão de hash (OS-012)."""
        import discord

        mock_channel = MagicMock()
        mock_channel.id = 555
        mock_channel.send = AsyncMock(return_value=MagicMock())

        embed_chunk_1 = discord.Embed(description="Parte 1: Início do raciocínio complexo sobre a apuração assistida.")
        embed_chunk_2 = discord.Embed(description="Parte 2: Conclusão detalhada com análise dogmática do CTN.")

        # Primeiro chunk
        res_1 = await self.gateway.dispatch(target=mock_channel, embed=embed_chunk_1)
        self.assertIsNotNone(res_1)

        # Aguarda 0.22s para testar Fast-Path do segundo chunk
        import asyncio
        await asyncio.sleep(0.22)

        # Segundo chunk imediato (diferente descrição no Embed)
        res_2 = await self.gateway.dispatch(target=mock_channel, embed=embed_chunk_2)
        self.assertIsNotNone(res_2)
        self.assertEqual(mock_channel.send.call_count, 2)
        self.assertEqual(self.gateway.get_status()["stats"]["duplicates_dropped"], 0)

    def test_sanitizacao_badges_repetidos(self):
        """Valida que a sanitização defensiva de badges remove 1, 2 ou múltiplos badges acumulados (OS-012)."""
        from llm_client import sanitizar_badges_repetidos

        texto_sujo = (
            "⚡ `[Google Gemini: gemini-3.5-flash]`\n\n"
            "⚡ `[Google Gemini: gemini-3.5-flash]`\n\n"
            "⚡ `[Google Gemini: gemini-3.5-flash]`\n\n"
            "Touché! Você foi na veia do debate tributário."
        )
        limpo = sanitizar_badges_repetidos(texto_sujo)
        self.assertEqual(limpo, "Touché! Você foi na veia do debate tributário.")
        self.assertNotIn("Google Gemini", limpo)


if __name__ == "__main__":
    unittest.main()
