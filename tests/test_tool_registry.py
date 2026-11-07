"""
Testes Unitários e Assíncronos para o Despachante de Ferramentas (ToolRegistry).
"""

import json
import sys
import unittest
from pathlib import Path

# Adiciona o diretório discord ao sys.path
DISCORD_PATH = Path(__file__).resolve().parent.parent / "discord"
if str(DISCORD_PATH) not in sys.path:
    sys.path.insert(0, str(DISCORD_PATH))

from tools.registry import ToolRegistry


class TestToolRegistry(unittest.IsolatedAsyncioTestCase):
    """Valida o registro e normalização canônica de ferramentas da LLM."""

    def setUp(self):
        self.registry = ToolRegistry()

    async def test_canonical_dict_return(self):
        """Tool que retorna dicionário canônico deve ser serializada em JSON idêntico."""
        @self.registry.register(name="tool_canonica", description="Teste canônico")
        def tool_canonica():
            return {"sucesso": True, "dados": {"valor": 42}, "erro": None}

        res_raw = await self.registry.execute("tool_canonica", {})
        data = json.loads(res_raw)

        self.assertTrue(data["sucesso"])
        self.assertEqual(data["dados"], {"valor": 42})
        self.assertIsNone(data["erro"])

    async def test_string_return_normalization(self):
        """Tool que retorna string pura deve ser automaticamente envolvida no schema canônico."""
        @self.registry.register(name="tool_string", description="Retorna texto")
        async def tool_string():
            return "Olá mundo!"

        res_raw = await self.registry.execute("tool_string", {})
        data = json.loads(res_raw)

        self.assertTrue(data["sucesso"])
        self.assertEqual(data["dados"], "Olá mundo!")
        self.assertIsNone(data["erro"])

    async def test_legacy_dict_normalization(self):
        """Tool legada que retorna {'sucesso': True, 'resultado': 10} deve ser adaptada para 'dados'."""
        @self.registry.register(name="tool_legada", description="Retorno legado")
        def tool_legada():
            return {"sucesso": True, "resultado": 10, "unidade": "ms"}

        res_raw = await self.registry.execute("tool_legada", {})
        data = json.loads(res_raw)

        self.assertTrue(data["sucesso"])
        self.assertIn("dados", data)
        self.assertEqual(data["dados"]["resultado"], 10)
        self.assertIsNone(data["erro"])

    async def test_exception_handling_normalization(self):
        """Tool que lança exceção não tratada deve retornar erro canônico sem quebrar o loop."""
        @self.registry.register(name="tool_falha", description="Lança exceção")
        def tool_falha():
            raise ValueError("Erro simulado de teste")

        res_raw = await self.registry.execute("tool_falha", {})
        data = json.loads(res_raw)

        self.assertFalse(data["sucesso"])
        self.assertIsNone(data["dados"])
        self.assertIn("Erro simulado de teste", data["erro"])

    async def test_nonexistent_tool(self):
        """Chamada de ferramenta não existente deve retornar erro estruturado."""
        res_raw = await self.registry.execute("ferramenta_fantasma", {})
        data = json.loads(res_raw)

        self.assertFalse(data["sucesso"])
        self.assertIsNone(data["dados"])
        self.assertIn("não encontrada", data["erro"])


if __name__ == "__main__":
    unittest.main()

