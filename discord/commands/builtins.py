"""
Agregador e Ponto de Entrada dos Comandos Embutidos do Bot (Builtins).

Modularizado na Onda 3 de Refatoração (OS-005) em submódulos de domínio especializado:
- system_commands.py: Diagnóstico, ajuda, ping, histórico, hora, status, voz, digest e gateway
- calendar_commands.py: Google Calendar (agenda, agendar, desmarcar)
- productivity_commands.py: Listas pessoais e lembretes agendados
- ai_commands.py: Modelos LLM, Central de Prompts e Personas por canal (IDEA-20 e IDEA-26)
- knowledge_commands.py: PDFs, RAG de livros, memória ChromaDB e tópicos de notas (IDEA-25)
- web_commands.py: Pesquisa web em tempo real e leitura analítica de links
"""

# Importa todos os módulos de comando para garantir o registro via @register_command
import commands.ai_commands  # noqa: F401
import commands.calendar_commands  # noqa: F401
import commands.knowledge_commands  # noqa: F401
import commands.productivity_commands  # noqa: F401
import commands.system_commands  # noqa: F401
import commands.web_commands  # noqa: F401

__all__ = [
    "ai_commands",
    "calendar_commands",
    "knowledge_commands",
    "productivity_commands",
    "system_commands",
    "web_commands",
]
