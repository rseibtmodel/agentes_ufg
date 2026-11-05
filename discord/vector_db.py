"""
Gerenciador de Memória Vetorial Persistente com ChromaDB e LM Studio Embeddings.

Responsável por:
1. Conectar ao servidor de embeddings do LM Studio (text-embedding-qwen3-embedding-4b).
2. Manter uma coleção vetorial isolada por usuário nomeada como `{user}_memory`.
3. Inserir mensagens do usuário e respostas do assistente na base vetorial.
4. Recuperar memórias passadas semanticamente relevantes para enriquecer prompts futuros (RAG).
"""

from datetime import datetime
import logging
from pathlib import Path
import re
from typing import Any, Dict, List, Optional
import uuid
import chromadb
from openai import AsyncOpenAI
from config import (
    CHROMA_DIR,
    LM_STUDIO_API_KEY,
    LM_STUDIO_EMBEDDING_MODEL,
    LM_STUDIO_EMBEDDING_URL,
    RAG_TOP_K,
)

logger = logging.getLogger(__name__)

# Garante a existência do diretório do ChromaDB
Path(CHROMA_DIR).mkdir(parents=True, exist_ok=True)

# Cliente persistente do ChromaDB
_chroma_client = chromadb.PersistentClient(path=str(CHROMA_DIR))

# Cliente assíncrono para o servidor de embeddings do LM Studio
_embedding_client = AsyncOpenAI(
    base_url=LM_STUDIO_EMBEDDING_URL,
    api_key=LM_STUDIO_API_KEY,
    timeout=30.0,
)


def sanitizar_nome_colecao(usuario: str) -> str:
    """Normaliza o identificador do usuário para o padrão '{user}_memory' compatível com ChromaDB.
    
    Regras do ChromaDB: 3-63 caracteres, apenas alfanuméricos, underscores e hifens.
    """
    user_str = getattr(usuario, "name", str(usuario)).strip()
    # Substitui caracteres inválidos por underscore
    limpo = re.sub(r"[^a-zA-Z0-9_\-]", "_", user_str).strip("_")
    if not limpo:
        limpo = "usuario"

    # Garante tamanho máximo permitindo sufixo _memory (7 caracteres)
    nome_base = limpo[:55]
    nome_colecao = f"{nome_base}_memory"
    return nome_colecao


def obter_colecao_usuario(usuario: str):
    """Obtém ou cria a coleção vetorial dedicada do usuário '{user}_memory'."""
    nome_colecao = sanitizar_nome_colecao(usuario)
    return _chroma_client.get_or_create_collection(
        name=nome_colecao,
        metadata={"descricao": f"Memoria vetorial semantica do usuario {usuario}"}
    )


async def gerar_embedding(texto: str) -> Optional[List[float]]:
    """Gera o vetor de embedding para o texto através do endpoint do LM Studio."""
    if not texto or not texto.strip():
        return None

    try:
        response = await _embedding_client.embeddings.create(
            model=LM_STUDIO_EMBEDDING_MODEL,
            input=texto.strip(),
        )
        return response.data[0].embedding
    except Exception as e:
        logger.warning(
            "Falha ao gerar embedding no LM Studio (%s) com modelo %s: %s",
            LM_STUDIO_EMBEDDING_URL,
            LM_STUDIO_EMBEDDING_MODEL,
            e,
        )
        return None


async def salvar_memoria_vetorial(
    usuario: str,
    role: str,
    content: str,
    metadata_extra: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    """Gera embedding e persiste uma mensagem na coleção '{user}_memory' do ChromaDB."""
    texto = (content or "").strip()
    if not texto:
        return None

    vetor = await gerar_embedding(texto)
    if not vetor:
        logger.info("Memória vetorial não persistida devido à indisponibilidade de embedding.")
        return None

    colecao = obter_colecao_usuario(usuario)
    doc_id = str(uuid.uuid4())
    timestamp = datetime.now().isoformat()

    metadata = {
        "role": str(role),
        "usuario": str(usuario),
        "timestamp": timestamp,
    }
    if metadata_extra:
        for k, v in metadata_extra.items():
            metadata[k] = str(v)

    try:
        colecao.add(
            ids=[doc_id],
            embeddings=[vetor],
            documents=[texto],
            metadatas=[metadata],
        )
        logger.info(
            "Memória vetorial gravada na coleção '%s' (role=%s, doc_id=%s)",
            colecao.name,
            role,
            doc_id,
        )
        return doc_id
    except Exception as e:
        logger.exception("Erro ao inserir memória no ChromaDB: %s", e)
        return None


async def buscar_memorias_relevantes(
    usuario: str,
    query: str,
    top_k: int = RAG_TOP_K,
) -> List[Dict[str, Any]]:
    """Busca semanticamente na coleção '{user}_memory' as mensagens mais relevantes para a query."""
    texto_query = (query or "").strip()
    if not texto_query:
        return []

    colecao = obter_colecao_usuario(usuario)
    if colecao.count() == 0:
        return []

    vetor_query = await gerar_embedding(texto_query)
    if not vetor_query:
        return []

    try:
        limite = min(top_k, colecao.count())
        resultados = colecao.query(
            query_embeddings=[vetor_query],
            n_results=limite,
            include=["documents", "metadatas", "distances"],
        )

        documentos = resultados.get("documents", [[]])[0]
        metadatas = resultados.get("metadatas", [[]])[0]
        distancias = resultados.get("distances", [[]])[0]

        memorias = []
        for i in range(len(documentos)):
            meta = metadatas[i] if i < len(metadatas) else {}
            distancia = distancias[i] if i < len(distancias) else 0.0
            memorias.append({
                "conteudo": documentos[i],
                "role": meta.get("role", "desconhecido"),
                "timestamp": meta.get("timestamp", ""),
                "distancia": round(float(distancia), 4),
            })

        return memorias
    except Exception as e:
        logger.warning("Erro na consulta vetorial no ChromaDB: %s", e)
        return []


def contar_memorias(usuario: str) -> int:
    """Retorna o total de memórias armazenadas na coleção '{user}_memory'."""
    colecao = obter_colecao_usuario(usuario)
    return colecao.count()


def limpar_memoria_vetorial(usuario: str) -> bool:
    """Exclui e recria a coleção vetorial '{user}_memory' do usuário."""
    nome_colecao = sanitizar_nome_colecao(usuario)
    try:
        _chroma_client.delete_collection(name=nome_colecao)
        _chroma_client.create_collection(
            name=nome_colecao,
            metadata={"descricao": f"Memoria vetorial semantica do usuario {usuario}"}
        )
        logger.info("Coleção vetorial '%s' reiniciada com sucesso.", nome_colecao)
        return True
    except Exception as e:
        logger.warning("Falha ao limpar coleção '%s': %s", nome_colecao, e)
        return False


# ==============================================================================
# KNOWLEDGE HUB TEMÁTICO: RAG ISOLADO POR CANAL (IDEA-25)
# ==============================================================================

def sanitizar_nome_colecao_topico(channel_id: str | int) -> str:
    """Normaliza o identificador do canal para o padrão 'topic_notes_{channel_id}' compatível com ChromaDB."""
    c_str = str(channel_id).strip()
    limpo = re.sub(r"[^a-zA-Z0-9_\-]", "_", c_str).strip("_")
    if not limpo:
        limpo = "geral"
    # Máximo 63 caracteres conforme spec do ChromaDB
    nome = f"topic_notes_{limpo}"[:63]
    return nome


def obter_colecao_topico(channel_id: str | int):
    """Obtém ou cria a coleção vetorial dedicada e exclusiva do canal temático."""
    nome_colecao = sanitizar_nome_colecao_topico(channel_id)
    return _chroma_client.get_or_create_collection(
        name=nome_colecao,
        metadata={"descricao": f"Knowledge Hub RAG isolado do canal {channel_id}"}
    )


async def salvar_nota_vetorial(
    channel_id: str | int,
    note_id: str,
    content: str,
    metadata_extra: Optional[Dict[str, Any]] = None,
) -> bool:
    """Gera embedding e persiste uma nota na coleção vetorial exclusiva do canal temático."""
    texto = (content or "").strip()
    if not texto:
        return False

    vetor = await gerar_embedding(texto)
    if not vetor:
        logger.warning("Não foi possível gerar embedding para nota %s no canal %s.", note_id, channel_id)
        return False

    meta = {
        "note_id": str(note_id),
        "channel_id": str(channel_id),
        "timestamp": datetime.utcnow().isoformat(),
    }
    if metadata_extra:
        for k, v in metadata_extra.items():
            if isinstance(v, (str, int, float, bool)):
                meta[k] = v
            elif isinstance(v, (list, tuple)):
                meta[k] = ", ".join(str(item) for item in v)

    try:
        colecao = obter_colecao_topico(channel_id)
        colecao.upsert(
            ids=[str(note_id)],
            embeddings=[vetor],
            documents=[texto],
            metadatas=[meta],
        )
        logger.info("Nota %s vetorizada com sucesso na coleção do canal %s.", note_id, channel_id)
        return True
    except Exception as e:
        logger.error("Falha ao salvar nota vetorial %s no canal %s: %s", note_id, channel_id, e)
        return False


async def buscar_notas_canal_vetorial(
    channel_id: str | int,
    consulta_texto: str,
    top_k: int = 4,
) -> List[Dict[str, Any]]:
    """Executa busca semântica RAG estritamente isolada na coleção do canal temático."""
    query = (consulta_texto or "").strip()
    if not query:
        return []

    colecao = obter_colecao_topico(channel_id)
    if colecao.count() == 0:
        return []

    vetor_query = await gerar_embedding(query)
    if not vetor_query:
        return []

    try:
        limite = min(top_k, colecao.count())
        resultados = colecao.query(
            query_embeddings=[vetor_query],
            n_results=limite,
            include=["documents", "metadatas", "distances"],
        )

        documentos = resultados.get("documents", [[]])[0]
        metadatas = resultados.get("metadatas", [[]])[0]
        distancias = resultados.get("distances", [[]])[0]

        notas_relevantes = []
        for i in range(len(documentos)):
            meta = metadatas[i] if i < len(metadatas) else {}
            distancia = distancias[i] if i < len(distancias) else 0.0
            notas_relevantes.append({
                "conteudo": documentos[i],
                "note_id": meta.get("note_id", ""),
                "tags": meta.get("tags", ""),
                "user_id": meta.get("user_id", ""),
                "timestamp": meta.get("timestamp", ""),
                "distancia": round(float(distancia), 4),
            })

        return notas_relevantes
    except Exception as e:
        logger.warning("Erro na consulta vetorial RAG do canal %s: %s", channel_id, e)
        return []


def remover_nota_vetorial(channel_id: str | int, note_id: str) -> bool:
    """Remove o vetor de uma nota da coleção ChromaDB do canal."""
    try:
        colecao = obter_colecao_topico(channel_id)
        colecao.delete(ids=[str(note_id)])
        return True
    except Exception as e:
        logger.warning("Falha ao remover vetor da nota %s no canal %s: %s", note_id, channel_id, e)
        return False


def limpar_colecao_topico(channel_id: str | int) -> bool:
    """Exclui todos os vetores e recria a coleção do canal temático."""
    nome_colecao = sanitizar_nome_colecao_topico(channel_id)
    try:
        _chroma_client.delete_collection(name=nome_colecao)
        _chroma_client.create_collection(
            name=nome_colecao,
            metadata={"descricao": f"Knowledge Hub RAG isolado do canal {channel_id}"}
        )
        logger.info("Coleção vetorial '%s' reiniciada com sucesso.", nome_colecao)
        return True
    except Exception as e:
        logger.warning("Falha ao limpar coleção temática '%s': %s", nome_colecao, e)
        return False

