"""
Módulo de Componentes Visuais e Interativos do Discord (Discord UI).

Implementa a especificação IDEA-08:
1. InteractiveListView: Botões dinâmicos de checkbox para listas de compras/tarefas,
   botão de limpeza de concluídos e modal nativo para adição rápida de novos itens.
2. ReminderActionView: Botões de ação imediata em lembretes ativos (Concluir, +10min, +1h, Amanhã).
3. PDFChapterSelectView: Select Menu dropdown para navegação rápida e resumo de capítulos de livros/PDFs.
"""

import logging
from typing import Any, Dict, List, Optional
import discord
from config import DISCORD_UI_COMPONENTS_ENABLED, DISCORD_UI_TIMEOUT_SECONDS
import list_manager
import reminder_manager

logger = logging.getLogger(__name__)


# ==============================================================================
# MODAL PARA ADICIONAR ITENS À LISTA
# ==============================================================================

class AddItemModal(discord.ui.Modal):
    """Modal nativo do Discord para inclusão rápida de itens na lista."""

    def __init__(self, user_id: str, nome_lista: str, parent_view: "InteractiveListView"):
        super().__init__(title=f"Adicionar à lista: {nome_lista[:20]}")
        self.user_id = user_id
        self.nome_lista = nome_lista
        self.parent_view = parent_view

        self.item_input = discord.ui.TextInput(
            label="Nome do Item / Quantidade",
            placeholder="Ex: 2kg de maçã, Café em pó, Detergente...",
            required=True,
            min_length=1,
            max_length=100,
            style=discord.TextStyle.short,
        )
        self.add_item(self.item_input)

    async def on_submit(self, interaction: discord.Interaction):
        item_texto = self.item_input.value.strip()
        if not item_texto:
            await interaction.response.send_message("❌ O texto do item não pode estar vazio.", ephemeral=True)
            return

        res = list_manager.adicionar_item_lista(self.user_id, self.nome_lista, item_texto)
        if res.get("sucesso"):
            await self.parent_view.atualizar_mensagem(interaction)
        else:
            await interaction.response.send_message(f"⚠️ {res.get('mensagem')}", ephemeral=True)


# ==============================================================================
# VIEW DE LISTAS INTERATIVAS (CHECKBOXES, LIMPAR, NOVO ITEM)
# ==============================================================================

class InteractiveListView(discord.ui.View):
    """View interativa para gerenciamento visual de listas (compras, mercado, tarefas)."""

    def __init__(
        self,
        user_id: str,
        nome_lista: str,
        author_id: int,
        timeout: Optional[int] = None,
    ):
        segundos = timeout or DISCORD_UI_TIMEOUT_SECONDS
        super().__init__(timeout=segundos)
        self.user_id = user_id
        self.nome_lista = list_manager.sanitizar_nome_lista(nome_lista)
        self.author_id = author_id
        self.message: Optional[discord.Message] = None
        self._reconstruir_componentes()

    def _obter_dados_atualizados(self) -> Dict[str, Any]:
        return list_manager.obter_itens_lista(self.user_id, self.nome_lista)

    def _reconstruir_componentes(self):
        """Reconstrói dinamicamente os botões da View com base no estado atual do SQLite."""
        self.clear_items()
        dados = self._obter_dados_atualizados()
        itens: List[Dict[str, Any]] = dados.get("itens", [])

        # 1. Botões para os primeiros itens pendentes (limite de 10 botões para caber em Action Rows)
        pendentes = [it for it in itens if not it["concluido"]][:10]
        for it in pendentes:
            item_id = it["id"]
            texto = it["texto"]
            rotulo = f"☐ {texto}" if len(texto) <= 25 else f"☐ {texto[:22]}..."
            btn = discord.ui.Button(
                label=rotulo,
                style=discord.ButtonStyle.secondary,
                custom_id=f"list_toggle_{item_id}",
                row=0 if len(self.children) < 5 else 1,
            )
            btn.callback = self._criar_callback_toggle(item_id)
            self.add_item(btn)

        # 2. Botão Limpar Concluídos
        tem_concluidos = any(it["concluido"] for it in itens)
        btn_limpar = discord.ui.Button(
            label="🧹 Limpar Concluídos",
            style=discord.ButtonStyle.danger if tem_concluidos else discord.ButtonStyle.secondary,
            disabled=not tem_concluidos,
            custom_id="list_btn_clean",
            row=2,
        )
        btn_limpar.callback = self._callback_limpar
        self.add_item(btn_limpar)

        # 3. Botão Adicionar Item
        btn_add = discord.ui.Button(
            label="➕ Novo Item",
            style=discord.ButtonStyle.success,
            custom_id="list_btn_add",
            row=2,
        )
        btn_add.callback = self._callback_add
        self.add_item(btn_add)

        # 4. Botão Atualizar
        btn_refresh = discord.ui.Button(
            label="🔄 Atualizar",
            style=discord.ButtonStyle.primary,
            custom_id="list_btn_refresh",
            row=2,
        )
        btn_refresh.callback = self._callback_refresh
        self.add_item(btn_refresh)

    def _criar_callback_toggle(self, item_id: int):
        async def callback(interaction: discord.Interaction):
            if interaction.user.id != self.author_id:
                await interaction.response.send_message("⛔ Apenas o dono desta lista pode marcá-la.", ephemeral=True)
                return
            list_manager.ticar_item_lista(self.user_id, self.nome_lista, item_id)
            await self.atualizar_mensagem(interaction)
        return callback

    async def _callback_limpar(self, interaction: discord.Interaction):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("⛔ Apenas o dono desta lista pode limpá-la.", ephemeral=True)
            return
        list_manager.limpar_itens_concluidos(self.user_id, self.nome_lista)
        await self.atualizar_mensagem(interaction)

    async def _callback_add(self, interaction: discord.Interaction):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("⛔ Apenas o dono desta lista pode adicionar itens nela.", ephemeral=True)
            return
        modal = AddItemModal(self.user_id, self.nome_lista, self)
        await interaction.response.send_modal(modal)

    async def _callback_refresh(self, interaction: discord.Interaction):
        await self.atualizar_mensagem(interaction)

    async def atualizar_mensagem(self, interaction: discord.Interaction):
        """Atualiza a mensagem no Discord com a lista renderizada e os botões reconstruídos."""
        self._reconstruir_componentes()
        dados = self._obter_dados_atualizados()
        novo_conteudo = list_manager.formatar_lista_para_exibicao(dados)

        try:
            if interaction.response.is_done():
                alvo_msg = self.message or getattr(interaction, "message", None)
                if alvo_msg:
                    await alvo_msg.edit(content=novo_conteudo, view=self)
                elif hasattr(interaction, "followup"):
                    await interaction.followup.edit_message(message_id=interaction.message.id, content=novo_conteudo, view=self)
            else:
                await interaction.response.edit_message(content=novo_conteudo, view=self)
        except Exception as err:
            logger.warning("Falha ao atualizar mensagem interativa da lista: %s", err)

    async def on_timeout(self):
        """Desativa os botões quando a View expira por inatividade."""
        for child in self.children:
            child.disabled = True
        try:
            if self.message:
                await self.message.edit(view=self)
        except Exception:
            pass


# ==============================================================================
# VIEW DE AÇÕES DE LEMBRETES (CONCLUÍDO, ADIAR 10M, 1H, AMANHÃ)
# ==============================================================================

class ReminderActionView(discord.ui.View):
    """View anexada em notificações de lembretes ativos para resolução com 1 clique."""

    def __init__(
        self,
        lembrete_id: int,
        user_id: str,
        author_id: int,
        timeout: Optional[int] = None,
    ):
        segundos = timeout or DISCORD_UI_TIMEOUT_SECONDS
        super().__init__(timeout=segundos)
        self.lembrete_id = lembrete_id
        self.user_id = user_id
        self.author_id = author_id
        self.message: Optional[discord.Message] = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if self.author_id and interaction.user.id != self.author_id:
            await interaction.response.send_message("⛔ Apenas a pessoa mencionada neste lembrete pode interagir com ele.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="✅ Concluído", style=discord.ButtonStyle.success, custom_id="rem_btn_done")
    async def btn_concluido(self, interaction: discord.Interaction, button: discord.ui.Button):
        res = reminder_manager.concluir_lembrete(self.lembrete_id, self.user_id)
        for child in self.children:
            child.disabled = True
        msg_original = interaction.message.content if interaction.message else ""
        novo_texto = f"{msg_original}\n\n✅ **Lembrete concluído!**"
        await interaction.response.edit_message(content=novo_texto, view=self)

    @discord.ui.button(label="⏱️ +10 min", style=discord.ButtonStyle.primary, custom_id="rem_btn_10m")
    async def btn_adiar_10m(self, interaction: discord.Interaction, button: discord.ui.Button):
        res = reminder_manager.adiar_lembrete(self.lembrete_id, minutos=10, user_id=self.user_id)
        for child in self.children:
            child.disabled = True
        msg_original = interaction.message.content if interaction.message else ""
        novo_texto = f"{msg_original}\n\n⏱️ **Adiado por 10 minutos** (avisarei novamente às {res.get('remind_at')})."
        await interaction.response.edit_message(content=novo_texto, view=self)

    @discord.ui.button(label="🔁 +1 hora", style=discord.ButtonStyle.secondary, custom_id="rem_btn_1h")
    async def btn_adiar_1h(self, interaction: discord.Interaction, button: discord.ui.Button):
        res = reminder_manager.adiar_lembrete(self.lembrete_id, minutos=60, user_id=self.user_id)
        for child in self.children:
            child.disabled = True
        msg_original = interaction.message.content if interaction.message else ""
        novo_texto = f"{msg_original}\n\n🔁 **Adiado por 1 hora** (avisarei novamente às {res.get('remind_at')})."
        await interaction.response.edit_message(content=novo_texto, view=self)

    @discord.ui.button(label="📅 Amanhã", style=discord.ButtonStyle.secondary, custom_id="rem_btn_tomorrow")
    async def btn_adiar_amanha(self, interaction: discord.Interaction, button: discord.ui.Button):
        res = reminder_manager.adiar_lembrete(self.lembrete_id, minutos=1440, user_id=self.user_id)
        for child in self.children:
            child.disabled = True
        msg_original = interaction.message.content if interaction.message else ""
        novo_texto = f"{msg_original}\n\n📅 **Adiado para amanhã** (avisarei novamente às {res.get('remind_at')})."
        await interaction.response.edit_message(content=novo_texto, view=self)

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        try:
            if self.message:
                await self.message.edit(view=self)
        except Exception:
            pass


# ==============================================================================
# VIEW DE NAVEGAÇÃO DE CAPÍTULOS DE LIVROS / PDFS (SELECT MENU DROPDOWN)
# ==============================================================================

class PDFChapterSelect(discord.ui.Select):
    """Dropdown SelectMenu nativo para escolha de capítulos indexados."""

    def __init__(self, author: Any, doc_name: str, capitulos: List[Dict[str, Any]]):
        self.author = author
        self.doc_name = doc_name
        self.capitulos = capitulos

        # Limite máximo de 25 opções imposto pela Discord API
        opcoes = []
        for cap in capitulos[:25]:
            idx = cap.get("chapter_index", 0)
            titulo = (cap.get("title") or f"Capítulo {idx}").strip()
            rotulo = f"Cap. {idx}: {titulo}" if len(f"Cap. {idx}: {titulo}") <= 100 else f"Cap. {idx}: {titulo[:90]}..."
            pag = cap.get("start_page", 1)
            desc = f"Inicia na página {pag}"[:100]
            opcoes.append(
                discord.SelectOption(
                    label=rotulo,
                    value=str(idx),
                    description=desc,
                    emoji="📖",
                )
            )

        if not opcoes:
            opcoes.append(discord.SelectOption(label="Nenhum capítulo catalogado", value="0"))

        super().__init__(
            placeholder="📖 Selecione um capítulo para ver o resumo...",
            min_values=1,
            max_values=1,
            options=opcoes,
            custom_id="pdf_select_chapter",
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=False)
        cap_id = self.values[0]

        from pdf_manager import resumir_capitulo_documento
        res = await resumir_capitulo_documento(self.author, self.doc_name, cap_id)
        if not res.get("sucesso"):
            await interaction.followup.send(f"⚠️ {res.get('mensagem')}")
            return

        texto_resposta = res["resposta_formatada"]
        from utils import dividir_mensagem
        blocos = dividir_mensagem(texto_resposta, limite=1900)
        for bloco in blocos:
            await interaction.followup.send(bloco)


class PDFChapterSelectView(discord.ui.View):
    """View contendo o SelectMenu de capítulos de um livro/PDF."""

    def __init__(
        self,
        author: Any,
        doc_name: str,
        capitulos: List[Dict[str, Any]],
        timeout: Optional[int] = None,
    ):
        segundos = timeout or DISCORD_UI_TIMEOUT_SECONDS
        super().__init__(timeout=segundos)
        self.author = author
        self.doc_name = doc_name
        self.message: Optional[discord.Message] = None

        if capitulos:
            self.add_item(PDFChapterSelect(author, doc_name, capitulos))

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        try:
            if self.message:
                await self.message.edit(view=self)
        except Exception:
            pass


# ==============================================================================
# VIEW DE SELEÇÃO RÁPIDA DE PERSONAS (DROPDOWN / SELECT MENU) — IDEA-26
# ==============================================================================

class PersonaSelect(discord.ui.Select):
    """Dropdown SelectMenu para visualização e troca rápida de personas cognitivas por canal."""

    def __init__(
        self,
        channel_id: str | int,
        author_id: int | str,
        personas: List[Dict[str, Any]],
        guild_id: Optional[str | int] = None,
        channel_name: Optional[str] = None,
        persona_ativa_slug: Optional[str] = None,
    ):
        self.channel_id = str(channel_id)
        self.author_id = str(author_id)
        self.guild_id = str(guild_id) if guild_id else None
        self.channel_name = channel_name or str(channel_id)
        self.personas = personas

        opcoes: List[discord.SelectOption] = []

        # 1. Opção para restaurar o assistente padrão
        is_padrao_ativo = persona_ativa_slug is None or persona_ativa_slug in ("padrao", "")
        opcoes.append(
            discord.SelectOption(
                label="Assistente Padrão (Sem Persona)",
                value="__reset__",
                description="Restaura o tom, diretrizes e modelo padrão do assistente.",
                emoji="🔄",
                default=is_padrao_ativo,
            )
        )

        emojis_preset = {
            "dev": "💻",
            "cfo": "📊",
            "direto": "🎯",
            "revisor": "✍️",
            "socrates": "🏛️",
            "tributarista": "⚖️",
        }

        # 2. Adiciona personas do catálogo (máximo 24 para respeitar limite de 25 do Discord)
        for p in personas[:24]:
            slug = p["id"]
            if slug == "padrao":
                continue

            nome = p["nome"][:90]
            desc = (p.get("descricao") or f"Temperatura: {p.get('temperatura', 0.7)}")[:95]
            emoji = emojis_preset.get(slug, "🌟" if p.get("is_preset") else "👤")
            is_default = (persona_ativa_slug == slug)

            opcoes.append(
                discord.SelectOption(
                    label=nome,
                    value=slug,
                    description=desc,
                    emoji=emoji,
                    default=is_default,
                )
            )

        super().__init__(
            placeholder="🎭 Escolha uma persona para este canal...",
            min_values=1,
            max_values=1,
            options=opcoes,
            custom_id=f"select_persona_{channel_id}",
        )

    async def callback(self, interaction: discord.Interaction):
        import os
        from persona_manager import aplicar_preset_canal, resetar_persona_canal

        # Verifica permissão do usuário
        user_id_str = str(interaction.user.id)
        is_admin = True
        if interaction.guild is not None:
            perms = getattr(interaction.user, "guild_permissions", None)
            is_admin = bool(
                getattr(perms, "administrator", False)
                or getattr(perms, "manage_channels", False)
                or user_id_str == os.getenv("DISCORD_USER", "")
                or user_id_str == self.author_id
            )

        if not is_admin:
            await interaction.response.send_message(
                "⛔ Apenas administradores do servidor podem alterar a persona deste canal.",
                ephemeral=True,
            )
            return

        escolha = self.values[0]

        if escolha == "__reset__":
            resetar_persona_canal(self.channel_id)
            for opt in self.options:
                opt.default = (opt.value == "__reset__")

            msg_confirmacao = (
                f"🔄 **Assistente Padrão Restaurado!**\n"
                f"O canal **#{self.channel_name}** agora responde como o assistente padrão sem overrides cognitivos."
            )
            try:
                await interaction.response.edit_message(content=msg_confirmacao, view=self.view)
            except Exception:
                await interaction.response.send_message(msg_confirmacao, ephemeral=False)
            return

        # Aplica preset / persona selecionada
        res = aplicar_preset_canal(
            channel_id=self.channel_id,
            preset_slug=escolha,
            user_id=user_id_str,
            guild_id=self.guild_id,
            channel_name=self.channel_name,
        )

        p_info = next((p for p in self.personas if p["id"] == escolha), None)
        nome_display = p_info["nome"] if p_info else escolha.title()
        temp_display = p_info["temperatura"] if p_info else 0.7

        for opt in self.options:
            opt.default = (opt.value == escolha)

        msg_confirmacao = (
            f"🎭 **Persona Ativada com Sucesso!**\n"
            f"O canal **#{self.channel_name}** agora está operando como **{nome_display}** (`{escolha}`).\n"
            f"🌡️ **Temperatura:** `{temp_display}` | Todas as respostas neste canal seguirão este perfil cognitivo."
        )

        try:
            await interaction.response.edit_message(content=msg_confirmacao, view=self.view)
        except Exception:
            await interaction.response.send_message(msg_confirmacao, ephemeral=False)


class PersonaSelectView(discord.ui.View):
    """View contendo o SelectMenu dropdown de seleção de persona."""

    def __init__(
        self,
        channel_id: str | int,
        author_id: int | str,
        guild_id: Optional[str | int] = None,
        channel_name: Optional[str] = None,
        timeout: Optional[int] = None,
    ):
        segundos = timeout or DISCORD_UI_TIMEOUT_SECONDS
        super().__init__(timeout=segundos)
        self.channel_id = str(channel_id)
        self.author_id = str(author_id)
        self.guild_id = str(guild_id) if guild_id else None
        self.channel_name = channel_name or str(channel_id)
        self.message: Optional[discord.Message] = None

        from persona_manager import listar_personas_disponiveis, obter_persona_canal
        personas = listar_personas_disponiveis()
        p_ativa = obter_persona_canal(self.channel_id)
        slug_ativo = p_ativa.get("persona_slug") if p_ativa else None

        self.add_item(
            PersonaSelect(
                channel_id=self.channel_id,
                author_id=self.author_id,
                personas=personas,
                guild_id=self.guild_id,
                channel_name=self.channel_name,
                persona_ativa_slug=slug_ativo,
            )
        )

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        try:
            if self.message:
                await self.message.edit(view=self)
        except Exception:
            pass


def criar_view_selecao_persona(
    channel_id: str | int,
    author_id: int | str,
    guild_id: Optional[str | int] = None,
    channel_name: Optional[str] = None,
) -> Optional[PersonaSelectView]:
    """Cria e retorna a PersonaSelectView com dropdown interativo se a UI estiver habilitada."""
    if not DISCORD_UI_COMPONENTS_ENABLED:
        return None
    try:
        return PersonaSelectView(
            channel_id=channel_id,
            author_id=author_id,
            guild_id=guild_id,
            channel_name=channel_name,
        )
    except Exception as e:
        logger.warning("Falha ao instanciar PersonaSelectView: %s", e)
        return None
