"""
Comandos de Produtividade Pessoal (Listas e Lembretes Agendados).

Permite criar e gerenciar listas de compras/mercado/tarefas com suporte a componentes
interativos do Discord UI e agendamento de avisos com parser temporal natural.
"""

from commands.registry import CommandContext, register_command
from config import COMMAND_PREFIX, DISCORD_UI_COMPONENTS_ENABLED
from list_manager import (
    adicionar_item_lista,
    excluir_lista,
    formatar_lista_para_exibicao,
    limpar_itens_concluidos,
    listar_todas_listas,
    obter_itens_lista,
    remover_item_lista,
    ticar_item_lista,
)
from reminder_manager import (
    cancelar_lembrete,
    criar_lembrete,
    interpretar_expressao_tempo,
    listar_lembretes_usuario,
)
from ui_components import InteractiveListView


@register_command(
    name="lista",
    description="Gerencia listas pessoais (mercado, tarefas, compras). Subcomandos: ver, add, ticar, remover, limpar, excluir.",
    usage=f"{COMMAND_PREFIX}lista <ver|add|ticar|remover|limpar|excluir> [nome] [item]",
    category="Listas & Tarefas",
    example=f"{COMMAND_PREFIX}lista ver mercado",
    aliases=["list", "mercado", "tarefas"],
)
async def cmd_lista(ctx: CommandContext) -> None:
    """Manipula itens e exibições de listas pessoais do usuário."""
    if not ctx.args:
        # Se digitou apenas !lista, exibe a lista padrão 'mercado' se existir, ou ajuda
        dados = obter_itens_lista(ctx.author.name, "mercado")
        if dados.get("existe"):
            view = InteractiveListView(user_id=ctx.author.name, nome_lista="mercado", author_id=ctx.author.id) if DISCORD_UI_COMPONENTS_ENABLED else None
            await ctx.reply(formatar_lista_para_exibicao(dados), view=view)
        else:
            await ctx.reply(
                f"📋 **Comando de Listas:**\n"
                f"• `{COMMAND_PREFIX}lista add <nome> <item>` — Adiciona um item\n"
                f"• `{COMMAND_PREFIX}lista ver <nome>` — Exibe os itens da lista\n"
                f"• `{COMMAND_PREFIX}lista ticar <nome> <id/texto>` — Marca/desmarca como concluído\n"
                f"• `{COMMAND_PREFIX}lista remover <nome> <id/texto>` — Remove um item\n"
                f"• `{COMMAND_PREFIX}lista limpar <nome>` — Exclui itens finalizados\n"
                f"• `{COMMAND_PREFIX}lista excluir <nome>` — Apaga a lista inteira\n"
                f"• `{COMMAND_PREFIX}listas` — Lista todas as suas listas\n\n"
                f"💡 *Exemplo:* `{COMMAND_PREFIX}lista add mercado 2L de leite integral`"
            )
        return

    sub = ctx.args[0].lower()

    # Subcomando: ver (ex: !lista ver mercado ou !lista mercado)
    if sub == "ver":
        nome_lista = ctx.args[1] if len(ctx.args) > 1 else "mercado"
        dados = obter_itens_lista(ctx.author.name, nome_lista)
        view = InteractiveListView(user_id=ctx.author.name, nome_lista=nome_lista, author_id=ctx.author.id) if (DISCORD_UI_COMPONENTS_ENABLED and dados.get("existe")) else None
        await ctx.reply(formatar_lista_para_exibicao(dados), view=view)
        return

    # Subcomando: add (ex: !lista add mercado Arroz)
    if sub in ("add", "adicionar"):
        if len(ctx.args) < 3:
            await ctx.reply(f"❓ Uso: `{COMMAND_PREFIX}lista add <nome_lista> <item>`. Exemplo: `{COMMAND_PREFIX}lista add mercado Arroz 5kg`")
            return
        nome_lista = ctx.args[1]
        item_texto = " ".join(ctx.args[2:])
        res = adicionar_item_lista(ctx.author.name, nome_lista, item_texto)
        if res.get("sucesso"):
            await ctx.reply(f"✅ {res['mensagem']}")
        else:
            await ctx.reply(f"⚠️ {res.get('mensagem')}")
        return

    # Subcomando: ticar / concluir (ex: !lista ticar mercado 1)
    if sub in ("ticar", "check", "concluir", "marcar"):
        if len(ctx.args) < 3:
            await ctx.reply(f"❓ Uso: `{COMMAND_PREFIX}lista ticar <nome_lista> <id ou texto>`. Exemplo: `{COMMAND_PREFIX}lista ticar mercado 1`")
            return
        nome_lista = ctx.args[1]
        identificador = " ".join(ctx.args[2:])
        res = ticar_item_lista(ctx.author.name, nome_lista, identificador)
        if res.get("sucesso"):
            await ctx.reply(f"✔️ {res['mensagem']}")
        else:
            await ctx.reply(f"⚠️ {res.get('mensagem')}")
        return

    # Subcomando: remover (ex: !lista remover mercado 1)
    if sub in ("remover", "del", "apagar"):
        if len(ctx.args) < 3:
            await ctx.reply(f"❓ Uso: `{COMMAND_PREFIX}lista remover <nome_lista> <id ou texto>`. Exemplo: `{COMMAND_PREFIX}lista remover mercado 1`")
            return
        nome_lista = ctx.args[1]
        identificador = " ".join(ctx.args[2:])
        res = remover_item_lista(ctx.author.name, nome_lista, identificador)
        if res.get("sucesso"):
            await ctx.reply(f"🗑️ {res['mensagem']}")
        else:
            await ctx.reply(f"⚠️ {res.get('mensagem')}")
        return

    # Subcomando: limpar concluídos (ex: !lista limpar mercado)
    if sub in ("limpar", "clean", "limpar_concluidos"):
        nome_lista = ctx.args[1] if len(ctx.args) > 1 else "mercado"
        res = limpar_itens_concluidos(ctx.author.name, nome_lista)
        if res.get("sucesso"):
            await ctx.reply(f"🧹 {res['mensagem']}")
        else:
            await ctx.reply(f"⚠️ {res.get('mensagem')}")
        return

    # Subcomando: excluir lista inteira (ex: !lista excluir compras_antigas)
    if sub in ("excluir", "delete", "deletar"):
        if len(ctx.args) < 2:
            await ctx.reply(f"❓ Uso: `{COMMAND_PREFIX}lista excluir <nome_lista>`.")
            return
        nome_lista = ctx.args[1]
        res = excluir_lista(ctx.author.name, nome_lista)
        if res.get("sucesso"):
            await ctx.reply(f"💥 {res['mensagem']}")
        else:
            await ctx.reply(f"⚠️ {res.get('mensagem')}")
        return

    # Se o primeiro argumento for o nome de uma lista direta (ex: !lista mercado)
    dados = obter_itens_lista(ctx.author.name, sub)
    if dados.get("existe"):
        view = InteractiveListView(user_id=ctx.author.name, nome_lista=sub, author_id=ctx.author.id) if DISCORD_UI_COMPONENTS_ENABLED else None
        await ctx.reply(formatar_lista_para_exibicao(dados), view=view)
    else:
        await ctx.reply(
            f"❓ Subcomando ou lista '{sub}' não reconhecido.\n"
            f"Use `{COMMAND_PREFIX}lista ver {sub}`, `{COMMAND_PREFIX}lista add {sub} <item>` ou `{COMMAND_PREFIX}listas`."
        )


@register_command(
    name="listas",
    description="Exibe todas as listas de compras, mercado ou tarefas cadastradas pelo usuário.",
    usage=f"{COMMAND_PREFIX}listas",
    category="Listas & Tarefas",
    example=f"{COMMAND_PREFIX}listas",
    aliases=["minhas_listas"],
)
async def cmd_listas(ctx: CommandContext) -> None:
    """Lista todas as listas do usuário."""
    listas = listar_todas_listas(ctx.author.name)
    if not listas:
        await ctx.reply(
            f"📋 Você ainda não possui nenhuma lista cadastrada.\n"
            f"💡 Para criar uma, basta usar: `{COMMAND_PREFIX}lista add mercado Leite 2L`"
        )
        return

    linhas = ["📋 **Suas Listas Cadastradas:**", "─" * 35]
    for l in listas:
        linhas.append(
            f"• **{l['nome']}** — {l['total_itens']} itens ({l['pendentes']} pendentes, {l['concluidos']} concluídos)"
        )
    linhas.append("─" * 35)
    linhas.append(f"💡 *Para ver os itens de uma lista: `{COMMAND_PREFIX}lista <nome>`*")
    await ctx.reply("\n".join(linhas))


@register_command(
    name="lembrete",
    description="Agenda um aviso ou lembrete para você. Aceita tempo relativo ('em 15m') ou data e hora ('19/10/2026 09:00').",
    usage=f"{COMMAND_PREFIX}lembrete <quando> <mensagem>",
    category="Lembretes Agendados",
    example=f"{COMMAND_PREFIX}lembrete em 15m tomar café",
    aliases=["lembrar", "aviso", "avisar"],
)
async def cmd_lembrete(ctx: CommandContext) -> None:
    """Programa um lembrete com notificação ativa no Discord."""
    if not ctx.args or len(ctx.args) < 2:
        await ctx.reply(
            f"❓ **Como usar o agendador de lembretes:**\n"
            f"• Tempo relativo: `{COMMAND_PREFIX}lembrete em 15m desligar o forno`\n"
            f"• Horário hoje/amanhã: `{COMMAND_PREFIX}lembrete 09:00 tomar remédio`\n"
            f"• Data e horário: `{COMMAND_PREFIX}lembrete 19/10/2026 09:00 consulta médica`\n"
            f"• Listar pendentes: `{COMMAND_PREFIX}lembretes`"
        )
        return

    tokens = ctx.args
    dt_alvo = None
    msg_texto = ""

    # Tenta interpretar expressões de 1 a 3 palavras no início (ex: 'em 15 minutos', '19/10 09:00', '15m')
    for num_palavras in (3, 2, 1):
        if len(tokens) > num_palavras:
            candidato_tempo = " ".join(tokens[:num_palavras])
            dt = interpretar_expressao_tempo(candidato_tempo)
            if dt:
                dt_alvo = dt
                msg_texto = " ".join(tokens[num_palavras:])
                break

    if not dt_alvo or not msg_texto:
        await ctx.reply(
            f"⚠️ Não consegui entender o momento do lembrete.\n"
            f"Exemplos válidos:\n"
            f"• `{COMMAND_PREFIX}lembrete em 15m tirar o bolo do forno`\n"
            f"• `{COMMAND_PREFIX}lembrete 19/10 09:00 tomar remédio`"
        )
        return

    res = criar_lembrete(
        user_id=str(ctx.author.id),
        channel_id=str(ctx.channel.id),
        mensagem=msg_texto,
        quando_dt=dt_alvo,
    )

    if res.get("sucesso"):
        await ctx.reply(res["resposta_formatada"])
    else:
        await ctx.reply(f"⚠️ {res.get('mensagem')}")


@register_command(
    name="lembretes",
    description="Lista todos os seus lembretes pendentes agendados.",
    usage=f"{COMMAND_PREFIX}lembretes",
    category="Lembretes Agendados",
    example=f"{COMMAND_PREFIX}lembretes",
    aliases=["meus_lembretes", "avisos"],
)
async def cmd_lembretes(ctx: CommandContext) -> None:
    """Exibe todos os lembretes pendentes do usuário."""
    lembretes = listar_lembretes_usuario(str(ctx.author.id), apenas_pendentes=True)
    if not lembretes:
        await ctx.reply("⏰ Você não possui nenhum lembrete pendente programado no momento.")
        return

    linhas = ["⏰ **Seus Lembretes Pendentes:**", "─" * 40]
    for l in lembretes:
        linhas.append(f"• `#{l['id']}` **{l['remind_at']}** — {l['mensagem']}")
    linhas.append("─" * 40)
    linhas.append(f"💡 *Para cancelar: `{COMMAND_PREFIX}cancelar_lembrete <ID>`*")
    await ctx.reply("\n".join(linhas))


@register_command(
    name="cancelar_lembrete",
    description="Cancela um lembrete pendente através do ID.",
    usage=f"{COMMAND_PREFIX}cancelar_lembrete <ID>",
    category="Lembretes Agendados",
    example=f"{COMMAND_PREFIX}cancelar_lembrete 3",
    aliases=["remover_lembrete", "desmarcar_lembrete"],
)
async def cmd_cancelar_lembrete(ctx: CommandContext) -> None:
    """Cancela um lembrete pelo ID numérico."""
    if not ctx.args or not ctx.args[0].isdigit():
        await ctx.reply(f"❓ Por favor, informe o ID numérico do lembrete. Exemplo: `{COMMAND_PREFIX}cancelar_lembrete 3`")
        return

    lembrete_id = int(ctx.args[0])
    res = cancelar_lembrete(str(ctx.author.id), lembrete_id)
    if res.get("sucesso"):
        await ctx.reply(f"🗑️ {res['mensagem']}")
    else:
        await ctx.reply(f"⚠️ {res.get('mensagem')}")

