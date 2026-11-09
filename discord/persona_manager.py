"""
Gerenciador de Personas & Overrides Cognitivos por Canal e Thread — IDEA-26.

Responsável por fixar estilos cognitivos, system prompts, temperaturas de inferência
e overrides de modelo específicos por canal ou thread no Discord.
Integra-se ao Prompt Hub (IDEA-20) para importação de presets e templates.
"""

import logging
import re
import sqlite3
from typing import Any, Dict, List, Optional
from config import DB_FILE
from prompt_hub import (
    listar_templates,
    obter_template,
    remover_template,
    salvar_template,
)

logger = logging.getLogger(__name__)


def _get_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    caminho = db_path or DB_FILE
    return sqlite3.connect(caminho, timeout=30.0)


def _ensure_persona_slug_column(conn: sqlite3.Connection) -> None:
    """Garante que todas as colunas de identidade multimodal (IDEA-27) existam na tabela channel_personas."""
    try:
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(channel_personas);")
        cols = {r[1] for r in cursor.fetchall()}
        colunas_necessarias = {
            "persona_slug": "TEXT",
            "display_name": "TEXT",
            "avatar_url": "TEXT",
            "avatar_seed": "TEXT",
            "age": "TEXT",
            "bio": "TEXT",
            "is_adaptive": "INTEGER DEFAULT 1",
            "is_locked": "INTEGER DEFAULT 0",
            "last_evolved_at": "DATETIME DEFAULT NULL",
            "evolution_history_json": "TEXT DEFAULT '[]'",
        }
        for col, col_type in colunas_necessarias.items():
            if col not in cols:
                try:
                    cursor.execute(f"ALTER TABLE channel_personas ADD COLUMN {col} {col_type};")
                    conn.commit()
                except Exception as ex_col:
                    logger.debug("Falha ao adicionar coluna %s: %s", col, ex_col)
    except Exception as ex:
        logger.debug("Verificação de colunas multimodais: %s", ex)


def init_persona_db(db_path: Optional[str] = None) -> None:
    """Inicializa a tabela de personas por canal no SQLite."""
    with _get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS channel_personas (
                channel_id TEXT PRIMARY KEY,
                guild_id TEXT,
                channel_name TEXT,
                system_prompt TEXT NOT NULL,
                temperature REAL DEFAULT 0.7,
                model_override TEXT,
                created_by_user_id TEXT NOT NULL,
                persona_slug TEXT,
                display_name TEXT,
                avatar_url TEXT,
                avatar_seed TEXT,
                age TEXT,
                bio TEXT,
                is_adaptive INTEGER DEFAULT 1,
                is_locked INTEGER DEFAULT 0,
                last_evolved_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                evolution_history_json TEXT DEFAULT '[]',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_channel_personas_guild ON channel_personas(guild_id);")
        _ensure_persona_slug_column(conn)
        conn.commit()
    logger.info("Tabela channel_personas (IDEA-26 / IDEA-27) inicializada com sucesso.")


def obter_persona_canal(channel_id: str | int, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Recupera as diretrizes cognitivas e de identidade multimodal ativas para um canal específico."""
    c_id = str(channel_id).strip()
    with _get_connection(db_path) as conn:
        _ensure_persona_slug_column(conn)
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT channel_id, guild_id, channel_name, system_prompt, temperature, model_override, created_by_user_id, updated_at, persona_slug,
                   display_name, avatar_url, avatar_seed, age, bio, is_adaptive, is_locked, last_evolved_at, evolution_history_json
            FROM channel_personas
            WHERE channel_id = ?
            """,
            (c_id,),
        )
        row = cursor.fetchone()
        if not row:
            return None
        slug_val = row[8] if len(row) > 8 else None
        return {
            "channel_id": row[0],
            "guild_id": row[1],
            "channel_name": row[2] or "",
            "persona_id": slug_val or row[2] or "personalizada",
            "persona_slug": slug_val,
            "system_prompt": row[3],
            "temperature": row[4],
            "model_override": row[5],
            "created_by_user_id": row[6],
            "updated_at": row[7],
            "display_name": row[9] if len(row) > 9 else None,
            "avatar_url": row[10] if len(row) > 10 else None,
            "avatar_seed": row[11] if len(row) > 11 else None,
            "age": row[12] if len(row) > 12 else None,
            "bio": row[13] if len(row) > 13 else None,
            "is_adaptive": bool(row[14]) if len(row) > 14 and row[14] is not None else True,
            "is_locked": bool(row[15]) if len(row) > 15 and row[15] is not None else False,
            "last_evolved_at": row[16] if len(row) > 16 else None,
            "evolution_history_json": row[17] if len(row) > 17 and row[17] else "[]",
        }


def definir_persona_canal(
    channel_id: str | int,
    system_prompt: str = "",
    user_id: str | int = "",
    guild_id: Optional[str | int] = None,
    channel_name: Optional[str] = None,
    temperature: Optional[float] = None,
    model_override: Optional[str] = None,
    persona_slug: Optional[str] = None,
    display_name: Optional[str] = None,
    avatar_url: Optional[str] = None,
    avatar_seed: Optional[str] = None,
    age: Optional[str] = None,
    bio: Optional[str] = None,
    is_adaptive: Optional[bool] = None,
    is_locked: Optional[bool] = None,
    db_path: Optional[str] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Define ou atualiza o System Prompt e metadados de identidade específicos de um canal/thread."""
    c_id = str(channel_id).strip()
    u_id = str(user_id or kwargs.get("autor_id") or "sistema").strip()
    g_id = str(guild_id).strip() if guild_id else None
    prompt = (system_prompt or kwargs.get("prompt") or kwargs.get("prompt_persona") or "").strip()
    c_name = channel_name or kwargs.get("persona_id") or kwargs.get("nome") or ""
    slug_final = persona_slug or kwargs.get("slug") or kwargs.get("persona_slug")

    if not prompt:
        return {"sucesso": False, "mensagem": "O texto do prompt para o canal não pode ser vazio."}

    # Validação de tamanho (máximo 2.000 caracteres conforme o gatekeeper)
    if len(prompt) > 2000:
        return {
            "sucesso": False,
            "mensagem": f"O prompt excede o limite máximo permitido de 2.000 caracteres (tamanho atual: {len(prompt)}).",
        }

    # Preserva parâmetros existentes caso não fornecidos
    existente = obter_persona_canal(c_id, db_path=db_path)
    temp_final = float(temperature) if temperature is not None else (existente["temperature"] if existente else 0.7)
    temp_final = max(0.0, min(1.0, temp_final))
    model_final = model_override if model_override is not None else (existente["model_override"] if existente else None)
    if not slug_final and existente:
        slug_final = existente.get("persona_slug")

    disp_name = display_name if display_name is not None else (existente.get("display_name") if existente else None)
    av_url = avatar_url if avatar_url is not None else (existente.get("avatar_url") if existente else None)
    av_seed = avatar_seed if avatar_seed is not None else (existente.get("avatar_seed") if existente else None)
    age_final = age if age is not None else (existente.get("age") if existente else None)
    bio_final = bio if bio is not None else (existente.get("bio") if existente else None)
    adapt_val = int(is_adaptive) if is_adaptive is not None else (1 if not existente else int(existente.get("is_adaptive", 1)))
    lock_val = int(is_locked) if is_locked is not None else (0 if not existente else int(existente.get("is_locked", 0)))

    with _get_connection(db_path) as conn:
        _ensure_persona_slug_column(conn)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO channel_personas (
                channel_id, guild_id, channel_name, system_prompt, temperature, model_override, created_by_user_id, persona_slug,
                display_name, avatar_url, avatar_seed, age, bio, is_adaptive, is_locked, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(channel_id) DO UPDATE SET
                guild_id=COALESCE(excluded.guild_id, channel_personas.guild_id),
                channel_name=COALESCE(excluded.channel_name, channel_personas.channel_name),
                system_prompt=excluded.system_prompt,
                temperature=excluded.temperature,
                model_override=excluded.model_override,
                created_by_user_id=excluded.created_by_user_id,
                persona_slug=excluded.persona_slug,
                display_name=COALESCE(excluded.display_name, channel_personas.display_name),
                avatar_url=COALESCE(excluded.avatar_url, channel_personas.avatar_url),
                avatar_seed=COALESCE(excluded.avatar_seed, channel_personas.avatar_seed),
                age=COALESCE(excluded.age, channel_personas.age),
                bio=COALESCE(excluded.bio, channel_personas.bio),
                is_adaptive=excluded.is_adaptive,
                is_locked=excluded.is_locked,
                updated_at=CURRENT_TIMESTAMP
            """,
            (c_id, g_id, c_name or None, prompt, temp_final, model_final, u_id, slug_final,
             disp_name, av_url, av_seed, age_final, bio_final, adapt_val, lock_val),
        )
        conn.commit()

    return {
        "sucesso": True,
        "mensagem": f"🎭 Persona ativada com sucesso para o canal `{c_name or c_id}`!",
        "channel_id": c_id,
        "persona_id": slug_final or c_name or "personalizada",
        "persona_slug": slug_final,
        "display_name": disp_name,
        "avatar_url": av_url,
        "age": age_final,
        "temperature": temp_final,
        "model_override": model_final,
    }


def obter_avatar_persona(persona: Optional[Dict[str, Any]]) -> str:
    """Retorna URL do avatar da persona, recorrendo a avatar_url ou DiceBear determinístico."""
    if persona:
        if persona.get("avatar_url") and str(persona["avatar_url"]).strip().startswith("http"):
            return str(persona["avatar_url"]).strip()
        seed = (
            persona.get("avatar_seed")
            or persona.get("persona_slug")
            or persona.get("display_name")
            or persona.get("channel_name")
            or "antigravity"
        )
        seed_clean = re.sub(r"[^a-zA-Z0-9_-]", "", str(seed).strip().lower())
        return f"https://api.dicebear.com/7.x/bottts/png?seed={seed_clean or 'antigravity'}"
    return "https://api.dicebear.com/7.x/bottts/png?seed=antigravity"


def definir_avatar_canal(
    channel_id: str | int,
    avatar_url: Optional[str] = None,
    avatar_seed: Optional[str] = None,
    db_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Define a URL da imagem ou a semente do avatar para a persona do canal."""
    c_id = str(channel_id).strip()
    existente = obter_persona_canal(c_id, db_path=db_path)
    if not existente:
        return {
            "sucesso": False,
            "mensagem": "Este canal ainda não possui uma persona configurada. Ative uma persona com `!persona canal <prompt>` primeiro.",
        }

    url_final = avatar_url.strip() if avatar_url and avatar_url.strip() else None
    seed_final = avatar_seed.strip() if avatar_seed and avatar_seed.strip() else None

    with _get_connection(db_path) as conn:
        _ensure_persona_slug_column(conn)
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE channel_personas
            SET avatar_url = ?, avatar_seed = ?, is_locked = 1, updated_at = CURRENT_TIMESTAMP
            WHERE channel_id = ?
            """,
            (url_final, seed_final, c_id),
        )
        conn.commit()

    avatar_preview = url_final or f"https://api.dicebear.com/7.x/bottts/png?seed={seed_final or 'avatar'}"
    return {
        "sucesso": True,
        "mensagem": f"🖼️ Avatar da persona do canal atualizado com sucesso!\n• URL/Preview: {avatar_preview}",
        "avatar_url": url_final,
        "avatar_seed": seed_final,
    }


def definir_identidade_canal(
    channel_id: str | int,
    display_name: Optional[str] = None,
    age: Optional[str] = None,
    bio: Optional[str] = None,
    db_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Define metadados biográficos da persona do canal (Nome de exibição, Idade e Bio)."""
    c_id = str(channel_id).strip()
    existente = obter_persona_canal(c_id, db_path=db_path)
    if not existente:
        return {
            "sucesso": False,
            "mensagem": "Este canal ainda não possui uma persona configurada. Ative uma persona com `!persona canal <prompt>` primeiro.",
        }

    nome_final = display_name.strip() if display_name and display_name.strip() else existente.get("display_name")
    idade_final = age.strip() if age and age.strip() else existente.get("age")
    bio_final = bio.strip() if bio and bio.strip() else existente.get("bio")

    with _get_connection(db_path) as conn:
        _ensure_persona_slug_column(conn)
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE channel_personas
            SET display_name = ?, age = ?, bio = ?, is_locked = 1, updated_at = CURRENT_TIMESTAMP
            WHERE channel_id = ?
            """,
            (nome_final, idade_final, bio_final, c_id),
        )
        conn.commit()

    return {
        "sucesso": True,
        "mensagem": (
            f"👤 **Identidade da Persona Atualizada:**\n"
            f"• **Nome:** `{nome_final or 'Padrão'}`\n"
            f"• **Idade:** `{idade_final or 'Não especificada'}`\n"
            f"• **Bio:** *{bio_final or 'Sem bio'}*"
        ),
        "display_name": nome_final,
        "age": idade_final,
        "bio": bio_final,
    }


def definir_trava_persona_canal(
    channel_id: str | int,
    is_locked: bool = True,
    db_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Trava ou destrava a persona do canal contra metamorfoses automáticas semanais."""
    c_id = str(channel_id).strip()
    existente = obter_persona_canal(c_id, db_path=db_path)
    if not existente:
        return {
            "sucesso": False,
            "mensagem": "Este canal ainda não possui uma persona configurada.",
        }

    lock_val = 1 if is_locked else 0
    with _get_connection(db_path) as conn:
        _ensure_persona_slug_column(conn)
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE channel_personas
            SET is_locked = ?, updated_at = CURRENT_TIMESTAMP
            WHERE channel_id = ?
            """,
            (lock_val, c_id),
        )
        conn.commit()

    if is_locked:
        msg = "🔒 **Persona Travada com Sucesso!** O perfil atual agora é permanente e não sofrerá mutações semanais."
    else:
        msg = "🔓 **Persona Destravada!** O perfil deste canal agora está em modo adaptativo e evoluirá a cada 7 dias com base nas conversas."

    return {"sucesso": True, "mensagem": msg, "is_locked": is_locked}


def aplicar_preset_canal(
    channel_id: str | int,
    preset_slug: str,
    user_id: str | int = "",
    guild_id: Optional[str | int] = None,
    channel_name: Optional[str] = None,
    db_path: Optional[str] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Aplica diretamente um template ou preset da Central de Prompts (IDEA-20) no canal."""
    slug = (preset_slug or "").lower().strip()
    template = obter_template(slug, db_path=db_path)
    if not template:
        return {
            "sucesso": False,
            "mensagem": f"Template ou preset '{slug}' não encontrado no catálogo da Central de Prompts (!prompts).",
        }

    c_name = channel_name or slug
    return definir_persona_canal(
        channel_id=channel_id,
        system_prompt=template["template_text"],
        user_id=user_id,
        guild_id=guild_id,
        channel_name=c_name,
        temperature=template["temperatura"],
        model_override=None,
        persona_slug=slug,
        db_path=db_path,
        persona_id=c_name,
    )


def definir_temperatura_canal(channel_id: str | int, temperature: float, db_path: Optional[str] = None) -> Dict[str, Any]:
    """Ajusta a temperatura da LLM exclusivamente para o canal especificado."""
    c_id = str(channel_id).strip()
    existente = obter_persona_canal(c_id, db_path=db_path)
    if not existente:
        return {
            "sucesso": False,
            "mensagem": "Este canal ainda não possui uma persona configurada. Use `!persona canal <prompt>` primeiro.",
        }

    temp = max(0.0, min(1.0, float(temperature)))
    with _get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE channel_personas SET temperature = ?, updated_at = CURRENT_TIMESTAMP WHERE channel_id = ?",
            (temp, c_id),
        )
        conn.commit()

    return {"sucesso": True, "mensagem": f"🌡️ Temperatura do canal ajustada para `{temp}`."}


def definir_modelo_canal(channel_id: str | int, model_name: Optional[str], db_path: Optional[str] = None) -> Dict[str, Any]:
    """Define um override de modelo/provedor para o canal (ex: 'local', 'gemini-flash', 'gemini-pro')."""
    c_id = str(channel_id).strip()
    existente = obter_persona_canal(c_id, db_path=db_path)
    if not existente:
        return {
            "sucesso": False,
            "mensagem": "Este canal ainda não possui uma persona configurada. Use `!persona canal <prompt>` primeiro.",
        }

    mod = model_name.strip() if model_name else None
    with _get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE channel_personas SET model_override = ?, updated_at = CURRENT_TIMESTAMP WHERE channel_id = ?",
            (mod, c_id),
        )
        conn.commit()

    desc = f"`{mod}`" if mod else "padrão do usuário/sistema"
    return {"sucesso": True, "mensagem": f"🤖 Modelo padrão do canal definido para: {desc}."}


def resetar_persona_canal(channel_id: str | int, db_path: Optional[str] = None) -> Dict[str, Any]:
    """Remove o override de persona do canal, restaurando o assistente padrão."""
    c_id = str(channel_id).strip()
    with _get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM channel_personas WHERE channel_id = ?", (c_id,))
        afetados = cursor.rowcount
        conn.commit()

    if afetados > 0:
        return {"sucesso": True, "mensagem": "🔄 Persona do canal removida. O canal voltou a responder como o assistente padrão."}
    return {"sucesso": False, "mensagem": "Este canal não possuía persona customizada ativa."}


def listar_personas_canais(guild_id: Optional[str | int] = None, db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Lista todos os canais que possuem personas customizadas ativas."""
    with _get_connection(db_path) as conn:
        _ensure_persona_slug_column(conn)
        cursor = conn.cursor()
        if guild_id:
            cursor.execute(
                """
                SELECT channel_id, guild_id, channel_name, system_prompt, temperature, model_override, updated_at,
                       display_name, avatar_url, age, is_locked, persona_slug
                FROM channel_personas
                WHERE guild_id = ?
                ORDER BY updated_at DESC
                """,
                (str(guild_id).strip(),),
            )
        else:
            cursor.execute(
                """
                SELECT channel_id, guild_id, channel_name, system_prompt, temperature, model_override, updated_at,
                       display_name, avatar_url, age, is_locked, persona_slug
                FROM channel_personas
                ORDER BY updated_at DESC
                """
            )
        rows = cursor.fetchall()
        return [
            {
                "channel_id": r[0],
                "guild_id": r[1],
                "channel_name": r[2] or r[0],
                "prompt_preview": (r[3][:120] + "...") if len(r[3]) > 120 else r[3],
                "temperature": r[4],
                "model_override": r[5],
                "updated_at": r[6],
                "display_name": r[7] if len(r) > 7 else None,
                "avatar_url": r[8] if len(r) > 8 else None,
                "age": r[9] if len(r) > 9 else None,
                "is_locked": bool(r[10]) if len(r) > 10 and r[10] is not None else False,
                "persona_slug": r[11] if len(r) > 11 else None,
            }
            for r in rows
        ]


# Aliases de conveniência
configurar_persona_canal = definir_persona_canal
remover_persona_canal = resetar_persona_canal


def listar_personas_disponiveis(categoria: Optional[str] = None, db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retorna todas as personas e presets cadastrados no catálogo para aplicação rápida."""
    templates = listar_templates(categoria=categoria, incluir_presets=True, db_path=db_path)
    personas = []
    for t in templates:
        personas.append({
            "id": t["id"],
            "slug": t["id"],
            "nome": t["nome"],
            "descricao": t["descricao"],
            "categoria": t["categoria"],
            "temperatura": t["temperatura"],
            "is_preset": t.get("is_preset", False),
            "created_at": t.get("created_at"),
        })
    return personas


def salvar_nova_persona(
    slug_id: str,
    prompt: str,
    nome: Optional[str] = None,
    descricao: Optional[str] = None,
    categoria: str = "personas",
    temperatura: float = 0.7,
    user_id: Optional[str] = None,
    db_path: Optional[str] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Cadastra uma nova persona no catálogo geral para uso em qualquer canal."""
    texto_prompt = prompt or kwargs.get("template_text") or kwargs.get("prompt_diretrizes") or ""
    res = salvar_template(
        slug_id=slug_id,
        nome=nome or slug_id,
        template_text=texto_prompt,
        descricao=descricao or kwargs.get("description"),
        categoria=categoria,
        temperatura=temperatura,
        user_id=user_id,
        db_path=db_path,
    )
    if res.get("sucesso"):
        return {
            "sucesso": True,
            "mensagem": f"🎭 Nova persona **{nome or slug_id}** (`{slug_id}`) cadastrada com sucesso no catálogo! Para ativá-la em qualquer canal, use: `!persona canal aplicar {slug_id}`.",
            "id": slug_id,
            "nome": nome or slug_id,
        }
    return res


def remover_persona_catalogo(
    slug_id: str,
    user_id: Optional[str] = None,
    db_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Remove uma persona customizada do catálogo."""
    return remover_template(slug_ou_id=slug_id, user_id=user_id, db_path=db_path)


# Aliases adicionais
listar_catalogo_personas = listar_personas_disponiveis
cadastrar_persona = salvar_nova_persona
