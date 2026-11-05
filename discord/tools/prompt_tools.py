"""
Ferramentas de Consulta e Gestão de Templates de Prompt (Prompt Hub) para a LLM — IDEA-20.
"""

from context_manager import get_current_user_id
from prompt_hub import listar_templates, obter_template, salvar_template
from tools.registry import register_tool
from typing import Optional


@register_tool(
    name="listar_templates_prompt",
    description="Lista os templates de prompts e presets cognitivos disponíveis no catálogo central (ex: dev, cfo, direto, revisor, socrates, tributarista).",
    parameters={
        "type": "object",
        "properties": {
            "categoria": {
                "type": "string",
                "description": "Filtro opcional por categoria (ex: 'programacao', 'negocios', 'produtividade', 'escrita', 'filosofia', 'tributario').",
            }
        },
    },
)
async def tool_listar_templates_prompt(categoria: Optional[str] = None) -> str:
    """Retorna os templates disponíveis na Central de Prompts."""
    templates = listar_templates(categoria=categoria)
    if not templates:
        return "Nenhum template encontrado no catálogo para a categoria informada."

    linhas = ["📚 **Templates de Prompt Disponíveis no Catálogo:**"]
    for t in templates:
        tipo = "🔒 Oficial" if t["is_builtin"] else "👤 Custom"
        linhas.append(f"• **`{t['id']}`** ({tipo}) — *{t['nome']}*: {t['descricao']} (cat: `{t['categoria']}`)")

    return "\n".join(linhas)


@register_tool(
    name="obter_template_prompt",
    description="Recupera o texto completo de um template ou preset de prompt pelo seu identificador (slug) na Central de Prompts.",
    parameters={
        "type": "object",
        "properties": {
            "slug_template": {
                "type": "string",
                "description": "Identificador do template (ex: 'dev', 'cfo', 'direto', 'socrates', 'tributarista').",
            }
        },
        "required": ["slug_template"],
    },
)
async def tool_obter_template_prompt(slug_template: str) -> str:
    """Retorna o conteúdo do template solicitado."""
    template = obter_template(slug_template)
    if not template:
        return f"Template '{slug_template}' não encontrado no catálogo da Central de Prompts (!prompts)."

    tipo = "Oficial de Fábrica" if template["is_builtin"] else "Customizado do Usuário"
    return (
        f"📋 **Template:** `{template['id']}` ({template['nome']})\n"
        f"🏷️ **Tipo:** {tipo} | **Categoria:** `{template['categoria']}` | **Temp Sugerida:** `{template['temperatura']}`\n"
        f"📝 **Descrição:** {template['descricao']}\n\n"
        f"```text\n{template['template_text']}\n```"
    )


@register_tool(
    name="salvar_template_prompt",
    description="Salva um novo template de prompt reutilizável no catálogo pessoal da Central de Prompts.",
    parameters={
        "type": "object",
        "properties": {
            "slug": {
                "type": "string",
                "description": "Identificador curto em minúsculas sem espaços (ex: 'arquiteto_rust', 'copywriter').",
            },
            "nome": {
                "type": "string",
                "description": "Nome legível do template (ex: 'Especialista em Rust').",
            },
            "texto_prompt": {
                "type": "string",
                "description": "As instruções completas do prompt a serem reutilizadas.",
            },
            "descricao": {
                "type": "string",
                "description": "Breve explicação do objetivo do template.",
            },
            "categoria": {
                "type": "string",
                "description": "Categoria do prompt (ex: 'programacao', 'negocios', 'escrita', 'geral').",
            },
        },
        "required": ["slug", "nome", "texto_prompt"],
    },
)
async def tool_salvar_template_prompt(
    slug: str,
    nome: str,
    texto_prompt: str,
    descricao: Optional[str] = None,
    categoria: str = "geral",
) -> str:
    """Salva um novo template no catálogo."""
    user_id = get_current_user_id()
    res = salvar_template(
        slug_id=slug,
        nome=nome,
        template_text=texto_prompt,
        descricao=descricao,
        categoria=categoria,
        user_id=user_id,
    )
    return res["mensagem"]
