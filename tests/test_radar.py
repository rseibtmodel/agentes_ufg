"""
Testes unitários do Radar Autônomo de RSS, ArXiv e GitHub (IDEA-29).
"""

import os
import sys
import tempfile
import unittest
from unittest.mock import AsyncMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "discord")))

from radar_manager import (
    FeedItem,
    RadarManager,
    fazer_parse_xml_feed,
    init_radar_db,
    normalizar_url_fonte,
)


class TestRadarManager(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "test_radar.db")
        init_radar_db(self.db_path)
        self.manager = RadarManager(db_path=self.db_path)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_normalizar_url_fonte(self) -> None:
        # Teste GitHub 'dono/repo'
        tipo, url = normalizar_url_fonte("vllm-project/vllm")
        self.assertEqual(tipo, "GITHUB")
        self.assertEqual(url, "https://github.com/vllm-project/vllm/releases.atom")

        # Teste GitHub URL completa
        tipo_gh, url_gh = normalizar_url_fonte("https://github.com/torvalds/linux")
        self.assertEqual(tipo_gh, "GITHUB")
        self.assertEqual(url_gh, "https://github.com/torvalds/linux/releases.atom")

        # Teste ArXiv
        tipo_ar, url_ar = normalizar_url_fonte("arxiv:cs.AI")
        self.assertEqual(tipo_ar, "ARXIV")
        self.assertIn("export.arxiv.org/api/query", url_ar)
        self.assertIn("cat:cs.AI", url_ar)

        # Teste RSS genérico
        tipo_rss, url_rss = normalizar_url_fonte("https://news.ycombinator.com/rss")
        self.assertEqual(tipo_rss, "RSS")
        self.assertEqual(url_rss, "https://news.ycombinator.com/rss")

    def test_parse_atom_feed(self) -> None:
        xml_atom = """<?xml version="1.0" encoding="UTF-8"?>
        <feed xmlns="http://www.w3.org/2005/Atom">
            <title>Releases · vllm-project/vllm</title>
            <entry>
                <id>tag:github.com,2008:Repository/123/v0.6.0</id>
                <title>v0.6.0 Architecture Overhaul</title>
                <link rel="alternate" type="text/html" href="https://github.com/vllm-project/vllm/releases/tag/v0.6.0"/>
                <updated>2026-11-14T10:00:00Z</updated>
                <content type="html">&lt;p&gt;Major release with V1 engine support&lt;/p&gt;</content>
            </entry>
        </feed>
        """.encode("utf-8")
        itens = fazer_parse_xml_feed(xml_atom)
        self.assertEqual(len(itens), 1)
        self.assertEqual(itens[0].title, "v0.6.0 Architecture Overhaul")
        self.assertEqual(itens[0].link, "https://github.com/vllm-project/vllm/releases/tag/v0.6.0")
        self.assertIn("Major release", itens[0].summary)

    def test_parse_rss_feed(self) -> None:
        xml_rss = b"""<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
            <channel>
                <title>Tech Blog</title>
                <item>
                    <title>AI Trends 2026</title>
                    <link>https://example.com/ai-2026</link>
                    <guid>https://example.com/ai-2026</guid>
                    <pubDate>Fri, 14 Nov 2026 12:00:00 GMT</pubDate>
                    <description>Summary of modern autonomous agent architectures.</description>
                </item>
            </channel>
        </rss>
        """
        itens = fazer_parse_xml_feed(xml_rss)
        self.assertEqual(len(itens), 1)
        self.assertEqual(itens[0].title, "AI Trends 2026")
        self.assertEqual(itens[0].link, "https://example.com/ai-2026")
        self.assertIn("autonomous agent", itens[0].summary)

    def test_crud_assinaturas(self) -> None:
        sub = self.manager.criar_assinatura(
            user_id="user_123",
            channel_id="chan_456",
            url_ou_chave="huggingface/transformers",
            keywords_regex="release|patch",
            mode="REALTIME",
            digest_time="19:00",
        )
        self.assertIsNotNone(sub.get("id"))
        self.assertEqual(sub["source_type"], "GITHUB")
        self.assertEqual(sub["mode"], "REALTIME")

        subs = self.manager.listar_assinaturas(user_id="user_123")
        self.assertEqual(len(subs), 1)
        self.assertEqual(subs[0]["channel_id"], "chan_456")

        removido = self.manager.remover_assinatura(sub["id"])
        self.assertTrue(removido)

        subs_depois = self.manager.listar_assinaturas(user_id="user_123")
        self.assertEqual(len(subs_depois), 0)

    async def test_processamento_item_com_desduplicacao(self) -> None:
        sub_info = self.manager.criar_assinatura(
            user_id="user_1",
            channel_id="999888",
            url_ou_chave="test/repo",
            keywords_regex="engine|v1",
            mode="REALTIME",
        )
        sub_id = sub_info["id"]

        from radar_manager import RadarSubscription
        sub = RadarSubscription(
            id=sub_id,
            user_id="user_1",
            channel_id="999888",
            source_type="GITHUB",
            source_url="https://github.com/test/repo/releases.atom",
            keywords_regex="engine|v1",
            mode="REALTIME",
            digest_time="18:00",
            etag=None,
            last_modified=None,
            next_run_at="2026-01-01 00:00:00",
            ativo=True,
            created_at="2026-01-01 00:00:00",
        )

        item = FeedItem(
            item_id="item_001",
            title="Release V1 Engine",
            link="https://github.com/test/repo/releases/tag/v1.0",
            published="2026-11-14",
            summary="New inference engine released.",
        )

        with patch.object(self.manager, "_sintetizar_impacto_llm", new=AsyncMock(return_value="Resumo mock")):
            with patch.object(self.manager, "_despachar_tempo_real", new=AsyncMock()) as mock_dispatch:
                # 1ª execução: item novo e dá match no regex
                processou = await self.manager._processar_item(sub, item)
                self.assertTrue(processou)
                mock_dispatch.assert_called_once()

                # 2ª execução com mesmo item: deduplicado pelo hash SHA-256
                mock_dispatch.reset_mock()
                processou_segunda = await self.manager._processar_item(sub, item)
                self.assertFalse(processou_segunda)
                mock_dispatch.assert_not_called()

        # Verifica se o item foi indexado na busca de itens
        itens_busca = self.manager.buscar_itens_radar(termo="Engine")
        self.assertEqual(len(itens_busca), 1)
        self.assertEqual(itens_busca[0]["titulo"], "Release V1 Engine")

    async def test_catch_up_boletim_apos_horario(self) -> None:
        """Valida que o boletim pendente é despachado mesmo se o servidor subir após o horário."""
        sub = self.manager.criar_assinatura(
            user_id="user_test",
            channel_id="123456789",
            url_ou_chave="openai/whisper",
            mode="DIGEST",
            digest_time="08:00",
        )
        sub_id = sub["id"]

        # Adiciona um item no buffer de digest
        self.manager._bufferizar_digest(
            sub_id=sub_id,
            channel_id="123456789",
            title="New Whisper Release",
            link="https://github.com/openai/whisper/releases/tag/v2026",
            summary="Faster inference update",
        )

        with patch("message_gateway.message_gateway.dispatch", new=AsyncMock()) as mock_dispatch:
            # 1ª execução com horário simulado às 10:30 (servidor subiu após as 08:00)
            from datetime import datetime
            import zoneinfo
            fake_agora = datetime(2026, 11, 14, 10, 30, tzinfo=zoneinfo.ZoneInfo("America/Sao_Paulo"))

            with patch("radar_manager.datetime") as mock_dt:
                mock_dt.now.return_value = fake_agora
                mock_dt.strftime = datetime.strftime

                enviados = await self.manager.verificar_envio_boletins()
                self.assertEqual(enviados, 1)
                mock_dispatch.assert_called_once()

                # 2ª execução no mesmo dia não deve reenviar
                mock_dispatch.reset_mock()
                enviados_2 = await self.manager.verificar_envio_boletins()
                self.assertEqual(enviados_2, 0)
                mock_dispatch.assert_not_called()


if __name__ == "__main__":
    unittest.main()
