"""
Comandos de Integração com Google Calendar.

Permite consultar, adicionar e desmarcar compromissos da agenda do Google
de forma totalmente assíncrona e não-bloqueante via asyncio.to_thread().
"""

import asyncio
from commands.registry import CommandContext, register_command
from config import COMMAND_PREFIX
from google_calendar import adicionar_compromisso, listar_compromissos, remover_compromisso


@register_command(
    name="agenda",
    description="Consulta seus próximos compromissos no Google Calendar.",
    usage=f"{COMMAND_PREFIX}agenda [dias]",
    aliases=["calendario", "compromissos", "eventos"],
)
async def cmd_agenda(ctx: CommandContext) -> None:
    """Consulta a agenda do Google Calendar de forma assíncrona/não-bloqueante."""
    dias = int(ctx.args[0]) if ctx.args and ctx.args[0].isdigit() else 7
    res = await asyncio.to_thread(listar_compromissos, dias_a_frente=dias)

    if not res.get("sucesso"):
        await ctx.reply(f"⚠️ {res.get('erro')}")
        return

    eventos = res.get("eventos", [])
    if not eventos:
        await ctx.reply(f"📅 Nenhum compromisso encontrado na sua agenda Google para os próximos {dias} dias.")
        return

    linhas = [f"📅 **Sua Agenda Google (Próximos {dias} dias):**\n"]
    for idx, ev in enumerate(eventos, start=1):
        linhas.append(f"{idx}. **{ev['titulo']}**")
        linhas.append(f"   ⏰ `{ev['inicio']}` até `{ev['fim']}`")
        if ev.get("local"):
            linhas.append(f"   📍 Local: {ev['local']}")
        if ev.get("link"):
            linhas.append(f"   🔗 [Abrir no Google Calendar]({ev['link']})")

    await ctx.reply("\n".join(linhas))


@register_command(
    name="agendar",
    description="Adiciona um novo compromisso no Google Calendar.",
    usage=f"{COMMAND_PREFIX}agendar <Título> | <Data/Hora Início> [| <Data/Hora Fim>]",
    aliases=["marcar", "novo_evento"],
)
async def cmd_agendar(ctx: CommandContext) -> None:
    """Adiciona evento na agenda do Google de forma assíncrona/não-bloqueante."""
    if not ctx.arg_str or "|" not in ctx.arg_str:
        await ctx.reply(
            f"❓ Formato inválido. Use barra vertical `|` para separar o título da data/hora.\n"
            f"Exemplo: `{COMMAND_PREFIX}agendar Reunião de Alinhamento | 2026-10-22 15:00`"
        )
        return

    partes = [p.strip() for p in ctx.arg_str.split("|")]
    titulo = partes[0]
    inicio = partes[1]
    fim = partes[2] if len(partes) > 2 else ""

    res = await asyncio.to_thread(adicionar_compromisso, titulo=titulo, inicio=inicio, fim=fim)
    if not res.get("sucesso"):
        await ctx.reply(f"⚠️ {res.get('erro')}")
        return

    await ctx.reply(
        f"✅ **Compromisso Agendado no Google Calendar!**\n"
        f"• **Título:** `{res.get('titulo')}`\n"
        f"• **Início:** `{res.get('inicio')}`\n"
        f"• **Término:** `{res.get('fim')}`\n"
        f"• **Link:** [Ver no Calendário]({res.get('link')})"
    )


@register_command(
    name="desmarcar",
    description="Remove ou cancela um compromisso da agenda do Google Calendar.",
    usage=f"{COMMAND_PREFIX}desmarcar <Nome do Evento ou ID>",
    aliases=["cancelar_evento", "remover_evento"],
)
async def cmd_desmarcar(ctx: CommandContext) -> None:
    """Remove evento da agenda do Google de forma assíncrona/não-bloqueante."""
    if not ctx.args:
        await ctx.reply(f"❓ Por favor, informe o nome ou ID do evento a remover. Exemplo: `{COMMAND_PREFIX}desmarcar Dentista`")
        return

    termo = ctx.arg_str
    res = await asyncio.to_thread(remover_compromisso, termo_ou_id=termo)

    if not res.get("sucesso"):
        await ctx.reply(f"⚠️ {res.get('erro')}")
        return

    await ctx.reply(f"🗑️ {res.get('mensagem')}")

