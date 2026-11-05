"""
Processador Central de Mensagens e Ciclo de Conversação.

Orquestra o fluxo de entrada de mensagens do Discord:
1. Recepção e salvamento de anexos PDF em `discord/pdf/{user}/`.
2. Identificação e despacho de comandos com prefixo (!).
3. Gestão de contexto de usuário para ferramentas da LLM (Function Calling).
4. Persistência de histórico no SQLite.
5. Invocação assíncrona da LLM com entrega de arquivos PDF anexados sob demanda.
6. Divisão automática de mensagens longas (> 2000 caracteres).
"""

import logging
import unicodedata
import discord
from audio_manager import baixar_e_transcrever_anexo_audio, eh_anexo_audio
from commands import handle_command
from config import (
    COMMAND_PREFIX,
    DISCORD_USER,
    HISTORICO_LIMITE_PADRAO,
    LLM_TEMPERATURE,
    RAG_TOP_K,
    SYSTEM_PROMPT,
)
from context_manager import (
    add_pending_view,
    clear_pending_files,
    clear_pending_views,
    get_pending_files,
    get_pending_views,
    set_contexto_requisicao,
    set_current_user,
)
from database import (
    definir_modo_resposta,
    definir_preferencia_modelo,
    normalizar_modo_resposta,
    obter_historico,
    obter_modo_resposta,
    obter_preferencia_modelo,
    salvar_mensagem,
)
from llm_client import llm_client
from tts_manager import sintetizar_fala_edge
from pdf_manager import (
    formatar_tamanho,
    listar_pdfs_usuario,
    localizar_pdf_usuario,
    salvar_anexo_pdf,
    sanitizar_nome_usuario,
)
from tools import filtrar_ferramentas_relevantes
from utils import dividir_mensagem
from vector_db import buscar_memorias_relevantes, salvar_memoria_vetorial
from message_gateway import message_gateway, MessagePriority
from topic_manager import obter_topico_canal, adicionar_nota, buscar_notas_rag
from persona_manager import obter_persona_canal
from typing import Any, List, Optional

logger = logging.getLogger(__name__)


async def _send_gateway(
    target: Any,
    content: Optional[str] = None,
    embed: Optional[discord.Embed] = None,
    file: Optional[discord.File] = None,
    files: Optional[List[discord.File]] = None,
    view: Optional[discord.ui.View] = None,
) -> Any:
    """Despacha mensagem pelo Barramento Centralizado (IDEA-24) com Fast-Path prioritário (<100ms)."""
    return await message_gateway.dispatch(
        target,
        content=content,
        embed=embed,
        file=file,
        files=files,
        view=view,
        priority=MessagePriority.HIGH,
    )


def detectar_solicitacao_modelo(texto: str) -> Optional[str]:
    """Identifica se o usuário solicitou alternar o modelo/provedor de IA (local, google, auto) via chat."""
    if not texto:
        return None
    t = texto.lower().strip()
    t_clean = "".join(c for c in unicodedata.normalize("NFD", t) if unicodedata.category(c) != "Mn")

    termos_acao = ("trocar", "troque", "mudar", "mude", "usar", "use", "ativar", "ative", "coloque", "colocar", "quero", "voltar", "volte", "definir", "modo")
    tem_acao = any(a in t_clean for a in termos_acao)

    if not tem_acao:
        return None

    # 1. Solicitações para Google Gemini Pro (prioridade antes do Gemini Flash geral)
    if "gemini pro" in t_clean or "gemini-pro" in t_clean or "google pro" in t_clean:
        return "gemini-pro"

    # 2. Solicitações para Google Gemini
    if "gemini" in t_clean or "google" in t_clean or "nuvem" in t_clean or "cloud" in t_clean:
        return "google"

    # 3. Solicitações para LM Studio Local
    if "local" in t_clean or "lm studio" in t_clean or "lm-studio" in t_clean or "offline" in t_clean or "qwen" in t_clean:
        return "local"

    # 4. Solicitações para Modo Automático / Roteamento Inteligente
    if "auto" in t_clean or "automatico" in t_clean or "hibrido" in t_clean or "dinamico" in t_clean or "rotear" in t_clean:
        return "auto"

    return None




def detectar_solicitacao_modo_resposta(texto: str) -> Optional[str]:
    """Identifica se o usuário solicitou alternar o modo de resposta (texto/áudio/ambos) via chat."""
    t = (texto or "").lower().strip()
    t = "".join(c for c in unicodedata.normalize("NFD", t) if unicodedata.category(c) != "Mn")

    # 1. Solicitações para ambos (texto e áudio simultâneos)
    if any(p in t for p in (
        "texto e audio", "audio e texto", "texto e voz", "voz e texto",
        "ambos os modos", "ambas as opcoes", "duas opcoes", "nos dois formatos",
        "responder em texto e audio", "responda em texto e audio",
        "responder com texto e audio", "responda com texto e audio",
        "mudar para texto e audio", "mude para texto e audio",
        "mudar para ambos", "mude para ambos", "ativar ambos", "modo ambos"
    )):
        return "ambos"

    # 2. Solicitações para apenas áudio (voz)
    if any(p in t for p in (
        "responda em audio", "responda por audio", "responda com audio",
        "me responda em audio", "me responda por audio", "me responda com audio",
        "responder em audio", "responder por audio", "responder com audio",
        "mudar para audio", "mude para audio", "mudar pro audio", "mude pro audio",
        "ativar audio", "ativar voz", "quero em audio", "somente audio", "so audio", "apenas audio",
        "responda por voz", "responda em voz", "me responda por voz", "me responda em voz",
        "mudar para voz", "mude para voz", "modo audio", "modo de voz"
    )):
        return "audio"

    # 3. Solicitações para apenas texto
    if any(p in t for p in (
        "responda em texto", "responda por texto", "responda com texto",
        "me responda em texto", "me responda por texto", "me responda com texto",
        "responder em texto", "responder por texto", "responder com texto",
        "mudar para texto", "mude para texto", "mudar pro texto", "mude pro texto",
        "desativar audio", "desativar voz", "quero em texto", "somente texto", "so texto", "apenas texto",
        "modo texto", "parar audio", "sem audio", "sem voz"
    )):
        return "texto"

    return None


async def processar_mensagem(message: discord.Message, client: discord.Client) -> None:
    """Função principal que orquestra o ciclo de vida de cada mensagem recebida."""
    # 1. Ignora mensagens enviadas pelo próprio bot para prevenir loops
    if message.author == client.user:
        return

    # 2. Filtro opcional por ID de usuário (se configurado explicitamente no ambiente)
    if DISCORD_USER and str(DISCORD_USER).strip():
        # if str(message.author.id) != str(DISCORD_USER).strip():
        #     return
        pass

    transcricoes_audio = []

    # =========================================================================
    # RECONHECIMENTO DE ANEXOS (PDFS E ÁUDIOS/VOZ)
    # =========================================================================
    if message.attachments:
        for attachment in message.attachments:
            # 1. Verifica se é arquivo PDF
            eh_pdf = (
                attachment.filename.lower().endswith(".pdf")
                or (attachment.content_type and "pdf" in attachment.content_type.lower())
            )
            if eh_pdf:
                caminho_salvo, tamanho = await salvar_anexo_pdf(attachment, message.author)
                pasta_usuario = sanitizar_nome_usuario(message.author)

                # Fase 1: Pré-processamento leve na ingestão
                try:
                    from pdf_manager import pre_processar_pdf
                    dados_pdf = await pre_processar_pdf(caminho_salvo, message.author.id, message.author.name)
                    qtd_caps = len(dados_pdf.get("chapters", []))
                    total_pags = dados_pdf.get("total_pages", 0)
                    autor_str = dados_pdf.get("author", "Não informado")
                    titulo_str = dados_pdf.get("title", attachment.filename)
                    info_extra = (
                        f"• **Título:** {titulo_str}\n"
                        f"• **Autor:** {autor_str}\n"
                        f"• **Páginas:** {total_pags}\n"
                        f"• **Estrutura:** {qtd_caps} capítulo(s)/seção(ões) identificados\n"
                    )
                except Exception as e:
                    logger.warning("Falha no pré-processamento leve do PDF: %s", e)
                    info_extra = ""

                await _send_gateway(
                    message.channel,
                    content=(
                        f"📄 **Arquivo PDF recebido e catalogado com sucesso!**\n"
                        f"• **Arquivo:** `{attachment.filename}` ({formatar_tamanho(tamanho)})\n"
                        f"{info_extra}"
                        f"• **Destino:** `discord/pdf/{pasta_usuario}/`\n\n"
                        f"💡 *Comandos inteligentes disponíveis:*\n"
                        f"• `{COMMAND_PREFIX}pdf info {attachment.filename}` — Ficha e sinopse\n"
                        f"• `{COMMAND_PREFIX}pdf sumario {attachment.filename}` — Ver capítulos\n"
                        f"• `{COMMAND_PREFIX}pdf capitulo {attachment.filename} 1` — Resumo do capítulo\n"
                        f"• `{COMMAND_PREFIX}pdf indexar {attachment.filename}` — Iniciar RAG para perguntas\n"
                        f"• `{COMMAND_PREFIX}pdf perguntar {attachment.filename} <dúvida>` — Tirar dúvidas sobre a obra"
                    ),
                )
                continue

            # 2. Verifica se é Áudio ou Mensagem de Voz
            if eh_anexo_audio(attachment):
                async with message.channel.typing():
                    status_msg = await _send_gateway(message.channel, content="🎙️ *Ouvindo e transcrevendo áudio...*")
                    texto_transcrito, erro = await baixar_e_transcrever_anexo_audio(attachment)

                    if erro or not texto_transcrito:
                        if status_msg and hasattr(status_msg, "edit"):
                            await status_msg.edit(content="⚠️ *Não foi possível transcrever o áudio ou o arquivo está inaudível.*")
                    else:
                        if status_msg and hasattr(status_msg, "edit"):
                            await status_msg.edit(content=f"🎙️ **Áudio transcrito:** *\"{texto_transcrito}\"*")
                        transcricoes_audio.append(texto_transcrito)

    conteudo = (message.content or "").strip()

    # Se houve transcrição de áudio, integra ao conteúdo da mensagem
    if transcricoes_audio:
        texto_audio = " ".join(transcricoes_audio).strip()
        if conteudo:
            conteudo = f"{conteudo}\n{texto_audio}"
        else:
            conteudo = texto_audio

    # Se a mensagem não contiver texto nem transcrição, encerra o processamento
    if not conteudo:
        return

    # =========================================================================
    # INICIALIZAÇÃO DO CONTEXTO DE EXECUÇÃO
    # =========================================================================
    guild_id_str = str(message.guild.id) if message.guild else None
    channel_name_str = getattr(message.channel, "name", str(message.channel.id))
    set_contexto_requisicao(
        message.author.name,
        message.author.id,
        message.channel.id,
        guild_id=guild_id_str,
        channel_name=channel_name_str,
    )
    clear_pending_files()
    clear_pending_views()

    # =========================================================================
    # INTERCEPTAÇÃO DE COMANDOS COM PREFIXO (EX: !ajuda, !pdfs, !enviar)
    # =========================================================================
    if conteudo.startswith(COMMAND_PREFIX):
        foi_comando = await handle_command(message, client)
        if foi_comando:
            return

    # =========================================================================
    # SAUDAÇÕES RÁPIDAS
    # =========================================================================
    if conteudo.lower() == "hello bot":
        usuario = message.author.name
        await _send_gateway(message.channel, content=f"Hello {usuario}!")
        return

    # =========================================================================
    # RECONHECIMENTO DE ALTERAÇÃO DE MODO DE RESPOSTA VIA TEXTO NATURAL
    # =========================================================================
    modo_solicitado = detectar_solicitacao_modo_resposta(conteudo)
    if modo_solicitado:
        res = definir_modo_resposta(message.author.id, modo_solicitado)
        msg_confirmacao = f"🔊 {res['mensagem']}"
        if modo_solicitado in ("audio", "ambos"):
            caminho_audio, _ = await sintetizar_fala_edge(res["mensagem"])
            try:
                if caminho_audio and caminho_audio.exists():
                    await _send_gateway(
                        message.channel,
                        content=msg_confirmacao,
                        file=discord.File(str(caminho_audio), filename="resposta.mp3"),
                    )
                else:
                    await _send_gateway(message.channel, content=msg_confirmacao)
            finally:
                if caminho_audio and caminho_audio.exists():
                    caminho_audio.unlink()
        else:
            await _send_gateway(message.channel, content=msg_confirmacao)
        return

    # =========================================================================
    # RECONHECIMENTO DE ALTERAÇÃO DE MODELO LLM VIA TEXTO NATURAL
    # =========================================================================
    modelo_solicitado = detectar_solicitacao_modelo(conteudo)
    if modelo_solicitado:
        if modelo_solicitado in ("google", "gemini-pro") and not llm_client.tem_gemini_disponivel():
            msg_aviso_chave = (
                "⚠️ Para ativar o **Google Gemini**, é necessário configurar a sua `GEMINI_API_KEY`.\n"
                f"Você pode definir no arquivo `discord/.env` ou usar o comando:\n"
                f"`{COMMAND_PREFIX}modelo key <sua_chave_do_google>` (o bot apagará sua mensagem automaticamente para proteger sua chave)."
            )
            await _send_gateway(message.channel, content=msg_aviso_chave)
            return

        res_mod = definir_preferencia_modelo(message.author.id, message.author.name, modelo_solicitado)
        await _send_gateway(message.channel, content=f"🤖 {res_mod['mensagem']}")
        return


    # =========================================================================
    # RECUPERAÇÃO DE MEMÓRIAS PASSADAS E PERSISTÊNCIA DA MENSAGEM DO USUÁRIO
    # =========================================================================
    user_id = str(message.author.id)
    user_name = message.author.name
    channel_id = str(message.channel.id)

    # Identifica se o canal atual possui tópico temático vinculado (IDEA-25)
    topico_canal = obter_topico_canal(channel_id)
    persona_canal = obter_persona_canal(channel_id)

    # Verifica se a mensagem contém a flag --global para escapar do RAG isolado
    flag_global = "--global" in conteudo
    conteudo_limpo = conteudo.replace("--global", "").strip() if flag_global else conteudo

    # Modo Auto-Captura de Notas no Canal de Tópico (IDEA-25)
    if topico_canal and topico_canal.get("auto_capture_mode") and len(conteudo_limpo) >= 15:
        if not conteudo_limpo.endswith("?") and not conteudo_limpo.startswith(COMMAND_PREFIX):
            try:
                await adicionar_nota(
                    channel_id=channel_id,
                    conteudo=conteudo_limpo,
                    autor_id=user_id,
                    autor_nome=user_name,
                    tags=["auto_capture"],
                )
                try:
                    await message.add_reaction("📝")
                except Exception:
                    pass
            except Exception as e_ac:
                logger.warning("Falha na auto-captura de nota no canal %s: %s", channel_id, e_ac)

    # RAG Isolado vs Geral:
    notas_topico = []
    memorias_passadas = []

    if topico_canal:
        # Canal temático: Busca RAG nas notas isoladas do canal
        notas_topico = await buscar_notas_rag(channel_id, query=conteudo_limpo, top_k=RAG_TOP_K)
        # Se tiver --global, também recupera memórias do ChromaDB geral
        if flag_global:
            memorias_passadas = await buscar_memorias_relevantes(user_name, conteudo_limpo, top_k=RAG_TOP_K)
    else:
        # Canal comum / DM: Busca padrão no ChromaDB geral do usuário
        memorias_passadas = await buscar_memorias_relevantes(user_name, conteudo_limpo, top_k=RAG_TOP_K)

    # Persistência da mensagem do usuário:
    # Se estiver em canal de tópico, isola o histórico recente com channel_id
    if topico_canal:
        salvar_mensagem(user_id, "user", conteudo, channel_id=channel_id)
        if flag_global:
            await salvar_memoria_vetorial(user_name, "user", conteudo_limpo)
    else:
        salvar_mensagem(user_id, "user", conteudo)
        await salvar_memoria_vetorial(user_name, "user", conteudo)

    # =========================================================================
    # INFERÊNCIA LLM E PROCESSAMENTO CONVERSACIONAL
    # =========================================================================
    async with message.channel.typing():
        try:
            # Recupera histórico recente de conversa do SQLite (com isolamento por canal se for tópico)
            historico = obter_historico(
                user_id,
                limite=HISTORICO_LIMITE_PADRAO,
                channel_id=channel_id if topico_canal else None,
            )

            # Monta System Prompt único (modelos modernos no LM Studio exigem no máximo 1 system message e no início)
            partes_system = [SYSTEM_PROMPT]

            # Injeção da Persona do Canal (IDEA-26) - Camada 2
            if persona_canal and persona_canal.get("system_prompt"):
                nome_p = persona_canal.get("persona_id") or "personalizada"
                prompt_persona = (
                    f"[DIRETRIZES DA PERSONA DESTE CANAL - '{nome_p.upper()}']:\n"
                    f"{persona_canal['system_prompt']}"
                )
                partes_system.append(prompt_persona)

            # Injeção das Notas Temáticas Isoladas do Canal (IDEA-25)
            if notas_topico:
                bloco_notas = []
                for n in notas_topico:
                    tags_str = f" [tags: {n['tags']}]" if n.get("tags") else ""
                    bloco_notas.append(f"• [Nota #{n['id']}]{tags_str}: {n['conteudo']}")

                prompt_notas = (
                    f"[BASE DE CONHECIMENTO TEMÁTICA DO CANAL ({topico_canal.get('topic_name', 'Tópico')}) - RAG ISOLADO]:\n"
                    "As seguintes notas foram recuperadas por similaridade temática com a mensagem atual. "
                    "Elas constituem a fonte primária e contexto exclusivo deste canal. "
                    "Responda fundamentando-se nestas informações:\n"
                    + "\n".join(bloco_notas)
                )
                partes_system.append(prompt_notas)

            # Injeta contexto RAG de memórias semânticas de longo prazo gerais (se houver e não duplicar histórico)
            if memorias_passadas:
                textos_historico_imediato = {h["content"].strip() for h in historico if "content" in h and h["content"]}
                bloco_rag = []
                for mem in memorias_passadas:
                    # Filtra para evitar duplicar o que já está nas mensagens recentes do SQLite
                    if mem.get("conteudo", "").strip() not in textos_historico_imediato:
                        papel = "Usuário" if mem.get("role") == "user" else "Assistente"
                        bloco_rag.append(f"• ({papel}): {mem['conteudo']}")

                if bloco_rag:
                    prompt_rag = (
                        "[MEMÓRIA SEMÂNTICA GERAL DO USUÁRIO]:\n"
                        "As seguintes mensagens de conversas passadas foram recuperadas por similaridade "
                        "com a solicitação atual. Utilize estas informações para lembrar fatos ou contexto anterior:\n"
                        + "\n".join(bloco_rag)
                    )
                    partes_system.append(prompt_rag)

            # Define rigorosamente UMA ÚNICA mensagem de sistema no índice 0
            mensagens_para_llm = [
                {"role": "system", "content": "\n\n".join(partes_system)}
            ]

            # Adiciona o histórico conversacional recente (apenas papéis user e assistant)
            for h in historico:
                if h.get("role") in ("user", "assistant") and h.get("content"):
                    mensagens_para_llm.append({"role": h["role"], "content": h["content"]})

            # Seleciona semanticamente apenas as ferramentas mais relevantes para a mensagem (Tool RAG)
            ferramentas_selecionadas = await filtrar_ferramentas_relevantes(conteudo_limpo)

            # Parâmetros de inferência (temperatura e modelo) com suporte a overrides da Persona (IDEA-26)
            temperatura = LLM_TEMPERATURE
            prov_alvo = None
            mod_alvo = None

            if persona_canal:
                if persona_canal.get("temperature") is not None:
                    try:
                        temperatura = float(persona_canal["temperature"])
                    except (ValueError, TypeError):
                        pass

                override_m = persona_canal.get("model_override")
                if override_m:
                    if override_m == "local":
                        prov_alvo = "local"
                        mod_alvo = llm_client.local_model
                    elif override_m in ("gemini-flash", "google"):
                        prov_alvo = "google"
                        mod_alvo = llm_client.gemini_flash_model
                    elif override_m == "gemini-pro":
                        prov_alvo = "google"
                        mod_alvo = llm_client.gemini_pro_model

            # Se não houver override de modelo na persona do canal, usa a preferência do usuário
            if not prov_alvo:
                pref_modelo = obter_preferencia_modelo(user_id)
                prov_alvo = pref_modelo.get("provider", "local")
                mod_alvo = pref_modelo.get("model_name")
                failover_ativo = pref_modelo.get("auto_failover", True)
            else:
                failover_ativo = True

            # Gera resposta da LLM de forma assíncrona (não-bloqueante) com roteamento híbrido
            resposta_texto = await llm_client.gerar_resposta(
                mensagens_para_llm,
                tools=ferramentas_selecionadas,
                temperatura=temperatura,
                provider=prov_alvo,
                model=mod_alvo,
                permitir_failover=failover_ativo,
                incluir_badge=True,
            )

            # Salva a resposta gerada no banco SQLite e no ChromaDB
            if resposta_texto and resposta_texto.strip():
                if topico_canal:
                    salvar_mensagem(user_id, "assistant", resposta_texto, channel_id=channel_id)
                    if flag_global:
                        await salvar_memoria_vetorial(user_name, "assistant", resposta_texto)
                else:
                    salvar_mensagem(user_id, "assistant", resposta_texto)
                    await salvar_memoria_vetorial(user_name, "assistant", resposta_texto)

            # Divide e prepara mensagens respeitando o limite do Discord
            chunks = dividir_mensagem(resposta_texto)
            if not chunks:
                chunks = ["*O assistente não gerou conteúdo de texto.*"]

            # =================================================================
            # ENTREGA DE RESPOSTA CONFORME A PREFERÊNCIA (TEXTO / ÁUDIO / AMBOS)
            # =================================================================
            modo_resposta = obter_modo_resposta(user_id)
            caminho_audio = None

            views_pendentes = get_pending_views(user_name)
            view_to_attach = views_pendentes.pop(0) if views_pendentes else None

            try:
                if modo_resposta == "texto":
                    # Opção 1: Apenas Texto
                    for idx, chunk in enumerate(chunks):
                        v = view_to_attach if idx == len(chunks) - 1 else None
                        await _send_gateway(message.channel, content=chunk, view=v)

                elif modo_resposta == "audio":
                    # Opção 2: Apenas Áudio (Francisca pt-BR via edge-tts)
                    caminho_audio, erro_tts = await sintetizar_fala_edge(resposta_texto)
                    if caminho_audio and caminho_audio.exists():
                        await _send_gateway(
                            message.channel,
                            content="🎙️ **Resposta em áudio (Francisca):**",
                            file=discord.File(str(caminho_audio), filename="resposta.mp3"),
                            view=view_to_attach,
                        )
                    else:
                        logger.warning("Falha na síntese de áudio: %s. Enviando texto como fallback.", erro_tts)
                        for idx, chunk in enumerate(chunks):
                            v = view_to_attach if idx == len(chunks) - 1 else None
                            await _send_gateway(message.channel, content=chunk, view=v)

                elif modo_resposta == "ambos":
                    # Opção 3: Texto e Áudio Simultâneos
                    for idx, chunk in enumerate(chunks):
                        v = view_to_attach if idx == len(chunks) - 1 else None
                        await _send_gateway(message.channel, content=chunk, view=v)

                    caminho_audio, erro_tts = await sintetizar_fala_edge(resposta_texto)
                    if caminho_audio and caminho_audio.exists():
                        await _send_gateway(
                            message.channel,
                            content="🎙️ **Narração em áudio (Francisca):**",
                            file=discord.File(str(caminho_audio), filename="resposta.mp3"),
                        )
                    else:
                        logger.warning("Falha na síntese de áudio para modo ambos: %s", erro_tts)

            finally:
                # REGRA CRÍTICA: Apaga arquivos temporários imediatamente
                if caminho_audio and caminho_audio.exists():
                    try:
                        caminho_audio.unlink()
                        logger.info("Arquivo temporário de resposta TTS removido: %s", caminho_audio)
                    except Exception as ex_del:
                        logger.warning("Falha ao remover arquivo temporário TTS %s: %s", caminho_audio, ex_del)

            # =================================================================
            # ENTREGA DE ARQUIVOS PDF AGENDADOS PELAS TOOLS
            # =================================================================
            arquivos_pendentes = get_pending_files()
            for arq_path in arquivos_pendentes:
                if arq_path.exists():
                    await _send_gateway(
                        message.channel,
                        content=f"📥 **Aqui está o seu PDF solicitado:** `{arq_path.name}`",
                        file=discord.File(str(arq_path), filename=arq_path.name),
                    )

        except ConnectionError as ce:
            logger.error("Erro de conexão com o LM Studio: %s", ce)

            # Fallback inteligente: se o usuário pediu lista ou envio de PDFs e o LM Studio está offline
            conteudo_lower = conteudo.lower()
            if any(termo in conteudo_lower for termo in ["quais pdf", "listar pdf", "meus pdf", "tem pdf", "pdfs disponiveis"]):
                arquivos = listar_pdfs_usuario(message.author)
                if not arquivos:
                    await _send_gateway(
                        message.channel,
                        content=f"📂 Sua pasta de PDFs (`pdf/{sanitizar_nome_usuario(message.author)}/`) está vazia no momento.",
                    )
                else:
                    linhas = [f"📚 **Seus Arquivos PDF Disponíveis ({len(arquivos)}):**"]
                    for idx, arq in enumerate(arquivos, start=1):
                        linhas.append(f"• `{arq['nome']}` — {arq['tamanho_formatado']}")
                    linhas.append(f"\n*(Respondido via fallback local. LM Studio indisponível)*")
                    await _send_gateway(message.channel, content="\n".join(linhas))
                return

            if any(termo in conteudo_lower for termo in ["envia", "manda", "disponibiliza", "devolve", "baixar"]) and "pdf" in conteudo_lower:
                # Tenta localizar por termos
                palavras = [p for p in conteudo_lower.replace(",", " ").replace(".", " ").split() if p not in ["me", "o", "a", "por", "favor", "envia", "manda", "disponibiliza", "pdf", "para", "mim", "devolve"]]
                termo_busca = " ".join(palavras) if palavras else ""
                caminho = localizar_pdf_usuario(message.author, termo_busca)
                if caminho and caminho.exists():
                    await _send_gateway(
                        message.channel,
                        content=f"📥 **Aqui está o seu PDF solicitado (fallback direto):** `{caminho.name}`",
                        file=discord.File(str(caminho), filename=caminho.name),
                    )
                    return

            await _send_gateway(message.channel, content=f"⚠️ **Erro de Conexão com LM Studio:**\n{ce}")

        except Exception as e:
            logger.exception("Erro inesperado no processamento da mensagem: %s", e)
            await _send_gateway(message.channel, content=f"⚠️ **Ocorreu um erro ao processar sua solicitação:** `{str(e)}`")

        finally:
            # Garante que as filas de anexos e views sejam sempre resetadas para a próxima mensagem
            clear_pending_files(user_name)
            clear_pending_views(user_name)
