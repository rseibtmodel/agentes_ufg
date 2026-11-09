"""
Comandos de Inteligência Artificial, Modelos, Central de Prompts e Personas (IDEA-20 e IDEA-26).

Permite gerenciar:
1. Provedor e modelo ativo da LLM (!modelo: local, google, gemini-pro, auto, key)
2. Central de Prompts (!prompts, !prompt: templates e presets cognitivos oficiais e customizados)
3. Personas por canal/thread (!persona: catálogo, calibração de prompts, temperatura e overrides)
"""

import logging
import os
import re
from typing import Optional

from commands.registry import CommandContext, register_command
from config import BASE_DIR, COMMAND_PREFIX, GEMINI_FLASH_MODEL, GEMINI_PRO_MODEL, MODELO_LLM
from database import definir_preferencia_modelo, obter_preferencia_modelo
from llm_client import llm_client
from persona_manager import (
    aplicar_preset_canal,
    definir_avatar_canal,
    definir_identidade_canal,
    definir_modelo_canal,
    definir_persona_canal,
    definir_temperatura_canal,
    definir_trava_persona_canal,
    listar_personas_canais,
    listar_personas_disponiveis,
    obter_avatar_persona,
    obter_persona_canal,
    remover_persona_catalogo,
    resetar_persona_canal,
    salvar_nova_persona,
)
from prompt_hub import listar_templates, obter_template, remover_template, salvar_template
from ui_components import criar_view_modal_persona, criar_view_selecao_persona

logger = logging.getLogger(__name__)


@register_command(
    name="modelo",
    description="Exibe e gerencia o modelo e provedor de LLM ativo (Local vs Google Gemini vs Auto).",
    usage=f"{COMMAND_PREFIX}modelo [local | google | gemini-pro | auto | key <chave>]",
    category="IA & Modelos",
    example=f"{COMMAND_PREFIX}modelo google",
    aliases=["llm", "ia", "provedor"],
)
async def cmd_modelo(ctx: CommandContext) -> None:
    """Exibe e gerencia o provedor e modelo de IA do usuário."""
    # Se não passou argumentos, exibe o status detalhado
    if not ctx.args:
        pref = obter_preferencia_modelo(ctx.author.id)
        gemini_disponivel = llm_client.tem_gemini_disponivel()
        status_gemini = "🟢 Conectado e Pronto" if gemini_disponivel else "⚪ Não configurado (Use `!modelo key <sua_chave>`)"

        prov_ativo = pref["provider"].upper()
        mod_ativo = pref["model_name"]
        failover_str = "Ativado (Fallback suave para Google se Local falhar)" if pref["auto_failover"] else "Desativado"

        texto = (
            f"🧠 **GERENCIADOR DE MODELOS & PROVEDORES DE IA**\n\n"
            f"• **Seu Provedor Ativo:** `{prov_ativo}`\n"
            f"• **Modelo em Execução:** `{mod_ativo}`\n"
            f"• **Status Google Gemini:** {status_gemini}\n"
            f"• **Failover de Alta Disponibilidade:** `{failover_str}`\n\n"
            f"📋 **Comandos de Troca Rápida:**\n"
            f"• `{COMMAND_PREFIX}modelo local` — Ativa o LM Studio local (`{MODELO_LLM}`)\n"
            f"• `{COMMAND_PREFIX}modelo google` — Ativa o Google Gemini Flash (`{GEMINI_FLASH_MODEL}`)\n"
            f"• `{COMMAND_PREFIX}modelo gemini-pro` — Ativa o Google Gemini Pro (`{GEMINI_PRO_MODEL}`)\n"
            f"• `{COMMAND_PREFIX}modelo auto` — Roteamento inteligente por demanda\n"
            f"• `{COMMAND_PREFIX}modelo key <sua_chave>` — Cadastra sua chave da Google Gemini API (a mensagem será apagada por segurança)"
        )
        await ctx.reply(texto)
        return

    sub = ctx.args[0].lower().strip()

    # Subcomando: Configurar Chave da API
    if sub in ("key", "chave", "apikey", "token"):
        if len(ctx.args) < 2:
            await ctx.reply(f"❓ Uso: `{COMMAND_PREFIX}modelo key <sua_api_key_do_google>`")
            return

        chave_informada = ctx.args[1].strip()

        # Apaga a mensagem do usuário imediatamente para evitar vazamento da chave no histórico do chat
        try:
            await ctx.message.delete()
        except Exception:
            pass

        if not chave_informada.startswith("AIza") and len(chave_informada) < 20:
            await ctx.reply("⚠️ Chave informada parece inválida. A chave da Google Gemini API geralmente começa com 'AIza...'.")
            return

        # Atualiza em memória no llm_client
        llm_client.atualizar_gemini_api_key(chave_informada)

        # Atualiza no arquivo .env para persistência definitiva
        try:
            env_file = BASE_DIR / ".env"
            if env_file.exists():
                conteudo_env = env_file.read_text(encoding="utf-8")
                if "GEMINI_API_KEY=" in conteudo_env:
                    conteudo_env = re.sub(r"GEMINI_API_KEY=.*", f"GEMINI_API_KEY={chave_informada}", conteudo_env)
                else:
                    conteudo_env += f"\nGEMINI_API_KEY={chave_informada}\n"
                env_file.write_text(conteudo_env, encoding="utf-8")
        except Exception as e_env:
            logger.warning("Falha ao persistir GEMINI_API_KEY no .env: %s", e_env)

        await ctx.reply(
            "🔒 **Chave do Google Gemini configurada com sucesso!**\n"
            "Sua mensagem foi apagada do chat para proteger seu segredo. O provedor Google já está pronto para uso!\n"
            f"Para ativar agora, use: `{COMMAND_PREFIX}modelo google`"
        )
        return

    # Subcomando: local
    if sub in ("local", "lmstudio", "lm-studio", "offline"):
        res = definir_preferencia_modelo(ctx.author.id, ctx.author.name, "local", MODELO_LLM)
        await ctx.reply(f"🏠 {res['mensagem']}")
        return

    # Subcomando: google / gemini
    if sub in ("google", "gemini", "flash", "gemini-flash"):
        if not llm_client.tem_gemini_disponivel():
            await ctx.reply(
                "⚠️ A API do Google Gemini ainda não possui uma chave configurada.\n"
                f"Utilize o comando: `{COMMAND_PREFIX}modelo key <sua_chave_do_google>` (sua mensagem será apagada automaticamente por segurança) "
                f"ou configure a variável `GEMINI_API_KEY` no arquivo `discord/.env`."
            )
            return
        res = definir_preferencia_modelo(ctx.author.id, ctx.author.name, "google", GEMINI_FLASH_MODEL)
        await ctx.reply(f"⚡ {res['mensagem']}")
        return

    # Subcomando: gemini-pro
    if sub in ("pro", "gemini-pro", "google-pro"):
        if not llm_client.tem_gemini_disponivel():
            await ctx.reply(
                "⚠️ A API do Google Gemini ainda não possui uma chave configurada.\n"
                f"Utilize o comando: `{COMMAND_PREFIX}modelo key <sua_chave_do_google>` para cadastrá-la."
            )
            return
        res = definir_preferencia_modelo(ctx.author.id, ctx.author.name, "google", GEMINI_PRO_MODEL)
        await ctx.reply(f"🧠 {res['mensagem']}")
        return

    # Subcomando: auto
    if sub in ("auto", "automatico", "automático", "dinamico", "hibrido"):
        res = definir_preferencia_modelo(ctx.author.id, ctx.author.name, "auto", "auto")
        await ctx.reply(f"🔀 {res['mensagem']}")
        return

    # Se não reconheceu
    await ctx.reply(
        f"❓ Opção `{sub}` não reconhecida.\n"
        f"Use: `{COMMAND_PREFIX}modelo` para ver o status, ou `{COMMAND_PREFIX}modelo [local | google | gemini-pro | auto | key]`."
    )


@register_command(
    name="prompts",
    description="Lista os templates de prompts e presets cognitivos disponíveis no catálogo central (IDEA-20).",
    usage=f"{COMMAND_PREFIX}prompts [categoria]",
    category="Central de Prompts",
    example=f"{COMMAND_PREFIX}prompts",
    aliases=["templates", "presets"],
)
async def cmd_prompts(ctx: CommandContext) -> None:
    """Lista templates e presets disponíveis no Prompt Hub."""
    cat = ctx.args[0].lower() if ctx.args else None
    templates = listar_templates(categoria=cat)

    if not templates:
        msg = f"Nenhum template encontrado na categoria `{cat}`." if cat else "O catálogo de prompts está vazio."
        await ctx.reply(f"ℹ️ {msg}")
        return

    linhas = [
        "📚 **CATÁLOGO DA CENTRAL DE PROMPTS (IDEA-20)**",
        "Use `!prompt ver <slug>` para ver o texto ou `!persona canal aplicar <slug>` para aplicar no canal atual:\n",
    ]
    for t in templates:
        tipo = "🔒 Oficial" if t["is_builtin"] else "👤 Custom"
        linhas.append(f"• **`{t['id']}`** ({tipo}) — *{t['nome']}*: {t['descricao']}")

    await ctx.reply("\n".join(linhas))


@register_command(
    name="prompt",
    description="Exibe, salva ou remove templates de prompt na Central de Prompts (IDEA-20).",
    usage=f"{COMMAND_PREFIX}prompt [ver|salvar|remover] <slug> [texto...]",
    category="Central de Prompts",
    example=f"{COMMAND_PREFIX}prompt ver dev",
    aliases=["template"],
)
async def cmd_prompt(ctx: CommandContext) -> None:
    """Gerencia templates de prompts no catálogo."""
    if not ctx.args:
        await ctx.reply(
            f"ℹ️ **Uso do comando !prompt:**\n"
            f"• `{COMMAND_PREFIX}prompt ver <slug>` — Exibe o texto completo do template\n"
            f"• `{COMMAND_PREFIX}prompt salvar <slug> <texto>` — Salva um novo template pessoal\n"
            f"• `{COMMAND_PREFIX}prompt remover <slug>` — Remove um template customizado\n"
            f"• `{COMMAND_PREFIX}prompts` — Lista todos os templates disponíveis"
        )
        return

    sub = ctx.args[0].lower()

    if sub in ("ver", "show", "info"):
        if len(ctx.args) < 2:
            await ctx.reply(f"❓ Informe o slug do template. Exemplo: `{COMMAND_PREFIX}prompt ver dev`")
            return
        slug = ctx.args[1]
        tpl = obter_template(slug)
        if not tpl:
            await ctx.reply(f"❌ Template `{slug}` não encontrado no catálogo. Veja a lista com `{COMMAND_PREFIX}prompts`.")
            return

        tipo = "Oficial de Fábrica" if tpl["is_builtin"] else "Customizado"
        msg = (
            f"📋 **Template:** `{tpl['id']}` (*{tpl['nome']}*)\n"
            f"🏷️ **Tipo:** {tipo} | **Categoria:** `{tpl['categoria']}` | **Temp:** `{tpl['temperatura']}`\n"
            f"📝 **Descrição:** {tpl['descricao']}\n\n"
            f"```text\n{tpl['template_text']}\n```"
        )
        await ctx.reply(msg)
        return

    if sub in ("salvar", "save", "criar", "add"):
        if len(ctx.args) < 3:
            await ctx.reply(f"❓ Uso: `{COMMAND_PREFIX}prompt salvar <slug> <texto completo do prompt>`")
            return
        slug = ctx.args[1]
        texto = " ".join(ctx.args[2:])
        res = salvar_template(slug_id=slug, nome=slug, template_text=texto, user_id=str(ctx.author.id))
        if res["sucesso"]:
            await ctx.reply(f"✅ {res['mensagem']}\nPara aplicá-lo a este canal, use: `{COMMAND_PREFIX}persona canal aplicar {slug}`")
        else:
            await ctx.reply(f"⚠️ {res['mensagem']}")
        return

    if sub in ("remover", "del", "delete", "rm"):
        if len(ctx.args) < 2:
            await ctx.reply(f"❓ Informe o slug a remover. Exemplo: `{COMMAND_PREFIX}prompt remover meu_prompt`")
            return
        slug = ctx.args[1]
        res = remover_template(slug)
        if res["sucesso"]:
            await ctx.reply(f"✅ {res['mensagem']}")
        else:
            await ctx.reply(f"⚠️ {res['mensagem']}")
        return

    await ctx.reply(f"❓ Subcomando desconhecido. Use `{COMMAND_PREFIX}prompt [ver|salvar|remover]` ou `{COMMAND_PREFIX}prompts`.")


@register_command(
    name="persona",
    description="Visualiza, calibra a identidade multimodal (avatar, nome, idade) e gerencia personas por canal e metamorfose semanal (IDEA-26 e IDEA-27).",
    usage=f"{COMMAND_PREFIX}persona [ver|editar|avatar <url>|identidade|fixar|destravar|metamorfose|historico|lista|canal]",
    category="Personas & Especialistas",
    example=f"{COMMAND_PREFIX}persona metamorfose",
    aliases=["personas", "personacanal"],
)
async def cmd_persona(ctx: CommandContext) -> None:
    """Gerencia o catálogo de personas e a especialidade cognitiva dos canais."""
    channel_id = str(ctx.channel.id)
    guild_id = str(ctx.message.guild.id) if ctx.message.guild else None
    channel_name = getattr(ctx.channel, "name", str(channel_id))
    user_id = str(ctx.author.id)

    # Verifica permissão de administrador ou manage_channels no servidor (em DM é liberado)
    is_admin = True
    if ctx.message.guild is not None:
        perms = getattr(ctx.author, "guild_permissions", None)
        is_admin = bool(
            getattr(perms, "administrator", False)
            or getattr(perms, "manage_channels", False)
            or str(ctx.author.id) == os.getenv("DISCORD_USER", "")
        )

    # Função auxiliar para renderizar Card Embed da Persona (IDEA-27)
    def _gerar_embed_status_persona(p: Optional[dict]) -> discord.Embed:
        import discord
        if not p:
            emb = discord.Embed(
                title=f"🎭 Persona do Canal: #{channel_name}",
                description="ℹ️ Este canal está utilizando o **Assistente Padrão** do sistema.",
                color=0x2B2D31,
            )
            emb.set_thumbnail(url="https://api.dicebear.com/7.x/bottts/png?seed=antigravity")
            return emb

        av = obter_avatar_persona(p)
        emb = discord.Embed(
            title=f"🎭 Persona do Canal: #{channel_name}",
            color=0x2B2D31,
        )
        emb.set_thumbnail(url=av)
        nome_display = p.get("display_name") or p.get("persona_slug") or p.get("persona_id") or "Personalizada"
        emb.add_field(name="👤 Nome de Exibição", value=f"`{nome_display}`", inline=True)
        emb.add_field(name="⏳ Idade / Maturação", value=f"`{p.get('age') or 'Não informada'}`", inline=True)
        lock_txt = "🔒 Travada (Permanente)" if p.get("is_locked") else "🔓 Adaptativa (7 dias)"
        emb.add_field(name="🔄 Evolução Semanal", value=f"`{lock_txt}`", inline=True)
        if p.get("bio"):
            emb.add_field(name="📜 Biografia / Contexto", value=f"*{p['bio']}*", inline=False)
        mod_txt = f" | Modelo: `{p['model_override']}`" if p.get("model_override") else ""
        emb.add_field(name="⚙️ Calibração", value=f"Temperatura: `{p.get('temperature', 0.7)}`{mod_txt}", inline=False)
        prompt_preview = p.get("system_prompt", "")
        if len(prompt_preview) > 500:
            prompt_preview = prompt_preview[:490] + "..."
        emb.add_field(name="📝 Diretrizes Cognitivas", value=f"```text\n{prompt_preview}\n```", inline=False)
        return emb

    # Sem argumentos: dashboard geral de personas e canais com dropdown interativo
    if not ctx.args:
        personas_cat = listar_personas_disponiveis()
        linhas = [
            "🎭 **CENTRAL DE PERSONAS COGNITIVAS (IDEA-26 & IDEA-27)**",
            "Consulte personas disponíveis, troque no menu interativo ou configure identidades:\n",
            f"**Personas no Catálogo ({len(personas_cat)}):**",
        ]
        for p in personas_cat[:8]:
            tag = "🌟" if p["is_preset"] else "👤"
            linhas.append(f"• `{p['id']}` — {tag} **{p['nome']}** (temp: `{p['temperatura']}`): *{p['descricao'][:60]}...*")
        if len(personas_cat) > 8:
            linhas.append(f"*...e mais {len(personas_cat) - 8} personas.* Use `{COMMAND_PREFIX}persona lista` para ver todas.")

        # Status do canal atual
        p_atual = obter_persona_canal(channel_id)
        if p_atual and p_atual.get("display_name"):
            linhas.append(f"\n📍 **Canal Atual (`#{channel_name}`):** Persona `{p_atual['display_name']}` ativa (temp: `{p_atual['temperature']}`)")
        elif p_atual and p_atual.get("persona_slug"):
            linhas.append(f"\n📍 **Canal Atual (`#{channel_name}`):** Persona ativa `{p_atual['persona_slug']}` (temp: `{p_atual['temperature']}`)")
        elif p_atual:
            linhas.append(f"\n📍 **Canal Atual (`#{channel_name}`):** Persona customizada ativa (temp: `{p_atual['temperature']}`)")
        else:
            linhas.append(f"\n📍 **Canal Atual (`#{channel_name}`):** Assistente padrão ativo")

        linhas.extend([
            "\n💡 **Identidade & Comandos Rápidos:**",
            f"• `{COMMAND_PREFIX}persona ver` — Exibe card com Avatar, Nome, Idade e Bio",
            f"• `{COMMAND_PREFIX}persona editar` — Abre formulário interativo de identidade",
            f"• `{COMMAND_PREFIX}persona avatar <url>` — Altera imagem de perfil do canal",
            f"• `{COMMAND_PREFIX}persona identidade <nome> | <idade> | <bio>` — Define perfil",
            f"• `{COMMAND_PREFIX}persona metamorfose` — Força metamorfose semanal com Bag-of-Words",
            f"• `{COMMAND_PREFIX}persona historico` — Exibe álbum de encarnações passadas",
            f"• `{COMMAND_PREFIX}persona fixar` / `{COMMAND_PREFIX}persona destravar` — Controla evolução de 7 dias",
            f"• `{COMMAND_PREFIX}persona canal reset` — Restaura assistente padrão",
        ])
        view_dropdown = criar_view_selecao_persona(
            channel_id=channel_id,
            author_id=ctx.author.id,
            guild_id=guild_id,
            channel_name=channel_name,
        )
        await ctx.reply("\n".join(linhas), view=view_dropdown)
        return

    sub = ctx.args[0].lower()

    # Subcomando: ver / status (Inspecionar persona ativa com Embed rico)
    if sub in ("ver", "status", "info"):
        persona = obter_persona_canal(channel_id)
        embed_status = _gerar_embed_status_persona(persona)
        view_dropdown = criar_view_selecao_persona(
            channel_id=channel_id,
            author_id=ctx.author.id,
            guild_id=guild_id,
            channel_name=channel_name,
        )
        await ctx.reply(embed=embed_status, view=view_dropdown)
        return

    # Subcomando: editar / modal (Dispara botão que abre o formulário nativo do Discord)
    if sub in ("editar", "modal", "customizar"):
        view_modal = criar_view_modal_persona(channel_id=channel_id)
        await ctx.reply(
            "🎭 **Editor de Identidade Multimodal da Persona (IDEA-27):**\n"
            "Clique no botão abaixo para abrir o formulário nativo e configurar Nome, Idade, Avatar e Bio:",
            view=view_modal,
        )
        return

    # Subcomando: avatar (Define imagem ou semente DiceBear da persona)
    if sub == "avatar":
        if len(ctx.args) < 2:
            await ctx.reply(
                f"❓ Uso: `{COMMAND_PREFIX}persona avatar <url_da_imagem | semente_dicebear>`\n"
                f"• Exemplo URL: `{COMMAND_PREFIX}persona avatar https://i.imgur.com/exemplo.png`\n"
                f"• Exemplo Semente: `{COMMAND_PREFIX}persona avatar cyberpunk-bot`"
            )
            return
        arg_av = ctx.args[1].strip()
        if arg_av.startswith("http://") or arg_av.startswith("https://"):
            res = definir_avatar_canal(channel_id=channel_id, avatar_url=arg_av)
        else:
            res = definir_avatar_canal(channel_id=channel_id, avatar_seed=arg_av)
        await ctx.reply(res["mensagem"])
        return

    # Subcomando: identidade (Define nome, idade e bio)
    if sub in ("identidade", "perfil", "bio"):
        if len(ctx.args) < 2:
            await ctx.reply(
                f"❓ Uso: `{COMMAND_PREFIX}persona identidade <Nome> | <Idade> | <Biografia>`\n"
                f"• Exemplo: `{COMMAND_PREFIX}persona identidade Dra. Neusa | 54 anos | Contadora pericial experiente e cética.`"
            )
            return
        corpo = " ".join(ctx.args[1:]).strip()
        partes = [p.strip() for p in corpo.split("|")]
        nome_arg = partes[0] if len(partes) > 0 and partes[0] else None
        idade_arg = partes[1] if len(partes) > 1 and partes[1] else None
        bio_arg = partes[2] if len(partes) > 2 and partes[2] else None
        res = definir_identidade_canal(
            channel_id=channel_id,
            display_name=nome_arg,
            age=idade_arg,
            bio=bio_arg,
        )
        await ctx.reply(res["mensagem"])
        return

    # Subcomando: fixar / travar (Desativa a metamorfose automática)
    if sub in ("fixar", "travar", "lock", "congelar"):
        res = definir_trava_persona_canal(channel_id=channel_id, is_locked=True)
        await ctx.reply(res["mensagem"])
        return

    # Subcomando: destravar / desfixar (Ativa a metamorfose automática)
    if sub in ("destravar", "descongelar", "unlock", "adaptativo"):
        res = definir_trava_persona_canal(channel_id=channel_id, is_locked=False)
        await ctx.reply(res["mensagem"])
        return

    # Subcomando: metamorfose / evoluir (Força evolução adaptativa imediata baseada nas conversas)
    if sub in ("metamorfose", "evoluir", "metamorphosis", "adaptar", "mutar"):
        from persona_evolution_manager import persona_evolution_manager
        from ui_components import criar_view_metamorfose

        res_msg = await ctx.reply("🌀 *Extraindo frequência semântica e sintetizando nova metamorfose semanal...*")
        msg_obj = res_msg[0] if isinstance(res_msg, list) and res_msg else res_msg

        res_evol = await persona_evolution_manager.executar_metamorfose_canal(
            channel_id=channel_id,
            forcar=True,
            client=ctx.client,
        )

        if not res_evol.get("sucesso"):
            erro_txt = f"⚠️ Falha ao executar metamorfose: {res_evol.get('erro', 'Erro desconhecido.')}"
            if msg_obj and hasattr(msg_obj, "edit"):
                await msg_obj.edit(content=erro_txt)
            else:
                await ctx.reply(erro_txt)
            return

        embed_anuncio = res_evol["embed"]
        view_acoes = criar_view_metamorfose(channel_id=channel_id)
        if msg_obj and hasattr(msg_obj, "edit"):
            await msg_obj.edit(content=None, embed=embed_anuncio, view=view_acoes)
        else:
            await ctx.reply(embed=embed_anuncio, view=view_acoes)
        return

    # Subcomando: historico / album (Exibe encarnações passadas da persona do canal)
    if sub in ("historico", "album", "encarnacoes", "passadas"):
        from persona_evolution_manager import persona_evolution_manager
        historico = await persona_evolution_manager.obter_historico_metamorfoses(channel_id=channel_id)

        if not historico:
            await ctx.reply(
                "📜 **Álbum de Metamorfoses Vazio:**\n"
                "Este canal ainda não possui encarnações anteriores registradas.\n"
                f"Para disparar uma metamorfose de teste agora, use: `{COMMAND_PREFIX}persona metamorfose`."
            )
            return

        emb_hist = discord.Embed(
            title=f"🏛️ Álbum Histórico de Personas: #{channel_name}",
            description="Registro genealógico das encarnações passadas geradas pelas conversas do canal:",
            color=0x3498DB,
        )
        for idx, enc in enumerate(historico, start=1):
            nome_enc = enc.get("display_name") or "Antigravity"
            idade_enc = enc.get("age") or "Idade não registrada"
            bio_enc = enc.get("bio") or "Sem biografia"
            data_enc = enc.get("evolved_at", "")[:10]
            termos = ", ".join(f"`{t}`" for t in enc.get("top_terms", [])) or "Nenhum"
            emb_hist.add_field(
                name=f"{idx}. {nome_enc} ({idade_enc}) — {data_enc}",
                value=f"• *{bio_enc}*\n• **Termos frequentes:** {termos}",
                inline=False,
            )
        emb_hist.set_footer(text=f"Total de {len(historico)} encarnações arquivadas.")
        await ctx.reply(embed=emb_hist)
        return

    # 1. Visualizar personas disponíveis no catálogo com dropdown interativo
    if sub in ("lista", "listar", "disponiveis", "catalogo", "presets"):
        cat = ctx.args[1].lower() if len(ctx.args) > 1 else None
        personas_cat = listar_personas_disponiveis(categoria=cat)
        if not personas_cat:
            await ctx.reply("ℹ️ Nenhuma persona encontrada no catálogo.")
            return

        linhas = [f"🎭 **PERSONAS DISPONÍVEIS NO CATÁLOGO ({len(personas_cat)}):**\n"]
        for p in personas_cat:
            tag = "🌟 [Oficial]" if p["is_preset"] else "👤 [Custom]"
            linhas.append(
                f"• `{p['id']}` — **{p['nome']}** {tag} (temp: `{p['temperatura']}`)\n"
                f"  *{p['descricao']}*"
            )
        linhas.extend([
            f"\n💡 **Troca Rápida:** Selecione qualquer persona no dropdown interativo abaixo para ativá-la neste canal!",
            f"➕ **Para cadastrar uma nova persona:** `{COMMAND_PREFIX}persona salvar <id> <prompt de diretrizes>`",
        ])
        view_dropdown = criar_view_selecao_persona(
            channel_id=channel_id,
            author_id=ctx.author.id,
            guild_id=guild_id,
            channel_name=channel_name,
        )
        await ctx.reply("\n".join(linhas), view=view_dropdown)
        return

    # 2. Cadastrar / Incluir nova persona no catálogo
    if sub in ("salvar", "criar", "cadastrar", "add", "nova"):
        if len(ctx.args) < 3:
            await ctx.reply(
                f"❓ Formato incorreto. Use:\n"
                f"`{COMMAND_PREFIX}persona salvar <identificador> <diretrizes / system prompt>`\n\n"
                f"*Exemplo:* `{COMMAND_PREFIX}persona salvar arquiteto Você é um Arquiteto de Software Sênior focado em microsserviços, Clean Architecture e resiliência.`"
            )
            return

        slug = ctx.args[1].lower().strip()
        prompt_texto = " ".join(ctx.args[2:]).strip()
        nome_display = slug.replace("_", " ").title()
        desc_resumo = (prompt_texto[:110] + "...") if len(prompt_texto) > 110 else prompt_texto

        res = salvar_nova_persona(
            slug_id=slug,
            prompt=prompt_texto,
            nome=nome_display,
            descricao=desc_resumo,
            user_id=user_id,
        )
        if res.get("sucesso"):
            view_dropdown = criar_view_selecao_persona(
                channel_id=channel_id,
                author_id=ctx.author.id,
                guild_id=guild_id,
                channel_name=channel_name,
            )
            await ctx.reply(
                f"✅ Persona **{nome_display}** (`{slug}`) salva no catálogo!\n"
                f"Você pode ativá-la diretamente no dropdown abaixo ou digitar: `{COMMAND_PREFIX}persona canal aplicar {slug}`",
                view=view_dropdown,
            )
        else:
            await ctx.reply(f"❌ {res.get('mensagem', 'Falha ao salvar persona.')}")
        return

    # 3. Remover persona customizada do catálogo
    if sub in ("remover", "excluir", "del", "delete"):
        if len(ctx.args) < 2:
            await ctx.reply(f"❓ Informe o identificador da persona a remover. Exemplo: `{COMMAND_PREFIX}persona remover arquiteto`")
            return
        slug = ctx.args[1].lower().strip()
        res = remover_persona_catalogo(slug, user_id=user_id)
        await ctx.reply(res.get("mensagem", "Operação concluída."))
        return

    # 4. Listar canais com personas configuradas
    if sub in ("canais", "ativos"):
        personas = listar_personas_canais(guild_id=guild_id)
        if not personas:
            await ctx.reply("ℹ️ Nenhum canal possui persona customizada configurada no momento. O bot utiliza o assistente padrão em todos os canais.")
            return

        linhas = ["🎭 **CANAIS COM PERSONAS ATIVAS (IDEA-26):**\n"]
        for p in personas:
            mod_txt = f" | mod: `{p['model_override']}`" if p["model_override"] else ""
            linhas.append(f"• <#{p['channel_id']}> (temp: `{p['temperature']}`{mod_txt}):\n  *{p['prompt_preview']}*")
        await ctx.reply("\n".join(linhas))
        return

    # 5. Atalho direto para aplicar no canal atual: !persona aplicar <preset>
    if sub == "aplicar":
        if len(ctx.args) < 2:
            await ctx.reply(f"❓ Informe o identificador da persona. Exemplo: `{COMMAND_PREFIX}persona aplicar dev`")
            return
        if not is_admin:
            await ctx.reply("⛔ Apenas administradores do servidor podem alterar a persona deste canal.")
            return
        slug = ctx.args[1].lower().strip()
        res = aplicar_preset_canal(
            channel_id=channel_id,
            preset_slug=slug,
            user_id=user_id,
            guild_id=guild_id,
            channel_name=channel_name,
        )
        view_dropdown = criar_view_selecao_persona(
            channel_id=channel_id,
            author_id=ctx.author.id,
            guild_id=guild_id,
            channel_name=channel_name,
        )
        await ctx.reply(res["mensagem"], view=view_dropdown)
        return

    # 6. Comandos de canal: !persona canal ...
    if sub == "canal":
        if len(ctx.args) < 2:
            persona = obter_persona_canal(channel_id)
            view_dropdown = criar_view_selecao_persona(
                channel_id=channel_id,
                author_id=ctx.author.id,
                guild_id=guild_id,
                channel_name=channel_name,
            )
            if not persona:
                await ctx.reply(
                    f"ℹ️ Este canal não possui persona específica ativa (usa o assistente padrão).\n"
                    f"• Para aplicar uma persona do catálogo: `{COMMAND_PREFIX}persona canal aplicar <id>` (ex: `dev`, `cfo`)\n"
                    f"• Para definir prompt livre: `{COMMAND_PREFIX}persona canal <prompt>`\n"
                    f"• Para ver o catálogo: `{COMMAND_PREFIX}persona lista`\n"
                    f"💡 Ou utilize o menu dropdown interativo abaixo:",
                    view=view_dropdown,
                )
                return
            mod_txt = f" | **Modelo:** `{persona['model_override']}`" if persona["model_override"] else ""
            await ctx.reply(
                f"🎭 **Persona Ativa no Canal `{channel_name}`:**\n"
                f"• **Temperatura:** `{persona['temperature']}`{mod_txt}\n\n"
                f"**Instruções de Sistema:**\n```text\n{persona['system_prompt']}\n```",
                view=view_dropdown,
            )
            return

        acao = ctx.args[1].lower()

        if acao in ("ver", "show", "status"):
            persona = obter_persona_canal(channel_id)
            embed_status = _gerar_embed_status_persona(persona)
            view_dropdown = criar_view_selecao_persona(
                channel_id=channel_id,
                author_id=ctx.author.id,
                guild_id=guild_id,
                channel_name=channel_name,
            )
            await ctx.reply(embed=embed_status, view=view_dropdown)
            return

        if not is_admin:
            await ctx.reply("⛔ Apenas administradores do servidor podem alterar a persona deste canal.")
            return

        if acao in ("aplicar", "preset", "template"):
            if len(ctx.args) < 3:
                await ctx.reply(f"❓ Informe a persona a aplicar. Exemplo: `{COMMAND_PREFIX}persona canal aplicar dev` (Veja opções em `{COMMAND_PREFIX}persona lista`).")
                return
            slug = ctx.args[2].lower()
            res = aplicar_preset_canal(
                channel_id=channel_id,
                preset_slug=slug,
                user_id=user_id,
                guild_id=guild_id,
                channel_name=channel_name,
            )
            view_dropdown = criar_view_selecao_persona(
                channel_id=channel_id,
                author_id=ctx.author.id,
                guild_id=guild_id,
                channel_name=channel_name,
            )
            await ctx.reply(res["mensagem"], view=view_dropdown)
            return

        if acao in ("temp", "temperatura"):
            if len(ctx.args) < 3:
                await ctx.reply(f"❓ Informe um valor entre 0.0 e 1.0. Exemplo: `{COMMAND_PREFIX}persona canal temp 0.3`")
                return
            try:
                val = float(ctx.args[2])
                res = definir_temperatura_canal(channel_id, val)
                await ctx.reply(res["mensagem"])
            except ValueError:
                await ctx.reply("⚠️ O valor de temperatura deve ser um número decimal válido (ex: 0.3, 0.7).")
            return

        if acao in ("modelo", "model"):
            if len(ctx.args) < 3:
                await ctx.reply(f"❓ Informe o modelo ou provedor (ex: `local`, `gemini-flash`, `gemini-pro` ou `reset`).")
                return
            mod_arg = ctx.args[2].lower()
            mod_val = None if mod_arg in ("reset", "padrao", "default", "none") else mod_arg
            res = definir_modelo_canal(channel_id, mod_val)
            await ctx.reply(res["mensagem"])
            return

        if acao in ("reset", "limpar", "remover"):
            res = resetar_persona_canal(channel_id)
            view_dropdown = criar_view_selecao_persona(
                channel_id=channel_id,
                author_id=ctx.author.id,
                guild_id=guild_id,
                channel_name=channel_name,
            )
            await ctx.reply(res["mensagem"], view=view_dropdown)
            return

        # Caso contrário, o usuário digitou direto um prompt: !persona canal Você é um arquiteto...
        prompt_texto = " ".join(ctx.args[1:])
        res = definir_persona_canal(
            channel_id=channel_id,
            system_prompt=prompt_texto,
            user_id=user_id,
            guild_id=guild_id,
            channel_name=channel_name,
        )
        view_dropdown = criar_view_selecao_persona(
            channel_id=channel_id,
            author_id=ctx.author.id,
            guild_id=guild_id,
            channel_name=channel_name,
        )
        await ctx.reply(res["mensagem"], view=view_dropdown)
        return

    view_dropdown = criar_view_selecao_persona(
        channel_id=channel_id,
        author_id=ctx.author.id,
        guild_id=guild_id,
        channel_name=channel_name,
    )
    await ctx.reply(
        f"❓ Comando não reconhecido. Use:\n"
        f"• `{COMMAND_PREFIX}persona lista` — Lista personas disponíveis no catálogo\n"
        f"• `{COMMAND_PREFIX}persona salvar <id> <prompt>` — Cadastra nova persona no catálogo\n"
        f"• `{COMMAND_PREFIX}persona remover <id>` — Remove persona customizada do catálogo\n"
        f"• `{COMMAND_PREFIX}persona canal aplicar <id>` — Aplica persona ao canal atual\n"
        f"• `{COMMAND_PREFIX}persona canal ver` — Inspeciona persona deste canal\n"
        f"• `{COMMAND_PREFIX}persona canal reset` — Restaura assistente padrão no canal\n"
        f"• `{COMMAND_PREFIX}persona canais` — Lista canais com personas configuradas",
        view=view_dropdown,
    )

