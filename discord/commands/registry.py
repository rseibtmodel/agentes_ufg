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
        """Responde referenciando a mensagem original do usuário através do Message Gateway (Outbox).
        
        Divide automaticamente respostas longas (> 1900 caracteres) em múltiplos blocos.
        Suporta componentes de interface interativos (discord.ui.View) anexados.
        100% dos despachos são canalizados pelo message_gateway, preservando controle anti-spam
        e limites de taxa da API do Discord.
        """
        from message_gateway import message_gateway, MessagePriority
        blocos = dividir_mensagem(content, limite=1900)
        mensagens = []
        primeiro = True
        for bloco in blocos:
            v = view if primeiro else None
            ref = self.message if primeiro else None
            try:
                msg = await message_gateway.dispatch(
                    self.channel,
                    content=bloco,
                    view=v,
                    priority=MessagePriority.HIGH,
                    reference=ref,
                )
                primeiro = False
                if msg:
                    mensagens.append(msg)
            except discord.Forbidden:
                texto = f"{self.author.mention}\n{bloco}" if primeiro else bloco
                msg = await message_gateway.dispatch(
                    self.channel,
                    content=texto,
                    view=v,
                    priority=MessagePriority.HIGH,
                )
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
    category: str = "Geral & Diagnóstico"
    example: Optional[str] = None
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
        category: Optional[str] = None,
        example: Optional[str] = None,
        aliases: Optional[List[str]] = None,
    ):
        """Decorador para registrar um novo comando com metadados para o Help dinâmico.
        
        Exemplo:
            @register_command(
                name="ping",
                description="Verifica a latência do bot",
                category="Geral & Diagnóstico",
                example="!ping",
                aliases=["latencia"]
            )
            async def cmd_ping(ctx: CommandContext):
                await ctx.reply("Pong! 🏓")
        """
        def decorator(func: Callable):
            cmd_name = (name or func.__name__).replace("cmd_", "").lower()
            cmd_desc = description or (func.__doc__ or "").strip() or "Sem descrição fornecida."
            cmd_usage = usage or f"{self.prefix}{cmd_name}"
            cmd_category = category or "Geral & Diagnóstico"
            cmd_aliases = [a.lower() for a in (aliases or [])]
            is_async = inspect.iscoroutinefunction(func)

            defn = CommandDefinition(
                name=cmd_name,
                func=func,
                description=cmd_desc,
                usage=cmd_usage,
                category=cmd_category,
                example=example,
                aliases=cmd_aliases,
                is_async=is_async,
            )

            self._commands[cmd_name] = defn
            for alias in cmd_aliases:
                self._aliases[alias] = cmd_name

            logger.info("Comando registrado: %s%s (cat=%s, aliases=%s)", self.prefix, cmd_name, cmd_category, cmd_aliases)
            return func

        return decorator

    def get_categories(self) -> List[str]:
        """Retorna lista ordenada de todas as categorias únicas registradas."""
        cats = {cmd.category for cmd in self._commands.values() if cmd.category}
        return sorted(list(cats))

    def get_commands_by_category(self, category: str) -> List[CommandDefinition]:
        """Retorna todos os comandos que pertencem à categoria informada (busca flexível)."""
        cat_termo = category.lower().strip()
        return [
            cmd for cmd in sorted(self._commands.values(), key=lambda c: c.name)
            if cat_termo in cmd.category.lower()
        ]

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
