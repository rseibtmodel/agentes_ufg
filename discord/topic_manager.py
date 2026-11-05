"""
Gerenciador de Tópicos e Banco de Notas Temático (Knowledge Hub) — IDEA-25.

Responsável por:
1. Vincular canais e threads do Discord a temas de conhecimento (topic_channels).
2. Persistir notas e anotações no SQLite (channel_notes) com tags e autor.
3. Indexar notas no ChromaDB (topic_notes_{channel_id}) de forma atômica e assíncrona.
4. Prover busca semântica RAG isolada por canal sem contaminação com a memória pessoal.
"""

import json
import logging
import re
import sqlite3
import uuid
from typing import Any, Dict, List, Optional
from config import DB_FILE
from vector_db import (
    buscar_notas_canal_vetorial,
    limpar_colecao_topico,
    remover_nota_vetorial,
    salvar_nota_vetorial,
)

logger = logging.getLogger(__name__)


def _get_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    caminho = db_path or DB_FILE
    return sqlite3.connect(caminho, timeout=30.0)


def init_topic_db(db_path: Optional[str] = None) -> None:
    """Inicializa as tabelas de tópicos e notas temáticas no SQLite."""
    with _get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS topic_channels (
                channel_id TEXT PRIMARY KEY,
                topic_slug TEXT NOT NULL,
                topic_name TEXT NOT NULL,
                description TEXT,
                auto_capture_mode INTEGER NOT NULL DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_topic_channels_slug ON topic_channels(topic_slug);")

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS channel_notes (
                id TEXT PRIMARY KEY,
                channel_id TEXT NOT NULL,
                topic_slug TEXT NOT NULL,
                user_id TEXT NOT NULL,
                content TEXT NOT NULL,
                tags TEXT,
                source_message_id TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (channel_id) REFERENCES topic_channels(channel_id) ON DELETE CASCADE
            )
            """
        )
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_channel_notes_topic ON channel_notes(topic_slug, channel_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_channel_notes_created ON channel_notes(created_at DESC);")
        conn.commit()
    logger.info("Tabelas topic_channels e channel_notes (IDEA-25) inicializadas com sucesso.")


def extrair_tags(texto: str) -> List[str]:
    """Extrai hashtags do texto (ex: #cbs, #reforma, #bug) normalizadas em minúsculas sem o prefixo #."""
    if not texto:
        return []
    tags = re.findall(r"#([a-zA-Z0-9_\-]+)", texto)
    return [t.lower() for t in tags]


def vincular_topico(
    channel_id: str | int,
    topic_slug: Optional[str] = None,
    topic_name: Optional[str] = None,
    description: Optional[str] = None,
    auto_capture_mode: bool = False,
    db_path: Optional[str] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Vincula o canal/thread a um tópico temático no SQLite."""
    c_id = str(channel_id).strip()
    nome = (topic_name or kwargs.get("nome") or topic_slug or "Tópico Geral").strip()
    slug_raw = topic_slug or kwargs.get("slug") or nome
    slug = re.sub(r"[^a-zA-Z0-9_\-]", "_", slug_raw.lower().strip()).strip("_")
    desc = (description or kwargs.get("topic_description") or kwargs.get("descricao") or "").strip()
    auto_cap = auto_capture_mode or kwargs.get("auto_capture", False)

    with _get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO topic_channels (channel_id, topic_slug, topic_name, description, auto_capture_mode, updated_at)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(channel_id) DO UPDATE SET
                topic_slug=excluded.topic_slug,
                topic_name=excluded.topic_name,
                description=excluded.description,
                auto_capture_mode=excluded.auto_capture_mode,
                updated_at=CURRENT_TIMESTAMP
            """,
            (c_id, slug, nome, desc, 1 if auto_cap else 0),
        )
        conn.commit()

    return {
        "sucesso": True,
        "mensagem": f"📌 Canal vinculado com sucesso ao tópico **{nome}** (`{slug}`)!",
        "topic_slug": slug,
        "topic_name": nome,
        "channel_id": c_id,
        "auto_capture_mode": bool(auto_cap),
    }


def obter_topico_canal(channel_id: str | int, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Consulta se o canal é um tópico temático ativo e retorna seus metadados."""
    c_id = str(channel_id).strip()
    with _get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT channel_id, topic_slug, topic_name, description, auto_capture_mode, created_at
            FROM topic_channels
            WHERE channel_id = ?
            """,
            (c_id,),
        )
        row = cursor.fetchone()
        if not row:
            return None
        return {
            "channel_id": row[0],
            "topic_slug": row[1],
            "topic_name": row[2],
            "description": row[3] or "",
            "auto_capture_mode": bool(row[4]),
            "created_at": row[5],
        }


def desvincular_topico(channel_id: str | int, db_path: Optional[str] = None) -> Dict[str, Any]:
    """Remove o vínculo do canal com o tópico (as notas salvas são preservadas)."""
    c_id = str(channel_id).strip()
    with _get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM topic_channels WHERE channel_id = ?", (c_id,))
        afetados = cursor.rowcount
        conn.commit()

    if afetados > 0:
        return {"sucesso": True, "mensagem": "🔓 Vínculo do canal com o tópico temático removido com sucesso."}
    return {"sucesso": False, "mensagem": "Este canal não estava vinculado a nenhum tópico."}


def definir_modo_livre(channel_id: str | int, ativo: bool, db_path: Optional[str] = None) -> Dict[str, Any]:
    """Ativa ou desativa a captura automática de mensagens como notas no canal."""
    c_id = str(channel_id).strip()
    topico = obter_topico_canal(c_id, db_path=db_path)
    if not topico:
        return {"sucesso": False, "mensagem": "Este canal precisa estar vinculado a um tópico primeiro (!topico vincular)."}

    with _get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE topic_channels SET auto_capture_mode = ?, updated_at = CURRENT_TIMESTAMP WHERE channel_id = ?",
            (1 if ativo else 0, c_id),
        )
        conn.commit()

    status = "ATIVADO (mensagens normais serão salvas como notas automaticamente)" if ativo else "DESATIVADO (apenas comandos !nota add ou reação 📝 salvam notas)"
    return {"sucesso": True, "mensagem": f"📝 Modo de captura livre: **{status}**."}


async def adicionar_nota(
    channel_id: str | int,
    user_id: str | int = "",
    content: str = "",
    tags: Optional[List[str]] = None,
    source_message_id: Optional[str | int] = None,
    db_path: Optional[str] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Registra uma nova nota no SQLite e indexa imediatamente no ChromaDB."""
    c_id = str(channel_id).strip()
    texto = (content or kwargs.get("conteudo") or "").strip()
    u_id = str(user_id or kwargs.get("autor_id") or "desconhecido").strip()

    if not texto:
        return {"sucesso": False, "mensagem": "O conteúdo da nota não pode ser vazio."}

    topico = obter_topico_canal(c_id, db_path=db_path)
    slug = topico["topic_slug"] if topico else "geral"

    # Extrai hashtags do texto e mescla com tags fornecidas explicitamente
    tags_auto = extrair_tags(texto)
    tags_finais = [str(t).lstrip("#").lower() for t in tags] if tags else []
    for t in tags_auto:
        t_clean = t.lstrip("#").lower()
        if t_clean not in tags_finais:
            tags_finais.append(t_clean)
    tags_json = json.dumps(tags_finais, ensure_ascii=False)

    note_id = str(uuid.uuid4())[:8]  # UUID curto de 8 caracteres legível

    # 1. Persistência Relacional no SQLite
    with _get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO channel_notes (id, channel_id, topic_slug, user_id, content, tags, source_message_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (note_id, c_id, slug, u_id, texto, tags_json, str(source_message_id) if source_message_id else None),
        )
        conn.commit()

    # 2. Indexação Vetorial no ChromaDB (topic_notes_{channel_id})
    try:
        await salvar_nota_vetorial(
            channel_id=c_id,
            note_id=note_id,
            content=texto,
            metadata_extra={"topic_slug": slug, "user_id": u_id, "tags": tags_finais},
        )
    except Exception as e_vec:
        logger.warning("Falha na indexação vetorial da nota %s: %s", note_id, e_vec)

    tags_str = f" `{' '.join(tags_finais)}`" if tags_finais else ""
    return {
        "sucesso": True,
        "mensagem": f"📝 Nota registrada com sucesso! ID: `{note_id}`{tags_str}",
        "id": note_id,
        "note_id": note_id,
        "topic_slug": slug,
        "tags": tags_finais,
        "content": texto,
        "conteudo": texto,
    }


def listar_notas(
    channel_id: str | int,
    tag: Optional[str] = None,
    limite: int = 10,
    termo_busca: Optional[str] = None,
    db_path: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Lista as notas mais recentes do canal temático com filtro opcional por tag ou termo."""
    c_id = str(channel_id).strip()
    tag_clean = tag.strip().lower().lstrip("#") if tag else None

    with _get_connection(db_path) as conn:
        cursor = conn.cursor()
        if tag_clean:
            cursor.execute(
                """
                SELECT id, channel_id, topic_slug, user_id, content, tags, created_at
                FROM channel_notes
                WHERE channel_id = ? AND LOWER(tags) LIKE ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (c_id, f"%{tag_clean}%", max(1, min(50, limite))),
            )
        elif termo_busca:
            cursor.execute(
                """
                SELECT id, channel_id, topic_slug, user_id, content, tags, created_at
                FROM channel_notes
                WHERE channel_id = ? AND LOWER(content) LIKE ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (c_id, f"%{termo_busca.lower().strip()}%", max(1, min(50, limite))),
            )
        else:
            cursor.execute(
                """
                SELECT id, channel_id, topic_slug, user_id, content, tags, created_at
                FROM channel_notes
                WHERE channel_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (c_id, max(1, min(50, limite))),
            )
        rows = cursor.fetchall()
        notas = []
        for r in rows:
            try:
                tags_list = json.loads(r[5]) if r[5] else []
            except Exception:
                tags_list = []
            notas.append({
                "id": r[0],
                "channel_id": r[1],
                "topic_slug": r[2],
                "user_id": r[3],
                "content": r[4],
                "tags": tags_list,
                "created_at": r[6],
            })
        return notas


def obter_nota(note_id: str, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Recupera os detalhes de uma nota específica pelo ID."""
    nid = note_id.strip()
    with _get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, channel_id, topic_slug, user_id, content, tags, created_at
            FROM channel_notes
            WHERE id = ?
            """,
            (nid,),
        )
        r = cursor.fetchone()
        if not r:
            return None
        try:
            tags_list = json.loads(r[5]) if r[5] else []
        except Exception:
            tags_list = []
        return {
            "id": r[0],
            "channel_id": r[1],
            "topic_slug": r[2],
            "user_id": r[3],
            "content": r[4],
            "tags": tags_list,
            "created_at": r[6],
        }


def remover_nota(note_id: str, channel_id: Optional[str | int] = None, db_path: Optional[str] = None) -> Dict[str, Any]:
    """Exclui a nota do SQLite e remove o vetor correspondente no ChromaDB."""
    nid = note_id.strip()
    nota = obter_nota(nid, db_path=db_path)
    if not nota:
        return {"sucesso": False, "mensagem": f"Nota `{nid}` não encontrada."}

    c_id = nota["channel_id"]
    with _get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM channel_notes WHERE id = ?", (nid,))
        conn.commit()

    # Remove vetor no ChromaDB
    remover_nota_vetorial(c_id, nid)

    return {"sucesso": True, "mensagem": f"🗑️ Nota `{nid}` excluída com sucesso da base temática!"}


def limpar_notas_topico(channel_id: str | int, db_path: Optional[str] = None) -> Dict[str, Any]:
    """Expurga todas as notas do canal temático no SQLite e no ChromaDB."""
    c_id = str(channel_id).strip()
    with _get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM channel_notes WHERE channel_id = ?", (c_id,))
        total = cursor.rowcount
        conn.commit()

    limpar_colecao_topico(c_id)
    return {"sucesso": True, "mensagem": f"🧹 Todas as {total} notas do canal foram expurgadas com sucesso."}


async def buscar_notas_rag(
    channel_id: str | int,
    consulta: str = "",
    top_k: int = 4,
    query: str = "",
) -> List[Dict[str, Any]]:
    """Executa busca semântica RAG isolada na coleção de notas do canal."""
    texto_busca = consulta or query
    return await buscar_notas_canal_vetorial(channel_id, texto_busca, top_k=top_k)


def listar_topicos(db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Lista todos os canais que possuem tópicos temáticos vinculados."""
    with _get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM topic_channels ORDER BY topic_name ASC")
        rows = cursor.fetchall()
        return [dict(r) for r in rows]


def alternar_auto_captura(channel_id: str | int, db_path: Optional[str] = None) -> bool:
    """Alterna o status do modo de auto-captura (modo livre) e retorna o novo booleano."""
    c_id = str(channel_id).strip()
    topico = obter_topico_canal(c_id, db_path=db_path)
    if not topico:
        return False
    novo_status = not bool(topico.get("auto_capture_mode", 0))
    definir_modo_livre(c_id, novo_status, db_path=db_path)
    return novo_status


def buscar_notas_texto(channel_id: str | int, termo: str, db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Busca textual direta de notas por palavra-chave no canal."""
    return listar_notas(channel_id, termo_busca=termo, db_path=db_path)


# Aliases de compatibilidade
limpar_notas_canal = limpar_notas_topico
listar_notas_canal = listar_notas
