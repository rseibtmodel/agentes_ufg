"""
Testes Unitários para a Identidade Multimodal de Personas (Onda 1 - IDEA-27).
"""

from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import AsyncMock, MagicMock

DISCORD_PATH = Path(__file__).resolve().parent.parent / "discord"
if str(DISCORD_PATH) not in sys.path:
    sys.path.insert(0, str(DISCORD_PATH))

import persona_manager
from commands.registry import CommandContext
from commands.ai_commands import cmd_persona


class TestPersonaMultimodal(unittest.TestCase):
    """Valida as migrations, métodos e integridade de dados multimodais no SQLite."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = str(Path(self.temp_dir) / "test_personas.db")
        persona_manager.init_persona_db(self.db_path)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_definir_e_obter_identidade_multimodal(self):
        """Valida que display_name, avatar, idade e bio são salvos e retornados corretamente."""
        canal_id = "11223344"

        # 1. Cria persona base
        res_base = persona_manager.definir_persona_canal(
            channel_id=canal_id,
            system_prompt="Você é a Dra. Neusa, contadora pericial.",
            user_id="user_admin",
            channel_name="fiscal",
            db_path=self.db_path,
        )
        self.assertTrue(res_base["sucesso"])

        # 2. Define identidade (nome, idade, bio)
        res_id = persona_manager.definir_identidade_canal(
            channel_id=canal_id,
            display_name="Dra. Neusa",
            age="54 anos",
            bio="Perita contábil cética focada em números exatos.",
            db_path=self.db_path,
        )
        self.assertTrue(res_id["sucesso"])
        self.assertEqual(res_id["display_name"], "Dra. Neusa")

        # 3. Define avatar com URL externa
        res_av = persona_manager.definir_avatar_canal(
            channel_id=canal_id,
            avatar_url="https://exemplo.com/neusa.png",
            db_path=self.db_path,
        )
        self.assertTrue(res_av["sucesso"])

        # 4. Recupera e verifica integridade
        persona = persona_manager.obter_persona_canal(canal_id, db_path=self.db_path)
        self.assertIsNotNone(persona)
        self.assertEqual(persona["display_name"], "Dra. Neusa")
        self.assertEqual(persona["age"], "54 anos")
        self.assertEqual(persona["bio"], "Perita contábil cética focada em números exatos.")
        self.assertEqual(persona["avatar_url"], "https://exemplo.com/neusa.png")
        self.assertTrue(persona["is_locked"])  # Edição manual trava a persona

        # 5. Valida URL do avatar
        av_final = persona_manager.obter_avatar_persona(persona)
        self.assertEqual(av_final, "https://exemplo.com/neusa.png")

    def test_avatar_fallback_dicebear(self):
        """Se não houver avatar_url, recorre a avatar_seed ou DiceBear determinístico."""
        canal_id = "55667788"
        persona_manager.definir_persona_canal(
            channel_id=canal_id,
            system_prompt="Você é um hacker cyberpunk.",
            user_id="user_admin",
            channel_name="dev",
            db_path=self.db_path,
        )
        persona_manager.definir_avatar_canal(
            channel_id=canal_id,
            avatar_seed="cyber-neon",
            db_path=self.db_path,
        )

        persona = persona_manager.obter_persona_canal(canal_id, db_path=self.db_path)
        av_url = persona_manager.obter_avatar_persona(persona)
        self.assertIn("api.dicebear.com", av_url)
        self.assertIn("seed=cyber-neon", av_url)

    def test_trava_e_destrava_persona(self):
        """Valida que fixar e destravar a persona atualiza a flag is_locked."""
        canal_id = "998877"
        persona_manager.definir_persona_canal(
            channel_id=canal_id,
            system_prompt="Assistente geral.",
            user_id="user_admin",
            db_path=self.db_path,
        )

        # Trava
        res_lock = persona_manager.definir_trava_persona_canal(canal_id, is_locked=True, db_path=self.db_path)
        self.assertTrue(res_lock["sucesso"])
        p = persona_manager.obter_persona_canal(canal_id, db_path=self.db_path)
        self.assertTrue(p["is_locked"])

        # Destrava
        res_unlock = persona_manager.definir_trava_persona_canal(canal_id, is_locked=False, db_path=self.db_path)
        self.assertTrue(res_unlock["sucesso"])
        p = persona_manager.obter_persona_canal(canal_id, db_path=self.db_path)
        self.assertFalse(p["is_locked"])


class TestPersonaCommands(unittest.IsolatedAsyncioTestCase):
    """Valida despacho dos novos subcomandos de persona."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = str(Path(self.temp_dir) / "test_personas_cmd.db")
        persona_manager.init_persona_db(self.db_path)
        # Patch do DB_FILE global no persona_manager para usar o temporário
        self.original_db = persona_manager.DB_FILE
        persona_manager.DB_FILE = self.db_path

    def tearDown(self):
        persona_manager.DB_FILE = self.original_db
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    async def test_cmd_persona_identidade_e_avatar(self):
        """Valida execução dos subcomandos !persona identidade e !persona avatar."""
        mock_msg = MagicMock()
        mock_msg.author.id = 123
        mock_msg.channel.id = 999
        mock_msg.channel.name = "geral"
        mock_msg.guild = None

        mock_client = MagicMock()

        # Cria persona base primeiro
        persona_manager.definir_persona_canal("999", "Prompt inicial", db_path=self.db_path)

        # 1. Testa !persona identidade
        ctx_id = CommandContext(
            message=mock_msg,
            client=mock_client,
            command_name="persona",
            args=["identidade", "Cadu", "|", "22", "anos", "|", "Dev", "Python"],
            arg_str="identidade Cadu | 22 anos | Dev Python",
        )
        with unittest.mock.patch.object(ctx_id, "reply", new_callable=AsyncMock) as mock_reply:
            await cmd_persona(ctx_id)
            mock_reply.assert_called_once()
            args, _ = mock_reply.call_args
            self.assertIn("Identidade da Persona Atualizada", args[0])

        # 2. Testa !persona avatar
        ctx_av = CommandContext(
            message=mock_msg,
            client=mock_client,
            command_name="persona",
            args=["avatar", "cadu-seed"],
            arg_str="avatar cadu-seed",
        )
        with unittest.mock.patch.object(ctx_av, "reply", new_callable=AsyncMock) as mock_reply:
            await cmd_persona(ctx_av)
            mock_reply.assert_called_once()
            args, _ = mock_reply.call_args
            self.assertIn("Avatar da persona do canal atualizado", args[0])

        # 3. Testa !persona fixar
        ctx_lock = CommandContext(
            message=mock_msg,
            client=mock_client,
            command_name="persona",
            args=["fixar"],
            arg_str="fixar",
        )
        with unittest.mock.patch.object(ctx_lock, "reply", new_callable=AsyncMock) as mock_reply:
            await cmd_persona(ctx_lock)
            mock_reply.assert_called_once()
            args, _ = mock_reply.call_args
            self.assertIn("Persona Travada com Sucesso", args[0])


if __name__ == "__main__":
    unittest.main()

