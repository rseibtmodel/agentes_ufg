"""
Comandos de Navegação e Pesquisa na Web (!buscar, !ler).

Permite pesquisas em tempo real no DuckDuckGo/Tavily e extração limpa de artigos
web com síntese analítica gerada pela LLM.
"""

from commands.registry import CommandContext, register_command
from config import COMMAND_PREFIX


@register_command(
    name="buscar",
    description="Pesquisa informações atualizadas na internet em tempo real (notícias, cotações, fatos).",
    usage=f"{COMMAND_PREFIX}buscar <termo de pesquisa>",
    category="Pesquisa & Web",
    example=f"{COMMAND_PREFIX}buscar cotação do dólar hoje",
    aliases=["pesquisar", "busca", "search", "web"],
)
async def cmd_buscar(ctx: CommandContext) -> None:
    """Executa uma busca na internet em tempo real via DuckDuckGo/Tavily."""
    from web_search_manager import web_search_manager

    if not ctx.args:
        linhas = [
            "🔍 **COMO USAR O COMANDO DE BUSCA NA WEB:**",
            f"Digite `{COMMAND_PREFIX}buscar <o que você deseja pesquisar>`\n",
            "**Exemplos de uso:**",
            f"• `{COMMAND_PREFIX}buscar cotação do dólar hoje comercial`",
            f"• `{COMMAND_PREFIX}buscar previsão do tempo são paulo fim de semana`",
            f"• `{COMMAND_PREFIX}buscar últimas notícias inteligência artificial`",
            f"• `{COMMAND_PREFIX}buscar resultado jogo do flamengo ontem`\n",
            "💡 *Dica:* Durante a conversa normal sem prefixo, a IA aciona a busca na internet automaticamente quando necessário!",
        ]
        await ctx.reply("\n".join(linhas))
        return

    query = " ".join(ctx.args).strip()
    async with ctx.channel.typing():
        try:
            resultados = await web_search_manager.buscar_na_web(query=query, max_resultados=4)
            if not resultados:
                await ctx.reply(f"🔍 Nenhum resultado encontrado na web para: *\"{query}\"*.")
                return

            msg_formatada = web_search_manager.formatar_para_discord(resultados, query)
            if len(msg_formatada) > 1950:
                msg_formatada = msg_formatada[:1940] + "\n..."
            await ctx.reply(msg_formatada)
        except Exception as e:
            await ctx.reply(f"⚠️ Erro ao executar busca na web: {str(e)}")


@register_command(
    name="ler",
    description="Acessa uma página web ou artigo, extrai o texto limpo e gera uma síntese inteligente.",
    usage=f"{COMMAND_PREFIX}ler <url>",
    category="Pesquisa & Web",
    example=f"{COMMAND_PREFIX}ler https://exemplo.com/artigo",
    aliases=["ler_artigo", "ler_pagina", "browse", "extrair", "resumir_link"],
)
async def cmd_ler(ctx: CommandContext) -> None:
    """Lê uma página da web e produz uma síntese estruturada com a LLM."""
    from database import obter_preferencia_modelo
    from llm_client import llm_client
    from web_search_manager import web_search_manager

    if not ctx.args:
        linhas = [
            "📖 **COMO USAR O COMANDO DE LEITURA DE LINKS:**",
            f"Digite `{COMMAND_PREFIX}ler <url da página>`\n",
            "**Exemplo:**",
            f"• `{COMMAND_PREFIX}ler https://g1.globo.com/tecnologia/...`\n",
            "A IA acessará a página, removerá menus e propagandas, e gerará um resumo estruturado com os pontos principais.",
        ]
        await ctx.reply("\n".join(linhas))
        return

    url = ctx.args[0].strip()
    if not (url.startswith("http://") or url.startswith("https://")):
        await ctx.reply("⚠️ URL inválida. O link deve começar com `http://` ou `https://`.")
        return

    res_status = await ctx.reply(f"⏳ *Acessando e extraindo conteúdo legível de:* `<{url}>`...")
    msg_status = res_status[0] if isinstance(res_status, list) and res_status else res_status
    async with ctx.channel.typing():
        try:
            res = await web_search_manager.ler_pagina_web(url=url, max_caracteres=3500)
            if not res.get("sucesso"):
                texto_erro = f"⚠️ {res.get('erro', 'Não foi possível ler esta página.')}"
                if msg_status and hasattr(msg_status, "edit"):
                    await msg_status.edit(content=texto_erro)
                else:
                    await ctx.reply(texto_erro)
                return

            titulo = res.get("titulo", "Página Web")
            conteudo = res.get("conteudo", "")

            # Solicita à LLM a síntese executiva do artigo
            prompt_sintese = (
                f"Você é um assistente de leitura inteligente. Resuma em português de forma clara e estruturada o seguinte conteúdo extraído da web.\n"
                f"Título: {titulo}\n"
                f"URL: {url}\n\n"
                f"Texto do Artigo:\n{conteudo}\n\n"
                f"Instruções:\n"
                f"1. Resumo Executivo (1 a 2 parágrafos objetivos).\n"
                f"2. Principais Destaques (3 a 5 tópicos em bullet points).\n"
                f"3. Conclusão ou Impacto."
            )
            mensagens = [{"role": "user", "content": prompt_sintese}]
            pref = obter_preferencia_modelo(ctx.author.id)

            resumo_llm = await llm_client.gerar_resposta(
                mensagens=mensagens,
                provider=pref.get("provider", "local"),
                model=pref.get("model_name"),
                permitir_failover=True,
                incluir_badge=True,
            )

            cabecalho = f"📰 **Leitura & Síntese:** [{titulo}]({url})\n\n"
            resposta_final = cabecalho + resumo_llm
            if len(resposta_final) > 2000:
                resposta_final = resposta_final[:1990] + "..."

            if msg_status and hasattr(msg_status, "edit"):
                await msg_status.edit(content=resposta_final)
            else:
                await ctx.reply(resposta_final)
        except Exception as e:
            texto_falha = f"⚠️ Falha durante a leitura da página: {str(e)}"
            if msg_status and hasattr(msg_status, "edit"):
                await msg_status.edit(content=texto_falha)
            else:
                await ctx.reply(texto_falha)


@register_command(
    name="pesquisa_profunda",
    description="Executa uma investigação profunda na web (Deep Research), cruzando múltiplas fontes e gerando um dossiê executivo com citações.",
    usage=f"{COMMAND_PREFIX}pesquisa_profunda <tema ou pergunta complexa>",
    category="Pesquisa & Web",
    example=f"{COMMAND_PREFIX}pesquisa Reforma tributária CBS no SaaS",
    aliases=["pesquisa", "deepresearch", "investigar", "dossie"],
)
async def cmd_pesquisa_profunda(ctx: CommandContext) -> None:
    """Executa a pesquisa profunda autônoma e anexa o dossiê técnico."""
    import discord
    from pathlib import Path
    from deep_research_manager import deep_research_manager

    if not ctx.args:
        linhas = [
            "🧭 **AGENTE DE PESQUISA PROFUNDA (DEEP RESEARCH — IDEA-17)**",
            f"Uso: `{COMMAND_PREFIX}pesquisa_profunda <tema complexo>`\n",
            "**Como funciona:**",
            "1. 🧠 Decompõe seu tema em 3 a 4 eixos de investigação",
            "2. 🔍 Varre a web em paralelo e lê 8 a 12 artigos em profundidade",
            "3. 📑 Cruza dados, elimina contradições e redige um Dossiê Técnico",
            "4. 📥 Entrega o resumo no chat e anexa o arquivo Markdown com referências\n",
            "**Exemplos de temas:**",
            f"• `{COMMAND_PREFIX}pesquisa Reforma tributária CBS e impactos em SaaS no Brasil`",
            f"• `{COMMAND_PREFIX}pesquisa Comparativo técnico Mac Studio M2 Max vs instâncias H100 para LLM local`",
            f"• `{COMMAND_PREFIX}pesquisas` — Lista dossiês elaborados anteriormente"
        ]
        await ctx.reply("\n".join(linhas))
        return

    tema = " ".join(ctx.args).strip()
    res_status = await ctx.reply(f"🧭 **Iniciando Deep Research:** *\"{tema}\"*\n*Aguarde, este processo realiza varredura e cruzamento de múltiplas fontes...*")
    msg_status = res_status[0] if isinstance(res_status, list) and res_status else res_status

    # Callback para atualização em tempo real no Discord
    async def atualizar_progresso(status_texto: str) -> None:
        try:
            if msg_status and hasattr(msg_status, "edit"):
                await msg_status.edit(content=f"{status_texto}\n\n📌 **Tema:** *\"{tema}\"*")
        except Exception:
            pass

    async with ctx.channel.typing():
        try:
            resultado = await deep_research_manager.executar_pesquisa_completa(
                tema=tema,
                user_id=str(ctx.author.id),
                progress_callback=atualizar_progresso,
            )

            if not resultado.get("sucesso"):
                msg_erro = resultado.get("erro", "Falha na elaboração da pesquisa.")
                if msg_status and hasattr(msg_status, "edit"):
                    await msg_status.edit(content=f"⚠️ {msg_erro}")
                else:
                    await ctx.reply(f"⚠️ {msg_erro}")
                return

            dados = resultado["dados"]
            caminho_arq = Path(dados["file_path"])

            corpo_resposta = (
                f"📑 **DOSSIÊ TÉCNICO CONCLUÍDO (ID: `{dados['report_id']}`)**\n"
                f"• **Tema:** *{dados['tema']}*\n"
                f"• **Fontes Analisadas:** `{dados['total_fontes']}` artigos na web\n\n"
                f"**Sumário Executivo:**\n"
                f"{dados['resumo_executivo']}\n\n"
                f"📥 *O dossiê analítico completo com todas as referências foi anexado abaixo:*"
            )

            if caminho_arq.exists():
                arquivo_discord = discord.File(str(caminho_arq), filename=caminho_arq.name)
                await ctx.channel.send(content=corpo_resposta, file=arquivo_discord)
            else:
                await ctx.reply(corpo_resposta)

        except Exception as e:
            texto_excecao = f"⚠️ Falha inesperada durante o Deep Research: {str(e)}"
            if msg_status and hasattr(msg_status, "edit"):
                await msg_status.edit(content=texto_excecao)
            else:
                await ctx.reply(texto_excecao)


@register_command(
    name="pesquisas",
    description="Lista seus relatórios e dossiês de pesquisa profunda já concluídos.",
    usage=f"{COMMAND_PREFIX}pesquisas",
    category="Pesquisa & Web",
    example=f"{COMMAND_PREFIX}pesquisas",
    aliases=["meus_dossies", "relatorios_pesquisa"],
)
async def cmd_pesquisas(ctx: CommandContext) -> None:
    """Lista pesquisas anteriores do usuário com metadados."""
    import discord
    from pathlib import Path
    from deep_research_manager import deep_research_manager

    # Se passou o ID de um relatório para baixar (ex: !pesquisas baixar abc12345)
    if ctx.args and ctx.args[0].lower() in ("baixar", "obter", "ver", "get") and len(ctx.args) > 1:
        rid = ctx.args[1].strip()
        rel = deep_research_manager.obter_relatorio(rid)
        if not rel:
            await ctx.reply(f"❌ Relatório `{rid}` não encontrado.")
            return

        caminho_arq = Path(rel["file_path"])
        if caminho_arq.exists():
            arq_discord = discord.File(str(caminho_arq), filename=caminho_arq.name)
            await ctx.channel.send(
                content=f"📥 **Aqui está o Dossiê solicitado:** `{rel['topic']}`",
                file=arq_discord,
            )
        else:
            await ctx.reply(f"⚠️ O arquivo físico do relatório `{rid}` não foi localizado no servidor.")
        return

    relatorios = deep_research_manager.listar_relatorios(str(ctx.author.id), limite=10)
    if not relatorios:
        await ctx.reply(
            f"📭 Você ainda não possui nenhum relatório de pesquisa profunda.\n"
            f"Para iniciar uma nova investigação, digite: `{COMMAND_PREFIX}pesquisa_profunda <tema>`"
        )
        return

    linhas = [
        f"📚 **SEUS DOSSIÊS DE PESQUISA PROFUNDA ({len(relatorios)}):**\n",
    ]
    for idx, r in enumerate(relatorios, start=1):
        linhas.append(
            f"{idx}. `[{r['id']}]` **{r['topic']}** ({r['total_sources']} fontes consultadas)\n"
            f"   📅 *Criado em:* `{r['created_at']}`\n"
            f"   💡 *Para baixar:* `{COMMAND_PREFIX}pesquisas baixar {r['id']}`\n"
        )

    await ctx.reply("\n".join(linhas))

