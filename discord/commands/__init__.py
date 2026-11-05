"""
Pacote de Comandos do Bot Discord (Prefixados com '!').

Importa os comandos embutidos e expõe as rotinas de despacho e registro.
"""

from commands.registry import CommandContext, CommandDefinition, register_command, registry
import commands.builtins  # noqa: F401


async def handle_command(message, client) -> bool:
    """Despacha uma mensagem para o registro de comandos.
    
    Retorna True se foi processada como comando, False se deve continuar o fluxo normal.
    """
    return await registry.dispatch(message, client)


__all__ = [
    "handle_command",
    "register_command",
    "registry",
    "CommandContext",
    "CommandDefinition",
]
