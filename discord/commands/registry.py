"""
Sistema de Registro e Roteamento de Comandos com Prefixo (!).

Permite criar e registrar comandos personalizados facilmente usando o decorador
`@register_command`, fornecendo um contexto estruturado com métodos auxiliares.
"""

import asyncio
from dataclasses import dataclass, field
import inspect
import logging
from typing import Callable, Dict, List, Optional
import discord
from config import COMMAND_PREFIX
from utils import dividir_mensagem, parse_comando

logger = logging.getLogger(__name__)


@dataclass
class CommandContext:
    """Contexto de execução de um comando acionado pelo usuário."""
    message: discord.Message
    client: discord.Client
    command_name: str
    args: List[str]
    arg_str: str

    @property
    def author(self):
        return self.message.author

    @property
    def channel(self):
        return self.message.channel

    async def reply(self, content: str, view: Optional[discord.ui.View] = None) -> List[discord.Message]:
        """Responde referenciando a mensagem original do usuário.
        
        Divide automaticamente respostas longas (> 1900 caracteres) em múltiplos blocos.
        Suporta componentes de interface interativos (discord.ui.View) anexados.
        Caso o bot não possua permissão 'Read Message History' (código 160002)
        no canal para responder com citação, envia diretamente com menção via Message Gateway.
        """
        blocos = dividir_mensagem(content, limite=1900)
        mensagens = []
        primeiro = True
        for bloco in blocos:
            v = view if primeiro else None
            try:
                if primeiro:
                    if v is not None:
                        msg = await self.message.reply(bloco, view=v)
                    else:
                        msg = await self.message.reply(bloco)
                    primeiro = False
                else:
                    from message_gateway import message_gateway, MessagePriority
                    msg = await message_gateway.dispatch(self.channel, content=bloco, priority=MessagePriority.HIGH)
                if msg:
                    mensagens.append(msg)
            except discord.Forbidden:
                from message_gateway import message_gateway, MessagePriority
                texto = f"{self.author.mention}\n{bloco}" if primeiro else bloco
                msg = await message_gateway.dispatch(self.channel, content=texto, view=v, priority=MessagePriority.HIGH)
                primeiro = False
                if msg:
                    mensagens.append(msg)
        return mensagens

    async def send(self, content: str, view: Optional[discord.ui.View] = None) -> List[discord.Message]:
        """Envia mensagens no canal dividindo em blocos se ultrapassar o limite."""
        from message_gateway import message_gateway, MessagePriority
        blocos = dividir_mensagem(content, limite=1900)
        mensagens = []
        primeiro = True
        for bloco in blocos:
            v = view if primeiro else None
            msg = await message_gateway.dispatch(self.channel, content=bloco, view=v, priority=MessagePriority.HIGH)
            primeiro = False
            if msg:
                mensagens.append(msg)
        return mensagens


@dataclass
class CommandDefinition:
    """Metadados de um comando registrado."""
    name: str
    func: Callable
    description: str
    usage: str
    aliases: List[str] = field(default_factory=list)
    is_async: bool = True


class CommandRegistry:
    """Registro e despachante de comandos iniciados com prefixo."""

    def __init__(self, prefix: str = COMMAND_PREFIX):
        self.prefix = prefix
        self._commands: Dict[str, CommandDefinition] = {}
        self._aliases: Dict[str, str] = {}

    def register(
        self,
        name: Optional[str] = None,
        description: Optional[str] = None,
        usage: Optional[str] = None,
        aliases: Optional[List[str]] = None,
    ):
        """Decorador para registrar um novo comando.
        
        Exemplo:
            @register_command(
                name="ping",
                description="Verifica a latência do bot",
                aliases=["latencia"]
            )
            async def cmd_ping(ctx: CommandContext):
                await ctx.reply("Pong! 🏓")
        """
        def decorator(func: Callable):
            cmd_name = (name or func.__name__).replace("cmd_", "").lower()
            cmd_desc = description or (func.__doc__ or "").strip() or "Sem descrição fornecida."
            cmd_usage = usage or f"{self.prefix}{cmd_name}"
            cmd_aliases = [a.lower() for a in (aliases or [])]
            is_async = inspect.iscoroutinefunction(func)

            defn = CommandDefinition(
                name=cmd_name,
                func=func,
                description=cmd_desc,
                usage=cmd_usage,
                aliases=cmd_aliases,
                is_async=is_async,
            )

            self._commands[cmd_name] = defn
            for alias in cmd_aliases:
                self._aliases[alias] = cmd_name

            logger.info("Comando registrado: %s%s (aliases=%s)", self.prefix, cmd_name, cmd_aliases)
            return func

        return decorator

    def get_command(self, name: str) -> Optional[CommandDefinition]:
        """Busca a definição do comando por nome ou apelido (alias)."""
        clean_name = name.lower()
        if clean_name in self._commands:
            return self._commands[clean_name]
        if clean_name in self._aliases:
            return self._commands[self._aliases[clean_name]]
        return None

    async def dispatch(self, message: discord.Message, client: discord.Client) -> bool:
        """Verifica se a mensagem é um comando válido e executa.
        
        Retorna True se a mensagem foi tratada como comando, ou False caso contrário.
        """
        conteudo = message.content or ""
        if not conteudo.startswith(self.prefix):
            return False

        cmd_name, arg_str, args_list = parse_comando(conteudo, self.prefix)
        if not cmd_name:
            return False

        defn = self.get_command(cmd_name)
        if not defn:
            # Comando desconhecido com o prefixo
            await message.channel.send(
                f"❓ Comando `{self.prefix}{cmd_name}` não reconhecido. "
                f"Digite `{self.prefix}ajuda` para ver os comandos disponíveis."
            )
            return True

        ctx = CommandContext(
            message=message,
            client=client,
            command_name=cmd_name,
            args=args_list,
            arg_str=arg_str,
        )

        try:
            if defn.is_async:
                await defn.func(ctx)
            else:
                await asyncio.to_thread(defn.func, ctx)
            return True
        except Exception as e:
            logger.exception("Erro ao executar comando %s", cmd_name)
            await message.channel.send(f"⚠️ Erro ao executar `{self.prefix}{cmd_name}`: {str(e)}")
            return True

    def get_all_commands(self) -> List[CommandDefinition]:
        """Retorna lista ordenada de todos os comandos registrados."""
        return sorted(self._commands.values(), key=lambda c: c.name)


# Instância global padrão do registro de comandos
registry = CommandRegistry()
register_command = registry.register
