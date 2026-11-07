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

    msg_status = await ctx.reply(f"⏳ *Acessando e extraindo conteúdo legível de:* `<{url}>`...")
    async with ctx.channel.typing():
        try:
            res = await web_search_manager.ler_pagina_web(url=url, max_caracteres=3500)
            if not res.get("sucesso"):
                await msg_status.edit(content=f"⚠️ {res.get('erro', 'Não foi possível ler esta página.')}")
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

            await msg_status.edit(content=resposta_final)
        except Exception as e:
            await msg_status.edit(content=f"⚠️ Falha durante a leitura da página: {str(e)}")

