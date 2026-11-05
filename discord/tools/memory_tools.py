"""
Ferramentas de Consulta à Memória Vetorial (ChromaDB) para a LLM.

Permite que a LLM pesquise ativamente no acervo de memórias passadas do usuário
quando precisar resgatar fatos, preferências ou diálogos antigos.
"""

from context_manager import get_current_user
from tools.registry import register_tool
from vector_db import buscar_memorias_relevantes, contar_memorias


@register_tool(
    name="consultar_memoria_passada",
    description="Pesquisa no banco vetorial ChromaDB por mensagens, preferências, fatos ou detalhes que o usuário mencionou em conversas passadas. Útil para lembrar preferências pessoais, histórico profissional, projetos ou tópicos discutidos anteriormente.",
    parameters={
        "type": "object",
        "properties": {
            "termo_ou_pergunta": {
                "type": "string",
                "description": "Texto ou pergunta para busca semântica na memória (ex: 'qual a cor favorita do usuário', 'carro', 'empresa onde trabalha').",
            }
        },
        "required": ["termo_ou_pergunta"],
    },
)
async def tool_consultar_memoria_passada(termo_ou_pergunta: str) -> str:
    """Busca semanticamente na coleção '{user}_memory' do usuário."""
    usuario = get_current_user()
    total = contar_memorias(usuario)

    if total == 0:
        return f"A memória vetorial do usuário '{usuario}' está vazia no momento."

    memorias = await buscar_memorias_relevantes(usuario, termo_ou_pergunta, top_k=3)
    if not memorias:
        return f"Nenhum registro relevante encontrado na memória vetorial para '{termo_ou_pergunta}'."

    linhas = [f"Resultados encontrados na memória vetorial de '{usuario}' ({len(memorias)} registro(s)):"]
    for idx, mem in enumerate(memorias, start=1):
        papel = "Usuário" if mem["role"] == "user" else "Assistente"
        linhas.append(f"{idx}. [{papel}]: {mem['conteudo']} (relevância: distância {mem['distancia']})")

    return "\n".join(linhas)
