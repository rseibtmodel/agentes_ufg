"""
Gerenciador de Contexto de Execução por Mensagem e Usuário.

Mantém o estado do usuário ativo e armazena de forma isolada por usuário
os arquivos PDF agendados para envio como anexo no Discord, garantindo compatibilidade
entre o loop de eventos assíncrono e threads auxiliares (`asyncio.to_thread`).
"""

from collections import defaultdict
from contextvars import ContextVar
from pathlib import Path
from typing import Dict, List, Optional

# ContextVar para rastreamento assíncrono seguro
_current_user_var: ContextVar[str] = ContextVar("current_user", default="default")
_current_user_id_var: ContextVar[str] = ContextVar("current_user_id", default="")
_current_channel_id_var: ContextVar[str] = ContextVar("current_channel_id", default="")
_current_guild_id_var: ContextVar[str] = ContextVar("current_guild_id", default="")
_current_channel_name_var: ContextVar[str] = ContextVar("current_channel_name", default="")

# Dicionários compartilhados thread-safe em nível de processo indexados por usuário
_pending_files_by_user: Dict[str, List[Path]] = defaultdict(list)
_pending_views_by_user: Dict[str, List[Any]] = defaultdict(list)


def set_current_user(user: str) -> None:
    """Define o identificador/nome do usuário para o contexto atual."""
    _current_user_var.set(user)


def get_current_user() -> str:
    """Recupera o identificador/nome do usuário do contexto atual."""
    return _current_user_var.get() or "default"


def set_current_user_id(user_id: str | int) -> None:
    """Define o ID numérico do usuário no Discord para o contexto atual."""
    _current_user_id_var.set(str(user_id))


def get_current_user_id() -> str:
    """Recupera o ID numérico do usuário no Discord do contexto atual."""
    return _current_user_id_var.get() or ""


def set_current_channel_id(channel_id: str | int) -> None:
    """Define o ID do canal onde a mensagem foi recebida."""
    _current_channel_id_var.set(str(channel_id))


def get_current_channel_id() -> str:
    """Recupera o ID do canal da mensagem atual."""
    return _current_channel_id_var.get() or ""


def set_current_guild_id(guild_id: Optional[str | int]) -> None:
    """Define o ID do servidor (guild) do contexto atual."""
    _current_guild_id_var.set(str(guild_id) if guild_id else "")


def get_current_guild_id() -> str:
    """Recupera o ID do servidor (guild) do contexto atual."""
    return _current_guild_id_var.get() or ""


def set_current_channel_name(channel_name: Optional[str]) -> None:
    """Define o nome amigável do canal atual."""
    _current_channel_name_var.set(str(channel_name) if channel_name else "")


def get_current_channel_name() -> str:
    """Recupera o nome do canal do contexto atual."""
    return _current_channel_name_var.get() or ""


def set_contexto_requisicao(
    user_name: str,
    user_id: str | int,
    channel_id: str | int,
    guild_id: Optional[str | int] = None,
    channel_name: Optional[str] = None,
) -> None:
    """Configura todo o contexto da requisição atual de uma só vez."""
    set_current_user(user_name)
    set_current_user_id(user_id)
    set_current_channel_id(channel_id)
    set_current_guild_id(guild_id)
    set_current_channel_name(channel_name)


def clear_pending_files(user: Optional[str] = None) -> None:
    """Limpa a lista de arquivos pendentes de envio para o usuário."""
    usuario = user or get_current_user()
    _pending_files_by_user[usuario].clear()


def add_pending_file(path: Path, user: Optional[str] = None) -> None:
    """Registra um arquivo para ser enviado como anexo no Discord."""
    usuario = user or get_current_user()
    if path not in _pending_files_by_user[usuario]:
        _pending_files_by_user[usuario].append(path)


def get_pending_files(user: Optional[str] = None) -> List[Path]:
    """Retorna os arquivos pendentes para envio como anexo no Discord."""
    usuario = user or get_current_user()
    return list(_pending_files_by_user[usuario])


def add_pending_view(view: Any, user: Optional[str] = None) -> None:
    """Agenda uma discord.ui.View para ser anexada à mensagem de resposta."""
    usuario = user or get_current_user()
    _pending_views_by_user[usuario].append(view)


def get_pending_views(user: Optional[str] = None) -> List[Any]:
    """Retorna as views interativas agendadas para o usuário atual."""
    usuario = user or get_current_user()
    return list(_pending_views_by_user[usuario])


def clear_pending_views(user: Optional[str] = None) -> None:
    """Limpa a lista de views interativas agendadas para o usuário."""
    usuario = user or get_current_user()
    if usuario in _pending_views_by_user:
        _pending_views_by_user[usuario].clear()

