"""
Central de Prompts & Catálogo de Templates Reutilizáveis (Prompt Hub & Presets) — IDEA-20.

Responsável por armazenar, versionar e gerenciar templates de prompts, estilos cognitivos
e diretrizes reutilizáveis (Presets: dev, cfo, direto, revisor, socrates, tributarista).
Serve como biblioteca para alimentar os canais temáticos (IDEA-26) e tarefas do assistente.
"""

import logging
import sqlite3
from typing import Any, Dict, List, Optional
from config import DB_FILE

logger = logging.getLogger(__name__)

# Presets de fábrica oficiais (embutidos e protegidos)
BUILTIN_PRESETS: List[Dict[str, Any]] = [
    {
        "id": "padrao",
        "nome": "Assistente Pessoal Padrão",
        "descricao": "Equilibrado, educado, bem-humorado, prestativo e com respostas naturais.",
        "categoria": "geral",
        "temperatura": 0.7,
        "template_text": (
            "Você é o assistente pessoal padrão do usuário no Discord. "
            "Mantenha um tom acolhedor, prestativo, bem-humorado e equilibrado. "
            "Responda com clareza, objetividade e riqueza de detalhes quando solicitado."
        ),
    },
    {
        "id": "dev",
        "nome": "Tech Lead & Arquiteto de Software",
        "descricao": "Focado em código idiomático, boas práticas, segurança, performance e sem explicações óbvias.",
        "categoria": "programacao",
        "temperatura": 0.3,
        "template_text": (
            "Você atua como um Tech Lead e Arquiteto de Software sênior. "
            "Foque em código limpo, tipado, assíncrono, performático e seguro. "
            "Evite introduções e despedidas desnecessárias; vá direto à solução técnica com snippets explicativos quando relevante."
        ),
    },
    {
        "id": "direto",
        "nome": "Modo Ultra-Conciso",
        "descricao": "Respostas telegráficas em tópicos rápidos, máximo 3 frases, sem enrolação ou saudações.",
        "categoria": "produtividade",
        "temperatura": 0.2,
        "template_text": (
            "Responda de forma telegráfica e ultra-direta. "
            "Limite suas respostas a tópicos curtos (bullet points) ou no máximo 3 frases concisas. "
            "Nunca inclua introduções, elogios ou frases de cortesia."
        ),
    },
    {
        "id": "revisor",
        "nome": "Editor Textual Rígido",
        "descricao": "Análise rígida de gramática, coesão, clareza, tom e sugestões de estilo persuasivo.",
        "categoria": "escrita",
        "temperatura": 0.4,
        "template_text": (
            "Você é um editor e revisor de textos rigoroso e atento aos mínimos detalhes. "
            "Aponte erros gramaticais, ortográficos, problemas de concisão, ambiguidade e clareza. "
            "Sempre forneça uma versão revisada recomendada justificando as alterações pontuais."
        ),
    },
    {
        "id": "cfo",
        "nome": "Consultor Financeiro & Estratégico",
        "descricao": "Focado em ROI, custos, sustentabilidade de negócios, controle de riscos e projeções.",
        "categoria": "negocios",
        "temperatura": 0.3,
        "template_text": (
            "Você é um consultor financeiro e estrategista de negócios (CFO). "
            "Analise decisões sempre sob a ótica de retorno sobre investimento (ROI), gestão de riscos, "
            "eficiência de custos, liquidez e sustentabilidade de longo prazo."
        ),
    },
    {
        "id": "socrates",
        "nome": "Filósofo Maiêutico",
        "descricao": "Não entrega respostas prontas; formula perguntas reflexivas para guiar o usuário na resolução do seu dilema.",
        "categoria": "filosofia",
        "temperatura": 0.7,
        "template_text": (
            "Você é um filósofo socrático praticante da maiêutica. "
            "Não forneça respostas prontas de imediato. Em vez disso, desafie premissas, aponte contradições "
            "e faça perguntas profundas para ajudar o interlocutor a descobrir a verdade por si mesmo."
        ),
    },
    {
        "id": "tributarista",
        "nome": "Consultor Tributário & Contábil (CBS/IBS)",
        "descricao": "Especialista em direito tributário, contabilidade, Reforma Tributária, CBS e IBS.",
        "categoria": "tributario",
        "temperatura": 0.2,
        "template_text": (
            "Você é um consultor tributário e contábil sênior especialista na legislação brasileira e na Reforma Tributária (CBS e IBS). "
            "Forneça respostas fundamentadas, com precisão técnica e terminologia jurídica/contábil correta. "
            "Sempre aponte impactos práticos em cálculos, alíquotas e obrigações acessórias."
        ),
    },
]


def _get_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    caminho = db_path or DB_FILE
    return sqlite3.connect(caminho, timeout=30.0)


def init_prompt_hub_db(db_path: Optional[str] = None) -> None:
    """Inicializa a tabela de templates de prompts e carrega os presets oficiais."""
    with _get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS prompt_templates (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                nome TEXT NOT NULL,
                descricao TEXT,
                template_text TEXT NOT NULL,
                categoria TEXT DEFAULT 'geral',
                temperatura_sugerida REAL DEFAULT 0.7,
                is_builtin INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_prompt_templates_cat ON prompt_templates(categoria);")

        # Insere ou atualiza os presets oficiais embutidos
        for p in BUILTIN_PRESETS:
            cursor.execute(
                """
                INSERT INTO prompt_templates (id, user_id, nome, descricao, template_text, categoria, temperatura_sugerida, is_builtin)
                VALUES (?, NULL, ?, ?, ?, ?, ?, 1)
                ON CONFLICT(id) DO UPDATE SET
                    nome=excluded.nome,
                    descricao=excluded.descricao,
                    template_text=excluded.template_text,
                    categoria=excluded.categoria,
                    temperatura_sugerida=excluded.temperatura_sugerida,
                    is_builtin=1
                """,
                (
                    p["id"],
                    p["nome"],
                    p["descricao"],
                    p["template_text"],
                    p["categoria"],
                    p["temperatura"],
                ),
            )
        conn.commit()
    logger.info("Catálogo Prompt Hub (IDEA-20) inicializado com %d presets oficiais.", len(BUILTIN_PRESETS))


def listar_templates(
    categoria: Optional[str] = None,
    incluir_presets: bool = True,
    db_path: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Lista todos os templates disponíveis no catálogo (filtrado por categoria opcional)."""
    with _get_connection(db_path) as conn:
        cursor = conn.cursor()
        query = "SELECT id, nome, descricao, categoria, temperatura_sugerida, is_builtin, created_at FROM prompt_templates WHERE 1=1"
        params: List[Any] = []

        if categoria:
            query += " AND categoria = ?"
            params.append(categoria.lower().strip())

        if not incluir_presets:
            query += " AND is_builtin = 0"

        query += " ORDER BY is_builtin DESC, categoria ASC, id ASC"
        cursor.execute(query, tuple(params))
        rows = cursor.fetchall()
        return [
            {
                "id": r[0],
                "nome": r[1],
                "descricao": r[2] or "",
                "categoria": r[3],
                "temperatura": r[4],
                "is_builtin": bool(r[5]),
                "is_preset": bool(r[5]),
                "created_at": r[6],
            }
            for r in rows
        ]


def obter_template(slug_ou_id: str, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Recupera os detalhes completos e texto do template pelo ID/slug."""
    if not slug_ou_id:
        return None
    slug = slug_ou_id.lower().strip()
    with _get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, nome, descricao, template_text, categoria, temperatura_sugerida, is_builtin, created_at
            FROM prompt_templates
            WHERE LOWER(id) = ?
            """,
            (slug,),
        )
        row = cursor.fetchone()
        if not row:
            return None
        return {
            "id": row[0],
            "nome": row[1],
            "descricao": row[2] or "",
            "template_text": row[3],
            "categoria": row[4],
            "temperatura": row[5],
            "is_builtin": bool(row[6]),
            "created_at": row[7],
        }


def salvar_template(
    slug_id: str = "",
    nome: Optional[str] = None,
    template_text: str = "",
    descricao: Optional[str] = None,
    categoria: str = "geral",
    temperatura: float = 0.7,
    user_id: Optional[str] = None,
    db_path: Optional[str] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Cria ou atualiza um template de prompt customizado pelo usuário."""
    slug = (slug_id or nome or kwargs.get("id") or "").lower().strip()
    texto_final = (template_text or kwargs.get("prompt") or "").strip()
    nome_final = (nome or slug).strip()
    u_id = str(user_id or kwargs.get("autor_id") or "sistema").strip()

    if not slug or not texto_final:
        return {"sucesso": False, "mensagem": "Identificador (slug) e texto do prompt são obrigatórios."}

    # Protege presets de fábrica
    existente = obter_template(slug, db_path=db_path)
    if existente and existente["is_builtin"]:
        return {
            "sucesso": False,
            "mensagem": f"O identificador '{slug}' pertence a um preset oficial de fábrica e não pode ser sobrescrito.",
        }

    with _get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO prompt_templates (id, user_id, nome, descricao, template_text, categoria, temperatura_sugerida, is_builtin, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, 0, CURRENT_TIMESTAMP)
            ON CONFLICT(id) DO UPDATE SET
                nome=excluded.nome,
                descricao=excluded.descricao,
                template_text=excluded.template_text,
                categoria=excluded.categoria,
                temperatura_sugerida=excluded.temperatura_sugerida,
                updated_at=CURRENT_TIMESTAMP
            """,
            (
                slug,
                u_id,
                nome_final,
                (descricao or "").strip(),
                texto_final,
                categoria.lower().strip() or "geral",
                max(0.0, min(1.0, float(temperatura))),
            ),
        )
        conn.commit()

    return {
        "sucesso": True,
        "mensagem": f"Template de prompt '{slug}' salvo com sucesso no catálogo!",
        "id": slug,
    }


def remover_template(
    slug_ou_id: str,
    user_id: Optional[str] = None,
    db_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Remove um template customizado. Presets de fábrica são protegidos."""
    # Trata caso o segundo argumento seja db_path
    if user_id and (".db" in str(user_id) or "/" in str(user_id)):
        db_path = user_id
        user_id = None

    slug = slug_ou_id.lower().strip()
    existente = obter_template(slug, db_path=db_path)
    if not existente:
        return {"sucesso": False, "mensagem": f"Template '{slug}' não encontrado no catálogo."}

    if existente["is_builtin"]:
        return {"sucesso": False, "mensagem": f"O template '{slug}' é um preset oficial e não pode ser excluído."}

    with _get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM prompt_templates WHERE LOWER(id) = ?", (slug,))
        conn.commit()

    return {"sucesso": True, "mensagem": f"Template '{slug}' removido com sucesso do catálogo."}
