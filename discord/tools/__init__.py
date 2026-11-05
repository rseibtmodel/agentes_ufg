"""
Pacote de Tools para a LLM (Function Calling).

Importa os módulos de ferramentas para garantir o registro automático
e exporta funções públicas para obtenção de schemas e execução.
"""

from tools.registry import registry, register_tool

# Importação dos módulos de ferramentas para acionar o registro
import tools.datetime_tools  # noqa: F401
import tools.pdf_tools  # noqa: F401
import tools.memory_tools  # noqa: F401
import tools.calendar_tools  # noqa: F401
import tools.list_tools  # noqa: F401
import tools.reminder_tools  # noqa: F401
import tools.settings_tools  # noqa: F401
import tools.digest_tools  # noqa: F401
import tools.web_tools  # noqa: F401
import tools.prompt_tools  # noqa: F401
import tools.topic_tools  # noqa: F401
import tools.persona_tools  # noqa: F401


from tools.tool_filter import (
    filtrar_ferramentas_relevantes,
    inicializar_cache_ferramentas,
)


def get_tools_schema():
    """Retorna a lista de schemas de ferramentas no formato da API OpenAI/LM Studio."""
    return registry.get_schemas()


async def execute_tool(name: str, arguments: dict | str) -> str:
    """Executa a ferramenta informada pelo nome."""
    return await registry.execute(name, arguments)


__all__ = [
    "registry",
    "register_tool",
    "get_tools_schema",
    "execute_tool",
    "filtrar_ferramentas_relevantes",
    "inicializar_cache_ferramentas",
]
