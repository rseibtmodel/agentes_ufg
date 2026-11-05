"""
Gerenciador de Armazenamento, Análise Inteligente, Sumarização e RAG de Livros/PDFs.

Responsável por:
1. Isolar e organizar arquivos por usuário na pasta `discord/pdf/{user}/`.
2. Salvar anexos PDF recebidos via mensagens do Discord.
3. Pré-processar PDFs na ingestão (metadados, sumário/TOC, contagem de páginas e sinopse inicial).
4. Fornecer ficha catalográfica e sumário navegável de capítulos.
5. Sumarizar capítulos individuais sob demanda com cache em SQLite.
6. Indexar livros/documentos em coleções vetoriais dedicadas do ChromaDB.
7. Realizar busca semântica RAG no conteúdo do livro e responder com citação exata de páginas.
"""

import asyncio
from datetime import datetime
import json
import logging
from pathlib import Path
import re
import sqlite3
from typing import Any, Dict, List, Optional, Tuple
import chromadb
import discord
from openai import AsyncOpenAI
import pymupdf

from config import (
    BASE_DIR,
    CHROMA_DIR,
    DB_FILE,
    LM_STUDIO_API_KEY,
    LM_STUDIO_EMBEDDING_MODEL,
    LM_STUDIO_EMBEDDING_URL,
)

logger = logging.getLogger(__name__)

# Diretório base para armazenamento de PDFs
PDF_BASE_DIR = BASE_DIR / "pdf"

# Cliente ChromaDB dedicado para coleções de documentos/livros
Path(CHROMA_DIR).mkdir(parents=True, exist_ok=True)
_chroma_client = chromadb.PersistentClient(path=str(CHROMA_DIR))

# Cliente assíncrono para o servidor de embeddings do LM Studio
_embedding_client = AsyncOpenAI(
    base_url=LM_STUDIO_EMBEDDING_URL,
    api_key=LM_STUDIO_API_KEY,
    timeout=45.0,
)


def _get_db_path(db_path: Optional[str] = None) -> str:
    """Retorna o caminho do arquivo de banco de dados SQLite."""
    caminho = db_path or DB_FILE
    parent = Path(caminho).parent
    if parent and not parent.exists():
        parent.mkdir(parents=True, exist_ok=True)
    return str(caminho)


def _get_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    """Abre conexão com o SQLite configurada com timeout de 30s."""
    return sqlite3.connect(_get_db_path(db_path), timeout=30.0)


def init_pdf_db(db_path: Optional[str] = None) -> None:
    """Inicializa as tabelas de catálogo de PDFs e capítulos no SQLite."""
    with _get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA journal_mode = WAL;")

        # Tabela de documentos PDF catalogados
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS user_pdf_documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                user_name TEXT NOT NULL DEFAULT '',
                filename TEXT NOT NULL,
                filepath TEXT NOT NULL,
                title TEXT,
                author TEXT,
                total_pages INTEGER DEFAULT 0,
                file_size_bytes INTEGER DEFAULT 0,
                short_summary TEXT,
                is_indexed INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, filename)
            );
            """
        )

        # Tabela de capítulos e estrutura das obras
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS user_pdf_chapters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                doc_id INTEGER NOT NULL,
                chapter_index INTEGER NOT NULL,
                level INTEGER DEFAULT 1,
                title TEXT NOT NULL,
                start_page INTEGER NOT NULL,
                end_page INTEGER NOT NULL,
                summary TEXT,
                FOREIGN KEY(doc_id) REFERENCES user_pdf_documents(id) ON DELETE CASCADE
            );
            """
        )

        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_pdf_docs_user ON user_pdf_documents(user_id, filename);"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_pdf_chapters_doc ON user_pdf_chapters(doc_id, chapter_index);"
        )
        conn.commit()
    logger.info("Banco de dados de Catálogo de PDFs e Capítulos inicializado com sucesso.")


def sanitizar_nome_usuario(usuario: str | discord.User | discord.Member) -> str:
    """Sanitiza o identificador do usuário para uso seguro como nome de diretório."""
    nome = getattr(usuario, "name", str(usuario))
    sanitizado = re.sub(r"[^\w\-\.]", "_", nome).strip(" ._")
    return sanitizado or "usuario_desconhecido"


def obter_pasta_usuario(usuario: str | discord.User | discord.Member) -> Path:
    """Retorna o caminho da pasta de PDFs do usuário, criando-a se necessário."""
    nome_sanitizado = sanitizar_nome_usuario(usuario)
    pasta = PDF_BASE_DIR / nome_sanitizado
    pasta.mkdir(parents=True, exist_ok=True)
    return pasta


def formatar_tamanho(bytes_qty: int) -> str:
    """Converte quantidade de bytes em formato legível para humanos."""
    if bytes_qty < 1024:
        return f"{bytes_qty} B"
    elif bytes_qty < 1024 * 1024:
        return f"{bytes_qty / 1024:.1f} KB"
    else:
        return f"{bytes_qty / (1024 * 1024):.2f} MB"


def _sanitizar_nome_colecao_livro(usuario: str, doc_id: int | str) -> str:
    """Gera um nome de coleção ChromaDB válido para o livro do usuário (3 a 63 caracteres)."""
    user_sanitizado = re.sub(r"[^a-zA-Z0-9_\-]", "_", str(usuario)).strip("_")[:40]
    nome = f"pdf_{user_sanitizado}_{doc_id}"[:63]
    return nome


def obter_colecao_livro(usuario: str | discord.User | discord.Member, doc_id: int | str):
    """Obtém ou cria a coleção vetorial dedicada no ChromaDB para o livro especificado."""
    nome_usuario = getattr(usuario, "name", str(usuario))
    nome_colecao = _sanitizar_nome_colecao_livro(nome_usuario, doc_id)

    # 1. Tenta obter pelo nome de usuário
    try:
        col = _chroma_client.get_collection(name=nome_colecao)
        return col
    except Exception:
        pass

    # 2. Tenta obter pelo ID se usuário possuir atributo id
    if hasattr(usuario, "id"):
        nome_alt = _sanitizar_nome_colecao_livro(str(usuario.id), doc_id)
        try:
            return _chroma_client.get_collection(name=nome_alt)
        except Exception:
            pass

    return _chroma_client.get_or_create_collection(
        name=nome_colecao,
        metadata={"descricao": f"Colecao RAG do livro doc_id={doc_id} para usuario={nome_usuario}"},
    )



async def salvar_anexo_pdf(
    attachment: discord.Attachment,
    usuario: str | discord.User | discord.Member,
) -> Tuple[Path, int]:
    """Salva um anexo PDF do Discord na pasta do usuário."""
    pasta = obter_pasta_usuario(usuario)
    nome_arquivo = Path(attachment.filename).name
    if not nome_arquivo.lower().endswith(".pdf"):
        nome_arquivo += ".pdf"

    caminho_destino = pasta / nome_arquivo
    await attachment.save(str(caminho_destino))

    tamanho = caminho_destino.stat().st_size
    logger.info("PDF salvo com sucesso: %s (%s) para usuário %s", nome_arquivo, formatar_tamanho(tamanho), usuario)
    return caminho_destino, tamanho


def listar_pdfs_usuario(usuario: str | discord.User | discord.Member) -> List[Dict[str, Any]]:
    """Lista todos os arquivos PDF presentes na pasta do usuário com seus metadados."""
    pasta = obter_pasta_usuario(usuario)
    if not pasta.exists():
        return []

    arquivos = []
    for arquivo in sorted(pasta.glob("*.pdf"), key=lambda p: p.name.lower()):
        try:
            stat = arquivo.stat()
            modificado = datetime.fromtimestamp(stat.st_mtime).strftime("%d/%m/%Y %H:%M")
            arquivos.append({
                "nome": arquivo.name,
                "tamanho_bytes": stat.st_size,
                "tamanho_formatado": formatar_tamanho(stat.st_size),
                "modificado_em": modificado,
                "caminho": arquivo,
            })
        except OSError as e:
            logger.warning("Falha ao ler status do arquivo %s: %s", arquivo, e)

    return arquivos


def localizar_pdf_usuario(
    usuario: str | discord.User | discord.Member,
    termo_busca: str,
) -> Optional[Path]:
    """Localiza um arquivo PDF na pasta do usuário utilizando correspondência flexível."""
    if not termo_busca or not termo_busca.strip():
        return None

    pasta = obter_pasta_usuario(usuario).resolve()
    termo = termo_busca.strip()

    # 1. Busca exata direta
    candidato = (pasta / termo).resolve()
    if candidato.is_file() and candidato.is_relative_to(pasta):
        return candidato

    # 2. Busca exata com .pdf
    if not termo.lower().endswith(".pdf"):
        candidato_pdf = (pasta / f"{termo}.pdf").resolve()
        if candidato_pdf.is_file() and candidato_pdf.is_relative_to(pasta):
            return candidato_pdf

    # 3. Busca insensível a maiúsculas/minúsculas
    termo_lower = termo.lower()
    termo_com_pdf = termo_lower if termo_lower.endswith(".pdf") else f"{termo_lower}.pdf"
    todos_pdfs = list(pasta.glob("*.pdf"))

    for arq in todos_pdfs:
        if arq.name.lower() == termo_lower or arq.name.lower() == termo_com_pdf:
            if arq.resolve().is_relative_to(pasta):
                return arq

    # 4. Busca parcial (termo contido no nome do arquivo)
    termo_limpo = termo_lower.replace(".pdf", "")
    parciais = [
        arq for arq in todos_pdfs
        if termo_limpo in arq.name.lower() and arq.resolve().is_relative_to(pasta)
    ]

    if parciais:
        parciais.sort(key=lambda p: len(p.name))
        return parciais[0]

    return None


# ==============================================================================
# FASE 1: EXTRAÇÃO LEVE E PRÉ-PROCESSAMENTO NA INGESTÃO
# ==============================================================================

def _extrair_estrutura_pdf_sync(caminho_arquivo: Path) -> Dict[str, Any]:
    """Executa a extração síncrona de metadados, sumário e introdução via PyMuPDF."""
    doc = pymupdf.open(str(caminho_arquivo))
    total_paginas = len(doc)
    metadata = doc.metadata or {}

    titulo = (metadata.get("title") or "").strip()
    if not titulo:
        titulo = caminho_arquivo.stem.replace("_", " ").replace("-", " ").title()

    autor = (metadata.get("author") or "").strip()
    if not autor:
        autor = "Não informado"

    # 1. Extração de TOC (Table of Contents / Bookmarks)
    toc = doc.get_toc()  # [[level, title, page], ...]
    capitulos = []

    if toc:
        for i, item in enumerate(toc):
            level, cap_titulo, start_page = item
            next_page = toc[i + 1][2] if i + 1 < len(toc) else total_paginas + 1
            end_page = max(start_page, next_page - 1)
            if end_page > total_paginas:
                end_page = total_paginas
            capitulos.append({
                "chapter_index": i + 1,
                "level": level,
                "title": cap_titulo.strip(),
                "start_page": max(1, start_page),
                "end_page": max(1, end_page),
            })
    else:
        # Heurística caso o PDF não possua bookmarks
        # Verifica se há padrões de capítulos nas primeiras 20 páginas
        cap_encontrados = []
        padrao_cap = re.compile(
            r"^(?:cap[ií]tulo|chapter|se[çc][aã]o|parte|m[oó]dulo)\s+([0-9ivxlcdm]+)[\s:\-\.]*(.*)$",
            re.IGNORECASE | re.MULTILINE,
        )
        limite_busca = min(25, total_paginas)
        for num_p in range(limite_busca):
            texto_p = doc[num_p].get_text()
            for linha in texto_p.splitlines():
                linha_clean = linha.strip()
                match = padrao_cap.match(linha_clean)
                if match:
                    nome_completo = linha_clean[:80]
                    cap_encontrados.append((nome_completo, num_p + 1))
                    break

        if cap_encontrados:
            for i, (cap_tit, start_p) in enumerate(cap_encontrados):
                next_p = cap_encontrados[i + 1][1] if i + 1 < len(cap_encontrados) else total_paginas + 1
                end_p = max(start_p, next_p - 1)
                capitulos.append({
                    "chapter_index": i + 1,
                    "level": 1,
                    "title": cap_tit,
                    "start_page": start_p,
                    "end_page": min(total_paginas, end_p),
                })
        else:
            # Se não encontrou capítulos, divide por blocos de páginas lógicos
            if total_paginas <= 20:
                capitulos.append({
                    "chapter_index": 1,
                    "level": 1,
                    "title": "Documento Completo",
                    "start_page": 1,
                    "end_page": total_paginas,
                })
            else:
                bloco = 20
                idx = 1
                for st in range(1, total_paginas + 1, bloco):
                    ed = min(st + bloco - 1, total_paginas)
                    capitulos.append({
                        "chapter_index": idx,
                        "level": 1,
                        "title": f"Seção {idx} (Páginas {st} a {ed})",
                        "start_page": st,
                        "end_page": ed,
                    })
                    idx += 1

    # 2. Extração de Amostra Inicial (primeiras 2-3 páginas) para Sinopse Preliminar
    texto_amostra = ""
    for p_idx in range(min(3, total_paginas)):
        texto_amostra += doc[p_idx].get_text() + "\n"
    
    texto_amostra = re.sub(r"\s+", " ", texto_amostra).strip()
    sinopse = texto_amostra[:1200]
    if len(texto_amostra) > 1200:
        sinopse += "..."

    doc.close()

    return {
        "title": titulo,
        "author": autor,
        "total_pages": total_paginas,
        "file_size_bytes": caminho_arquivo.stat().st_size,
        "short_summary": sinopse,
        "chapters": capitulos,
    }


async def pre_processar_pdf(
    caminho_arquivo: Path,
    user_id: str | int,
    usuario_nome: str,
    db_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Executa o pré-processamento leve e grava os metadados no SQLite."""
    user_str = str(user_id)
    caminho_str = str(caminho_arquivo.resolve())
    nome_arquivo = caminho_arquivo.name

    dados = await asyncio.to_thread(_extrair_estrutura_pdf_sync, caminho_arquivo)

    with _get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO user_pdf_documents (
                user_id, user_name, filename, filepath, title, author,
                total_pages, file_size_bytes, short_summary, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id, filename) DO UPDATE SET
                filepath = excluded.filepath,
                title = excluded.title,
                author = excluded.author,
                total_pages = excluded.total_pages,
                file_size_bytes = excluded.file_size_bytes,
                short_summary = excluded.short_summary,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                user_str,
                usuario_nome,
                nome_arquivo,
                caminho_str,
                dados["title"],
                dados["author"],
                dados["total_pages"],
                dados["file_size_bytes"],
                dados["short_summary"],
            ),
        )
        conn.commit()

        cursor.execute("SELECT id FROM user_pdf_documents WHERE user_id = ? AND filename = ?", (user_str, nome_arquivo))
        row = cursor.fetchone()
        doc_id = row[0] if row else None

        if doc_id:
            cursor.execute("DELETE FROM user_pdf_chapters WHERE doc_id = ?", (doc_id,))
            for cap in dados["chapters"]:
                cursor.execute(
                    """
                    INSERT INTO user_pdf_chapters (
                        doc_id, chapter_index, level, title, start_page, end_page
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        doc_id,
                        cap["chapter_index"],
                        cap["level"],
                        cap["title"],
                        cap["start_page"],
                        cap["end_page"],
                    ),
                )
            conn.commit()

    dados["doc_id"] = doc_id
    dados["filename"] = nome_arquivo
    dados["filepath"] = caminho_str
    logger.info("PDF '%s' catalogado com sucesso (ID: %s, Páginas: %d, Capítulos: %d).", nome_arquivo, doc_id, dados["total_pages"], len(dados["chapters"]))
    return dados


async def obter_ou_catalogar_documento(
    usuario: str | discord.User | discord.Member,
    termo_busca: str,
    user_id: Optional[str | int] = None,
    db_path: Optional[str] = None,
) -> Tuple[Optional[Dict[str, Any]], List[Dict[str, Any]], Optional[Path]]:
    """Localiza o PDF no disco e assegura que ele esteja catalogado no SQLite."""
    caminho = localizar_pdf_usuario(usuario, termo_busca)
    if not caminho or not caminho.exists():
        return None, [], None

    nome_arquivo = caminho.name
    nome_user = getattr(usuario, "name", str(usuario))
    uid_str = str(user_id or getattr(usuario, "id", nome_user))

    with _get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, user_id, user_name, filename, filepath, title, author,
                   total_pages, file_size_bytes, short_summary, is_indexed, created_at
            FROM user_pdf_documents
            WHERE (user_id = ? OR user_name = ? OR user_id = ?) AND filename = ?
            ORDER BY is_indexed DESC, id ASC
            LIMIT 1
            """,
            (uid_str, nome_user, nome_user, nome_arquivo),
        )
        row = cursor.fetchone()

        if not row:
            # Auto-catalogação retroativa para arquivos já existentes
            logger.info("PDF '%s' localizado no disco sem catálogo no SQLite. Executando catalogação automática...", nome_arquivo)
            await pre_processar_pdf(caminho, uid_str, nome_user, db_path=db_path)
            cursor.execute(
                """
                SELECT id, user_id, user_name, filename, filepath, title, author,
                       total_pages, file_size_bytes, short_summary, is_indexed, created_at
                FROM user_pdf_documents
                WHERE (user_id = ? OR user_name = ? OR user_id = ?) AND filename = ?
                ORDER BY is_indexed DESC, id ASC
                LIMIT 1
                """,
                (uid_str, nome_user, nome_user, nome_arquivo),
            )
            row = cursor.fetchone()

        if not row:
            return None, [], caminho

        doc_dict = {
            "id": row[0],
            "user_id": row[1],
            "user_name": row[2],
            "filename": row[3],
            "filepath": row[4],
            "title": row[5],
            "author": row[6],
            "total_pages": row[7],
            "file_size_bytes": row[8],
            "file_size_formatado": formatar_tamanho(row[8]),
            "short_summary": row[9],
            "is_indexed": bool(row[10]),
            "created_at": row[11],
        }

        cursor.execute(
            """
            SELECT id, doc_id, chapter_index, level, title, start_page, end_page, summary
            FROM user_pdf_chapters
            WHERE doc_id = ?
            ORDER BY chapter_index ASC
            """,
            (doc_dict["id"],),
        )
        cap_rows = cursor.fetchall()
        capitulos = [
            {
                "id": c[0],
                "doc_id": c[1],
                "chapter_index": c[2],
                "level": c[3],
                "title": c[4],
                "start_page": c[5],
                "end_page": c[6],
                "summary": c[7],
            }
            for c in cap_rows
        ]

        return doc_dict, capitulos, caminho


# ==============================================================================
# FASE 2: CONSULTAS DE METADADOS, SUMÁRIO E RESUMO DE CAPÍTULO
# ==============================================================================

async def obter_metadados_documento(
    usuario: str | discord.User | discord.Member,
    termo_busca: str,
) -> Dict[str, Any]:
    """Retorna ficha catalográfica detalhada e sinopse inicial da obra."""
    doc, caps, caminho = await obter_ou_catalogar_documento(usuario, termo_busca)
    if not doc:
        return {
            "sucesso": False,
            "mensagem": f"Arquivo PDF correspondente a '{termo_busca}' não foi encontrado.",
        }

    status_rag = "🟢 Indexado no RAG (Pronto para conversação)" if doc["is_indexed"] else "⚪ Não indexado no RAG (Use !pdf indexar)"

    texto_formatado = (
        f"📘 **FICHA CATALOGRÁFICA DO DOCUMENTO**\n"
        f"• **Título:** {doc['title']}\n"
        f"• **Arquivo:** `{doc['filename']}`\n"
        f"• **Autor:** {doc['author']}\n"
        f"• **Total de Páginas:** {doc['total_pages']} páginas\n"
        f"• **Tamanho do Arquivo:** {doc['file_size_formatado']}\n"
        f"• **Estrutura Mapeada:** {len(caps)} capítulo(s) / seção(ões)\n"
        f"• **Status Vetorial:** {status_rag}\n\n"
        f"📝 **Apresentação / Sinopse Inicial:**\n"
        f"> *{doc['short_summary']}*\n\n"
        f"💡 *Ações disponíveis:* `!pdf sumario {doc['filename']}`, `!pdf capitulo {doc['filename']} <n>`, `!pdf perguntar {doc['filename']} <dúvida>`."
    )

    return {
        "sucesso": True,
        "doc": doc,
        "capitulos_total": len(caps),
        "resposta_formatada": texto_formatado,
    }


async def obter_sumario_documento(
    usuario: str | discord.User | discord.Member,
    termo_busca: str,
) -> Dict[str, Any]:
    """Retorna o sumário com capítulos e suas respectivas páginas."""
    doc, caps, caminho = await obter_ou_catalogar_documento(usuario, termo_busca)
    if not doc:
        return {
            "sucesso": False,
            "mensagem": f"Arquivo PDF correspondente a '{termo_busca}' não foi encontrado.",
        }

    if not caps:
        return {
            "sucesso": True,
            "doc": doc,
            "resposta_formatada": f"📑 O documento `{doc['filename']}` ({doc['total_pages']} páginas) não possui divisões formais de capítulos registradas.",
        }

    linhas = [
        f"📑 **SUMÁRIO & ESTRUTURA: {doc['title'].upper()}**",
        f"*(Arquivo: `{doc['filename']}` — {doc['total_pages']} páginas)*\n",
    ]

    for cap in caps[:35]:
        recuo = "  " * (cap["level"] - 1) if cap["level"] > 1 else ""
        linhas.append(
            f"{recuo}• **#{cap['chapter_index']}** {cap['title']} — `Pág. {cap['start_page']} a {cap['end_page']}`"
        )

    if len(caps) > 35:
        linhas.append(f"\n*... e mais {len(caps) - 35} seções.*")

    linhas.append(
        f"\n💡 *Para ler o resumo de uma seção, digite:* `!pdf capitulo {doc['filename']} <número ou nome>`"
    )

    return {
        "sucesso": True,
        "doc": doc,
        "capitulos": caps,
        "resposta_formatada": "\n".join(linhas),
    }


def _extrair_texto_intervalo_paginas_sync(caminho_arquivo: Path, start_page: int, end_page: int) -> str:
    """Extrai o texto contido em um intervalo específico de páginas via PyMuPDF."""
    doc = pymupdf.open(str(caminho_arquivo))
    total = len(doc)
    sp = max(0, start_page - 1)
    ep = min(total, end_page)

    partes = []
    for p_num in range(sp, ep):
        texto = doc[p_num].get_text()
        if texto.strip():
            partes.append(f"--- [Página {p_num + 1}] ---\n{texto}")

    doc.close()
    return "\n\n".join(partes)


async def resumir_capitulo_documento(
    usuario: str | discord.User | discord.Member,
    termo_busca: str,
    capitulo_identificador: str,
    db_path: Optional[str] = None,
    gerar_resposta_llm: bool = True,
) -> Dict[str, Any]:
    """Sintetiza os pontos centrais de um capítulo com cache no SQLite."""
    doc, caps, caminho = await obter_ou_catalogar_documento(usuario, termo_busca, db_path=db_path)
    if not doc or not caminho:
        return {
            "sucesso": False,
            "mensagem": f"Arquivo PDF correspondente a '{termo_busca}' não foi encontrado.",
        }

    if not caps:
        return {
            "sucesso": False,
            "mensagem": f"O documento `{doc['filename']}` não possui capítulos mapeados.",
        }

    alvo = None
    ident = capitulo_identificador.strip()

    # 1. Correspondência por índice numérico
    if ident.isdigit():
        idx = int(ident)
        for c in caps:
            if c["chapter_index"] == idx:
                alvo = c
                break

    # 2. Correspondência textual no título
    if not alvo:
        ident_lower = ident.lower()
        for c in caps:
            if ident_lower in c["title"].lower():
                alvo = c
                break

    if not alvo:
        return {
            "sucesso": False,
            "mensagem": f"Capítulo ou seção '{capitulo_identificador}' não foi localizado no documento `{doc['filename']}`.",
        }

    # Verifica se já temos resumo em cache no SQLite
    if alvo.get("summary") and str(alvo["summary"]).strip():
        logger.info("Resumo do capítulo #%d resgatado do cache do SQLite.", alvo["chapter_index"])
        texto_resumo = alvo["summary"]
    else:
        # Extrai texto do intervalo de páginas
        texto_capitulo = await asyncio.to_thread(
            _extrair_texto_intervalo_paginas_sync,
            caminho,
            alvo["start_page"],
            alvo["end_page"],
        )

        if not texto_capitulo.strip():
            return {
                "sucesso": False,
                "mensagem": f"Não foi possível extrair texto legível das páginas {alvo['start_page']} a {alvo['end_page']}.",
            }

        # Trunca para caber na janela de contexto se o capítulo for massivo
        if len(texto_capitulo) > 12000:
            texto_capitulo = texto_capitulo[:12000] + "\n\n[... trecho truncado para caber no limite de contexto ...]"

        # Se chamado por uma ferramenta da LLM, retorna o texto extraído diretamente
        # evitando chamadas aninhadas à LLM que provocam concorrência e timeout no LM Studio.
        if not gerar_resposta_llm:
            texto_extraido = (
                f"📖 Trecho do capítulo #{alvo['chapter_index']}: '{alvo['title']}' "
                f"(Páginas {alvo['start_page']} a {alvo['end_page']}) da obra '{doc['title']}':\n\n"
                f"{texto_capitulo}\n\n"
                f"Instruções para o assistente: Elabore uma síntese estruturada e didática do capítulo acima, "
                f"apresentando a tese central, conceitos fundamentais e conclusões."
            )
            return {
                "sucesso": True,
                "doc": doc,
                "capitulo": alvo,
                "resumo": texto_extraido,
                "resposta_formatada": texto_extraido,
            }

        prompt_resumo = (
            f"Você é um tutor acadêmico e analista textual de alta precisão. "
            f"Elabore uma síntese estruturada e didática do capítulo '{alvo['title']}' "
            f"(Páginas {alvo['start_page']} a {alvo['end_page']}) da obra '{doc['title']}'.\n\n"
            f"Estrutura obrigatória da resposta:\n"
            f"1. **Tese / Ideia Central**: Qual o objetivo central deste capítulo.\n"
            f"2. **Conceitos Fundamentais**: Os tópicos e argumentos essenciais.\n"
            f"3. **Exemplos e Aplicações Práticas** (se houver).\n"
            f"4. **Conclusão / Ponto de Fechamento**.\n\n"
            f"Texto do capítulo extraído:\n{texto_capitulo}"
        )

        try:
            from llm_client import llm_client
            mensagens_envio = [
                {"role": "system", "content": "Você é um assistente especialista em síntese literária e técnica."},
                {"role": "user", "content": prompt_resumo},
            ]
            res_llm = await llm_client.gerar_resposta(
                mensagens=mensagens_envio,
                tools=[],
            )
            texto_resumo = res_llm.strip()
        except Exception as e:
            logger.warning("Falha ao gerar resumo do capítulo via LLM: %s. Utilizando síntese base.", e)
            texto_resumo = (
                f"Capítulo **{alvo['title']}** abrangendo as páginas {alvo['start_page']} a {alvo['end_page']}.\n"
                f"Trecho inicial:\n> {texto_capitulo[:600]}..."
            )

        # Salva o resumo gerado em cache no SQLite
        with _get_connection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE user_pdf_chapters SET summary = ? WHERE id = ?",
                (texto_resumo, alvo["id"]),
            )
            conn.commit()

    resposta_final = (
        f"📖 **RESUMO DO CAPÍTULO #{alvo['chapter_index']}: {alvo['title'].upper()}**\n"
        f"• **Obra:** {doc['title']} (`{doc['filename']}`)\n"
        f"• **Páginas:** `{alvo['start_page']} a {alvo['end_page']}`\n\n"
        f"{texto_resumo}"
    )

    return {
        "sucesso": True,
        "doc": doc,
        "capitulo": alvo,
        "resumo": texto_resumo,
        "resposta_formatada": resposta_final,
    }


# ==============================================================================
# FASE 3: INDEXAÇÃO VETORIAL (RAG) & BUSCA SEMÂNTICA POR PERGUNTA
# ==============================================================================

def _extrair_chunks_documento_sync(caminho_arquivo: Path, capitulos: List[Dict[str, Any]], chunk_size: int = 900, overlap: int = 150) -> List[Dict[str, Any]]:
    """Lê todas as páginas do PDF e fatia o texto em chunks identificados por página e capítulo."""
    doc = pymupdf.open(str(caminho_arquivo))
    total_paginas = len(doc)

    chunks = []
    for num_p in range(total_paginas):
        pag_num = num_p + 1
        texto_pag = doc[num_p].get_text()
        if not texto_pag or not texto_pag.strip():
            continue

        # Identifica a qual capítulo esta página pertence
        cap_nome = "Geral"
        for c in capitulos:
            if c["start_page"] <= pag_num <= c["end_page"]:
                cap_nome = c["title"]
                break

        # Segmentação da página com overlap
        pos = 0
        comprimento = len(texto_pag)
        while pos < comprimento:
            fim = min(pos + chunk_size, comprimento)
            bloco = texto_pag[pos:fim].strip()
            if len(bloco) > 50:  # Ignora fragmentos minúsculos
                chunks.append({
                    "texto": bloco,
                    "pagina": pag_num,
                    "capitulo": cap_nome,
                })
            pos += (chunk_size - overlap)
            if pos >= comprimento:
                break

    doc.close()
    return chunks


async def indexar_documento_rag(
    usuario: str | discord.User | discord.Member,
    termo_busca: str,
    db_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Fatia o PDF, gera embeddings no LM Studio e armazena na coleção vetorial do ChromaDB."""
    doc, caps, caminho = await obter_ou_catalogar_documento(usuario, termo_busca, db_path=db_path)
    if not doc or not caminho:
        return {
            "sucesso": False,
            "mensagem": f"Arquivo PDF correspondente a '{termo_busca}' não foi encontrado.",
        }

    nome_user = getattr(usuario, "name", str(usuario))
    colecao = obter_colecao_livro(nome_user, doc["id"])

    # Se já estiver indexado e houver itens no ChromaDB
    if doc["is_indexed"] and colecao.count() > 0:
        return {
            "sucesso": True,
            "doc": doc,
            "mensagem": f"A obra `{doc['filename']}` já está indexada no RAG vetorial com `{colecao.count()}` fragmentos!",
        }

    logger.info("Iniciando indexação RAG do documento '%s' (ID: %s)...", doc["filename"], doc["id"])

    # Extrai chunks
    chunks = await asyncio.to_thread(_extrair_chunks_documento_sync, caminho, caps)
    if not chunks:
        return {
            "sucesso": False,
            "mensagem": f"Nenhum texto legível foi extraído para indexação do arquivo `{doc['filename']}`.",
        }

    total_chunks = len(chunks)
    logger.info("Extraídos %d fragmentos de texto para vetorização...", total_chunks)

    # Processa embeddings em lotes de 16 chunks para alta velocidade
    # Processa embeddings em lotes de 4 chunks para evitar sobrecarga no LM Studio
    batch_size = 4
    chunks_vetorizados = 0

    for i in range(0, total_chunks, batch_size):
        lote = chunks[i : i + batch_size]
        textos_lote = [c["texto"] for c in lote]

        try:
            res_emb = await _embedding_client.embeddings.create(
                model=LM_STUDIO_EMBEDDING_MODEL,
                input=textos_lote,
            )
            vetores = [d.embedding for d in res_emb.data]

            ids_lote = [f"doc{doc['id']}_p{c['pagina']}_idx{i + idx}" for idx, c in enumerate(lote)]
            metadatas_lote = [
                {
                    "pagina": str(c["pagina"]),
                    "capitulo": str(c["capitulo"])[:100],
                    "arquivo": doc["filename"],
                    "doc_id": str(doc["id"]),
                }
                for c in lote
            ]

            colecao.add(
                ids=ids_lote,
                embeddings=vetores,
                documents=textos_lote,
                metadatas=metadatas_lote,
            )
            chunks_vetorizados += len(lote)
        except Exception as e:
            logger.warning("Falha ao gerar lote %d-%d no LM Studio: %s. Tentando inserção individual...", i, i + len(lote), e)
            for sub_idx, c in enumerate(lote):
                try:
                    res_ind = await _embedding_client.embeddings.create(
                        model=LM_STUDIO_EMBEDDING_MODEL,
                        input=c["texto"],
                    )
                    v_ind = res_ind.data[0].embedding
                    colecao.add(
                        ids=[f"doc{doc['id']}_p{c['pagina']}_idx{i + sub_idx}"],
                        embeddings=[v_ind],
                        documents=[c["texto"]],
                        metadatas=[{
                            "pagina": str(c["pagina"]),
                            "capitulo": str(c["capitulo"])[:100],
                            "arquivo": doc["filename"],
                            "doc_id": str(doc["id"]),
                        }],
                    )
                    chunks_vetorizados += 1
                except Exception as err_ind:
                    logger.error("Erro no chunk individual p%d: %s", c["pagina"], err_ind)

    # Atualiza status no SQLite
    with _get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE user_pdf_documents SET is_indexed = 1, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (doc["id"],),
        )
        conn.commit()

    logger.info("Indexação RAG concluída: %d/%d fragmentos gravados no ChromaDB.", chunks_vetorizados, total_chunks)

    texto_formatado = (
        f"✅ **OBRA INDEXADA COM SUCESSO NO RAG VETORIAL!**\n"
        f"• **Obra:** {doc['title']} (`{doc['filename']}`)\n"
        f"• **Páginas Processadas:** {doc['total_pages']} páginas\n"
        f"• **Fragmentos Vetorizados:** `{chunks_vetorizados}` blocos de conhecimento\n"
        f"• **Coleção ChromaDB:** `{colecao.name}`\n\n"
        f"💡 *Agora você pode fazer perguntas diretas sobre a obra:* `!pdf perguntar {doc['filename']} <sua dúvida>`"
    )

    return {
        "sucesso": True,
        "doc": doc,
        "total_chunks": chunks_vetorizados,
        "resposta_formatada": texto_formatado,
    }


async def consultar_documento_rag(
    usuario: str | discord.User | discord.Member,
    termo_busca: str,
    pergunta: str,
    db_path: Optional[str] = None,
    gerar_resposta_llm: bool = True,
) -> Dict[str, Any]:
    """Realiza busca vetorial no livro e responde à pergunta com citação de páginas."""
    doc, caps, caminho = await obter_ou_catalogar_documento(usuario, termo_busca, db_path=db_path)
    if not doc:
        return {
            "sucesso": False,
            "mensagem": f"Arquivo PDF correspondente a '{termo_busca}' não foi encontrado.",
        }

    nome_user = doc.get("user_name") or getattr(usuario, "name", str(usuario))
    colecao = obter_colecao_livro(nome_user, doc["id"])

    # Se ainda não estiver indexado no RAG:
    if not doc["is_indexed"] or colecao.count() == 0:
        # Se for um documento pequeno (<= 35 páginas), indexa automaticamente na hora!
        if doc["total_pages"] <= 35:
            logger.info("Documento '%s' possui %d páginas. Indexando automaticamente antes da consulta...", doc["filename"], doc["total_pages"])
            await indexar_documento_rag(usuario, termo_busca, db_path=db_path)
        else:
            return {
                "sucesso": False,
                "requer_indexacao": True,
                "mensagem": (
                    f"⚠️ A obra `{doc['filename']}` ({doc['total_pages']} páginas) ainda não foi indexada no RAG vetorial.\n"
                    f"Por favor, execute primeiro: `!pdf indexar {doc['filename']}` para que eu possa vetorizar os capítulos!"
                ),
            }

    # Gera embedding da pergunta
    try:
        res_emb = await _embedding_client.embeddings.create(
            model=LM_STUDIO_EMBEDDING_MODEL,
            input=pergunta.strip(),
        )
        vetor_pergunta = res_emb.data[0].embedding
    except Exception as e:
        logger.error("Erro ao gerar embedding da pergunta no LM Studio: %s", e)
        return {
            "sucesso": False,
            "mensagem": "Não foi possível conectar ao LM Studio para processar a busca semântica.",
        }

    # Busca top 4 fragmentos mais relevantes
    try:
        limite = min(4, colecao.count())
        res_query = colecao.query(
            query_embeddings=[vetor_pergunta],
            n_results=limite,
            include=["documents", "metadatas", "distances"],
        )

        documentos = res_query.get("documents", [[]])[0]
        metadatas = res_query.get("metadatas", [[]])[0]
    except Exception as e:
        logger.error("Erro ao consultar coleção vetorial do livro no ChromaDB: %s", e)
        return {
            "sucesso": False,
            "mensagem": f"Erro na recuperação vetorial no ChromaDB: {e}",
        }

    if not documentos:
        return {
            "sucesso": False,
            "mensagem": f"Nenhum trecho relevante foi encontrado na obra `{doc['filename']}` para responder à sua dúvida.",
        }

    # Monta o contexto injetado com indicação explícita de página e capítulo
    contextos_formatados = []
    paginas_citadas = set()

    for idx, doc_texto in enumerate(documentos, start=1):
        meta = metadatas[idx - 1] if idx - 1 < len(metadatas) else {}
        pag = meta.get("pagina", "?")
        cap = meta.get("capitulo", "Geral")
        paginas_citadas.add(pag)
        contextos_formatados.append(
            f"--- [Trecho #{idx} | Página {pag} | Capítulo: {cap}] ---\n{doc_texto}"
        )

    contexto_str = "\n\n".join(contextos_formatados)
    paginas_lista = sorted(list(paginas_citadas), key=lambda x: int(x) if str(x).isdigit() else 9999)
    paginas_str = ", ".join([f"Pág. {p}" for p in paginas_lista])

    # Se invocado por uma Tool de LLM (Function Calling), retorna os trechos diretamente!
    # Isso evita chamadas aninhadas à LLM que provocam timeout e looping infinito no LM Studio.
    if not gerar_resposta_llm:
        texto_trechos = (
            f"📖 **Trechos recuperados da obra '{doc['title']}' (`{doc['filename']}`)**\n"
            f"*(Fontes: `{paginas_str}`)*\n\n"
            f"{contexto_str}\n\n"
            f"Instruções para a sua resposta ao usuário:\n"
            f"- Responda à dúvida do usuário com base com fidelidade e clareza nos trechos acima.\n"
            f"- Cite explicitamente as páginas de onde as informações foram retiradas (ex: [Página X])."
        )
        return {
            "sucesso": True,
            "doc": doc,
            "trechos": contextos_formatados,
            "paginas_consultadas": paginas_lista,
            "resposta": texto_trechos,
            "resposta_formatada": texto_trechos,
        }

    prompt_rag = (
        f"Você é um tutor intelectual e assistente especialista no livro '{doc['title']}'. "
        f"Responda à pergunta do usuário baseando-se com fidelidade nos trechos extraídos da obra fornecidos abaixo.\n\n"
        f"Diretrizes:\n"
        f"1. Seja didático, claro, conciso e confiável.\n"
        f"2. Cite SEMPRE as páginas de onde as informações foram extraídas utilizando a tag [Página X].\n"
        f"3. Se a informação não constar nos trechos fornecidos, declare honestamente que o trecho não traz essa informação.\n\n"
        f"Trechos recuperados da obra:\n{contexto_str}\n\n"
        f"Pergunta do usuário: {pergunta}"
    )

    try:
        from llm_client import llm_client
        from database import obter_preferencia_modelo
        uid = str(getattr(usuario, "id", usuario))
        pref = obter_preferencia_modelo(uid)
        mensagens_envio = [
            {"role": "system", "content": "Você é um assistente acadêmico e tutor de leitura técnica."},
            {"role": "user", "content": prompt_rag},
        ]
        resposta_llm = await llm_client.gerar_resposta(
            mensagens=mensagens_envio,
            tools=[],
            provider=pref.get("provider", "auto"),
            model=pref.get("model_name"),
            permitir_failover=True,
        )
    except Exception as e:
        logger.error("Falha ao gerar resposta RAG via LLM: %s", e)
        resposta_llm = "Houve uma instabilidade no processamento da LLM ao sintetizar a resposta com os trechos do livro."

    texto_final = (
        f"🔍 **RESPOSTA SOBRE A OBRA: {doc['title'].upper()}**\n"
        f"*(Fontes consultadas: `{paginas_str}` | `{doc['filename']}`)*\n\n"
        f"{resposta_llm}"
    )

    return {
        "sucesso": True,
        "doc": doc,
        "resposta": resposta_llm,
        "paginas_consultadas": paginas_lista,
        "resposta_formatada": texto_final,
    }


def listar_status_pdfs_usuario(
    usuario: str | discord.User | discord.Member,
    db_path: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Retorna a listagem de PDFs combinando os arquivos em disco e o status de catálogo e RAG."""
    arquivos_disco = listar_pdfs_usuario(usuario)
    if not arquivos_disco:
        return []

    nome_user = getattr(usuario, "name", str(usuario))

    with _get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT filename, title, author, total_pages, is_indexed
            FROM user_pdf_documents
            WHERE user_name = ? OR user_id = ?
            """,
            (nome_user, str(getattr(usuario, "id", nome_user))),
        )
        rows = {r[0]: {"title": r[1], "author": r[2], "total_pages": r[3], "is_indexed": bool(r[4])} for r in cursor.fetchall()}

    resultado = []
    for arq in arquivos_disco:
        info_db = rows.get(arq["nome"], {})
        resultado.append({
            "nome": arq["nome"],
            "tamanho_formatado": arq["tamanho_formatado"],
            "modificado_em": arq["modificado_em"],
            "title": info_db.get("title", arq["nome"]),
            "author": info_db.get("author", "Não catalogado"),
            "total_pages": info_db.get("total_pages", 0),
            "is_indexed": info_db.get("is_indexed", False),
            "catalogado": arq["nome"] in rows,
        })

    return resultado
