"""
Testes Unitários e Assíncronos para o Antigravity Remote Runner (IDEA-23).
"""

import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

# Adiciona o diretório discord ao sys.path
DISCORD_PATH = Path(__file__).resolve().parent.parent / "discord"
if str(DISCORD_PATH) not in sys.path:
    sys.path.insert(0, str(DISCORD_PATH))

from agy_manager import AGYManager, agy_manager
from commands.registry import CommandContext
from commands.system_commands import cmd_agy
from tools.registry import registry
import tools.agy_tools  # noqa: F401


class TestAGYRunner(unittest.IsolatedAsyncioTestCase):
    """Valida o catálogo de skills, inspeção, telemetria e consultas analíticas Read-Only."""

    def setUp(self):
        self.manager = AGYManager()

    def test_listar_skills_reais(self):
        """Valida que o gerenciador descobre as skills reais existentes em .agents/skills/."""
        skills = self.manager.listar_skills()
        self.assertIsInstance(skills, list)
        self.assertGreaterEqual(len(skills), 5)

        nomes = [s["name"] for s in skills]
        self.assertIn("architect", nomes)
        self.assertIn("critic", nomes)
        self.assertIn("oraculo", nomes)

    def test_obter_skill_existente_e_inexistente(self):
        """Valida a busca individual por nome ou pasta."""
        skill = self.manager.obter_skill("critic")
        self.assertIsNotNone(skill)
        self.assertEqual(skill["name"], "critic")
        self.assertIn("Advogado do Diabo", skill["description"])

        skill_inexistente = self.manager.obter_skill("skill_fantasma_123")
        self.assertIsNone(skill_inexistente)

    def test_telemetria_runtime(self):
        """Valida a extração de métricas de telemetria local."""
        telemetria = self.manager.obter_status_telemetria()
        self.assertIn("plataforma", telemetria)
        self.assertIn("uptime", telemetria)
        self.assertIn("memoria_processo_mb", telemetria)
        self.assertIn("total_skills_locais", telemetria)
        self.assertEqual(telemetria["modo_execucao"], "Read-Only Runner (Seguro)")

    async def test_consultar_skill_com_mock(self):
        """Valida a execução de consulta analítica à persona de uma skill."""
        mock_resposta = "Laudo pericial: O uso de SQLite WAL é adequado para baixa concorrência de escrita."

        with patch("llm_client.llm_client.gerar_resposta", new_callable=AsyncMock) as mock_llm, \
             patch("agy_manager.obter_preferencia_modelo", return_value={"provider": "auto", "model_name": "teste"}):

            mock_llm.return_value = mock_resposta

            res = await self.manager.consultar_skill(
                nome_skill="critic",
                consulta="Avalie o uso do SQLite em alta escala",
                user_id="user_123",
            )

            self.assertTrue(res["sucesso"])
            dados = res["dados"]
            self.assertEqual(dados["skill"], "critic")
            self.assertEqual(dados["resposta"], mock_resposta)
            self.assertEqual(dados["modo"], "read_only")

    async def test_consultar_skill_inexistente(self):
        """Valida erro limpo ao consultar skill inexistente."""
        res = await self.manager.consultar_skill(
            nome_skill="nao_existe",
            consulta="Teste",
        )
        self.assertFalse(res["sucesso"])
        self.assertIn("não encontrado", res["erro"])

    async def test_tools_integration(self):
        """Valida as ferramentas registradas no ToolRegistry."""
        # Tool: listar_skills_antigravity
        res_list_raw = await registry.execute("listar_skills_antigravity", {})
        res_list = json.loads(res_list_raw)
        self.assertTrue(res_list["sucesso"])
        self.assertGreaterEqual(res_list["dados"]["total"], 5)

        # Tool: consultar_skill_antigravity
        with patch("llm_client.llm_client.gerar_resposta", new_callable=AsyncMock) as mock_llm, \
             patch("agy_manager.obter_preferencia_modelo", return_value={"provider": "auto", "model_name": "teste"}):

            mock_llm.return_value = "Visão arquitetural aprovada."
            res_consult_raw = await registry.execute(
                "consultar_skill_antigravity",
                {"nome_skill": "architect", "consulta": "Design de microsserviços"},
            )
            res_consult = json.loads(res_consult_raw)
            self.assertTrue(res_consult["sucesso"])
            self.assertEqual(res_consult["dados"]["skill"], "architect")

    async def test_comando_agy_no_chat(self):
        """Valida o despachante do comando !agy no Discord."""
        mock_message = MagicMock()
        mock_message.author.id = 123456
        mock_message.channel.id = 999

        # Teste !agy skills
        ctx_skills = CommandContext(
            message=mock_message,
            client=MagicMock(),
            command_name="agy",
            args=["skills"],
            arg_str="skills",
        )
        with patch.object(ctx_skills, "reply", new_callable=AsyncMock) as mock_reply:
            await cmd_agy(ctx_skills)
            mock_reply.assert_called_once()
            args, _ = mock_reply.call_args
            self.assertIn("CATÁLOGO DE SKILLS", args[0])

        # Teste !agy status
        ctx_status = CommandContext(
            message=mock_message,
            client=MagicMock(),
            command_name="agy",
            args=["status"],
            arg_str="status",
        )
        with patch.object(ctx_status, "reply", new_callable=AsyncMock) as mock_reply:
            await cmd_agy(ctx_status)
            mock_reply.assert_called_once()
            args, _ = mock_reply.call_args
            self.assertIn("TELEMETRIA DO RUNTIME LOCAL", args[0])


if __name__ == "__main__":
    unittest.main()
