"""
Testes Unitários para o Motor de Metamorfose Semanal & Bag-of-Words Local (Onda 2 - IDEA-27).
"""

import asyncio
from datetime import datetime, timedelta
import json
from pathlib import Path
import shutil
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

DISCORD_PATH = Path(__file__).resolve().parent.parent / "discord"
if str(DISCORD_PATH) not in sys.path:
    sys.path.insert(0, str(DISCORD_PATH))

import persona_manager
from persona_evolution_manager import PersonaEvolutionManager, persona_evolution_manager
from text_frequency import (
    extrair_top_palavras_canal,
    formatar_bag_of_words_prompt,
    sanitizar_texto_mensagem,
)
from commands.registry import CommandContext
from commands.ai_commands import cmd_persona


class TestTextFrequency(unittest.TestCase):
    """Valida a sanitização e a extração local de termos por frequência."""

    def test_sanitizar_texto_mensagem(self):
        """Garante a remoção de markdown, URLs, menções do Discord e comandos."""
        texto_bruto = (
            "Olha este link https://exemplo.com/teste e veja o comando !persona ver "
            "com menção <@123456789> e código ```print('olá')``` e `inline code`."
        )
        limpo = sanitizar_texto_mensagem(texto_bruto)
        self.assertNotIn("https://", limpo)
        self.assertNotIn("!persona", limpo)
        self.assertNotIn("<@123456789>", limpo)
        self.assertNotIn("print('olá')", limpo)
        self.assertNotIn("inline code", limpo)

    def test_extrair_top_palavras_canal(self):
        """Valida que stopwords em português e inglês são ignoradas e contagens são exatas."""
        mensagens = [
            "Precisamos refatorar o backend e otimizar o banco de dados sqlite.",
            "O banco de dados sqlite precisa de índices para o backend rodar liso.",
            "Backend e sqlite são o foco principal desta sprint de dados.",
        ]
        top = extrair_top_palavras_canal(mensagens, top_n=5)
        palavras = [p[0] for p in top]
        self.assertIn("sqlite", palavras)
        self.assertIn("backend", palavras)
        self.assertIn("dados", palavras)
        # Stopwords não devem aparecer
        self.assertNotIn("de", palavras)
        self.assertNotIn("para", palavras)
        self.assertNotIn("são", palavras)

    def test_formatar_bag_of_words_prompt(self):
        """Verifica a formatação compacta de termos frequentes."""
        top = [("sqlite", 10), ("python", 8), ("asyncio", 5)]
        resultado = formatar_bag_of_words_prompt(top, max_termos=2)
        self.assertEqual(resultado, "sqlite (10x), python (8x)")


class TestPersonaEvolutionManager(unittest.IsolatedAsyncioTestCase):
    """Valida a lógica assíncrona de verificação e execução de metamorfoses no SQLite."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = str(Path(self.temp_dir) / "test_evolution.db")
        persona_manager.init_persona_db(self.db_path)

        # Inicializa tabela messages para simular histórico conversacional
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT,
                    role TEXT,
                    content TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    channel_id TEXT
                )
                """
            )
            conn.commit()

        self.mgr = PersonaEvolutionManager(db_path=self.db_path)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    async def test_verificar_canais_para_metamorfose_elegibilidade(self):
        """Canais travados (is_locked=1) ou recentes (< 7 dias) não devem ser selecionados."""
        canal_elegivel = "canal_antigo_1"
        canal_travado = "canal_travado_2"
        canal_recente = "canal_recente_3"

        data_antiga = (datetime.now() - timedelta(days=8)).strftime("%Y-%m-%d %H:%M:%S")
        data_recente = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S")

        with sqlite3.connect(self.db_path) as conn:
            # 1. Elegível: adaptive=1, locked=0, 8 dias atrás
            conn.execute(
                """
                INSERT INTO channel_personas (channel_id, system_prompt, is_adaptive, is_locked, last_evolved_at, created_by_user_id)
                VALUES (?, ?, 1, 0, ?, 'user_test')
                """,
                (canal_elegivel, "Prompt 1", data_antiga),
            )
            # 2. Travado: adaptive=1, locked=1, 8 dias atrás
            conn.execute(
                """
                INSERT INTO channel_personas (channel_id, system_prompt, is_adaptive, is_locked, last_evolved_at, created_by_user_id)
                VALUES (?, ?, 1, 1, ?, 'user_test')
                """,
                (canal_travado, "Prompt 2", data_antiga),
            )
            # 3. Recente: adaptive=1, locked=0, 2 dias atrás
            conn.execute(
                """
                INSERT INTO channel_personas (channel_id, system_prompt, is_adaptive, is_locked, last_evolved_at, created_by_user_id)
                VALUES (?, ?, 1, 0, ?, 'user_test')
                """,
                (canal_recente, "Prompt 3", data_recente),
            )
            conn.commit()

        aptos = await self.mgr.verificar_canais_para_metamorfose(db_path=self.db_path)
        ids_aptos = [c["channel_id"] for c in aptos]
        self.assertIn(canal_elegivel, ids_aptos)
        self.assertNotIn(canal_travado, ids_aptos)
        self.assertNotIn(canal_recente, ids_aptos)

    async def test_executar_metamorfose_e_preservar_historico(self):
        """Valida a execução completa da metamorfose com atualização e arquivamento de histórico."""
        canal_id = "canal_metamorfose_teste"

        # 1. Configura persona inicial
        persona_manager.definir_persona_canal(
            channel_id=canal_id,
            system_prompt="Você é o assistente alfa.",
            display_name="Alfa Inicial",
            age="10 dias",
            bio="Versão alfa original.",
            avatar_seed="alfa-seed",
            is_adaptive=True,
            is_locked=False,
            db_path=self.db_path,
        )

        # 2. Insere mensagens para compor o Bag-of-Words
        with sqlite3.connect(self.db_path) as conn:
            for _ in range(5):
                conn.execute(
                    "INSERT INTO messages (user_id, role, content, channel_id) VALUES (?, ?, ?, ?)",
                    ("user_1", "user", "Estamos estudando arquitetura de microservices e kubernetes.", canal_id),
                )
            conn.commit()

        # Mock da LLM para retornar JSON de metamorfose estruturado
        mock_llm_json = json.dumps({
            "display_name": "Arquiteto K8s",
            "age": "2 anos de cluster",
            "bio": "Especialista em containers e orquestração distribuída.",
            "avatar_seed": "k8s-pod",
            "mensagem_anuncio": "✨ O cluster evoluiu! Agora sou o Arquiteto K8s.",
        })

        with patch("persona_evolution_manager._obter_llm_client") as mock_obter_llm:
            mock_client = MagicMock()
            mock_client.gerar_resposta = AsyncMock(return_value=mock_llm_json)
            mock_obter_llm.return_value = mock_client

            res = await self.mgr.executar_metamorfose_canal(
                channel_id=canal_id,
                forcar=True,
                db_path=self.db_path,
            )

        self.assertTrue(res["sucesso"])
        self.assertEqual(res["display_name"], "Arquiteto K8s")
        self.assertEqual(res["avatar_seed"], "k8s-pod")

        # 3. Inspeciona o banco de dados e valida se os dados foram persistidos
        p_atualizada = persona_manager.obter_persona_canal(canal_id, db_path=self.db_path)
        self.assertEqual(p_atualizada["display_name"], "Arquiteto K8s")
        self.assertEqual(p_atualizada["age"], "2 anos de cluster")
        self.assertEqual(p_atualizada["bio"], "Especialista em containers e orquestração distribuída.")

        # 4. Valida se a encarnação anterior foi preservada no histórico JSON
        historico = await self.mgr.obter_historico_metamorfoses(canal_id, db_path=self.db_path)
        self.assertEqual(len(historico), 1)
        self.assertEqual(historico[0]["display_name"], "Alfa Inicial")
        self.assertEqual(historico[0]["avatar_seed"], "alfa-seed")

    async def test_comando_persona_metamorfose_e_historico(self):
        """Valida a execução dos subcomandos !persona metamorfose e !persona historico."""
        canal_id = "canal_cmd_test"
        persona_manager.definir_persona_canal(
            channel_id=canal_id,
            system_prompt="Assistente de teste de comando.",
            display_name="Robô Base",
            db_path=self.db_path,
        )

        # Contexto mockado de comando do Discord
        mock_msg = MagicMock()
        mock_msg.guild = None
        mock_msg.channel.id = 123456
        mock_msg.channel.name = "dev-chat"
        mock_msg.author.id = "user_dev"

        ctx = MagicMock(spec=CommandContext)
        ctx.message = mock_msg
        ctx.channel = mock_msg.channel
        ctx.author = mock_msg.author
        ctx.client = MagicMock()
        ctx.reply = AsyncMock(return_value=MagicMock(edit=AsyncMock()))

        # Injeta db_path temporário no singleton durante o teste
        with patch.object(persona_evolution_manager, "db_path", self.db_path), \
             patch("persona_manager.DB_FILE", self.db_path), \
             patch("persona_evolution_manager.DB_FILE", self.db_path):

            # 1. Executa !persona historico antes de evoluir (vazio)
            ctx.args = ["historico"]
            await cmd_persona(ctx)
            ctx.reply.assert_called()
            self.assertIn("Álbum de Metamorfoses Vazio", str(ctx.reply.call_args))

            # 2. Executa !persona metamorfose
            ctx.args = ["metamorfose"]
            with patch.object(persona_evolution_manager, "executar_metamorfose_canal", new_callable=AsyncMock) as mock_exec:
                import discord
                mock_embed = discord.Embed(title="✨ Metamorfose Teste")
                mock_exec.return_value = {
                    "sucesso": True,
                    "embed": mock_embed,
                }
                await cmd_persona(ctx)
                mock_exec.assert_called_once()


if __name__ == "__main__":
    unittest.main()
