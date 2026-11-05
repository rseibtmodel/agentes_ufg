"""
Ponto de Entrada Principal do Bot Discord (Antigravity Chatbot).

Responsável pela inicialização do cliente Discord, conexão dos eventos de gateway
e delegação do ciclo de mensagens para o processador modular.
"""

import asyncio
import fcntl
import logging
import os
from pathlib import Path
import sys
import discord
from config import (
    CHROMA_DIR,
    COMMAND_PREFIX,
    DISCORD_TOKEN,
    LM_STUDIO_EMBEDDING_MODEL,
    LM_STUDIO_EMBEDDING_URL,
    LM_STUDIO_URL,
    MODELO_LLM,
)
from database import init_db
from message_handler import processar_mensagem
from reminder_manager import iniciar_worker_lembretes
from digest_manager import iniciar_worker_digest
from audio_manager import get_whisper_model
from tools import inicializar_cache_ferramentas
from tools.registry import registry as tools_registry
from commands.registry import registry as commands_registry
import commands.builtins  # Carrega comandos nativos


# Configuração de logging estruturado
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("discord_bot")

# Trava atômica de processo para impedir múltiplas instâncias concorrentes
LOCK_FILE_PATH = Path(__file__).resolve().parent / ".bot.lock"
_lock_file_handle = None


def adquirir_lock_instancia_unica() -> bool:
    """Garante que apenas uma instância de chat_discord.py esteja em execução.

    Utiliza fcntl.flock para criar um bloqueio no arquivo a nível de sistema operacional.
    Se outra instância já estiver ativa, avisa no log e encerra com segurança, prevenindo
    que duas instâncias recebam os mesmos eventos do Discord Gateway e dupliquem mensagens.
    """
    global _lock_file_handle
    try:
        _lock_file_handle = open(LOCK_FILE_PATH, "a+")
        fcntl.flock(_lock_file_handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        _lock_file_handle.seek(0)
        _lock_file_handle.truncate()
        _lock_file_handle.write(f"{os.getpid()}\n")
        _lock_file_handle.flush()
        return True
    except (BlockingIOError, IOError):
        pid_anterior = "desconhecido"
        try:
            if LOCK_FILE_PATH.exists():
                pid_anterior = LOCK_FILE_PATH.read_text().strip()
        except Exception:
            pass
        logger.warning(
            "⚠️ ATENÇÃO: Outra instância do bot já está em execução (PID: %s)! "
            "Encerrando esta inicialização para evitar mensagens duplicadas no Discord.",
            pid_anterior,
        )
        return False

# Inicializa as tabelas do banco SQLite
init_db()

# Configuração de permissões e intents do Discord
intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)


# Flag de controle para evitar inicialização redundante de workers em reconexões do Gateway
_workers_iniciados = False


@client.event
async def on_ready():
    """Disparado quando o bot estabelece conexão bem-sucedida com o Discord Gateway."""
    global _workers_iniciados
    logger.info("=" * 60)
    logger.info("🤖 Bot conectado com sucesso como: %s", client.user)
    logger.info("🧠 Modelo LLM: %s", MODELO_LLM)
    logger.info("📐 Modelo Embedding: %s (%s)", LM_STUDIO_EMBEDDING_MODEL, LM_STUDIO_EMBEDDING_URL)
    logger.info("🌐 LM Studio Endpoint: %s", LM_STUDIO_URL)
    logger.info("🗄️  ChromaDB Path: %s", CHROMA_DIR)
    logger.info("⚙️  Prefixo de Comandos: %s", COMMAND_PREFIX)
    logger.info("🔧 Tools ativas (%d): %s", len(tools_registry.get_registered_names()), tools_registry.get_registered_names())
    logger.info("⚡ Comandos ativos (%d): %s", len(commands_registry.get_all_commands()), [c.name for c in commands_registry.get_all_commands()])
    logger.info("=" * 60)
    logger.info("Pronto para receber mensagens e comandos no Discord!")

    if _workers_iniciados:
        logger.info("Reconexão detectada: workers de background já estão em execução.")
        return
    _workers_iniciados = True

    # Inicia o worker do Barramento Centralizado de Mensagens e Fila Outbox (IDEA-24)
    from message_gateway import message_gateway
    message_gateway.start_worker(client)

    # Inicia o worker em segundo plano para envio automático de lembretes
    asyncio.create_task(iniciar_worker_lembretes(client))

    # Inicia o worker em segundo plano para envio automático diário do resumo matinal
    asyncio.create_task(iniciar_worker_digest(client))

    # Pré-aquece o cache de embeddings das ferramentas para acelerar o Tool Filtering
    asyncio.create_task(inicializar_cache_ferramentas())

    # Pré-carrega o modelo faster-whisper em segundo plano para transcrição de áudio instantânea
    asyncio.create_task(asyncio.to_thread(get_whisper_model))


@client.event
async def on_message(message: discord.Message):
    """Disparado a cada nova mensagem recebida em servidores ou mensagens diretas."""
    await processar_mensagem(message, client)


@client.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    """Permite capturar mensagens instantaneamente como notas ao reagir com o emoji 📝 (IDEA-25)."""
    if client.user and payload.user_id == client.user.id:
        return

    if str(payload.emoji.name) != "📝":
        return

    channel_id = str(payload.channel_id)
    from topic_manager import obter_topico_canal, adicionar_nota

    topico = obter_topico_canal(channel_id)
    if not topico:
        return

    try:
        channel = client.get_channel(payload.channel_id)
        if not channel:
            channel = await client.fetch_channel(payload.channel_id)
        if not channel or not hasattr(channel, "fetch_message"):
            return

        message = await channel.fetch_message(payload.message_id)
        if not message or not message.content or not message.content.strip():
            return

        autor_nome = payload.member.name if payload.member else "desconhecido"
        nota = await adicionar_nota(
            channel_id=channel_id,
            conteudo=message.content.strip(),
            autor_id=str(payload.user_id),
            autor_nome=autor_nome,
            tags=["reaction_save"],
        )
        logger.info(
            "Nota #%s salva via reação 📝 no canal %s (%s)",
            nota["id"],
            channel_id,
            topico.get("topic_name"),
        )
        try:
            await message.add_reaction("✅")
        except Exception:
            pass
    except Exception as e_react:
        logger.warning("Erro ao processar reação 📝 para salvar nota: %s", e_react)


def main():
    """Valida configurações essenciais e inicia a execução do bot."""
    # Garante que apenas um processo do bot seja executado por vez
    if not adquirir_lock_instancia_unica():
        sys.exit(0)

    if not DISCORD_TOKEN or DISCORD_TOKEN == "SEU_TOKEN_AQUI":
        logger.error(
            "DISCORD_TOKEN não foi configurado. "
            "Por favor, configure o arquivo discord/.env com o token do seu bot."
        )
        sys.exit(1)

    logger.info("Iniciando o bot Discord...")
    client.run(DISCORD_TOKEN)


if __name__ == "__main__":
    main()