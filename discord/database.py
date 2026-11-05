"""
Camada de Acesso a Dados (SQLite).

Responsável pelo armazenamento, concatenação e recuperação do histórico
de mensagens de conversação de cada usuário no Discord.
"""

from pathlib import Path
import sqlite3
from typing import Any, Dict, List, Optional, Tuple
from config import DB_FILE, HISTORICO_LIMITE_PADRAO


def _get_db_path(db_path: Optional[str] = None) -> str:
    """Retorna o caminho do arquivo de banco de dados."""
    caminho = db_path or DB_FILE
    # Garante que o diretório pai exista se for um arquivo com pasta
    parent = Path(caminho).parent
    if parent and not parent.exists():
        parent.mkdir(parents=True, exist_ok=True)
    return str(caminho)


def _get_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    """Abre uma conexão com o SQLite configurada com timeout de 30s para evitar travamentos."""
    caminho = _get_db_path(db_path)
    return sqlite3.connect(caminho, timeout=30.0)


def init_db(db_path: Optional[str] = None) -> None:
    """Inicializa a estrutura do banco de dados SQLite (mensagens, listas e lembretes)."""
    caminho = _get_db_path(db_path)
    with _get_connection(db_path) as conn:
        cursor = conn.cursor()
        # Habilita Write-Ahead Logging (WAL) para alta concorrência sem bloqueios de leitura/escrita
        cursor.execute("PRAGMA journal_mode = WAL;")
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        # Cria índices para otimizar consultas por usuário e ordenação
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_messages_user_id 
            ON messages (user_id, id DESC)
            """
        )
        # Garante a existência da coluna channel_id para isolamento de sessão por canal (IDEA-25)
        cursor.execute("PRAGMA table_info(messages);")
        colunas_msgs = [c[1] for c in cursor.fetchall()]
        if "channel_id" not in colunas_msgs:
            cursor.execute("ALTER TABLE messages ADD COLUMN channel_id TEXT DEFAULT NULL;")
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_messages_channel_id 
            ON messages (channel_id, id DESC)
            """
        )

        # Cria tabela de configurações e preferências do usuário (ex: modo de resposta texto/áudio)
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS user_settings (
                user_id TEXT PRIMARY KEY,
                response_mode TEXT NOT NULL DEFAULT 'texto',
                voice_name TEXT NOT NULL DEFAULT 'pt-BR-FranciscaNeural',
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        # Cria tabela de preferências de modelo e provedor LLM (Local vs Google Gemini vs Auto)
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS user_model_preferences (
                user_id TEXT PRIMARY KEY,
                user_name TEXT NOT NULL,
                provider TEXT NOT NULL DEFAULT 'local',
                model_name TEXT NOT NULL DEFAULT 'qwen/qwen3.5-9b',
                auto_failover INTEGER DEFAULT 1,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.commit()

    # Inicializa tabelas dos subsistemas
    from list_manager import init_list_db
    from reminder_manager import init_reminder_db
    from digest_manager import init_digest_db
    from pdf_manager import init_pdf_db
    from prompt_hub import init_prompt_hub_db
    from persona_manager import init_persona_db
    from topic_manager import init_topic_db
    init_list_db(caminho)
    init_reminder_db(caminho)
    init_digest_db(caminho)
    init_pdf_db(caminho)
    init_prompt_hub_db(caminho)
    init_persona_db(caminho)
    init_topic_db(caminho)


def salvar_mensagem(
    user_id: str | int,
    role: str,
    content: str,
    channel_id: Optional[str | int] = None,
    db_path: Optional[str] = None,
) -> None:
    """Salva uma mensagem no histórico.
    
    Se a última mensagem no mesmo contexto (user_id e channel_id) for da mesma 'role',
    concatena o novo conteúdo. Caso contrário, cria um novo registro.
    """
    if not content or not str(content).strip():
        return

    user_str = str(user_id)
    c_str = str(channel_id).strip() if channel_id else None

    with _get_connection(db_path) as conn:
        cursor = conn.cursor()
        if c_str:
            cursor.execute(
                """
                SELECT id, role, content 
                FROM messages 
                WHERE user_id = ? AND channel_id = ?
                ORDER BY id DESC 
                LIMIT 1
                """,
                (user_str, c_str)
            )
        else:
            cursor.execute(
                """
                SELECT id, role, content 
                FROM messages 
                WHERE user_id = ? AND channel_id IS NULL
                ORDER BY id DESC 
                LIMIT 1
                """,
                (user_str,)
            )
        ultima_msg = cursor.fetchone()

        if ultima_msg and ultima_msg[1] == role:
            # Mesma role: concatena o novo conteúdo ao existente
            msg_id, _, conteudo_anterior = ultima_msg
            novo_conteudo = f"{conteudo_anterior}\n\n{content}"
            cursor.execute(
                """
                UPDATE messages 
                SET content = ? 
                WHERE id = ?
                """,
                (novo_conteudo, msg_id)
            )
        else:
            # Role diferente ou histórico vazio: insere novo registro
            cursor.execute(
                """
                INSERT INTO messages (user_id, role, content, channel_id) 
                VALUES (?, ?, ?, ?)
                """,
                (user_str, role, content, c_str)
            )
        conn.commit()


def obter_historico(
    user_id: str | int,
    limite: int = HISTORICO_LIMITE_PADRAO,
    channel_id: Optional[str | int] = None,
    db_path: Optional[str] = None,
) -> List[Dict[str, str]]:
    """Retorna as últimas N mensagens para manter o contexto na LLM.
    
    Se channel_id for fornecido, recupera estritamente o histórico daquele canal/thread.
    Garante que a primeira mensagem da lista seja sempre do tipo 'user'.
    """
    user_str = str(user_id)
    c_str = str(channel_id).strip() if channel_id else None

    with _get_connection(db_path) as conn:
        cursor = conn.cursor()
        if c_str:
            cursor.execute(
                """
                SELECT role, content 
                FROM messages 
                WHERE channel_id = ? 
                ORDER BY id DESC 
                LIMIT ?
                """,
                (c_str, limite)
            )
        else:
            cursor.execute(
                """
                SELECT role, content 
                FROM messages 
                WHERE user_id = ? 
                ORDER BY id DESC 
                LIMIT ?
                """,
                (user_str, limite)
            )
        linhas = cursor.fetchall()

    # Ordem cronológica (mais antiga -> mais recente)
    historico = [{"role": role, "content": content} for role, content in reversed(linhas)]

    # Encontra o índice da primeira mensagem de "user"
    primeiro_indice_user = next(
        (i for i, msg in enumerate(historico) if msg["role"] == "user"),
        None
    )

    # Se encontrou um "user", descarta o que veio antes; se não houver "user", retorna vazio
    if primeiro_indice_user is not None:
        return historico[primeiro_indice_user:]

    return []


def limpar_historico(user_id: str | int, db_path: Optional[str] = None) -> int:
    """Apaga o histórico de mensagens de um usuário específico.
    
    Retorna a quantidade de registros apagados.
    """
    user_str = str(user_id)

    with _get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM messages WHERE user_id = ?", (user_str,))
        removidos = cursor.rowcount
        conn.commit()
    return removidos


def contar_mensagens(user_id: str | int, db_path: Optional[str] = None) -> int:
    """Retorna a quantidade total de registros armazenados para o usuário."""
    user_str = str(user_id)

    with _get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM messages WHERE user_id = ?", (user_str,))
        row = cursor.fetchone()
        return row[0] if row else 0


# ==============================================================================
# CONFIGURAÇÕES DE PREFERÊNCIA DO USUÁRIO (MODO DE RESPOSTA TEXTO / ÁUDIO / AMBOS)
# ==============================================================================

MODOS_RESPOSTA_VALIDOS = {"texto", "audio", "ambos"}


def normalizar_modo_resposta(modo: str) -> Optional[str]:
    """Normaliza expressões comuns para 'texto', 'audio' ou 'ambos'."""
    m = (modo or "").strip().lower()
    if m in ("texto", "text", "mensagem", "escrito", "apenas texto", "so texto", "somente texto"):
        return "texto"
    if m in ("audio", "voz", "áudio", "som", "narracao", "apenas audio", "so audio", "somente audio", "apenas voz", "so voz"):
        return "audio"
    if m in ("ambos", "tudo", "dois", "duas", "duas opcoes", "texto e audio", "audio e texto", "texto_e_audio", "audio_e_texto", "texto e voz", "voz e texto"):
        return "ambos"
    return None


def obter_modo_resposta(user_id: str | int, db_path: Optional[str] = None) -> str:
    """Retorna o modo de resposta configurado pelo usuário ('texto', 'audio' ou 'ambos').
    
    Padrão se não configurado: 'texto'.
    """
    user_str = str(user_id)
    with _get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT response_mode FROM user_settings WHERE user_id = ?", (user_str,))
        row = cursor.fetchone()
        if row and row[0] in MODOS_RESPOSTA_VALIDOS:
            return row[0]
    return "texto"


def definir_modo_resposta(user_id: str | int, modo: str, db_path: Optional[str] = None) -> Dict[str, Any]:
    """Define o modo de resposta preferido pelo usuário ('texto', 'audio' ou 'ambos')."""
    modo_norm = normalizar_modo_resposta(modo)
    if not modo_norm:
        return {
            "sucesso": False,
            "mensagem": f"Modo '{modo}' inválido. Escolha entre: `texto`, `audio` ou `ambos`."
        }

    user_str = str(user_id)
    with _get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO user_settings (user_id, response_mode, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id) DO UPDATE SET
                response_mode = excluded.response_mode,
                updated_at = CURRENT_TIMESTAMP
            """,
            (user_str, modo_norm)
        )
        conn.commit()

    descricoes = {
        "texto": "Apenas Texto (mensagens escritas convencionais)",
        "audio": "Apenas Áudio (mensagens de voz narradas pela Francisca pt-BR)",
        "ambos": "Texto e Áudio (mensagens de texto acompanhadas de áudio narrado)",
    }
    return {
        "sucesso": True,
        "modo": modo_norm,
        "descricao": descricoes[modo_norm],
        "mensagem": f"Modo de resposta alterado com sucesso para: **{descricoes[modo_norm]}**."
    }


# ==============================================================================
# GESTÃO DE PREFERÊNCIAS DE MODELO & PROVEDOR LLM (LOCAL vs GOOGLE GEMINI vs AUTO)
# ==============================================================================

PROVEDORES_VALIDOS = ("local", "google", "gemini", "gemini-pro", "auto")


def normalizar_provedor_modelo(termo: str) -> Optional[Tuple[str, str]]:
    """Normaliza o identificador do provedor e modelo solicitado.

    Retorna uma tupla (provedor, nome_modelo_padrao) ou None caso não reconhecido.
    """
    if not termo:
        return None
    t = termo.strip().lower()
    if t in ("local", "lm-studio", "lmstudio", "offline", "qwen", "llama"):
        return "local", "qwen/qwen3.5-9b"
    if t in ("google", "gemini", "gemini-flash", "flash", "nuvem", "cloud"):
        return "google", "gemini-3.5-flash"
    if t in ("gemini-pro", "pro", "google-pro"):
        return "google", "gemini-3.5-flash"
    if t in ("auto", "automatico", "automático", "dinamico", "dinâmico", "hibrido", "híbrido"):
        return "auto", "auto"
    return None


def obter_preferencia_modelo(user_id: str | int, db_path: Optional[str] = None) -> Dict[str, Any]:
    """Retorna a preferência de modelo/provedor configurada para o usuário."""
    user_str = str(user_id)
    with _get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT provider, model_name, auto_failover, updated_at
            FROM user_model_preferences
            WHERE user_id = ?
            """,
            (user_str,)
        )
        row = cursor.fetchone()
        if row:
            return {
                "provider": row[0],
                "model_name": row[1],
                "auto_failover": bool(row[2]),
                "updated_at": row[3],
            }
    return {
        "provider": "local",
        "model_name": "qwen/qwen3.5-9b",
        "auto_failover": True,
        "updated_at": None,
    }


def definir_preferencia_modelo(
    user_id: str | int,
    user_name: str,
    provedor: str,
    nome_modelo: Optional[str] = None,
    auto_failover: bool = True,
    db_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Salva a preferência de modelo do usuário no SQLite."""
    res_norm = normalizar_provedor_modelo(provedor)
    if not res_norm:
        return {
            "sucesso": False,
            "mensagem": f"Provedor '{provedor}' não reconhecido. Opções válidas: `local`, `google` (ou `gemini`), `gemini-pro`, `auto`."
        }
    prov, mod_padrao = res_norm
    mod_final = nome_modelo if (nome_modelo and nome_modelo.strip()) else mod_padrao

    user_str = str(user_id)
    with _get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO user_model_preferences (user_id, user_name, provider, model_name, auto_failover, updated_at)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id) DO UPDATE SET
                user_name = excluded.user_name,
                provider = excluded.provider,
                model_name = excluded.model_name,
                auto_failover = excluded.auto_failover,
                updated_at = CURRENT_TIMESTAMP
            """,
            (user_str, user_name, prov, mod_final, 1 if auto_failover else 0)
        )
        conn.commit()

    nomes_exibicao = {
        "local": f"🏠 LM Studio Local (`{mod_final}`)",
        "google": f"⚡ Google Gemini (`{mod_final}`)",
        "auto": "🔀 Roteamento Inteligente (Local para rotina + Google para tarefas pesadas)",
    }
    return {
        "sucesso": True,
        "provider": prov,
        "model_name": mod_final,
        "auto_failover": auto_failover,
        "descricao": nomes_exibicao.get(prov, prov),
        "mensagem": f"Modelo ativo configurado com sucesso para: **{nomes_exibicao.get(prov, prov)}**."
    }

