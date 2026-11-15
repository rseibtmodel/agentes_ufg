"""
Comandos da Base de Conhecimento, Documentos, RAG de Livros e Knowledge Hub por Canal (IDEA-25).

Contempla:
1. Catálogo e RAG de PDFs/Livros (!pdfs, !enviar, !pdf)
2. Memória Vetorial Pessoal no ChromaDB (!memoria, !limpar_memoria)
3. Tópicos de Conhecimento e Notas RAG isoladas por canal (!topico, !nota, !notas)
"""

import logging
from typing import Optional

import discord

from commands.registry import CommandContext, register_command
from config import COMMAND_PREFIX, DISCORD_UI_COMPONENTS_ENABLED
from database import obter_modo_resposta
from tts_manager import sintetizar_fala_edge
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
from topic_manager import (
    adicionar_nota,
    buscar_notas_rag,
    definir_modo_livre,
    desvincular_topico,
    limpar_notas_topico,
    listar_notas,
    obter_nota,
    obter_topico_canal,
    remover_nota,
    vincular_topico,
)
from ui_components import PDFChapterSelectView
from vector_db import buscar_memorias_relevantes, contar_memorias, limpar_memoria_vetorial
from radar_manager import radar_manager

logger = logging.getLogger(__name__)


@register_command(
    name="pdfs",
    description="Lista todos os arquivos PDF salvos na sua pasta pessoal com status de catálogo e RAG.",
    usage=f"{COMMAND_PREFIX}pdfs",
    category="PDFs & Documentos",
    example=f"{COMMAND_PREFIX}pdfs",
    aliases=["listar_pdfs", "meus_pdfs"],
)
async def cmd_pdfs(ctx: CommandContext) -> None:
    """Lista os PDFs disponíveis na pasta do usuário."""
    status_lista = listar_status_pdfs_usuario(ctx.author)
    if not status_lista:
        await ctx.reply(
            f"📂 Sua pasta de PDFs (`pdf/{ctx.author.name}/`) está vazia no momento.\n"
            "Envie um arquivo PDF aqui no chat para que eu possa guardá-lo e catalogá-lo para você!"
        )
        return

    linhas = [
        f"📚 **Seus Arquivos PDF Disponíveis ({len(status_lista)}):**",
        f"*(Local: `pdf/{ctx.author.name}/`)*\n",
    ]
    for idx, arq in enumerate(status_lista, start=1):
        tag_rag = "🟢 RAG Ativo" if arq["is_indexed"] else "⚪ Não Indexado"
        pags_str = f"{arq['total_pages']} págs" if arq["total_pages"] > 0 else "Páginas n/c"
        linhas.append(f"• `{arq['nome']}` — **{arq['title']}** ({pags_str}, {arq['tamanho_formatado']}) [{tag_rag}]")

    linhas.append(
        f"\n💡 *Dica:* Use `{COMMAND_PREFIX}pdf info <nome>` para ver detalhes, `{COMMAND_PREFIX}pdf capitulo <nome> <n>` para resumos ou `{COMMAND_PREFIX}enviar <nome>` para baixar o arquivo!"
    )
    await ctx.reply("\n".join(linhas))


@register_command(
    name="enviar",
    description="Envia de volta um arquivo PDF da sua pasta como anexo.",
    usage=f"{COMMAND_PREFIX}enviar <nome_do_arquivo>",
    category="PDFs & Documentos",
    example=f"{COMMAND_PREFIX}enviar relatorio",
    aliases=["baixar", "disponibilizar", "obter", "download"],
)
async def cmd_enviar(ctx: CommandContext) -> None:
    """Envia o PDF solicitado como anexo no Discord."""
    if not ctx.args:
        await ctx.reply(f"❓ Por favor, informe o nome do arquivo. Exemplo: `{COMMAND_PREFIX}enviar relatorio`")
        return

    termo = ctx.arg_str
    caminho = localizar_pdf_usuario(ctx.author, termo)

    if not caminho or not caminho.exists():
        arquivos = listar_pdfs_usuario(ctx.author)
        nomes = [f"`{a['nome']}`" for a in arquivos]
        disponiveis_str = ", ".join(nomes) if nomes else "Nenhum"
        await ctx.reply(
            f"❌ Arquivo `{termo}` não encontrado na sua pasta.\n"
            f"📄 PDFs disponíveis: {disponiveis_str}\n"
            f"Use `{COMMAND_PREFIX}pdfs` para ver a lista completa."
        )
        return

    arquivo_discord = discord.File(str(caminho), filename=caminho.name)
    await ctx.channel.send(
        content=f"📥 **Aqui está o seu PDF solicitado:** `{caminho.name}`",
        file=arquivo_discord,
    )


@register_command(
    name="pdf",
    description="Navegação, metadados, sumários, resumos de capítulos e RAG vetorial de livros e PDFs.",
    usage=f"{COMMAND_PREFIX}pdf [status|info|sumario|capitulo|indexar|perguntar] [arquivo] [argumentos...]",
    category="PDFs & Documentos",
    example=f"{COMMAND_PREFIX}pdf info relatorio",
    aliases=["livro", "livros", "ebook", "documento"],
)
async def cmd_pdf(ctx: CommandContext) -> None:
    """Comando central de leitura inteligente e RAG de livros e PDFs."""
    if not ctx.args or ctx.args[0].lower() in ("status", "listar", "list", "lista"):
        status_lista = listar_status_pdfs_usuario(ctx.author)
        if not status_lista:
            await ctx.reply(
                f"📂 Sua pasta de PDFs (`pdf/{ctx.author.name}/`) está vazia.\n"
                "Envie um arquivo PDF aqui no chat para que eu possa catalogá-lo para você!"
            )
            return

        linhas = [
            f"📚 **Seus Livros e Documentos PDF ({len(status_lista)}):**\n"
        ]
        for idx, arq in enumerate(status_lista, start=1):
            tag_rag = "🟢 RAG Ativo" if arq["is_indexed"] else "⚪ Não Indexado"
            pags_str = f"{arq['total_pages']} págs" if arq["total_pages"] > 0 else "Páginas n/c"
            linhas.append(f"{idx}. `{arq['nome']}` — **{arq['title']}** ({pags_str}, {arq['tamanho_formatado']}) [{tag_rag}]")

        linhas.append(
            f"\n💡 *Ações:* `{COMMAND_PREFIX}pdf info <arquivo>` • `{COMMAND_PREFIX}pdf sumario <arquivo>` • `{COMMAND_PREFIX}pdf capitulo <arquivo> <n>` • `{COMMAND_PREFIX}pdf indexar <arquivo>` • `{COMMAND_PREFIX}pdf perguntar <arquivo> <dúvida>`"
        )
        await ctx.reply("\n".join(linhas))
        return

    sub = ctx.args[0].lower()

    # Subcomando: info / metadados
    if sub in ("info", "metadados", "detalhes", "sobre"):
        if len(ctx.args) < 2:
            await ctx.reply(f"❓ Uso: `{COMMAND_PREFIX}pdf info <nome_do_arquivo>`. Ex: `{COMMAND_PREFIX}pdf info rag-versao-final`")
            return
        arquivo = ctx.args[1]
        async with ctx.channel.typing():
            res = await obter_metadados_documento(ctx.author, arquivo)
            if res.get("sucesso"):
                await ctx.reply(res["resposta_formatada"])
            else:
                await ctx.reply(f"⚠️ {res.get('mensagem')}")
        return

    # Subcomando: sumario / capitulos / indice
    if sub in ("sumario", "capitulos", "indice", "toc", "secoes"):
        if len(ctx.args) < 2:
            await ctx.reply(f"❓ Uso: `{COMMAND_PREFIX}pdf sumario <nome_do_arquivo>`. Ex: `{COMMAND_PREFIX}pdf sumario rag-versao-final`")
            return
        arquivo = ctx.args[1]
        async with ctx.channel.typing():
            res = await obter_sumario_documento(ctx.author, arquivo)
            if res.get("sucesso"):
                view = None
                if DISCORD_UI_COMPONENTS_ENABLED and res.get("capitulos"):
                    view = PDFChapterSelectView(author=ctx.author, doc_name=arquivo, capitulos=res.get("capitulos", []))
                await ctx.reply(res["resposta_formatada"], view=view)
            else:
                await ctx.reply(f"⚠️ {res.get('mensagem')}")
        return

    # Subcomando: capitulo / resumir
    if sub in ("capitulo", "resumo", "resumir", "secao"):
        if len(ctx.args) < 3:
            await ctx.reply(
                f"❓ Uso: `{COMMAND_PREFIX}pdf capitulo <nome_do_arquivo> <número ou título>`.\n"
                f"Exemplo: `{COMMAND_PREFIX}pdf capitulo rag-versao-final 1` ou `{COMMAND_PREFIX}pdf capitulo rag-versao-final CRAG`"
            )
            return
        arquivo = ctx.args[1]
        cap_id = " ".join(ctx.args[2:])
        async with ctx.channel.typing():
            res = await resumir_capitulo_documento(ctx.author, arquivo, cap_id)
            if not res.get("sucesso"):
                await ctx.reply(f"⚠️ {res.get('mensagem')}")
                return

            texto_resposta = res["resposta_formatada"]
            modo_resp = obter_modo_resposta(str(ctx.author.id))

            # Entrega multimodal (Texto, Áudio Francisca ou Ambos)
            if modo_resp in ("audio", "ambos"):
                texto_narracao = f"Aqui está o resumo do capítulo {res['capitulo']['title']}. {res['resumo']}"
                caminho_mp3 = await sintetizar_fala_edge(texto_narracao)
                try:
                    if modo_resp == "ambos":
                        await ctx.reply(texto_resposta)
                    if caminho_mp3 and caminho_mp3.exists():
                        arq_discord = discord.File(str(caminho_mp3), filename=f"resumo_capitulo_{res['capitulo']['chapter_index']}.mp3")
                        await ctx.channel.send(content="🎙️ *(Áudio narrado pela Francisca)*", file=arq_discord)
                    elif modo_resp == "audio":
                        await ctx.reply(texto_resposta)
                finally:
                    if caminho_mp3 and caminho_mp3.exists():
                        caminho_mp3.unlink(missing_ok=True)
            else:
                await ctx.reply(texto_resposta)
        return

    # Subcomando: indexar (RAG)
    if sub in ("indexar", "rag", "vetorizar", "processar"):
        if len(ctx.args) < 2:
            await ctx.reply(f"❓ Uso: `{COMMAND_PREFIX}pdf indexar <nome_do_arquivo>`. Ex: `{COMMAND_PREFIX}pdf indexar rag-versao-final`")
            return
        arquivo = ctx.args[1]
        msg_aviso_res = await ctx.reply("⏳ *Iniciando leitura, fatiamento e vetorização da obra no ChromaDB... Aguarde alguns instantes.*")
        msg_aviso = msg_aviso_res[0] if isinstance(msg_aviso_res, list) and msg_aviso_res else msg_aviso_res
        res = await indexar_documento_rag(ctx.author, arquivo)
        texto_final = res.get("resposta_formatada") or res.get("mensagem")
        if msg_aviso and hasattr(msg_aviso, "edit"):
            await msg_aviso.edit(content=texto_final)
        else:
            await ctx.reply(texto_final)
        return

    # Subcomando: perguntar / consultar
    if sub in ("perguntar", "busca", "consultar", "duvida", "qna"):
        if len(ctx.args) < 3:
            await ctx.reply(
                f"❓ Uso: `{COMMAND_PREFIX}pdf perguntar <nome_do_arquivo> <sua pergunta>`.\n"
                f"Exemplo: `{COMMAND_PREFIX}pdf perguntar rag-versao-final O que é e quando usar GraphRAG?`"
            )
            return
        arquivo = ctx.args[1]
        pergunta = " ".join(ctx.args[2:])
        async with ctx.channel.typing():
            res = await consultar_documento_rag(ctx.author, arquivo, pergunta)
            if not res.get("sucesso"):
                await ctx.reply(res.get("mensagem", "Erro ao processar consulta."))
                return

            texto_resposta = res["resposta_formatada"]
            modo_resp = obter_modo_resposta(str(ctx.author.id))

            if modo_resp in ("audio", "ambos"):
                texto_narracao = res["resposta"]
                caminho_mp3 = await sintetizar_fala_edge(texto_narracao)
                try:
                    if modo_resp == "ambos":
                        await ctx.reply(texto_resposta)
                    if caminho_mp3 and caminho_mp3.exists():
                        arq_discord = discord.File(str(caminho_mp3), filename="resposta_rag_livro.mp3")
                        await ctx.channel.send(content="🎙️ *(Áudio narrado pela Francisca)*", file=arq_discord)
                    elif modo_resp == "audio":
                        await ctx.reply(texto_resposta)
                finally:
                    if caminho_mp3 and caminho_mp3.exists():
                        caminho_mp3.unlink(missing_ok=True)
            else:
                await ctx.reply(texto_resposta)
        return

    # Se o usuário digitou apenas o nome de um arquivo (ex: !pdf rag-versao-final)
    res = await obter_metadados_documento(ctx.author, sub)
    if res.get("sucesso"):
        await ctx.reply(res["resposta_formatada"])
    else:
        await ctx.reply(
            f"❓ Subcomando ou arquivo `{sub}` não reconhecido.\n"
            f"Digite `{COMMAND_PREFIX}pdf` para ver seus arquivos ou `{COMMAND_PREFIX}ajuda pdf` para ver os comandos."
        )


@register_command(
    name="memoria",
    description="Realiza uma busca semântica na sua memória vetorial de longo prazo (ChromaDB).",
    usage=f"{COMMAND_PREFIX}memoria <termo_ou_pergunta>",
    category="Memória de Longo Prazo",
    example=f"{COMMAND_PREFIX}memoria Python",
    aliases=["lembrar", "busca_vetorial", "rag"],
)
async def cmd_memoria(ctx: CommandContext) -> None:
    """Consulta memórias no ChromaDB."""
    if not ctx.args:
        total = contar_memorias(ctx.author.name)
        await ctx.reply(
            f"🧠 **Sua Coleção Vetorial no ChromaDB:** `{ctx.author.name}_memory`\n"
            f"• Total de fragmentos armazenados: `{total}`\n"
            f"Para buscar, informe o termo desejado. Exemplo: `{COMMAND_PREFIX}memoria Python`"
        )
        return

    termo = ctx.arg_str
    memorias = await buscar_memorias_relevantes(ctx.author.name, termo, top_k=3)

    if not memorias:
        await ctx.reply(f"🔍 Nenhuma memória encontrada no ChromaDB relacionada a `{termo}`.")
        return

    linhas = [f"🧠 **Memórias Semânticas Encontradas para '{termo}':**\n"]
    for idx, mem in enumerate(memorias, start=1):
        papel = "👤 Usuário" if mem["role"] == "user" else "🤖 Assistente"
        trecho = mem["conteudo"][:150].replace("\n", " ")
        if len(mem["conteudo"]) > 150:
            trecho += "..."
        linhas.append(f"{idx}. {papel} *(distância: {mem['distancia']})*:\n> {trecho}")

    await ctx.reply("\n".join(linhas))


@register_command(
    name="limpar_memoria",
    description="Limpa a sua memória vetorial no ChromaDB ({user}_memory).",
    usage=f"{COMMAND_PREFIX}limpar_memoria",
    category="Memória de Longo Prazo",
    example=f"{COMMAND_PREFIX}limpar_memoria",
    aliases=["reset_memoria", "clear_memory"],
)
async def cmd_limpar_memoria(ctx: CommandContext) -> None:
    """Exclui a coleção vetorial do usuário."""
    sucesso = limpar_memoria_vetorial(ctx.author.name)
    if sucesso:
        await ctx.reply(f"🧹 Coleção vetorial `{ctx.author.name}_memory` no ChromaDB resetada com sucesso!")
    else:
        await ctx.reply("⚠️ Ocorreu uma falha ao tentar resetar a coleção vetorial no ChromaDB.")


@register_command(
    name="topico",
    description="Vincula, inspeciona e gerencia o tópico temático do canal atual (IDEA-25).",
    usage=f"{COMMAND_PREFIX}topico [vincular|status|desvincular|modo_livre]",
    category="Knowledge Hub & Notas",
    example=f"{COMMAND_PREFIX}topico status",
    aliases=["tema", "hub"],
)
async def cmd_topico(ctx: CommandContext) -> None:
    """Gerencia a associação do canal a um tópico de conhecimento."""
    channel_id = str(ctx.channel.id)

    if not ctx.args:
        topico = obter_topico_canal(channel_id)
        if topico:
            total_notas = len(listar_notas(channel_id, limite=100))
            await ctx.reply(
                f"📌 **Tópico Vinculado a este Canal:**\n"
                f"• **Nome:** **{topico['topic_name']}** (`{topico['topic_slug']}`)\n"
                f"• **Descrição:** {topico['description'] or 'Nenhuma descrição fornecida.'}\n"
                f"• **Captura Livre:** {'🟢 Ativada' if topico['auto_capture_mode'] else '⚪ Desativada (!nota add ou 📝)'}\n"
                f"• **Total de Notas Indexadas:** `{total_notas}`\n\n"
                f"Para buscar notas: `{COMMAND_PREFIX}nota buscar <pergunta>` | Para adicionar: `{COMMAND_PREFIX}nota add <texto>`"
            )
        else:
            await ctx.reply(
                f"ℹ️ Este canal não está vinculado a nenhum tópico temático.\n"
                f"Para vinculá-lo, use: `{COMMAND_PREFIX}topico vincular <slug> [nome/descrição]`\n"
                f"Exemplo: `{COMMAND_PREFIX}topico vincular cbs \"Reforma Tributária e CBS\"`"
            )
        return

    sub = ctx.args[0].lower()

    if sub in ("vincular", "associar", "set", "criar"):
        if len(ctx.args) < 2:
            await ctx.reply(f"❓ Informe o identificador do tópico. Exemplo: `{COMMAND_PREFIX}topico vincular cbs \"Reforma Tributária\"`")
            return
        slug = ctx.args[1]
        nome = " ".join(ctx.args[2:]) if len(ctx.args) > 2 else slug
        res = vincular_topico(channel_id=channel_id, topic_slug=slug, topic_name=nome)
        await ctx.reply(res["mensagem"])
        return

    if sub in ("status", "info"):
        topico = obter_topico_canal(channel_id)
        if not topico:
            await ctx.reply(f"ℹ️ Este canal não possui tópico vinculado. Use `{COMMAND_PREFIX}topico vincular <slug>`.")
            return
        total_notas = len(listar_notas(channel_id, limite=100))
        await ctx.reply(
            f"📌 **Status do Tópico Temático:**\n"
            f"• **Tópico:** **{topico['topic_name']}** (`{topico['topic_slug']}`)\n"
            f"• **Descrição:** {topico['description'] or '-'}\n"
            f"• **Modo de Captura Livre:** {'🟢 Ligado' if topico['auto_capture_mode'] else '⚪ Desligado'}\n"
            f"• **Notas Indexadas no ChromaDB:** `{total_notas}`"
        )
        return

    if sub in ("desvincular", "remover", "unlink"):
        res = desvincular_topico(channel_id)
        await ctx.reply(res["mensagem"])
        return

    if sub in ("modo_livre", "livre", "autocapture"):
        if len(ctx.args) < 2:
            topico = obter_topico_canal(channel_id)
            atual = "Ligado" if (topico and topico["auto_capture_mode"]) else "Desligado"
            await ctx.reply(f"ℹ️ Modo de captura livre está atualmente **{atual}**. Use `{COMMAND_PREFIX}topico modo_livre [on|off]`.")
            return
        arg_modo = ctx.args[1].lower()
        ativar = arg_modo in ("on", "ligar", "1", "sim", "true", "ativar")
        res = definir_modo_livre(channel_id, ativo=ativar)
        await ctx.reply(res["mensagem"])
        return

    await ctx.reply(f"❓ Subcomando desconhecido. Use: `{COMMAND_PREFIX}topico [vincular|status|desvincular|modo_livre]`")


@register_command(
    name="nota",
    description="Adiciona, busca, inspeciona ou remove notas no tópico temático do canal (IDEA-25).",
    usage=f"{COMMAND_PREFIX}nota [add|buscar|ver|remover|limpar] [conteúdo...]",
    category="Knowledge Hub & Notas",
    example=f"{COMMAND_PREFIX}nota add Regra de apuração CBS #cbs",
    aliases=["notas_cmd", "anotacao", "ideia"],
)
async def cmd_nota(ctx: CommandContext) -> None:
    """Gerencia notas no banco temático do canal atual."""
    channel_id = str(ctx.channel.id)
    user_id = str(ctx.author.id)

    if not ctx.args:
        await ctx.reply(
            f"ℹ️ **Uso do comando !nota:**\n"
            f"• `{COMMAND_PREFIX}nota add <texto> [#tags]` — Registra nova nota no tópico\n"
            f"• `{COMMAND_PREFIX}nota buscar <pergunta>` — Busca semântica RAG isolada neste canal\n"
            f"• `{COMMAND_PREFIX}nota ver <id>` — Exibe nota completa pelo ID\n"
            f"• `{COMMAND_PREFIX}nota remover <id>` — Exclui nota do SQLite e ChromaDB\n"
            f"• `{COMMAND_PREFIX}notas` — Lista notas recentes deste canal"
        )
        return

    sub = ctx.args[0].lower()

    # Se o primeiro argumento não for um subcomando conhecido, trata tudo como adição direta de nota
    if sub not in ("add", "criar", "salvar", "buscar", "search", "ver", "remover", "del", "rm", "limpar"):
        texto = ctx.arg_str
        res = await adicionar_nota(channel_id=channel_id, user_id=user_id, content=texto)
        await ctx.reply(res["mensagem"])
        return

    if sub in ("add", "criar", "salvar"):
        if len(ctx.args) < 2:
            await ctx.reply(f"❓ Digite o conteúdo da nota. Exemplo: `{COMMAND_PREFIX}nota add Regra de apuração CBS #cbs #reforma`")
            return
        texto = " ".join(ctx.args[1:])
        res = await adicionar_nota(channel_id=channel_id, user_id=user_id, content=texto)
        await ctx.reply(res["mensagem"])
        return

    if sub in ("buscar", "search", "rag"):
        if len(ctx.args) < 2:
            await ctx.reply(f"❓ Digite o que deseja pesquisar. Exemplo: `{COMMAND_PREFIX}nota buscar alíquotas do CBS`")
            return
        consulta = " ".join(ctx.args[1:])
        notas = await buscar_notas_rag(channel_id, consulta, top_k=4)
        if not notas:
            await ctx.reply(f"🔍 Nenhuma nota relevante encontrada neste canal para: `{consulta}`.")
            return

        linhas = [f"🔍 **Resultados RAG no Tópico do Canal ({len(notas)} nota(s)):**\n"]
        for idx, n in enumerate(notas, start=1):
            tags_txt = f" `[{n.get('tags')}]`" if n.get("tags") else ""
            linhas.append(f"**{idx}.** (ID: `{n.get('note_id')}`{tags_txt}):\n{n.get('conteudo')}\n*(distância semântica: {n.get('distancia')})*\n")
        await ctx.reply("\n".join(linhas))
        return

    if sub in ("ver", "info"):
        if len(ctx.args) < 2:
            await ctx.reply(f"❓ Informe o ID da nota. Exemplo: `{COMMAND_PREFIX}nota ver 1a2b3c4d`")
            return
        nid = ctx.args[1]
        nota = obter_nota(nid)
        if not nota:
            await ctx.reply(f"❌ Nota `{nid}` não encontrada.")
            return
        tags_str = f" `{' '.join(nota['tags'])}`" if nota["tags"] else "Nenhuma"
        await ctx.reply(
            f"📝 **Nota:** `{nota['id']}` (Tópico: `{nota['topic_slug']}`)\n"
            f"🏷️ **Tags:** {tags_str} | **Criada em:** `{nota['created_at']}`\n\n"
            f"```text\n{nota['content']}\n```"
        )
        return

    if sub in ("remover", "del", "rm"):
        if len(ctx.args) < 2:
            await ctx.reply(f"❓ Informe o ID da nota a remover. Exemplo: `{COMMAND_PREFIX}nota remover 1a2b3c4d`")
            return
        nid = ctx.args[1]
        res = remover_nota(nid, channel_id=channel_id)
        await ctx.reply(res["mensagem"])
        return

    if sub in ("limpar", "purge"):
        if len(ctx.args) < 2 or ctx.args[1].lower() != "confirmar":
            await ctx.reply(f"⚠️ Para apagar TODAS as notas deste canal temático, digite: `{COMMAND_PREFIX}nota limpar confirmar`")
            return
        res = limpar_notas_topico(channel_id)
        await ctx.reply(res["mensagem"])
        return


@register_command(
    name="notas",
    description="Lista as notas salvas no tópico do canal atual com filtro por tag opcional (IDEA-25).",
    usage=f"{COMMAND_PREFIX}notas [#tag] [limite]",
    category="Knowledge Hub & Notas",
    example=f"{COMMAND_PREFIX}notas #cbs",
    aliases=["listanotas", "minhasnotas"],
)
async def cmd_notas(ctx: CommandContext) -> None:
    """Lista as notas salvas no canal temático."""
    channel_id = str(ctx.channel.id)

    tag = None
    limite = 10
    for a in ctx.args:
        if a.startswith("#"):
            tag = a
        elif a.isdigit():
            limite = int(a)

    notas = listar_notas(channel_id, tag=tag, limite=limite)
    topico = obter_topico_canal(channel_id)
    nome_topico = topico["topic_name"] if topico else "Notas Gerais do Canal"

    if not notas:
        filtro_txt = f" com a tag `{tag}`" if tag else ""
        await ctx.reply(f"ℹ️ Nenhuma nota registrada no tópico **{nome_topico}**{filtro_txt}.\nAdicione com `{COMMAND_PREFIX}nota add <conteúdo>` ou reagindo com 📝.")
        return

    linhas = [f"📚 **NOTAS REGISTRADAS NO TÓPICO: {nome_topico}** ({len(notas)} nota(s)):\n"]
    for idx, n in enumerate(notas, start=1):
        tags_str = f" `{' '.join(n['tags'])}`" if n["tags"] else ""
        preview = n["content"][:180] + ("..." if len(n["content"]) > 180 else "")
        linhas.append(f"• **`{n['id']}`**{tags_str}: {preview}")

    await ctx.reply("\n".join(linhas))


@register_command(
    name="radar",
    description="Radar autônomo de RSS, ArXiv e GitHub com curadoria por IA (IDEA-29).",
    usage=f"{COMMAND_PREFIX}radar [assinar|listar|remover|agora|boletim|ajuda]",
    category="Radar & Conhecimento",
    example=f"{COMMAND_PREFIX}radar assinar arxiv:cs.AI --tempo-real",
    aliases=["feed", "rss"],
)
async def cmd_radar(ctx: CommandContext) -> None:
    """Gerencia assinaturas e execuções do Radar de Feeds Técnicos."""
    sub = ctx.args[0].lower() if ctx.args else "ajuda"

    if not ctx.args or sub in ("ajuda", "help", "--help", "-h"):
        ajuda = [
            "📡 **RADAR AUTÔNOMO DE RSS, ARXIV & GITHUB (IDEA-29)**",
            "Monitora releases de repositórios, papers científicos e feeds com curadoria por IA.\n",
            "📋 **Comandos Principais:**",
            f"• `{COMMAND_PREFIX}radar assinar <fonte> [--tempo-real] [--boletim HH:MM] [--filtro 'regex']`",
            f"• `{COMMAND_PREFIX}radar listar` — Lista suas assinaturas ativas e canais de entrega.",
            f"• `{COMMAND_PREFIX}radar remover <id>` — Cancela o monitoramento de uma assinatura.",
            f"• `{COMMAND_PREFIX}radar agora` — Força varredura imediata de todas as fontes agendadas.",
            f"• `{COMMAND_PREFIX}radar boletim` — Despacha na hora os itens acumulados para este canal.\n",
            "🔬 **Como Assinar o ArXiv (`arxiv:<categoria>`):**",
            "• `arxiv:cs.AI` — Inteligência Artificial Geral",
            "• `arxiv:cs.CL` — NLP, Processamento de Linguagem & LLMs",
            "• `arxiv:cs.LG` — Aprendizado de Máquina (Machine Learning)",
            "• `arxiv:cs.CV` — Visão Computacional",
            "• `arxiv:cs.SE` — Engenharia de Software\n",
            "🐙 **Outras Fontes Suportadas:**",
            "• `dono/repo` — Releases do GitHub sem token (ex: `vllm-project/vllm`)",
            "• URL completa de qualquer feed RSS ou Atom XML\n",
            "⚙️ **Modos de Entrega & Filtros:**",
            "• `--tempo-real` — Alerta imediato a cada novo paper/release detectado.",
            "• `--boletim HH:MM` — Acumula os papers e envia um boletim consolidado no horário (padrão: 18:00).",
            "• `--filtro 'regex'` — Filtro prévio por palavras-chave (custo zero) antes de acionar a IA.\n",
            "💡 **Exemplos Práticos:**",
            f"  `{COMMAND_PREFIX}radar assinar arxiv:cs.AI --tempo-real`",
            f"  `{COMMAND_PREFIX}radar assinar arxiv:cs.CL --boletim 09:00 --filtro 'reasoning|agents'`",
            f"  `{COMMAND_PREFIX}radar assinar vllm-project/vllm --tempo-real`",
            f"  `{COMMAND_PREFIX}radar assinar https://huggingface.co/blog/feed.xml`",
        ]
        await ctx.reply("\n".join(ajuda))
        return

    if sub in ("listar", "list"):
        user_id = str(ctx.author.id)
        subs = radar_manager.listar_assinaturas(user_id=user_id)
        if not subs:
            await ctx.reply("ℹ️ Você não possui nenhuma assinatura ativa no Radar.\nAssine com `!radar assinar <fonte>`.")
            return

        linhas_subs = [f"📡 **SUAS ASSINATURAS NO RADAR ({len(subs)}):**\n"]
        for s in subs:
            modo_desc = "⚡ Tempo Real" if s["mode"] == "REALTIME" else f"📰 Boletim ({s['digest_time']})"
            filtro_desc = f" | Filtro: `{s['keywords_regex']}`" if s["keywords_regex"] else ""
            linhas_subs.append(
                f"• **`ID {s['id']}`** `[{s['source_type']}]` <{s['source_url']}>\n"
                f"  Modo: **{modo_desc}** | Canal: <#{s['channel_id']}>{filtro_desc}"
            )
        await ctx.reply("\n".join(linhas_subs))
        return

    if sub in ("remover", "del", "delete", "cancelar"):
        if len(ctx.args) < 2 or not ctx.args[1].isdigit():
            await ctx.reply(f"⚠️ Informe o ID da assinatura a remover. Ex: `{COMMAND_PREFIX}radar remover 1`")
            return
        sub_id = int(ctx.args[1])
        removido = radar_manager.remover_assinatura(sub_id)
        if removido:
            await ctx.reply(f"✅ Assinatura `ID {sub_id}` removida com sucesso do Radar.")
        else:
            await ctx.reply(f"⚠️ Assinatura `ID {sub_id}` não foi encontrada.")
        return

    if sub in ("agora", "run", "scan"):
        user_id = str(ctx.author.id)
        await ctx.reply("🔄 Executando varredura imediata e forçada dos seus feeds do Radar...")
        total = await radar_manager.processar_ciclo_agendado(forcar=True, user_id=user_id)
        await ctx.reply(f"✅ Ciclo concluído. `{total}` assinatura(s) verificada(s).")
        return

    if sub in ("boletim", "digest"):
        await ctx.reply(f"📰 Consolidando e despachando boletim pendente para o canal <#{ctx.channel.id}>...")
        enviou = await radar_manager.enviar_boletim_canal(ctx.channel.id)
        if enviou:
            await ctx.reply("✅ Boletim despachado com sucesso!")
        else:
            await ctx.reply("ℹ️ Não há novidades acumuladas no buffer para este canal no momento.")
        return

    if sub in ("assinar", "add", "subscribe"):
        if len(ctx.args) < 2:
            await ctx.reply(
                f"⚠️ Informe a fonte a monitorar. Exemplos:\n"
                f"• `{COMMAND_PREFIX}radar assinar vllm-project/vllm --tempo-real`\n"
                f"• `{COMMAND_PREFIX}radar assinar arxiv:cs.CL --boletim 08:30`"
            )
            return

        alvo = ctx.args[1]
        resto = " ".join(ctx.args[2:])

        modo = "DIGEST"
        if "--tempo-real" in resto or "--realtime" in resto:
            modo = "REALTIME"

        digest_time = "18:00"
        import re
        hora_match = re.search(r"--boletim\s+(\d{1,2}:\d{2})", resto)
        if hora_match:
            digest_time = hora_match.group(1)
            modo = "DIGEST"

        filtro_regex = None
        filtro_match = re.search(r"--filtro\s+[\"']?([^\"'\-\n]+)[\"']?", resto)
        if filtro_match:
            filtro_regex = filtro_match.group(1).strip()

        try:
            res = radar_manager.criar_assinatura(
                user_id=ctx.author.id,
                channel_id=ctx.channel.id,
                url_ou_chave=alvo,
                keywords_regex=filtro_regex,
                mode=modo,
                digest_time=digest_time,
            )
        except Exception as e_cad:
            await ctx.reply(f"❌ Erro ao cadastrar assinatura: `{e_cad}`")
            return

        modo_label = "⚡ Tempo Real" if res["mode"] == "REALTIME" else f"📰 Boletim diário ({res['digest_time']})"
        filtro_label = f"\n• **Filtro Regex:** `{res['keywords_regex']}`" if res["keywords_regex"] else ""

        await ctx.reply(
            f"✅ **Assinatura do Radar Cadastrada!** (ID: `{res['id']}`)\n"
            f"• **Tipo:** `{res['source_type']}`\n"
            f"• **Fonte:** <{res['source_url']}>\n"
            f"• **Canal:** <#{res['channel_id']}>\n"
            f"• **Frequência:** {modo_label}"
            f"{filtro_label}\n"
            f"💡 *A primeira verificação ocorrerá no próximo ciclo ou via `{COMMAND_PREFIX}radar agora`.*"
        )
        return

    await ctx.reply(f"⚠️ Subcomando `{sub}` desconhecido. Use `{COMMAND_PREFIX}radar` para ver as instruções.")


