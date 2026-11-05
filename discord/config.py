"""
Módulo de Configuração Central do Bot Discord.

Carrega variáveis de ambiente, define constantes operacionais e caminhos
de diretório para garantir portabilidade e consistência entre os módulos.
"""

import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Diretório base da pasta do discord
BASE_DIR = Path(__file__).resolve().parent

# Carrega o arquivo .env localizado na pasta discord ou na raiz
env_path = BASE_DIR / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    load_dotenv()

# Tokens e identificadores do Discord
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
DISCORD_USER = os.getenv("DISCORD_USER")

# Configurações do LM Studio / Provedor OpenAI compatível
LM_STUDIO_URL = os.getenv("LM_STUDIO_URL", "http://localhost:1234/v1")
LM_STUDIO_API_KEY = os.getenv("LM_STUDIO_API_KEY", "lm-studio")
MODELO_LLM = os.getenv("MODELO_LLM", "qwen/qwen3.5-9b")

# Configurações do Google Gemini & Roteamento Híbrido
DEFAULT_LLM_PROVIDER = os.getenv("DEFAULT_LLM_PROVIDER", "local")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_FLASH_MODEL = os.getenv("GEMINI_FLASH_MODEL", "gemini-3.5-flash")
GEMINI_PRO_MODEL = os.getenv("GEMINI_PRO_MODEL", "gemini-3.5-flash")
GEMINI_API_BASE_URL = os.getenv("GEMINI_API_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai/")
ENABLE_AUTO_FAILOVER = os.getenv("ENABLE_AUTO_FAILOVER", "true").lower() in ("true", "1", "yes")
LOCAL_TIMEOUT_FAILOVER_SECONDS = float(os.getenv("LOCAL_TIMEOUT_FAILOVER_SECONDS", "15.0"))

def _resolver_caminho_config(caminho_str: Optional[str], padrao: Path) -> str:
    if not caminho_str:
        return str(padrao.resolve())
    p = Path(caminho_str)
    if p.is_absolute():
        return str(p)
    partes = p.parts
    if partes and partes[0] == "discord" and BASE_DIR.name == "discord":
        return str((BASE_DIR.parent / p).resolve())
    return str((BASE_DIR / p).resolve())

# Configurações do Banco de Dados SQLite e ChromaDB
DB_FILE = _resolver_caminho_config(os.getenv("DB_FILE"), BASE_DIR / "chat_memory.db")
CHROMA_DIR = _resolver_caminho_config(os.getenv("CHROMA_DIR"), BASE_DIR / "chroma_db")
LM_STUDIO_EMBEDDING_URL = os.getenv("LM_STUDIO_EMBEDDING_URL", LM_STUDIO_URL)
LM_STUDIO_EMBEDDING_MODEL = os.getenv("LM_STUDIO_EMBEDDING_MODEL", "text-embedding-qwen3-embedding-4b")
RAG_TOP_K = int(os.getenv("RAG_TOP_K", "3"))

# Configurações de Comandos e Limites
COMMAND_PREFIX = os.getenv("COMMAND_PREFIX", "!")
MAX_DISCORD_MSG_LENGTH = 2000
MAX_CHUNK_LENGTH = 1900
MAX_TOOL_CALL_ITERATIONS = int(os.getenv("MAX_TOOL_CALL_ITERATIONS", "5"))
HISTORICO_LIMITE_PADRAO = int(os.getenv("HISTORICO_LIMITE_PADRAO", "10"))
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.7"))
LLM_TIMEOUT_SECONDS = float(os.getenv("LLM_TIMEOUT_SECONDS", "60.0"))

# Configurações de Filtragem Semântica de Tools (Tool RAG)
TOOL_FILTER_ENABLED = os.getenv("TOOL_FILTER_ENABLED", "true").lower() in ("true", "1", "yes")
TOOL_FILTER_TOP_K = int(os.getenv("TOOL_FILTER_TOP_K", "5"))
TOOL_FILTER_MIN_SIMILARITY = float(os.getenv("TOOL_FILTER_MIN_SIMILARITY", "0.20"))

# Configurações do Google Calendar
GOOGLE_CREDENTIALS_FILE = os.getenv("GOOGLE_CREDENTIALS_FILE", str(BASE_DIR / "credentials.json"))
GOOGLE_TOKEN_FILE = os.getenv("GOOGLE_TOKEN_FILE", str(BASE_DIR / "token.json"))
CALENDAR_DEFAULT_TIMEZONE = os.getenv("CALENDAR_DEFAULT_TIMEZONE", "America/Sao_Paulo")

# Configurações de Transcrição de Áudio (faster-whisper)
WHISPER_MODEL_SIZE = os.getenv("WHISPER_MODEL_SIZE", "base")
WHISPER_LANGUAGE = os.getenv("WHISPER_LANGUAGE", "pt")
WHISPER_DEVICE = os.getenv("WHISPER_DEVICE", "cpu")
WHISPER_COMPUTE_TYPE = os.getenv("WHISPER_COMPUTE_TYPE", "int8")

# Configurações de Síntese de Voz (edge-tts)
TTS_ENABLED = os.getenv("TTS_ENABLED", "true").lower() in ("true", "1", "yes")
TTS_VOICE = os.getenv("TTS_VOICE", "pt-BR-FranciscaNeural")
TTS_DEFAULT_MODE = os.getenv("TTS_DEFAULT_MODE", "texto")

# Configurações de Pesquisa na Web & Browsing
WEB_SEARCH_ENABLED = os.getenv("WEB_SEARCH_ENABLED", "true").lower() in ("true", "1", "yes")
WEB_SEARCH_PROVIDER = os.getenv("WEB_SEARCH_PROVIDER", "duckduckgo").lower()
WEB_SEARCH_MAX_RESULTS = int(os.getenv("WEB_SEARCH_MAX_RESULTS", "4"))
WEB_SEARCH_TIMEOUT = float(os.getenv("WEB_SEARCH_TIMEOUT", "12.0"))
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")
SEARXNG_URL = os.getenv("SEARXNG_URL", "")

# Prompt do Sistema
SYSTEM_PROMPT = os.getenv(
    "SYSTEM_PROMPT",
    "Você é um assistente pessoal prestativo respondendo via Discord. "
    "Lembre-se do contexto da conversa. Você tem acesso a ferramentas para:\n"
    "1. Gerenciar arquivos PDF na pasta pessoal ('listar_meus_pdfs', 'disponibilizar_pdf_usuario').\n"
    "2. Gerenciar a agenda do Google Calendar: use 'listar_agenda_google' para consultar compromissos, "
    "'adicionar_evento_google' para agendar novos eventos e 'remover_evento_google' para cancelar ou excluir compromissos.\n"
    "3. Buscar na memória vetorial do ChromaDB ('consultar_memoria_passada').\n"
    "4. Gerenciar listas de compras, mercado ou tarefas ('adicionar_item_lista', 'ver_itens_lista', 'ticar_item_lista', 'remover_item_lista', 'limpar_itens_concluidos_lista', 'listar_minhas_listas').\n"
    "5. Agendar avisos e lembretes para o usuário ('criar_lembrete', 'listar_meus_lembretes', 'cancelar_lembrete').\n"
    "6. Configurar o modo de resposta do bot (texto, áudio ou ambos) através de 'configurar_modo_resposta'.\n"
    "7. Gerar e configurar o Resumo Matinal Diário ('gerar_resumo_matinal', 'configurar_resumo_matinal') com compromissos, lembretes, listas e clima.\n"
    "8. Analisar livros/PDFs salvos, consultar metadados, listar sumários de capítulos, resumir capítulos específicos e responder a dúvidas sobre o conteúdo da obra através de RAG ('consultar_metadados_pdf', 'obter_sumario_pdf', 'resumir_capitulo_pdf', 'indexar_pdf_rag', 'consultar_conteudo_pdf_rag').\n"
    "9. Pesquisar na internet fatos em tempo real, notícias, clima, cotações e documentações ('buscar_na_web') e extrair o conteúdo limpo de links e páginas web ('ler_pagina_web'). Sempre cite a fonte das informações pesquisadas.\n"
    "Gere respostas curtas e objetivas e de no máximo 2000 caracteres, sempre de bom humor."
)

# ------------------------------------------------------------------------------
# 8. MESSAGE GATEWAY & OUTBOX ANTI-SPAM (IDEA-24)
# ------------------------------------------------------------------------------
MESSAGE_GATEWAY_ENABLED = os.getenv("MESSAGE_GATEWAY_ENABLED", "true").lower() in ("true", "1", "yes")
GATEWAY_LEAKY_BUCKET_INTERVAL_SEC = float(os.getenv("GATEWAY_LEAKY_BUCKET_INTERVAL_SEC", "1.5"))
GATEWAY_DEBOUNCE_WINDOW_SEC = int(os.getenv("GATEWAY_DEBOUNCE_WINDOW_SEC", "60"))
GATEWAY_CIRCUIT_BREAKER_MAX_MSGS = int(os.getenv("GATEWAY_CIRCUIT_BREAKER_MAX_MSGS", "8"))
GATEWAY_CIRCUIT_BREAKER_COOLDOWN_SEC = int(os.getenv("GATEWAY_CIRCUIT_BREAKER_COOLDOWN_SEC", "30"))
GATEWAY_PERSISTENCE_ENABLED = os.getenv("GATEWAY_PERSISTENCE_ENABLED", "true").lower() in ("true", "1", "yes")

# ------------------------------------------------------------------------------
# 9. DISCORD UI INTERATIVA (BUTTONS, MENUS, MODALS) (IDEA-08)
# ------------------------------------------------------------------------------
DISCORD_UI_COMPONENTS_ENABLED = os.getenv("DISCORD_UI_COMPONENTS_ENABLED", "true").lower() in ("true", "1", "yes")
DISCORD_UI_TIMEOUT_SECONDS = int(os.getenv("DISCORD_UI_TIMEOUT_SECONDS", "180"))


