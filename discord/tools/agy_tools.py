"""
Ferramentas do Antigravity Remote Runner (Function Calling — IDEA-23).

Permite à LLM consultar o ecossistema de skills e agentes locais, obter
status de telemetria do sistema e invocar a perspectiva analítica de um
especialista em modo estritamente Read-Only.
"""

from typing import Any, Dict, Optional

from agy_manager import agy_manager
from context_manager import get_current_user_id
from tools.registry import register_tool


@register_tool(
    name="listar_skills_antigravity",
    description=(
        "Lista todas as skills e agentes especialistas locais cadastrados no ecossistema Antigravity "
        "(.agents/skills/). Retorna seus nomes, pastas e descrições de especialidade."
    ),
    parameters={
        "type": "object",
        "properties": {},
    },
)
def tool_listar_skills_antigravity() -> Dict[str, Any]:
    """Retorna o catálogo de skills locais cadastradas."""
    skills = agy_manager.listar_skills()
    resumo = [
        {
            "nome": s["name"],
            "slug": s["pasta"],
            "descricao": s["description"],
        }
        for s in skills
    ]
    return {
        "sucesso": True,
        "dados": {
            "total": len(skills),
            "skills": resumo,
        },
        "erro": None,
    }


@register_tool(
    name="consultar_skill_antigravity",
    description=(
        "Consulta um agente especialista ou skill local do Antigravity (ex: 'critic', 'architect', "
        "'oraculo', 'ux_designer', 'review') sobre um tema, código ou decisão técnica. "
        "A consulta é executada no modo estritamente consultivo e analítico (Read-Only)."
    ),
    parameters={
        "type": "object",
        "properties": {
            "nome_skill": {
                "type": "string",
                "description": "Nome ou slug da skill a ser consultada (ex: 'architect', 'critic', 'oraculo').",
            },
            "consulta": {
                "type": "string",
                "description": "A pergunta, tema, código ou dilema a ser avaliado pelo especialista.",
            },
        },
        "required": ["nome_skill", "consulta"],
    },
)
async def tool_consultar_skill_antigravity(nome_skill: str, consulta: str) -> Dict[str, Any]:
    """Executa a consulta com a persona da skill solicitada."""
    user_id = get_current_user_id() or "usuario_padrao"
    return await agy_manager.consultar_skill(
        nome_skill=nome_skill,
        consulta=consulta,
        user_id=user_id,
    )
