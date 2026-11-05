"""
Módulo de Gerenciamento de Listas (Compras, Mercado, Tarefas).

Permite criar listas nomeadas por usuário, adicionar e remover itens,
marcar/ticar itens concluídos e limpar/excluir itens finalizados no SQLite.
"""

from pathlib import Path
import sqlite3
from typing import Any, Dict, List, Optional
from config import DB_FILE


def _get_db_path(db_path: Optional[str] = None) -> str:
    """Retorna o caminho seguro do banco de dados SQLite."""
    caminho = db_path or DB_FILE
    parent = Path(caminho).parent
    if parent and not parent.exists():
        parent.mkdir(parents=True, exist_ok=True)
    return str(caminho)


def init_list_db(db_path: Optional[str] = None) -> None:
    """Inicializa as tabelas de listas e itens no SQLite com suporte a integridade referencial."""
    caminho = _get_db_path(db_path)
    with sqlite3.connect(caminho) as conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys = ON;")
        
        # Tabela de listas por usuário
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS user_lists (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                name TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, name)
            )
            """
        )
        
        # Tabela de itens da lista
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS list_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                list_id INTEGER NOT NULL REFERENCES user_lists(id) ON DELETE CASCADE,
                item_text TEXT NOT NULL,
                concluido INTEGER NOT NULL DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        
        # Índices para performance
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_user_lists_user_name 
            ON user_lists (user_id, name)
            """
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_list_items_list_id 
            ON list_items (list_id, concluido)
            """
        )
        conn.commit()


def sanitizar_nome_lista(nome: str) -> str:
    """Padroniza o nome da lista para minúsculas e sem espaços extras."""
    return nome.strip().lower() if nome else "mercado"


def obter_ou_criar_lista(user_id: str, nome_lista: str, db_path: Optional[str] = None) -> int:
    """Recupera o ID da lista do usuário ou a cria caso ainda não exista."""
    caminho = _get_db_path(db_path)
    nome_norm = sanitizar_nome_lista(nome_lista)
    user_str = str(user_id)

    with sqlite3.connect(caminho) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id FROM user_lists WHERE user_id = ? AND name = ?",
            (user_str, nome_norm),
        )
        row = cursor.fetchone()
        if row:
            return row[0]

        cursor.execute(
            "INSERT INTO user_lists (user_id, name) VALUES (?, ?)",
            (user_str, nome_norm),
        )
        conn.commit()
        return cursor.lastrowid


def adicionar_item_lista(
    user_id: str,
    nome_lista: str,
    item_text: str,
    db_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Adiciona um item a uma lista específica do usuário."""
    texto = (item_text or "").strip()
    if not texto:
        return {"sucesso": False, "mensagem": "O texto do item não pode estar vazio."}

    list_id = obter_ou_criar_lista(user_id, nome_lista, db_path=db_path)
    caminho = _get_db_path(db_path)

    with sqlite3.connect(caminho) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO list_items (list_id, item_text, concluido) VALUES (?, ?, 0)",
            (list_id, texto),
        )
        item_id = cursor.lastrowid
        conn.commit()

    return {
        "sucesso": True,
        "mensagem": f"Item '{texto}' adicionado com sucesso na lista '{sanitizar_nome_lista(nome_lista)}'.",
        "item_id": item_id,
        "item_text": texto,
        "nome_lista": sanitizar_nome_lista(nome_lista),
    }


def obter_itens_lista(
    user_id: str,
    nome_lista: str,
    db_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Retorna os itens de uma lista com seus status de conclusão."""
    caminho = _get_db_path(db_path)
    nome_norm = sanitizar_nome_lista(nome_lista)
    user_str = str(user_id)

    with sqlite3.connect(caminho) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id FROM user_lists WHERE user_id = ? AND name = ?",
            (user_str, nome_norm),
        )
        list_row = cursor.fetchone()
        if not list_row:
            return {
                "sucesso": False,
                "existe": False,
                "nome_lista": nome_norm,
                "itens": [],
                "total": 0,
                "mensagem": f"A lista '{nome_norm}' não foi encontrada.",
            }

        list_id = list_row[0]
        cursor.execute(
            """
            SELECT id, item_text, concluido, created_at 
            FROM list_items 
            WHERE list_id = ? 
            ORDER BY concluido ASC, id ASC
            """,
            (list_id,),
        )
        linhas = cursor.fetchall()

    itens = [
        {
            "id": r[0],
            "texto": r[1],
            "concluido": bool(r[2]),
            "created_at": r[3],
        }
        for r in linhas
    ]

    total = len(itens)
    concluidos = sum(1 for i in itens if i["concluido"])
    pendentes = total - concluidos

    return {
        "sucesso": True,
        "existe": True,
        "list_id": list_id,
        "nome_lista": nome_norm,
        "itens": itens,
        "total": total,
        "pendentes": pendentes,
        "concluidos": concluidos,
    }


def listar_todas_listas(
    user_id: str,
    db_path: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Lista todas as listas registradas do usuário com contagem de itens."""
    caminho = _get_db_path(db_path)
    user_str = str(user_id)

    with sqlite3.connect(caminho) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT 
                l.id, 
                l.name, 
                COUNT(i.id) AS total_itens,
                SUM(CASE WHEN i.concluido = 1 THEN 1 ELSE 0 END) AS concluidos
            FROM user_lists l
            LEFT JOIN list_items i ON l.id = i.list_id
            WHERE l.user_id = ?
            GROUP BY l.id, l.name
            ORDER BY l.name ASC
            """,
            (user_str,),
        )
        rows = cursor.fetchall()

    listas = []
    for r in rows:
        total = r[2] or 0
        concluidos = r[3] or 0
        listas.append({
            "id": r[0],
            "nome": r[1],
            "total_itens": total,
            "concluidos": concluidos,
            "pendentes": total - concluidos,
        })
    return listas


def _localizar_item_id(
    list_id: int,
    identificador: str | int,
    cursor: sqlite3.Cursor,
) -> Optional[tuple[int, str, int]]:
    """Localiza o ID real, texto e status do item por ID numérico ou busca por texto."""
    ident_str = str(identificador).strip()
    
    # 1. Tenta buscar por ID primário se for número
    if ident_str.isdigit():
        cursor.execute(
            "SELECT id, item_text, concluido FROM list_items WHERE list_id = ? AND id = ?",
            (list_id, int(ident_str)),
        )
        row = cursor.fetchone()
        if row:
            return row

        # Também pode ser a posição ordinal (ex: item 1, item 2 da lista)
        cursor.execute(
            "SELECT id, item_text, concluido FROM list_items WHERE list_id = ? ORDER BY id ASC",
            (list_id,),
        )
        todos = cursor.fetchall()
        pos = int(ident_str) - 1
        if 0 <= pos < len(todos):
            return todos[pos]

    # 2. Busca por texto exato ou parcial
    cursor.execute(
        "SELECT id, item_text, concluido FROM list_items WHERE list_id = ? AND LOWER(item_text) = LOWER(?)",
        (list_id, ident_str),
    )
    row = cursor.fetchone()
    if row:
        return row

    cursor.execute(
        "SELECT id, item_text, concluido FROM list_items WHERE list_id = ? AND LOWER(item_text) LIKE LOWER(?)",
        (list_id, f"%{ident_str}%"),
    )
    return cursor.fetchone()


def ticar_item_lista(
    user_id: str,
    nome_lista: str,
    item_identificador: str | int,
    concluido: Optional[bool] = None,
    db_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Marca, desmarca ou alterna o status de concluído de um item da lista."""
    caminho = _get_db_path(db_path)
    nome_norm = sanitizar_nome_lista(nome_lista)
    user_str = str(user_id)

    with sqlite3.connect(caminho) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id FROM user_lists WHERE user_id = ? AND name = ?",
            (user_str, nome_norm),
        )
        list_row = cursor.fetchone()
        if not list_row:
            return {"sucesso": False, "mensagem": f"Lista '{nome_norm}' não encontrada."}

        list_id = list_row[0]
        item = _localizar_item_id(list_id, item_identificador, cursor)
        if not item:
            return {
                "sucesso": False,
                "mensagem": f"Item '{item_identificador}' não encontrado na lista '{nome_norm}'.",
            }

        item_id, item_text, status_atual = item
        novo_status = 1 if concluido is True else (0 if concluido is False else (0 if status_atual == 1 else 1))

        cursor.execute(
            "UPDATE list_items SET concluido = ? WHERE id = ?",
            (novo_status, item_id),
        )
        conn.commit()

    verbo = "marcado como concluído" if novo_status == 1 else "reaberto como pendente"
    return {
        "sucesso": True,
        "item_id": item_id,
        "item_text": item_text,
        "concluido": bool(novo_status),
        "mensagem": f"Item '{item_text}' foi {verbo} na lista '{nome_norm}'.",
    }


def remover_item_lista(
    user_id: str,
    nome_lista: str,
    item_identificador: str | int,
    db_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Remove um item individual da lista (seja por ID, posição ou texto)."""
    caminho = _get_db_path(db_path)
    nome_norm = sanitizar_nome_lista(nome_lista)
    user_str = str(user_id)

    with sqlite3.connect(caminho) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id FROM user_lists WHERE user_id = ? AND name = ?",
            (user_str, nome_norm),
        )
        list_row = cursor.fetchone()
        if not list_row:
            return {"sucesso": False, "mensagem": f"Lista '{nome_norm}' não encontrada."}

        list_id = list_row[0]
        item = _localizar_item_id(list_id, item_identificador, cursor)
        if not item:
            return {
                "sucesso": False,
                "mensagem": f"Item '{item_identificador}' não foi localizado na lista '{nome_norm}'.",
            }

        item_id, item_text, _ = item
        cursor.execute("DELETE FROM list_items WHERE id = ?", (item_id,))
        conn.commit()

    return {
        "sucesso": True,
        "item_id": item_id,
        "item_text": item_text,
        "mensagem": f"Item '{item_text}' foi removido da lista '{nome_norm}'.",
    }


def limpar_itens_concluidos(
    user_id: str,
    nome_lista: str,
    db_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Exclui permanentemente todos os itens ticados/concluídos da lista especificada."""
    caminho = _get_db_path(db_path)
    nome_norm = sanitizar_nome_lista(nome_lista)
    user_str = str(user_id)

    with sqlite3.connect(caminho) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id FROM user_lists WHERE user_id = ? AND name = ?",
            (user_str, nome_norm),
        )
        list_row = cursor.fetchone()
        if not list_row:
            return {"sucesso": False, "mensagem": f"Lista '{nome_norm}' não encontrada."}

        list_id = list_row[0]
        # Recupera os textos dos itens antes de apagar para retorno informativo
        cursor.execute(
            "SELECT item_text FROM list_items WHERE list_id = ? AND concluido = 1",
            (list_id,),
        )
        removidos_textos = [r[0] for r in cursor.fetchall()]

        if not removidos_textos:
            return {
                "sucesso": True,
                "removidos_total": 0,
                "itens_removidos": [],
                "mensagem": f"Não havia itens concluídos para limpar na lista '{nome_norm}'.",
            }

        cursor.execute("DELETE FROM list_items WHERE list_id = ? AND concluido = 1", (list_id,))
        conn.commit()

    return {
        "sucesso": True,
        "removidos_total": len(removidos_textos),
        "itens_removidos": removidos_textos,
        "mensagem": f"{len(removidos_textos)} item(ns) concluído(s) foram apagados da lista '{nome_norm}'.",
    }


def excluir_lista(
    user_id: str,
    nome_lista: str,
    db_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Exclui completamente a lista e todos os seus itens associados."""
    caminho = _get_db_path(db_path)
    nome_norm = sanitizar_nome_lista(nome_lista)
    user_str = str(user_id)

    with sqlite3.connect(caminho) as conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys = ON;")
        cursor.execute(
            "SELECT id FROM user_lists WHERE user_id = ? AND name = ?",
            (user_str, nome_norm),
        )
        list_row = cursor.fetchone()
        if not list_row:
            return {"sucesso": False, "mensagem": f"A lista '{nome_norm}' não existe."}

        list_id = list_row[0]
        # Remove explicitamente os itens filhos para garantir integridade mesmo sem cascade ativo
        cursor.execute("DELETE FROM list_items WHERE list_id = ?", (list_id,))
        cursor.execute("DELETE FROM user_lists WHERE id = ?", (list_id,))
        conn.commit()

    return {
        "sucesso": True,
        "mensagem": f"A lista '{nome_norm}' e todos os seus itens foram excluídos com sucesso.",
    }


def formatar_lista_para_exibicao(dados_lista: Dict[str, Any]) -> str:
    """Gera uma formatação elegante em Markdown para o Discord."""
    if not dados_lista.get("sucesso", False):
        return f"❌ {dados_lista.get('mensagem', 'Erro ao carregar a lista.')}"

    nome = dados_lista.get("nome_lista", "Lista")
    itens = dados_lista.get("itens", [])
    total = dados_lista.get("total", 0)
    pendentes = dados_lista.get("pendentes", 0)
    concluidos = dados_lista.get("concluidos", 0)

    if total == 0:
        return (
            f"📋 **Lista: {nome}**\n"
            f"*(A lista está vazia no momento)*\n\n"
            f"💡 *Use `!lista add {nome} <item>` ou me peça para adicionar itens!*"
        )

    linhas = [
        f"📋 **Lista: {nome.upper()}**",
        f"📊 *{total} item(ns) | ⏳ {pendentes} pendente(s) | ✅ {concluidos} concluído(s)*",
        "─" * 40,
    ]

    for idx, item in enumerate(itens, start=1):
        if item["concluido"]:
            linhas.append(f"✅ `#{item['id']}` ~~{item['texto']}~~")
        else:
            linhas.append(f"⬜ `#{item['id']}` **{item['texto']}**")

    linhas.append("─" * 40)
    linhas.append(f"💡 *Dicas: `!lista ticar {nome} <id/nome>` | `!lista limpar {nome}`*")

    return "\n".join(linhas)
