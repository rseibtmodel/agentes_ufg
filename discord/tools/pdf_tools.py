"""
Ferramentas de Gerenciamento, Análise, Sumarização e RAG de Livros/PDFs para a LLM.

Permite à LLM consultar o acervo de PDFs do usuário, extrair metadados,
listar sumários, resumir capítulos específicos, indexar no ChromaDB
e responder a dúvidas sobre as obras com citação de páginas.
"""

from typing import Optional
from context_manager import add_pending_file, get_current_user
from pdf_manager import (
    consultar_documento_rag,
    indexar_documento_rag,
    listar_pdfs_usuario,
    listar_status_pdfs_usuario,
    localizar_pdf_usuario,
    obter_metadados_documento,
    obter_sumario_documento,
    resumir_capitulo_documento,
)
from tools.registry import register_tool


@register_tool(
    name="listar_meus_pdfs",
    description="Lista todos os arquivos PDF disponíveis na pasta pessoal do usuário no Discord, informando título, tamanho e status de indexação RAG. Use sempre que o usuário perguntar quais PDFs ele possui salvos ou quais livros estão disponíveis.",
    parameters={
        "type": "object",
        "properties": {},
        "required": [],
    },
)
def tool_listar_meus_pdfs() -> str:
    """Retorna a lista de PDFs disponíveis para o usuário atual."""
    usuario = get_current_user()
    arquivos = listar_status_pdfs_usuario(usuario)

    if not arquivos:
        return f"Não há nenhum arquivo PDF salvo na pasta do usuário '{usuario}' no momento."

    linhas = [f"Arquivos PDF disponíveis para o usuário '{usuario}' ({len(arquivos)} arquivo(s)):"]
    for idx, arq in enumerate(arquivos, start=1):
        status_rag = "🟢 RAG Ativo" if arq.get("is_indexed") else "⚪ Não Indexado"
        linhas.append(
            f"{idx}. {arq['nome']} — {arq['title']} ({arq['total_pages']} págs, {arq['tamanho_formatado']}) [{status_rag}]"
        )

    return "\n".join(linhas)


@register_tool(
    name="disponibilizar_pdf_usuario",
    description="Localiza um arquivo PDF na pasta do usuário e agenda o envio do arquivo físico no chat do Discord. Use sempre que o usuário pedir para enviar, disponibilizar, mandar, devolver, baixar ou entregar um PDF específico.",
    parameters={
        "type": "object",
        "properties": {
            "nome_arquivo": {
                "type": "string",
                "description": "Nome completo ou parte do nome do arquivo PDF desejado (ex: 'relatorio.pdf', 'contrato', 'rag-versao-final').",
            }
        },
        "required": ["nome_arquivo"],
    },
)
def tool_disponibilizar_pdf(nome_arquivo: str) -> str:
    """Localiza o PDF e registra para envio como anexo no Discord."""
    usuario = get_current_user()
    caminho = localizar_pdf_usuario(usuario, nome_arquivo)

    if not caminho:
        arquivos = listar_pdfs_usuario(usuario)
        disponiveis = [a["nome"] for a in arquivos]
        return (
            f"Arquivo '{nome_arquivo}' não foi encontrado na pasta do usuário '{usuario}'. "
            f"Arquivos disponíveis no momento: {disponiveis}"
        )

    add_pending_file(caminho)
    return (
        f"Sucesso: O arquivo '{caminho.name}' foi localizado com sucesso na pasta do usuário "
        f"e será enviado automaticamente como anexo no chat do Discord."
    )


@register_tool(
    name="consultar_metadados_pdf",
    description="Consulta a ficha catalográfica e informações detalhadas de um livro/PDF (autor, título, total de páginas, tamanho e breve sinopse). Use quando o usuário perguntar quem escreveu o livro, quantas páginas tem ou pedir um resumo geral preliminar da obra.",
    parameters={
        "type": "object",
        "properties": {
            "arquivo": {
                "type": "string",
                "description": "Nome ou parte do nome do arquivo PDF (ex: 'rag-versao-final', 'clean-code').",
            }
        },
        "required": ["arquivo"],
    },
)
async def tool_consultar_metadados_pdf(arquivo: str) -> str:
    """Consulta os metadados catalográficos do PDF."""
    usuario = get_current_user()
    res = await obter_metadados_documento(usuario, arquivo)
    if not res.get("sucesso"):
        return res.get("mensagem", "Erro ao obter metadados do documento.")
    return res["resposta_formatada"]


@register_tool(
    name="obter_sumario_pdf",
    description="Retorna o sumário com a lista de capítulos, seções e páginas correspondentes de um livro/PDF. Use quando o usuário quiser saber como o texto está dividido, quais são os capítulos ou a estrutura do documento.",
    parameters={
        "type": "object",
        "properties": {
            "arquivo": {
                "type": "string",
                "description": "Nome ou parte do nome do arquivo PDF.",
            }
        },
        "required": ["arquivo"],
    },
)
async def tool_obter_sumario_pdf(arquivo: str) -> str:
    """Retorna o sumário e a estrutura de capítulos do PDF."""
    usuario = get_current_user()
    res = await obter_sumario_documento(usuario, arquivo)
    if not res.get("sucesso"):
        return res.get("mensagem", "Erro ao obter sumário do documento.")
    return res["resposta_formatada"]


@register_tool(
    name="resumir_capitulo_pdf",
    description="Gera uma síntese analítica dos pontos centrais, teses e conceitos de um capítulo ou seção específica de um livro/PDF. Use quando o usuário pedir o resumo de um capítulo (ex: 'resuma o capítulo 3', 'do que fala a seção de CRAG?').",
    parameters={
        "type": "object",
        "properties": {
            "arquivo": {
                "type": "string",
                "description": "Nome ou parte do nome do arquivo PDF.",
            },
            "capitulo": {
                "type": "string",
                "description": "Número do capítulo (ex: '1', '3') ou título/palavra-chave do capítulo.",
            },
        },
        "required": ["arquivo", "capitulo"],
    },
)
async def tool_resumir_capitulo_pdf(arquivo: str, capitulo: str) -> str:
    """Gera resumo de um capítulo específico do PDF."""
    usuario = get_current_user()
    res = await resumir_capitulo_documento(usuario, arquivo, capitulo, gerar_resposta_llm=False)
    if not res.get("sucesso"):
        return res.get("mensagem", "Erro ao resumir capítulo.")
    return res["resposta_formatada"]


@register_tool(
    name="indexar_pdf_rag",
    description="Fatia o texto completo do livro/PDF, gera embeddings vetoriais e armazena na base de conhecimento (ChromaDB) para permitir perguntas livres e conversação inteligente sobre o conteúdo da obra. Use quando o usuário pedir para indexar, preparar ou incluir o livro no RAG.",
    parameters={
        "type": "object",
        "properties": {
            "arquivo": {
                "type": "string",
                "description": "Nome ou parte do nome do arquivo PDF.",
            }
        },
        "required": ["arquivo"],
    },
)
async def tool_indexar_pdf_rag(arquivo: str) -> str:
    """Indexa o PDF no ChromaDB para busca semântica."""
    usuario = get_current_user()
    res = await indexar_documento_rag(usuario, arquivo)
    if not res.get("sucesso"):
        return res.get("mensagem", "Erro ao indexar o documento.")
    return res.get("resposta_formatada") or res.get("mensagem", "Documento indexado.")


@register_tool(
    name="consultar_conteudo_pdf_rag",
    description="Realiza busca semântica (RAG) nos capítulos e trechos de um livro/PDF salvo e retorna os trechos mais relevantes citando as páginas exatas. Use quando o usuário fizer perguntas conceituais ou factuais sobre o conteúdo de um livro/PDF.",
    parameters={
        "type": "object",
        "properties": {
            "arquivo": {
                "type": "string",
                "description": "Nome ou parte do nome do arquivo PDF a ser pesquisado (ex: 'rag-versao-final').",
            },
            "pergunta": {
                "type": "string",
                "description": "Pergunta ou dúvida a ser consultada no conteúdo da obra.",
            },
        },
        "required": ["arquivo", "pergunta"],
    },
)
async def tool_consultar_conteudo_pdf_rag(arquivo: str, pergunta: str) -> str:
    """Realiza consulta semântica com citação de páginas no conteúdo do PDF."""
    usuario = get_current_user()
    res = await consultar_documento_rag(usuario, arquivo, pergunta, gerar_resposta_llm=False)
    if not res.get("sucesso"):
        return res.get("mensagem", "Erro ao consultar o conteúdo do PDF.")
    return res["resposta_formatada"]
