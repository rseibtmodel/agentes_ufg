"""
Testes Unitários e Assíncronos para o Despachante e Registro de Comandos Modulares.
"""

from pathlib import Path
import sys
import unittest
from unittest.mock import AsyncMock, MagicMock

# Adiciona o diretório discord ao sys.path
DISCORD_PATH = Path(__file__).resolve().parent.parent / "discord"
if str(DISCORD_PATH) not in sys.path:
    sys.path.insert(0, str(DISCORD_PATH))

from commands.registry import CommandContext, CommandRegistry, register_command
from message_gateway import message_gateway
import commands.builtins  # Carrega todos os 6 submódulos modularizados


class TestCommandRegistry(unittest.IsolatedAsyncioTestCase):
    """Valida o registro de comandos, aliases e despacho modular."""

    def setUp(self):
        # Limpa cache do gateway para testes limpos
        message_gateway._dedup_cache.clear()

    def test_modular_commands_registration(self):
        """Valida que todos os comandos foram registrados nos submódulos."""
        from commands.registry import registry

        comandos_obrigatorios = [
            "ajuda",
            "ping",
            "status",
            "agenda",
            "agendar",
            "desmarcar",
            "lista",
            "listas",
            "lembrete",
            "lembretes",
            "modelo",
            "persona",
            "prompt",
            "prompts",
            "pdf",
            "pdfs",
            "memoria",
            "topico",
            "nota",
            "notas",
            "buscar",
            "ler",
            "gateway",
            "voz",
            "digest",
        ]
        for cmd in comandos_obrigatorios:
            self.assertIn(cmd, registry._commands, f"Comando '{cmd}' não encontrado no registro!")

    async def test_command_dispatch_and_reply(self):
        """Valida despacho de comando e resposta via CommandContext."""
        test_registry = CommandRegistry(prefix="!")

        @test_registry.register(name="teste", aliases=["t"])
        async def cmd_teste(ctx):
            await ctx.reply(f"Resposta de teste {ctx.arg_str}")

        mock_message = MagicMock()
        mock_message.content = "!teste arg1"
        mock_message.channel = MagicMock()
        mock_message.channel.id = 555
        mock_message.channel.send = AsyncMock(return_value=MagicMock())
        mock_message.author = MagicMock()
        mock_message.author.id = 777
        mock_message.author.name = "Testador"

        mock_client = MagicMock()

        # Despacha comando com nome principal
        executado = await test_registry.dispatch(mock_message, mock_client)
        self.assertTrue(executado)
        mock_message.channel.send.assert_called_once()

        # Despacha comando com alias '!t' e canal diferente para evitar debounce anti-spam
        mock_message_2 = MagicMock()
        mock_message_2.content = "!t arg2"
        mock_message_2.channel = MagicMock()
        mock_message_2.channel.id = 556
        mock_message_2.channel.send = AsyncMock(return_value=MagicMock())
        mock_message_2.author = MagicMock()
        mock_message_2.author.id = 777
        mock_message_2.author.name = "Testador"

        executado_alias = await test_registry.dispatch(mock_message_2, mock_client)
        self.assertTrue(executado_alias)
        mock_message_2.channel.send.assert_called_once()

    async def test_non_command_message_ignored(self):
        """Mensagem que não inicia com o prefixo não deve ser executada como comando."""
        test_registry = CommandRegistry(prefix="!")

        mock_message = MagicMock()
        mock_message.content = "Olá bot, como vai você?"
        mock_client = MagicMock()

        executado = await test_registry.dispatch(mock_message, mock_client)
        self.assertFalse(executado)

    async def test_commands_categories_and_dynamic_help(self):
        """Valida que comandos possuem categorias registradas e o !ajuda dinâmico responde corretamente."""
        from commands.registry import registry
        from commands.system_commands import cmd_ajuda

        # 1. Verifica categorias cadastradas
        categorias = registry.get_categories()
        self.assertIn("Google Calendar", categorias)
        self.assertIn("Pesquisa & Web", categorias)
        self.assertIn("Agentes & Skills (AGY)", categorias)

        # 2. Verifica comandos sob a categoria Pesquisa & Web
        cmds_web = registry.get_commands_by_category("Pesquisa & Web")
        nomes_web = [c.name for c in cmds_web]
        self.assertIn("pesquisa_profunda", nomes_web)
        self.assertIn("buscar", nomes_web)

        mock_msg = MagicMock()
        mock_msg.author.id = 999
        mock_client = MagicMock()

        # 3. Teste !ajuda (menu geral)
        ctx_geral = CommandContext(
            message=mock_msg,
            client=mock_client,
            command_name="ajuda",
            args=[],
            arg_str="",
        )
        with unittest.mock.patch.object(ctx_geral, "reply", new_callable=AsyncMock) as mock_reply:
            await cmd_ajuda(ctx_geral)
            mock_reply.assert_called_once()
            args, _ = mock_reply.call_args
            self.assertIn("CENTRAL DE AJUDA", args[0])
            self.assertIn("Agentes & Skills (AGY)", args[0])

        # 4. Teste !ajuda pesquisa_profunda (ficha específica de comando)
        ctx_cmd = CommandContext(
            message=mock_msg,
            client=mock_client,
            command_name="ajuda",
            args=["pesquisa_profunda"],
            arg_str="pesquisa_profunda",
        )
        with unittest.mock.patch.object(ctx_cmd, "reply", new_callable=AsyncMock) as mock_reply:
            await cmd_ajuda(ctx_cmd)
            mock_reply.assert_called_once()
            args, _ = mock_reply.call_args
            self.assertIn("MANUAL DO COMANDO: `!pesquisa_profunda`", args[0])
            self.assertIn("Pesquisa & Web", args[0])
            self.assertIn("Exemplo de uso", args[0])


if __name__ == "__main__":
    unittest.main()
