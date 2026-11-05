"""
Comandos Embutidos do Bot (!ajuda, !ping, !limpar, !historico, !hora, !modelo, !status).

Implementações de comandos de controle, diagnóstico e utilidades para o usuário.
"""

import logging

import discord
from commands.registry import CommandContext, register_command, registry
from config import COMMAND_PREFIX, DISCORD_UI_COMPONENTS_ENABLED, LM_STUDIO_URL, MODELO_LLM
from ui_components import InteractiveListView, PDFChapterSelectView
from database import (
    contar_mensagens,
    definir_modo_resposta,
    limpar_historico,
    obter_historico,
    obter_modo_resposta,
)
from digest_manager import (
    atualizar_configuracao_digest,
    enviar_resumo_matinal,
    obter_configuracao_digest,
)
from google_calendar import (
    adicionar_compromisso,
    listar_compromissos,
    remover_compromisso,
    verificar_status_autenticacao,
)
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
from tts_manager import sintetizar_fala_edge
from reminder_manager import (
    cancelar_lembrete,
    criar_lembrete,
    interpretar_expressao_tempo,
    listar_lembretes_usuario,
)
from utils import formatar_bloco_codigo, obter_hora_formatada
from vector_db import buscar_memorias_relevantes, contar_memorias, limpar_memoria_vetorial

logger = logging.getLogger(__name__)


@register_command(
    name="ajuda",
    description="Exibe a central de ajuda em 2 etapas (visão geral ou módulos detalhados).",
    usage=f"{COMMAND_PREFIX}ajuda [modulo]",
    aliases=["help", "comandos"],
)
async def cmd_ajuda(ctx: CommandContext):
    """Central de ajuda em duas etapas: visão geral de blocos ou detalhes por módulo."""
    if not ctx.args:
        # Etapa 1: Visão Geral de Blocos Temáticos
        linhas = [
            "🤖 **CENTRAL DE AJUDA DO BOT**",
            "*(Escolha um módulo abaixo para ver os comandos detalhados e exemplos)*\n",
            f"🛠️ **Geral & Diagnóstico:** `{COMMAND_PREFIX}ajuda geral`",
            "   Status, latência, histórico de conversas, hora e controle da sessão.\n",
            f"📅 **Google Calendar:** `{COMMAND_PREFIX}ajuda agenda`",
            "   Consultar compromissos agendados, marcar reuniões e desmarcar.\n",
            f"🛒 **Listas & Mercado:** `{COMMAND_PREFIX}ajuda lista`",
            "   Listas de compras, mercado e tarefas (adicionar, ver, ticar e limpar).\n",
            f"⏰ **Lembretes Agendados:** `{COMMAND_PREFIX}ajuda lembrete`",
            "   Avisos com notificação ativa no Discord em tempo relativo ou data/hora.\n",
            f"📄 **Arquivos & PDFs:** `{COMMAND_PREFIX}ajuda pdf`",
            "   Armazenamento automático na sua pasta e download de documentos.\n",
            f"🧠 **Memória de Longo Prazo:** `{COMMAND_PREFIX}ajuda memoria`",
            "   Busca semântica vetorial (ChromaDB) e gestão de memórias persistentes.\n",
            f"🔊 **Modo de Resposta (Voz/Texto):** `{COMMAND_PREFIX}ajuda voz`",
            "   Escolha entre respostas em texto, áudio (voz Francisca pt-BR) ou ambos.\n",
            f"☀️ **Resumo Matinal (Digest):** `{COMMAND_PREFIX}ajuda digest`",
            "   Consolidação diária proativa (agenda Google, lembretes, listas e previsão do tempo).\n",
            f"⚡ **Provedores de IA & Google Gemini:** `{COMMAND_PREFIX}ajuda modelo`",
            "   Alternância entre LM Studio Local, Google Gemini Cloud e Roteamento Inteligente.\n",
            f"🌐 **Pesquisa Web & Browsing:** `{COMMAND_PREFIX}ajuda web`",
            "   Pesquisa em tempo real na internet (notícias, cotações, clima) e leitura de artigos.\n",
            f"📋 **Central de Prompts:** `{COMMAND_PREFIX}ajuda prompts`",
            "   Catálogo de prompts reutilizáveis, templates customizados e 7 presets de fábrica.\n",
            f"📂 **Knowledge Hub & Notas:** `{COMMAND_PREFIX}ajuda notas`",
            "   Bases de conhecimento por canal, RAG 100% isolado, hashtags e auto-captura.\n",
            f"🎭 **Personas por Canal:** `{COMMAND_PREFIX}ajuda persona`",
            "   Especialistas por canal/thread com System Prompts, temperatura e modelos dedicados.\n",
            "─" * 40,
            f"📖 **Como usar:** Digite `{COMMAND_PREFIX}ajuda <modulo>` (ex: `{COMMAND_PREFIX}ajuda agenda` ou `{COMMAND_PREFIX}ajuda lista`)",
            "💡 *Dica:* Durante a conversa normal sem prefixo, a IA executa todas as ações de forma autônoma!",
        ]
        await ctx.reply("\n".join(linhas))
        return

    modulo = ctx.args[0].lower().strip()

    # Módulo: Geral & Diagnóstico
    if modulo in ("geral", "diagnostico", "bot", "sistema", "status", "utilidades"):
        linhas = [
            "🛠️ **AJUDA: MÓDULO GERAL & DIAGNÓSTICO**",
            "Comandos de controle, verificação de conectividade e sessão:\n",
            f"• `{COMMAND_PREFIX}ping`",
            "  Mede a latência atual de conexão com o Discord Gateway.",
            f"• `{COMMAND_PREFIX}status`",
            "  Exibe diagnóstico operacional (LLM, SQLite, ChromaDB, servidores).",
            f"• `{COMMAND_PREFIX}hora [fuso]`",
            "  Data e hora do servidor. Padrão: `America/Sao_Paulo`. Ex: `!hora UTC`",
            f"• `{COMMAND_PREFIX}modelo`",
            "  Exibe o modelo LLM ativo e a URL do LM Studio.",
            f"• `{COMMAND_PREFIX}historico`",
            "  Mostra a quantidade de mensagens salvas e o histórico imediato recente.",
            f"• `{COMMAND_PREFIX}gateway [status|pausar|retomar|limpar]`",
            "  Telemetria e controle anti-spam do barramento unificado de saída (Outbox).",
            f"• `{COMMAND_PREFIX}ajuda`",
            "  Retorna ao menu principal de blocos de ajuda.",
        ]
        await ctx.reply("\n".join(linhas))
        return

    # Módulo: Google Calendar
    if modulo in ("agenda", "calendario", "calendar", "google", "compromissos", "eventos"):
        linhas = [
            "📅 **AJUDA: MÓDULO GOOGLE CALENDAR**",
            "Comandos de integração e gerenciamento da sua agenda Google:\n",
            f"• `{COMMAND_PREFIX}agenda [dias]`",
            "  Consulta seus próximos compromissos agendados.",
            f"  *Exemplo:* `{COMMAND_PREFIX}agenda` (7 dias) ou `{COMMAND_PREFIX}agenda 15`\n",
            f"• `{COMMAND_PREFIX}agendar <Título> | <Início> [| <Fim>]`",
            "  Adiciona um novo evento diretamente na sua agenda Google.",
            f"  *Exemplo 1:* `{COMMAND_PREFIX}agendar Reunião com Cliente | 2026-10-22 14:30`",
            f"  *Exemplo 2:* `{COMMAND_PREFIX}agendar Dentista | 2026-10-25 09:00 | 2026-10-25 10:00`\n",
            f"• `{COMMAND_PREFIX}desmarcar <Nome do Evento ou ID>`",
            "  Cancela ou remove um compromisso agendado pelo nome ou ID.",
            f"  *Exemplo:* `{COMMAND_PREFIX}desmarcar Reunião com Cliente`\n",
            "💡 *Dica IA:* Você também pode falar no chat: *\"Marque uma reunião amanhã às 15h chamada Alinhamento\"*.",
        ]
        await ctx.reply("\n".join(linhas))
        return

    # Módulo: Listas e Mercado
    if modulo in ("lista", "listas", "mercado", "compras", "tarefas", "afazeres"):
        linhas = [
            "🛒 **AJUDA: MÓDULO LISTAS & MERCADO**",
            "Comandos para listas de compras, mercado e checklists de tarefas:\n",
            f"• `{COMMAND_PREFIX}lista ver <nome>` *(ou `{COMMAND_PREFIX}lista <nome>`)*",
            "  Exibe os itens da lista com caixas de status (⬜ pendente / ✅ concluído).",
            f"  *Exemplo:* `{COMMAND_PREFIX}lista ver mercado`\n",
            f"• `{COMMAND_PREFIX}lista add <nome> <item>`",
            "  Adiciona um novo item à lista especificada.",
            f"  *Exemplo:* `{COMMAND_PREFIX}lista add mercado 2L de leite integral`",
            f"  *Exemplo:* `{COMMAND_PREFIX}lista add tarefas Enviar relatório financeiro`\n",
            f"• `{COMMAND_PREFIX}lista ticar <nome> <id ou texto>`",
            "  Alterna o estado de um item entre concluído e pendente.",
            f"  *Exemplo:* `{COMMAND_PREFIX}lista ticar mercado 1` ou `{COMMAND_PREFIX}lista ticar mercado leite`\n",
            f"• `{COMMAND_PREFIX}lista remover <nome> <id ou texto>`",
            "  Remove um item específico da lista.",
            f"  *Exemplo:* `{COMMAND_PREFIX}lista remover mercado 2`\n",
            f"• `{COMMAND_PREFIX}lista limpar <nome>`",
            "  Exclui apenas os itens já marcados como concluídos (✅) da lista.",
            f"  *Exemplo:* `{COMMAND_PREFIX}lista limpar mercado`\n",
            f"• `{COMMAND_PREFIX}lista excluir <nome>`",
            "  Apaga permanentemente a lista inteira e todos os seus itens.",
            f"  *Exemplo:* `{COMMAND_PREFIX}lista excluir compras_antigas`\n",
            f"• `{COMMAND_PREFIX}listas`",
            "  Exibe um resumo de todas as suas listas ativas com quantidade de itens.\n",
            "💡 *Dica IA:* Pelo chat normal você pode dizer: *\"Adicione sabão e café na lista de mercado\"*.",
        ]
        await ctx.reply("\n".join(linhas))
        return

    # Módulo: Lembretes
    if modulo in ("lembrete", "lembretes", "aviso", "avisos", "lembrar", "avisar", "timer", "alarme"):
        linhas = [
            "⏰ **AJUDA: MÓDULO LEMBRETES AGENDADOS**",
            "Comandos para programar notificações e alertas ativos no Discord:\n",
            f"• `{COMMAND_PREFIX}lembrete <quando> <mensagem>`",
            "  Agenda um aviso para você. O bot marcará você no canal no momento exato!",
            "  *Formatos de tempo relativo:*",
            f"  • `{COMMAND_PREFIX}lembrete em 15m desligar o forno`",
            f"  • `{COMMAND_PREFIX}lembrete em 2h revisar documento`",
            f"  • `{COMMAND_PREFIX}lembrete em 30s testar notificação`",
            "  *Formatos de horário/data:*",
            f"  • `{COMMAND_PREFIX}lembrete 09:00 tomar remédio`",
            f"  • `{COMMAND_PREFIX}lembrete 19/10/2026 14:30 reunião com equipe`\n",
            f"• `{COMMAND_PREFIX}lembretes`",
            "  Lista todos os seus avisos programados que ainda estão pendentes.\n",
            f"• `{COMMAND_PREFIX}cancelar_lembrete <id>`",
            "  Cancela um aviso pendente antes do horário de disparo.",
            f"  *Exemplo:* `{COMMAND_PREFIX}cancelar_lembrete 3`\n",
            "💡 *Dica IA:* Você pode pedir na conversa: *\"Me avise daqui a 20 minutos para tomar água\"*.",
        ]
        await ctx.reply("\n".join(linhas))
        return

    # Módulo: Arquivos PDF e Livros Inteligentes
    if modulo in ("pdf", "pdfs", "livro", "livros", "ebook", "documento", "documentos", "arquivo", "arquivos"):
        linhas = [
            "📚 **AJUDA: MÓDULO ANÁLISE INTELIGENTE & RAG DE LIVROS/PDFS**",
            "Comandos de navegação, metadados, sumários, resumos e busca semântica em PDFs:\n",
            f"• `{COMMAND_PREFIX}pdf` ou `{COMMAND_PREFIX}pdf status`",
            "  Lista seus arquivos, total de páginas e status de indexação no RAG.\n",
            f"• `{COMMAND_PREFIX}pdf info <arquivo>`",
            "  Exibe a ficha catalográfica (título, autor, páginas, tamanho) e sinopse inicial.\n",
            f"• `{COMMAND_PREFIX}pdf sumario <arquivo>`",
            "  Exibe a estrutura de capítulos e as páginas correspondentes da obra.\n",
            f"• `{COMMAND_PREFIX}pdf capitulo <arquivo> <número_ou_nome>`",
            "  Gera uma síntese estruturada e didática dos pontos centrais do capítulo.\n",
            f"• `{COMMAND_PREFIX}pdf indexar <arquivo>`",
            "  Fatia a obra e gera embeddings vetoriais no ChromaDB para conversação livre.\n",
            f"• `{COMMAND_PREFIX}pdf perguntar <arquivo> <sua dúvida>`",
            "  Faz busca semântica no livro e responde citando as páginas exatas!\n",
            f"• `{COMMAND_PREFIX}enviar <arquivo>`",
            "  Envia o arquivo físico do PDF de volta como anexo no chat.\n",
            "💡 *Dica IA:* Pelo chat você pode pedir: *\"Resuma o capítulo 2 de rag-versao-final\"* ou *\"O que o livro fala sobre CRAG?\"*.",
        ]
        await ctx.reply("\n".join(linhas))
        return

    # Módulo: Memória Vetorial
    if modulo in ("memoria", "memorias", "rag", "chroma", "chromadb", "vetorial"):
        linhas = [
            "🧠 **AJUDA: MÓDULO MEMÓRIA DE LONGO PRAZO**",
            "Comandos de busca e gerenciamento da memória semântica vetorial:\n",
            f"• `{COMMAND_PREFIX}memoria <termo>`",
            "  Busca semântica no histórico de conversas passadas usando embeddings.",
            f"  *Exemplo:* `{COMMAND_PREFIX}memoria servidor de produção`\n",
            f"• `{COMMAND_PREFIX}memoria` *(sem argumentos)*",
            "  Informa o total de fragmentos e o nome da sua coleção no ChromaDB.\n",
            f"• `{COMMAND_PREFIX}limpar_memoria`",
            "  Limpa e reseta sua memória semântica vetorial no ChromaDB.\n",
            "💡 *Dica IA:* O bot consulta sua memória semântica automaticamente para lembrar fatos passados!",
        ]
        await ctx.reply("\n".join(linhas))
        return

    # Módulo: Voz e Modo de Resposta
    if modulo in ("voz", "audio", "resposta", "tts", "som"):
        linhas = [
            "🔊 **AJUDA: MÓDULO VOZ & MODO DE RESPOSTA (TTS)**",
            "Configura se o assistente responde por texto, voz (áudio) ou ambos:\n",
            f"• `{COMMAND_PREFIX}voz`",
            "  Mostra o seu modo de resposta atual e a voz configurada.",
            f"• `{COMMAND_PREFIX}voz texto`",
            "  Configura o bot para responder apenas com texto escrito.",
            f"• `{COMMAND_PREFIX}voz audio`",
            "  Configura o bot para responder apenas com áudio gravado (Francisca pt-BR).",
            f"• `{COMMAND_PREFIX}voz ambos`",
            "  Configura o bot para responder com texto e áudio simultaneamente.\n",
            "🎙️ **Mensagens de Áudio do Usuário:**",
            "Você pode gravar notas de voz ou enviar arquivos de áudio (.ogg, .mp3, .wav) no chat. O bot transcreverá automaticamente com faster-whisper e responderá no modo escolhido!\n",
            "💡 *Dica IA:* Você também pode alterar falando no chat: *\"A partir de agora me responda em áudio\"* ou *\"Volte para o modo texto\"*.",
        ]
        await ctx.reply("\n".join(linhas))
        return

    # Módulo: Resumo Matinal (Digest)
    if modulo in ("digest", "resumo", "matinal", "dia", "clima"):
        linhas = [
            "☀️ **AJUDA: MÓDULO RESUMO MATINAL DIÁRIO (DIGEST)**",
            "Consolidação diária em texto e/ou áudio (agenda Google, lembretes, listas e clima):\n",
            f"• `{COMMAND_PREFIX}digest` ou `{COMMAND_PREFIX}resumo`",
            "  Mostra as configurações atuais do seu resumo diário.",
            f"• `{COMMAND_PREFIX}digest agora`",
            "  Gera e envia imediatamente o seu resumo matinal de hoje para teste.",
            f"• `{COMMAND_PREFIX}digest hora <HH:MM>`",
            "  Define o horário do disparo diário (padrão: `08:00`). Ex: `!digest hora 07:30`",
            f"• `{COMMAND_PREFIX}digest cidade <nome>`",
            "  Define a cidade para a previsão do tempo. Ex: `!digest cidade Curitiba`",
            f"• `{COMMAND_PREFIX}digest canal`",
            "  Define o canal atual para onde o resumo diário deve ser enviado.",
            f"• `{COMMAND_PREFIX}digest on` / `{COMMAND_PREFIX}digest off`",
            "  Ativa ou pausa temporariamente o envio matinal diário.\n",
            "💡 *Dica:* A síntese matinal respeita a sua preferência de voz (`!voz audio` ou `!voz ambos`)!",
        ]
        await ctx.reply("\n".join(linhas))
        return

    # Módulo: Provedores & Modelos LLM
    if modulo in ("modelo", "modelos", "ia", "llm", "provedor", "gemini", "google"):
        linhas = [
            "🧠 **AJUDA: MÓDULO ROTEAMENTO DE MODELOS & GOOGLE GEMINI**",
            "Controle de provedores híbridos de IA (LM Studio Local vs Google Gemini Cloud):\n",
            f"• `{COMMAND_PREFIX}modelo`",
            "  Exibe o provedor ativo, o modelo em execução e o status do Google Gemini.",
            f"• `{COMMAND_PREFIX}modelo local`",
            "  Define o LM Studio local como provedor ativo (custo zero e privacidade).",
            f"• `{COMMAND_PREFIX}modelo google` ou `{COMMAND_PREFIX}modelo gemini`",
            "  Ativa o Google Gemini 2.5 Flash em nuvem (respostas rápidas e alta capacidade).",
            f"• `{COMMAND_PREFIX}modelo gemini-pro`",
            "  Ativa o Google Gemini 2.5 Pro para raciocínio analítico denso e código complexo.",
            f"• `{COMMAND_PREFIX}modelo auto`",
            "  Ativa o roteamento inteligente: tarefas do dia a dia no local e tarefas pesadas no Gemini.",
            f"• `{COMMAND_PREFIX}modelo key <sua_chave>`",
            "  Cadastra sua chave do Google Gemini (sua mensagem é apagada do chat por proteção).\n",
            "💡 *Dica IA:* Você também pode alternar em linguagem natural: *\"Troque para o modelo do Google\"* ou *\"Volte para o modelo local\"*.",
        ]
        await ctx.reply("\n".join(linhas))
        return

    # Módulo: Pesquisa na Web & Browsing
    if modulo in ("web", "buscar", "busca", "pesquisa", "internet", "google", "noticias", "noticia", "browsing", "ler", "navegador"):
        linhas = [
            "🌐 **AJUDA: MÓDULO PESQUISA NA WEB & BROWSING**",
            "Acesso a fatos atualizados, cotações, clima e leitura limpa de páginas em tempo real:\n",
            f"• `{COMMAND_PREFIX}buscar <pergunta ou termo>` (ou `{COMMAND_PREFIX}pesquisar`)",
            "  Pesquisa notícias, cotações financeiras, documentações e previsões na web.",
            "  *Exemplo:* `!buscar cotação do dólar hoje` ou `!buscar previsão do tempo são paulo`",
            f"• `{COMMAND_PREFIX}ler <url>` (ou `{COMMAND_PREFIX}artigo`)",
            "  Acessa uma página web, extrai o texto limpo e a IA sintetiza um resumo estruturado.",
            "  *Exemplo:* `!ler https://exemplo.com/materia-de-tecnologia`\n",
            "💡 *Dica Conversacional:* Durante a conversa normal sem prefixo, a IA aciona a busca na internet automaticamente sempre que você perguntar sobre fatos recentes, cotações ou notícias!",
        ]
        await ctx.reply("\n".join(linhas))
        return

    # Módulo: Central de Prompts & Templates (IDEA-20)
    if modulo in ("prompts", "prompt", "template", "templates", "preset", "presets", "hub"):
        linhas = [
            "📋 **AJUDA: MÓDULO CENTRAL DE PROMPTS & TEMPLATES**",
            "Biblioteca de prompts reutilizáveis, templates customizados e presets de fábrica:\n",
            f"• `{COMMAND_PREFIX}prompts [categoria]`",
            "  Lista todos os templates e presets disponíveis no catálogo.",
            "  *Exemplo:* `!prompts` ou `!prompts engenharia`\n",
            f"• `{COMMAND_PREFIX}prompt ver <slug>`",
            "  Exibe o texto completo, categoria e temperatura sugerida do prompt.",
            "  *Exemplo:* `!prompt ver cfo` ou `!prompt ver dev`\n",
            f"• `{COMMAND_PREFIX}prompt salvar <slug> <texto do prompt>`",
            "  Cria ou atualiza um template de prompt customizado pelo usuário.",
            "  *Exemplo:* `!prompt salvar arquiteto Você é um arquiteto sênior em nuvem...`\n",
            f"• `{COMMAND_PREFIX}prompt remover <slug>`",
            "  Exclui um prompt customizado criado por você (presets oficiais são protegidos).\n",
            "🌟 **Presets Oficiais Integrados:**",
            "• `padrao` — Assistente pessoal equilibrado e cordial.",
            "• `dev` — Tech Lead & Arquiteto de Software (TypeScript, Python, Clean Code).",
            "• `direto` — Modo Ultra-Conciso (direto ao ponto, sem preâmbulos).",
            "• `revisor` — Editor Textual Rígido (clareza, gramática e estilo).",
            "• `cfo` — Consultor Financeiro & Estratégico (ROI, margem e riscos).",
            "• `socrates` — Filósofo Maiêutico (condução reflexiva baseada em perguntas).",
            "• `tributarista` — Especialista Tributário & Contábil (CBS, IBS e Reforma).\n",
            f"💡 *Dica:* Você pode aplicar qualquer um desses presets direto a um canal com `{COMMAND_PREFIX}persona canal aplicar <preset>`!",
        ]
        await ctx.reply("\n".join(linhas))
        return

    # Módulo: Knowledge Hub Temático & Notas (IDEA-25)
    if modulo in ("topico", "topicos", "nota", "notas", "knowledge", "conhecimento", "hub_notas"):
        linhas = [
            "📂 **AJUDA: MÓDULO KNOWLEDGE HUB & NOTAS TEMÁTICAS**",
            "Transforme canais e threads em bases de conhecimento com RAG 100% isolado:\n",
            f"• `{COMMAND_PREFIX}topico vincular <nome do tópico>`",
            "  Vincula o canal atual a uma base temática exclusiva.",
            "  *Exemplo:* `!topico vincular Desenvolvimento Bot Discord`\n",
            f"• `{COMMAND_PREFIX}topico status`",
            "  Exibe detalhes do tópico vinculado, total de notas catalogadas e modo livre.\n",
            f"• `{COMMAND_PREFIX}topico modo_livre`",
            "  Alterna o modo de auto-captura (mensagens normais >= 15 chars são salvas como notas automaticamente).\n",
            f"• `{COMMAND_PREFIX}topico desvincular`",
            "  Desvincula o canal e retorna ao comportamento geral.\n",
            f"• `{COMMAND_PREFIX}nota add <conteúdo> [#tags]`",
            "  Registra uma nova nota temática com indexação vetorial imediata no ChromaDB.",
            "  *Exemplo:* `!nota add Adotamos SQLite com WAL para o banco #arquitetura`\n",
            f"• `{COMMAND_PREFIX}nota buscar <consulta>`",
            "  Busca semântica RAG isolada exclusivamente na coleção de notas deste canal.",
            "  *Exemplo:* `!nota buscar padrão de concorrência`\n",
            f"• `{COMMAND_PREFIX}nota ver <id>`",
            "  Exibe a íntegra, tags e data de criação de uma nota específica.\n",
            f"• `{COMMAND_PREFIX}nota remover <id>`",
            "  Exclui uma nota do banco SQLite e da coleção do ChromaDB.\n",
            f"• `{COMMAND_PREFIX}nota limpar`",
            "  Remove todas as notas da base do canal atual.\n",
            f"• `{COMMAND_PREFIX}notas [#tag] [limite]`",
            "  Lista as notas mais recentes do canal. *Exemplo:* `!notas #arquitetura`\n",
            "📝 **Atalho Visual:** Reaja a qualquer mensagem do canal com o emoji `📝` para salvá-la como nota!",
            "🌐 **Escape de Isolamento:** Adicione `--global` à sua mensagem para que a IA busque também na sua memória geral.",
        ]
        await ctx.reply("\n".join(linhas))
        return

    # Módulo: Personas por Canal (IDEA-26)
    if modulo in ("persona", "personas", "especialista", "especialistas", "override"):
        linhas = [
            "🎭 **AJUDA: MÓDULO PERSONAS & OVERRIDES COGNITIVOS**",
            "Catálogo de personas especializadas e personalização por canal ou thread:\n",
            f"• `{COMMAND_PREFIX}persona lista`",
            "  Visualiza todas as personas disponíveis no catálogo (oficiais e customizadas).\n",
            f"• `{COMMAND_PREFIX}persona salvar <id> <prompt>`",
            "  Cadastra uma nova persona especializada no catálogo para uso geral.",
            "  *Exemplo:* `!persona salvar arquiteto Você é um arquiteto cloud AWS sênior...`\n",
            f"• `{COMMAND_PREFIX}persona remover <id>`",
            "  Exclui uma persona customizada do catálogo.\n",
            f"• `{COMMAND_PREFIX}persona canal aplicar <id>`",
            "  Aplica instantaneamente uma persona do catálogo ao canal atual.",
            "  *Exemplo:* `!persona canal aplicar cfo` ou `!persona canal aplicar dev`\n",
            f"• `{COMMAND_PREFIX}persona canal ver`",
            "  Inspeciona a persona ativa, temperatura e modelo de IA no canal atual.\n",
            f"• `{COMMAND_PREFIX}persona canal temp <0.0 a 1.0>`",
            "  Calibra a temperatura da LLM exclusivamente para o canal atual.",
            "  *Exemplo:* `!persona canal temp 0.2` (mais analítico) ou `!persona canal temp 0.8` (mais criativo)\n",
            f"• `{COMMAND_PREFIX}persona canal modelo <local|flash|pro>`",
            "  Define qual modelo atenderá este canal: LM Studio Local, Gemini Flash ou Gemini Pro.\n",
            f"• `{COMMAND_PREFIX}persona canal reset`",
            "  Remove o override e restaura o comportamento e modelo padrão do assistente.\n",
            f"• `{COMMAND_PREFIX}persona canais`",
            "  Lista os canais do servidor que possuem personas customizadas configuradas.\n",
            "🤖 **Tools para a IA:** O assistente possui as ferramentas `listar_personas_disponiveis` e `cadastrar_nova_persona`, permitindo criar ou consultar personas via conversa natural!",
        ]
        await ctx.reply("\n".join(linhas))
        return

    # Módulo desconhecido
    linhas = [
        f"❓ **Módulo de ajuda '{modulo}' não reconhecido.**\n",
        "Os blocos temáticos disponíveis são:",
        f"• `{COMMAND_PREFIX}ajuda geral` — Diagnóstico e controle da sessão",
        f"• `{COMMAND_PREFIX}ajuda modelo` — Roteador de modelos (Local vs Google Gemini)",
        f"• `{COMMAND_PREFIX}ajuda web` — Pesquisa na internet e leitura de artigos",
        f"• `{COMMAND_PREFIX}ajuda prompts` — Central de Prompts, templates e presets",
        f"• `{COMMAND_PREFIX}ajuda notas` — Knowledge Hub temático e RAG isolado",
        f"• `{COMMAND_PREFIX}ajuda persona` — Personas, temperatura e modelo por canal",
        f"• `{COMMAND_PREFIX}ajuda agenda` — Google Calendar (consultar e agendar)",
        f"• `{COMMAND_PREFIX}ajuda lista` — Listas de mercado, compras e tarefas",
        f"• `{COMMAND_PREFIX}ajuda lembrete` — Avisos e notificações temporizadas",
        f"• `{COMMAND_PREFIX}ajuda pdf` — Gerenciamento e download de PDFs",
        f"• `{COMMAND_PREFIX}ajuda memoria` — Memória semântica no ChromaDB",
        f"• `{COMMAND_PREFIX}ajuda voz` — Modo de resposta (texto, áudio ou ambos)",
        f"• `{COMMAND_PREFIX}ajuda digest` — Resumo matinal diário proativo\n",
        f"💡 Digite `{COMMAND_PREFIX}ajuda` para ver o resumo completo.",
    ]
    await ctx.reply("\n".join(linhas))


@register_command(
    name="ping",
    description="Verifica se o bot está online e mede a latência da conexão com o Discord.",
    usage=f"{COMMAND_PREFIX}ping",
    aliases=["latencia"],
)
async def cmd_ping(ctx: CommandContext):
    """Responde com a latência do gateway."""
    latencia_ms = ctx.client.latency * 1000.0
    await ctx.reply(f"🏓 **Pong!** Latência do Gateway: `{latencia_ms:.1f}ms`")


@register_command(
    name="limpar",
    description="Limpa todo o histórico de conversas armazenado no banco para o seu usuário.",
    usage=f"{COMMAND_PREFIX}limpar",
    aliases=["clear", "reset"],
)
async def cmd_limpar(ctx: CommandContext):
    """Remove o histórico de mensagens do usuário no SQLite."""
    user_id = ctx.author.id
    removidos = limpar_historico(user_id)
    await ctx.reply(f"🧹 Histórico de conversa limpo com sucesso! `{removidos}` mensagens removidas do banco.")


@register_command(
    name="historico",
    description="Exibe o número de mensagens salvas e um resumo do contexto recente.",
    usage=f"{COMMAND_PREFIX}historico",
    aliases=["contexto"],
)
async def cmd_historico(ctx: CommandContext):
    """Mostra um resumo das mensagens armazenadas para o contexto."""
    user_id = ctx.author.id
    total = contar_mensagens(user_id)
    recentes = obter_historico(user_id, limite=6)

    if not recentes:
        await ctx.reply("📭 Seu histórico de conversação está vazio no momento.")
        return

    resumo = [f"📊 **Total de mensagens registradas:** `{total}`", "**Últimas mensagens do contexto:**"]
    for idx, msg in enumerate(recentes, start=1):
        papel = "👤 Usuário" if msg["role"] == "user" else "🤖 Assistente"
        conteudo_curto = msg["content"][:100].replace("\n", " ")
        if len(msg["content"]) > 100:
            conteudo_curto += "..."
        resumo.append(f"{idx}. {papel}: {conteudo_curto}")

    await ctx.reply("\n".join(resumo))


@register_command(
    name="hora",
    description="Informa a data e hora atual do servidor/fuso horário.",
    usage=f"{COMMAND_PREFIX}hora [fuso_horario]",
    aliases=["time", "data"],
)
async def cmd_hora(ctx: CommandContext):
    """Consulta rápida de data e hora."""
    fuso = ctx.args[0] if ctx.args else "America/Sao_Paulo"
    hora_str = obter_hora_formatada(fuso)
    await ctx.reply(f"⏰ **Horário Atual:** `{hora_str}`")


@register_command(
    name="modelo",
    description="Exibe e gerencia o modelo e provedor de LLM ativo (Local vs Google Gemini vs Auto).",
    usage=f"{COMMAND_PREFIX}modelo [local | google | gemini-pro | auto | key <chave>]",
    aliases=["llm", "ia", "provedor"],
)
async def cmd_modelo(ctx: CommandContext):
    """Exibe e gerencia o provedor e modelo de IA do usuário."""
    import re
    from database import definir_preferencia_modelo, obter_preferencia_modelo
    from llm_client import llm_client
    from config import BASE_DIR, GEMINI_FLASH_MODEL, GEMINI_PRO_MODEL

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
    name="status",
    description="Apresenta um diagnóstico geral do estado operacional do bot.",
    usage=f"{COMMAND_PREFIX}status",
    aliases=["info"],
)
async def cmd_status(ctx: CommandContext):
    """Exibe status geral do sistema."""
    guildas = len(ctx.client.guilds)
    latencia_ms = ctx.client.latency * 1000.0
    total_usuario = contar_mensagens(ctx.author.id)

    texto = (
        f"🟢 **Status do Sistema Antigravity Bot**\n"
        f"• **Conectado como:** `{ctx.client.user}`\n"
        f"• **Servidores conectados:** `{guildas}`\n"
        f"• **Latência Gateway:** `{latencia_ms:.1f}ms`\n"
        f"• **Mensagens salvas (você):** `{total_usuario}`\n"
        f"• **Modelo LLM:** `{MODELO_LLM}`\n"
        f"• **Hora do Servidor:** `{obter_hora_formatada()}`"
    )
    await ctx.reply(texto)


@register_command(
    name="pdfs",
    description="Lista todos os arquivos PDF salvos na sua pasta pessoal com status de catálogo e RAG.",
    usage=f"{COMMAND_PREFIX}pdfs",
    aliases=["listar_pdfs", "meus_pdfs"],
)
async def cmd_pdfs(ctx: CommandContext):
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
    aliases=["baixar", "disponibilizar", "obter", "download"],
)
async def cmd_enviar(ctx: CommandContext):
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
    aliases=["livro", "livros", "ebook", "documento"],
)
async def cmd_pdf(ctx: CommandContext):
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
    aliases=["lembrar", "busca_vetorial", "rag"],
)
async def cmd_memoria(ctx: CommandContext):
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
    aliases=["reset_memoria", "clear_memory"],
)
async def cmd_limpar_memoria(ctx: CommandContext):
    """Exclui a coleção vetorial do usuário."""
    sucesso = limpar_memoria_vetorial(ctx.author.name)
    if sucesso:
        await ctx.reply(f"🧹 Coleção vetorial `{ctx.author.name}_memory` no ChromaDB resetada com sucesso!")
    else:
        await ctx.reply("⚠️ Ocorreu uma falha ao tentar resetar a coleção vetorial no ChromaDB.")


@register_command(
    name="agenda",
    description="Consulta seus próximos compromissos no Google Calendar.",
    usage=f"{COMMAND_PREFIX}agenda [dias]",
    aliases=["calendario", "compromissos", "eventos"],
)
async def cmd_agenda(ctx: CommandContext):
    """Consulta a agenda do Google Calendar."""
    dias = int(ctx.args[0]) if ctx.args and ctx.args[0].isdigit() else 7
    res = listar_compromissos(dias_a_frente=dias)

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
async def cmd_agendar(ctx: CommandContext):
    """Adiciona evento na agenda do Google."""
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

    res = adicionar_compromisso(titulo=titulo, inicio=inicio, fim=fim)
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
async def cmd_desmarcar(ctx: CommandContext):
    """Remove evento da agenda do Google."""
    if not ctx.args:
        await ctx.reply(f"❓ Por favor, informe o nome ou ID do evento a remover. Exemplo: `{COMMAND_PREFIX}desmarcar Dentista`")
        return

    termo = ctx.arg_str
    res = remover_compromisso(termo_ou_id=termo)

    if not res.get("sucesso"):
        await ctx.reply(f"⚠️ {res.get('erro')}")
        return

    await ctx.reply(f"🗑️ {res.get('mensagem')}")


# ==============================================================================
# COMANDOS DE GERENCIAMENTO DE LISTAS (MERCADO, TAREFAS, ETC.)
# ==============================================================================

@register_command(
    name="lista",
    description="Gerencia listas pessoais (mercado, tarefas, compras). Subcomandos: ver, add, ticar, remover, limpar, excluir.",
    usage=f"{COMMAND_PREFIX}lista <ver|add|ticar|remover|limpar|excluir> [nome] [item]",
    aliases=["list", "mercado", "tarefas"],
)
async def cmd_lista(ctx: CommandContext):
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
    if sub == "add" or sub == "adicionar":
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
    aliases=["minhas_listas"],
)
async def cmd_listas(ctx: CommandContext):
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


# ==============================================================================
# COMANDOS DE LEMBRETES E AVISOS AGENDADOS (REMINDERS)
# ==============================================================================

@register_command(
    name="lembrete",
    description="Agenda um aviso ou lembrete para você. Aceita tempo relativo ('em 15m') ou data e hora ('19/10/2026 09:00').",
    usage=f"{COMMAND_PREFIX}lembrete <quando> <mensagem>",
    aliases=["lembrar", "aviso", "avisar"],
)
async def cmd_lembrete(ctx: CommandContext):
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
    aliases=["meus_lembretes", "avisos"],
)
async def cmd_lembretes(ctx: CommandContext):
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
    aliases=["remover_lembrete", "desmarcar_lembrete"],
)
async def cmd_cancelar_lembrete(ctx: CommandContext):
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


# ==============================================================================
# COMANDO DE CONFIGURAÇÃO DE VOZ E MODO DE RESPOSTA (TEXTO / ÁUDIO / AMBOS)
# ==============================================================================

@register_command(
    name="voz",
    description="Configura o modo de resposta do bot (texto, áudio com Francisca pt-BR, ou ambos).",
    usage=f"{COMMAND_PREFIX}voz [texto|audio|ambos]",
    aliases=["modo", "resposta", "modo_resposta", "audio"],
)
async def cmd_voz(ctx: CommandContext):
    """Configura ou consulta o modo de resposta do usuário."""
    user_id = str(ctx.author.id)

    if not ctx.args:
        modo_atual = obter_modo_resposta(user_id)
        descricoes = {
            "texto": "Apenas Texto (mensagens escritas convencionais)",
            "audio": "Apenas Áudio (mensagens de voz narradas pela Francisca pt-BR)",
            "ambos": "Texto e Áudio (mensagens escritas acompanhadas de áudio narrado)",
        }
        linhas = [
            "🔊 **Configuração de Resposta do Assistente (Voz & Texto):**",
            f"• **Seu modo atual:** `{modo_atual}` — *{descricoes.get(modo_atual, modo_atual)}*",
            f"• **Voz TTS:** `pt-BR-FranciscaNeural` (Francisca Brasil)",
            "",
            "**Opções para alterar:**",
            f"• `{COMMAND_PREFIX}voz texto` — Responde apenas com mensagens escritas",
            f"• `{COMMAND_PREFIX}voz audio` — Responde apenas com mensagem de áudio/voz",
            f"• `{COMMAND_PREFIX}voz ambos` — Responde com texto E áudio simultaneamente",
            "",
            "💡 *Dica:* Você também pode pedir naturalmente na conversa: *\"Responda apenas por áudio\"* ou *\"Quero respostas em texto e áudio\"*."
        ]
        await ctx.reply("\n".join(linhas))
        return

    modo_solicitado = ctx.args[0].lower().strip()
    res = definir_modo_resposta(user_id, modo_solicitado)
    if res.get("sucesso"):
        await ctx.reply(f"🔊 {res['mensagem']}")
    else:
        await ctx.reply(f"⚠️ {res['mensagem']}")


@register_command(
    name="digest",
    description="Configura ou executa o Resumo Matinal Diário (agenda, lembretes, listas e clima).",
    usage=f"{COMMAND_PREFIX}digest [agora | hora HH:MM | cidade Nome | on | off | canal]",
    aliases=["resumo", "matinal", "dia"],
)
async def cmd_digest(ctx: CommandContext):
    """Gerencia ou dispara o resumo matinal do usuário."""
    user_id = str(ctx.author.id)
    args = ctx.args

    if not args:
        cfg = obter_configuracao_digest(user_id)
        status_txt = "Ativado ✅" if cfg["enabled"] else "Desativado ❌"
        ch_id = cfg.get("channel_id")
        canal_info = f"<#{ch_id}>" if ch_id else "Canal atual / DM"
        linhas = [
            "☀️ **Configuração do seu Resumo Matinal Diário:**",
            f"• **Status:** {status_txt}",
            f"• **Horário agendado:** `{cfg['time']}` diariamente",
            f"• **Cidade (previsão do tempo):** {cfg['city']}",
            f"• **Canal de destino:** {canal_info}",
            f"• **Último envio:** {cfg['last_sent_date'] or 'Ainda não enviado hoje'}",
            "",
            "**Comandos para gerenciar:**",
            f"• `{COMMAND_PREFIX}digest agora` — Gera e envia o seu resumo de hoje imediatamente",
            f"• `{COMMAND_PREFIX}digest hora 07:30` — Altera o horário diário de envio",
            f"• `{COMMAND_PREFIX}digest cidade Curitiba` — Altera a cidade da previsão do tempo",
            f"• `{COMMAND_PREFIX}digest canal` — Define este canal atual como o destino do resumo",
            f"• `{COMMAND_PREFIX}digest on` / `{COMMAND_PREFIX}digest off` — Ativa ou pausa o envio matinal",
            "",
            "💡 *Dica:* O resumo matinal respeita a sua preferência de voz configurada em `!voz` (texto, áudio ou ambos)!",
        ]
        await ctx.reply("\n".join(linhas))
        return

    sub = args[0].lower().strip()

    if sub in ("agora", "hoje", "gerar", "run"):
        await ctx.reply("⏳ *Coletando compromissos, lembretes, tarefas e previsão do tempo para gerar seu resumo...*")
        res = await enviar_resumo_matinal(
            client=ctx.client,
            user_id=user_id,
            user_name=ctx.author.name,
            channel_id=ctx.channel.id,
            forcar=True,
        )
        if not res.get("sucesso"):
            await ctx.reply(f"⚠️ {res.get('mensagem', 'Falha ao gerar o resumo matinal.')}")
        return

    if sub in ("on", "ativar", "ligar"):
        res = atualizar_configuracao_digest(user_id, enabled=True, channel_id=ctx.channel.id)
        await ctx.reply(f"☀️ {res['mensagem']}")
        return

    if sub in ("off", "desativar", "desligar"):
        res = atualizar_configuracao_digest(user_id, enabled=False)
        await ctx.reply(f"☀️ {res['mensagem']}")
        return

    if sub in ("canal", "aqui"):
        res = atualizar_configuracao_digest(user_id, channel_id=ctx.channel.id)
        await ctx.reply(f"☀️ Canal do resumo matinal atualizado para este canal ({ctx.channel.mention})!")
        return

    if sub in ("hora", "horario") and len(args) > 1:
        hora_alvo = args[1].strip()
        res = atualizar_configuracao_digest(user_id, time=hora_alvo)
        await ctx.reply(f"☀️ {res['mensagem']}")
        return

    if sub in ("cidade", "local", "tempo", "clima") and len(args) > 1:
        cidade_alvo = " ".join(args[1:]).strip()
        res = atualizar_configuracao_digest(user_id, city=cidade_alvo)
        await ctx.reply(f"☀️ {res['mensagem']}")
        return

    await ctx.reply(f"❓ Subcomando não reconhecido. Use `{COMMAND_PREFIX}digest` para ver as opções ou `{COMMAND_PREFIX}digest agora`.")


# =============================================================================
# COMANDOS DE PESQUISA NA WEB & BROWSING (!buscar, !pesquisar, !ler)
# =============================================================================

@register_command(
    name="buscar",
    description="Pesquisa informações atualizadas na internet em tempo real (notícias, cotações, fatos).",
    usage=f"{COMMAND_PREFIX}buscar <termo de pesquisa>",
    aliases=["pesquisar", "busca", "search", "web"],
)
async def cmd_buscar(ctx: CommandContext):
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
async def cmd_ler(ctx: CommandContext):
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


# ==============================================================================
# COMANDO DE CONTROLE E AUDITORIA DO MESSAGE GATEWAY (IDEA-24)
# ==============================================================================

@register_command(
    name="gateway",
    description="Diagnóstico, telemetria e controle do Barramento Unificado de Mensagens e Outbox Anti-Spam (IDEA-24).",
    usage=f"{COMMAND_PREFIX}gateway [status|pausar|retomar|limpar]",
    aliases=["outbox", "antispam", "barramento"],
)
async def cmd_gateway(ctx: CommandContext):
    """Comando administrativo de controle e telemetria do Message Gateway."""
    from message_gateway import message_gateway
    sub = ctx.args[0].lower() if ctx.args else "status"

    if sub in ("status", "info", "telemetria"):
        st = message_gateway.get_status()
        linhas = [
            "🛡️ **STATUS DO MESSAGE GATEWAY & OUTBOX (IDEA-24)**",
            f"• **Status Geral:** {'🟢 Ativo' if st['enabled'] else '🔴 Desativado'}",
            f"• **Fila Outbox:** {'⏸️ Pausada' if st['is_paused'] else '▶️ Operando normalmente'}",
            f"• **Mensagens Pendentes na Fila:** `{st['queue_size']}`",
            f"• **Total Despachado:** `{st['stats']['total_dispatched']}`",
            f"• **Fast-Path (Latência <100ms):** `{st['stats']['fast_path_sent']}`",
            f"• **Enviadas via Fila Leaky Bucket:** `{st['stats']['queued_sent']}`",
            f"• **Duplicadas Descartadas (Anti-Spam):** `{st['stats']['duplicates_dropped']}`",
            f"• **Circuit Breakers Disparados:** `{st['stats']['circuit_breaker_trips']}`",
            f"• **Circuit Breakers Ativos no Momento:** `{len(st['active_circuit_breakers'])}`",
            f"• **Intervalo Leaky Bucket:** `{st['leaky_interval_sec']}s`",
            f"• **Janela Anti-Spam SHA-256:** `{st['debounce_window_sec']}s`",
        ]
        await ctx.reply("\n".join(linhas))
        return

    if sub in ("pausar", "pause"):
        message_gateway.pause()
        await ctx.reply("⏸️ **Fila Outbox do Gateway pausada com sucesso.** Novas mensagens de background serão represadas.")
        return

    if sub in ("retomar", "resume", "play"):
        message_gateway.resume()
        await ctx.reply("▶️ **Fila Outbox do Gateway retomada com sucesso.** Processamento normal reestabelecido.")
        return

    if sub in ("limpar", "clear", "purge"):
        qtd = message_gateway.clear_queue()
        await ctx.reply(f"🧹 **Fila Outbox limpa com sucesso!** `{qtd}` mensagens represadas foram descartadas.")
        return

    await ctx.reply(f"❓ Subcomando desconhecido. Use: `{COMMAND_PREFIX}gateway [status|pausar|retomar|limpar]`")


# ==============================================================================
# CENTRAL DE PROMPTS & TEMPLATES REUTILIZÁVEIS (IDEA-20)
# ==============================================================================

@register_command(
    name="prompts",
    description="Lista os templates de prompts e presets cognitivos disponíveis no catálogo central (IDEA-20).",
    usage=f"{COMMAND_PREFIX}prompts [categoria]",
    aliases=["templates", "presets"],
)
async def cmd_prompts(ctx: CommandContext):
    """Lista templates e presets disponíveis no Prompt Hub."""
    from prompt_hub import listar_templates
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
    aliases=["template"],
)
async def cmd_prompt(ctx: CommandContext):
    """Gerencia templates de prompts no catálogo."""
    from prompt_hub import obter_template, salvar_template, remover_template
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


# ==============================================================================
# KNOWLEDGE HUB TEMÁTICO: GESTÃO DE TÓPICOS E CANAIS (IDEA-25)
# ==============================================================================

@register_command(
    name="topico",
    description="Vincula, inspeciona e gerencia o tópico temático do canal atual (IDEA-25).",
    usage=f"{COMMAND_PREFIX}topico [vincular|status|desvincular|modo_livre]",
    aliases=["tema", "hub"],
)
async def cmd_topico(ctx: CommandContext):
    """Gerencia a associação do canal a um tópico de conhecimento."""
    from topic_manager import vincular_topico, obter_topico_canal, desvincular_topico, definir_modo_livre, listar_notas
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


# ==============================================================================
# KNOWLEDGE HUB TEMÁTICO: GESTÃO DE NOTAS E RAG ISOLADO (IDEA-25)
# ==============================================================================

@register_command(
    name="nota",
    description="Adiciona, busca, inspeciona ou remove notas no tópico temático do canal (IDEA-25).",
    usage=f"{COMMAND_PREFIX}nota [add|buscar|ver|remover|limpar] [conteúdo...]",
    aliases=["notas_cmd", "anotacao", "ideia"],
)
async def cmd_nota(ctx: CommandContext):
    """Gerencia notas no banco temático do canal atual."""
    from topic_manager import adicionar_nota, buscar_notas_rag, obter_nota, remover_nota, limpar_notas_topico, obter_topico_canal
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
    aliases=["listanotas", "minhasnotas"],
)
async def cmd_notas(ctx: CommandContext):
    """Lista as notas salvas no canal temático."""
    from topic_manager import listar_notas, obter_topico_canal
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


# ==============================================================================
# PERSONAS & OVERRIDES COGNITIVOS POR CANAL (IDEA-26)
# ==============================================================================

@register_command(
    name="persona",
    description="Visualiza, cadastra novas personas no catálogo e calibra personas específicas por canal/thread (IDEA-26).",
    usage=f"{COMMAND_PREFIX}persona [lista|salvar <id> <prompt>|remover <id>|canais|canal <aplicar|ver|temp|modelo|reset>]",
    aliases=["personas", "personacanal"],
)
async def cmd_persona(ctx: CommandContext):
    """Gerencia o catálogo de personas e a especialidade cognitiva dos canais."""
    import os
    from persona_manager import (
        definir_persona_canal,
        aplicar_preset_canal,
        obter_persona_canal,
        definir_temperatura_canal,
        definir_modelo_canal,
        resetar_persona_canal,
        listar_personas_canais,
        listar_personas_disponiveis,
        salvar_nova_persona,
        remover_persona_catalogo,
    )
    from ui_components import criar_view_selecao_persona

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

    # Sem argumentos: dashboard geral de personas e canais com dropdown interativo
    if not ctx.args:
        personas_cat = listar_personas_disponiveis()
        linhas = [
            "🎭 **CENTRAL DE PERSONAS COGNITIVAS**",
            "Consulte personas disponíveis, troque no menu interativo ou configure canais:\n",
            f"**Personas no Catálogo ({len(personas_cat)}):**",
        ]
        for p in personas_cat[:8]:
            tag = "🌟" if p["is_preset"] else "👤"
            linhas.append(f"• `{p['id']}` — {tag} **{p['nome']}** (temp: `{p['temperatura']}`): *{p['descricao'][:60]}...*")
        if len(personas_cat) > 8:
            linhas.append(f"*...e mais {len(personas_cat) - 8} personas.* Use `{COMMAND_PREFIX}persona lista` para ver todas.")

        # Status do canal atual
        p_atual = obter_persona_canal(channel_id)
        if p_atual and p_atual.get("persona_slug"):
            linhas.append(f"\n📍 **Canal Atual (`#{channel_name}`):** Persona ativa `{p_atual['persona_slug']}` (temp: `{p_atual['temperature']}`)")
        elif p_atual:
            linhas.append(f"\n📍 **Canal Atual (`#{channel_name}`):** Persona customizada ativa (temp: `{p_atual['temperature']}`)")
        else:
            linhas.append(f"\n📍 **Canal Atual (`#{channel_name}`):** Assistente padrão ativo")

        linhas.extend([
            "\n💡 **Troca Rápida de Persona:**",
            "Utilize o menu dropdown interativo abaixo para selecionar e ativar qualquer persona neste canal instantaneamente!\n",
            "**Comandos Úteis:**",
            f"• `{COMMAND_PREFIX}persona lista` — Ver catálogo completo",
            f"• `{COMMAND_PREFIX}persona salvar <id> <prompt>` — Cadastrar nova persona no catálogo",
            f"• `{COMMAND_PREFIX}persona canal ver` — Inspecionar detalhes do canal",
            f"• `{COMMAND_PREFIX}persona canal reset` — Restaurar assistente padrão",
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
            view_dropdown = criar_view_selecao_persona(
                channel_id=channel_id,
                author_id=ctx.author.id,
                guild_id=guild_id,
                channel_name=channel_name,
            )
            if not persona:
                await ctx.reply(f"ℹ️ O canal `{channel_name}` está utilizando o assistente padrão.", view=view_dropdown)
                return
            mod_txt = f" | **Modelo:** `{persona['model_override']}`" if persona["model_override"] else ""
            await ctx.reply(
                f"🎭 **Configurações de Persona de `{channel_name}`:**\n"
                f"• **Temperatura:** `{persona['temperature']}`{mod_txt}\n\n"
                f"**Prompt do Canal:**\n```text\n{persona['system_prompt']}\n```",
                view=view_dropdown,
            )
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




