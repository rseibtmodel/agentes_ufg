"""
Testes Unitários e Assíncronos para o Agente de Pesquisa Profunda (Deep Research — IDEA-17).
"""

from datetime import datetime
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import AsyncMock, patch

# Adiciona o diretório discord ao sys.path
DISCORD_PATH = Path(__file__).resolve().parent.parent / "discord"
if str(DISCORD_PATH) not in sys.path:
    sys.path.insert(0, str(DISCORD_PATH))

from deep_research_manager import DeepResearchManager, init_deep_research_db
from tools.registry import registry
import tools.research_tools  # noqa: F401


class TestDeepResearch(unittest.IsolatedAsyncioTestCase):
    """Valida o ciclo de planejamento, varredura web, síntese e persistência do Deep Research."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.temp_dir.name) / "test_research.db")
        init_deep_research_db(self.db_path)
        self.manager = DeepResearchManager(db_path=self.db_path)

    def tearDown(self):
        self.temp_dir.cleanup()
        from deep_research_manager import REPORTS_DIR
        for f in REPORTS_DIR.glob("dossie_*.md"):
            try:
                f.unlink(missing_ok=True)
            except Exception:
                pass

    async def test_planejar_subconsultas_json(self):
        """Valida que o LLM retorna e decompõe consultas em lista JSON estruturada."""
        mock_plan_json = json.dumps([
            "arquitetura deep research llm arxiv",
            "open deep research huggingface benchmarks",
            "langchain deep research state of the art"
        ])

        with patch("llm_client.llm_client.gerar_resposta", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_plan_json
            consultas = await self.manager.planejar_subconsultas("pesquisa profunda com agentes de IA")

            self.assertEqual(len(consultas), 3)
            self.assertIn("arquitetura deep research llm arxiv", consultas)

    async def test_planejar_subconsultas_fallback(self):
        """Valida fallback limpo caso o LLM retorne resposta inválida."""
        with patch("llm_client.llm_client.gerar_resposta", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = "Não foi possível gerar um JSON válido agora."
            consultas = await self.manager.planejar_subconsultas("algoritmos quânticos")

            self.assertEqual(len(consultas), 3)
            self.assertTrue(any("algoritmos quânticos" in c for c in consultas))

    async def test_executar_pesquisa_completa_e_persistencia(self):
        """Valida o fluxo completo de pesquisa, geração de markdown e gravação no banco SQLite."""
        mock_plan_json = json.dumps(["subconsulta 1", "subconsulta 2"])
        mock_synthesize_text = (
            "## 1. Resumo Executivo\n"
            "Análise detalhada sobre o tema pesquisado.\n\n"
            "## 2. Comparativo & Evidências\n"
            "- Ponto A comparado com Ponto B [1].\n\n"
            "## 3. Síntese Técnica & Recomendações\n"
            "Recomenda-se adotar a rota recomendada."
        )

        mock_search_results = [
            {"title": "Fonte Alfa", "href": "https://exemplo.com/alfa", "body": "Resumo Alfa"},
            {"title": "Fonte Beta", "href": "https://exemplo.com/beta", "body": "Resumo Beta"},
        ]

        with patch("llm_client.llm_client.gerar_resposta", new_callable=AsyncMock) as mock_llm, \
             patch("deep_research_manager.web_search_manager.buscar_na_web", new_callable=AsyncMock) as mock_search, \
             patch("deep_research_manager.web_search_manager.ler_pagina_web", new_callable=AsyncMock) as mock_read, \
             patch("deep_research_manager.obter_preferencia_modelo", return_value={"provider": "auto", "model_name": "modelo-teste"}):

            mock_llm.side_effect = [mock_plan_json, mock_synthesize_text]
            mock_search.return_value = mock_search_results
            mock_read.return_value = {
                "sucesso": True,
                "conteudo": "Conteúdo extraído detalhado da página web com dados analíticos.",
                "titulo": "Fonte Alfa",
            }

            resultado = await self.manager.executar_pesquisa_completa(
                tema="Agentes Autônomos de IA",
                user_id="user_123",
                profundidade=2,
            )

            self.assertTrue(resultado["sucesso"])
            dados = resultado["dados"]
            self.assertIn("report_id", dados)
            self.assertIn("resumo_executivo", dados)
            self.assertTrue(Path(dados["file_path"]).exists())

            # Valida conteúdo do arquivo Markdown gerado
            conteudo_md = Path(dados["file_path"]).read_text(encoding="utf-8")
            self.assertIn("## 1. Resumo Executivo", conteudo_md)
            self.assertIn("Análise detalhada", conteudo_md)

            # Valida persistência no SQLite
            relatorios = self.manager.listar_relatorios(user_id="user_123")
            self.assertEqual(len(relatorios), 1)
            self.assertEqual(relatorios[0]["id"], dados["report_id"])
            self.assertEqual(relatorios[0]["topic"], "Agentes Autônomos de IA")

            # Valida obtenção individual
            rel_especifico = self.manager.obter_relatorio(dados["report_id"])
            self.assertIsNotNone(rel_especifico)
            self.assertEqual(rel_especifico["topic"], "Agentes Autônomos de IA")

    async def test_research_tools_integration(self):
        """Valida a execução das tools de pesquisa registradas no ToolRegistry."""
        mock_plan_json = json.dumps(["consulta tool"])
        mock_synthesize_text = "Dossiê sintetizado via tool."

        with patch("llm_client.llm_client.gerar_resposta", new_callable=AsyncMock) as mock_llm, \
             patch("deep_research_manager.web_search_manager.buscar_na_web", new_callable=AsyncMock) as mock_search, \
             patch("deep_research_manager.web_search_manager.ler_pagina_web", new_callable=AsyncMock) as mock_read, \
             patch("deep_research_manager.obter_preferencia_modelo", return_value={"provider": "auto", "model_name": "modelo-teste"}), \
             patch("tools.research_tools.deep_research_manager", self.manager):

            mock_llm.side_effect = [mock_plan_json, mock_synthesize_text]
            mock_search.return_value = [{"title": "Doc", "href": "https://teste.com", "body": "Resumo"}]
            mock_read.return_value = {
                "sucesso": True,
                "conteudo": "Texto lido da web sobre Criptografia Quântica.",
                "titulo": "Doc Criptografia",
            }

            # Executa a tool executar_pesquisa_profunda
            res_json = await registry.execute("executar_pesquisa_profunda", {"tema": "Criptografia Quântica"})
            dados = json.loads(res_json)

            self.assertTrue(dados["sucesso"])
            self.assertEqual(dados["dados"]["tema"], "Criptografia Quântica")
            self.assertIn("report_id", dados["dados"])

            # Executa a tool listar_relatorios_pesquisa
            res_lista_json = await registry.execute("listar_relatorios_pesquisa", {"limite": 5})
            dados_lista = json.loads(res_lista_json)

            self.assertTrue(dados_lista["sucesso"])
            self.assertGreaterEqual(dados_lista["dados"]["total"], 1)


if __name__ == "__main__":
    unittest.main()
