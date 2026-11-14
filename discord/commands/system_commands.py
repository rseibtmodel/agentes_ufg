"""
Comandos de Sistema, Diagnóstico, Ajuda, Voz, Digest e Message Gateway.

Fornece comandos centrais de operação:
- !ajuda: manual navegável em 2 etapas
- !ping: latência do Discord Gateway
- !limpar: expurgo do histórico de conversação do SQLite
- !historico: contagem e preview de mensagens salvas
- !hora: data e hora atual do servidor por fuso horário
- !status: diagnóstico geral dos subsistemas
- !voz: modo de resposta (texto, áudio Francisca pt-BR, ambos)
- !digest: resumo matinal diário
- !gateway: telemetria e controle anti-spam do Message Gateway
"""

import logging
from typing import Optional

from commands.registry import CommandContext, register_command, registry as commands_registry
from config import COMMAND_PREFIX, MODELO_LLM
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
from agy_manager import agy_manager
from finops_manager import finops_manager
from message_gateway import message_gateway
from utils import obter_hora_formatada

logger = logging.getLogger(__name__)


@register_command(
    name="ajuda",
    description="Exibe a central de ajuda em 2 etapas (visão geral ou módulos detalhados).",
    usage=f"{COMMAND_PREFIX}ajuda [modulo]",
    aliases=["help", "comandos"],
)
async def cmd_ajuda(ctx: CommandContext) -> None:
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
            f"🧠 **Agentes & Skills (AGY):** `{COMMAND_PREFIX}ajuda agy`",
            "   Inspeção e consultas às 14 skills locais e telemetria do Antigravity Runner.\n",
            f"📡 **Radar de Feeds (ArXiv, GitHub, RSS):** `{COMMAND_PREFIX}ajuda radar`",
            "   Sentinela de releases do GitHub, papers do ArXiv e curadoria por IA.\n",
            f"💰 **FinOps & Custos LLM:** `{COMMAND_PREFIX}ajuda finops`",
            "   Telemetria de tokens, cotas diárias, estimativa de custos e economia local.\n",
            "─" * 40,
            f"📖 **Como usar:** Digite `{COMMAND_PREFIX}ajuda <modulo>` (ex: `{COMMAND_PREFIX}ajuda agenda` ou `{COMMAND_PREFIX}ajuda web`)",
            f"💡 **Ficha de Comando:** Digite `{COMMAND_PREFIX}ajuda <comando>` (ex: `{COMMAND_PREFIX}ajuda pesquisa_profunda` ou `{COMMAND_PREFIX}ajuda agy`) para ver o manual completo de qualquer comando!",
            "💡 *Dica:* Durante a conversa normal sem prefixo, a IA executa todas as ações de forma autônoma!",
        ]
        await ctx.reply("\n".join(linhas))
        return

    modulo = ctx.args[0].lower().strip().lstrip(COMMAND_PREFIX)

    # 1. Verificação de Ajuda Direta por Comando Específico
    cmd_especifico = commands_registry.get_command(modulo)
    if cmd_especifico:
        aliases_str = ", ".join([f"`{COMMAND_PREFIX}{a}`" for a in cmd_especifico.aliases]) if cmd_especifico.aliases else "Nenhum"
        exemplo_str = f"\n• **Exemplo de uso:** `{cmd_especifico.example}`" if cmd_especifico.example else ""
        linhas_cmd = [
            f"📌 **MANUAL DO COMANDO: `{COMMAND_PREFIX}{cmd_especifico.name}`**",
            f"• **Categoria:** `{cmd_especifico.category}`",
            f"• **Descrição:** {cmd_especifico.description}",
            f"• **Sintaxe:** `{cmd_especifico.usage}`{exemplo_str}",
            f"• **Apelidos (Aliases):** {aliases_str}",
        ]
        await ctx.reply("\n".join(linhas_cmd))
        return

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
            f"• `{COMMAND_PREFIX}agy [skills|info|status|consultar]`",
            "  Inspeção e consultas às skills e agentes locais em modo Read-Only.",
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
    if modulo in ("web", "buscar", "busca", "pesquisa", "internet", "noticias", "noticia", "browsing", "ler", "navegador", "deepresearch"):
        linhas = [
            "🌐 **AJUDA: MÓDULO PESQUISA NA WEB, BROWSING & DEEP RESEARCH**",
            "Acesso a fatos atualizados, cotações, leitura de páginas e investigações profundas:\n",
            f"• `{COMMAND_PREFIX}buscar <pergunta ou termo>` (ou `{COMMAND_PREFIX}pesquisar`)",
            "  Pesquisa notícias, cotações financeiras, documentações e previsões na web.",
            "  *Exemplo:* `!buscar cotação do dólar hoje` ou `!buscar previsão do tempo são paulo`\n",
            f"• `{COMMAND_PREFIX}ler <url>` (ou `{COMMAND_PREFIX}artigo`)",
            "  Acessa uma página web, extrai o texto limpo e a IA sintetiza um resumo estruturado.",
            "  *Exemplo:* `!ler https://exemplo.com/materia-de-tecnologia`\n",
            f"• `{COMMAND_PREFIX}pesquisa_profunda <tema>` (ou `{COMMAND_PREFIX}pesquisa`, `{COMMAND_PREFIX}deepresearch`)",
            "  Conduz uma investigação profunda multi-fontes na web, cruzando dados e gerando um dossiê executivo com anexo Markdown.",
            "  *Exemplo:* `!pesquisa_profunda Reforma Tributária CBS no setor de tecnologia`\n",
            f"• `{COMMAND_PREFIX}pesquisas`",
            "  Lista seus relatórios e dossiês de pesquisa profunda já gerados anteriormente.\n",
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

    # Módulo: Agentes & Skills Locais (AGY Runner — IDEA-23)
    if modulo in ("agy", "agente", "agentes", "skill", "skills", "skills_locais", "runner"):
        linhas = [
            "🧠 **AJUDA: MÓDULO AGENTES & SKILLS LOCAIS (AGY REMOTE RUNNER)**",
            "Inspeção e consultas às skills e especialistas locais do Antigravity em modo Read-Only:\n",
            f"• `{COMMAND_PREFIX}agy skills` (ou `{COMMAND_PREFIX}agentes`)",
            "  Lista todas as 14 skills locais registradas em `.agents/skills/` com nome e descrição.",
            "  *Exemplo:* `!agy skills`\n",
            f"• `{COMMAND_PREFIX}agy info <skill>`",
            "  Exibe o manifesto detalhado, regras e escopo da skill.",
            "  *Exemplo:* `!agy info critic` ou `!agy info architect`\n",
            f"• `{COMMAND_PREFIX}agy status`",
            "  Exibe a telemetria do runtime local (uptime, RAM alocada, CPU, tarefas ativas).",
            "  *Exemplo:* `!agy status`\n",
            f"• `{COMMAND_PREFIX}agy consultar <skill> <sua dúvida>`",
            "  Consulta a persona de um especialista para emitir um laudo técnico (somente leitura).",
            "  *Exemplo:* `!agy consultar critic Qual o risco de concorrência no SQLite WAL?`\n",
            "💡 *Dica:* A IA também possui as tools `listar_skills_antigravity` e `consultar_skill_antigravity` para consultas via linguagem natural!",
        ]
        await ctx.reply("\n".join(linhas))
        return

    # Módulo: Radar Autônomo de RSS, ArXiv & GitHub (IDEA-29)
    if modulo in ("radar", "feed", "feeds", "rss", "arxiv", "papers"):
        linhas = [
            "📡 **AJUDA: MÓDULO RADAR AUTÔNOMO (RSS, ARXIV & GITHUB)**",
            "Sentinela proativa de feeds técnicos, releases do GitHub e papers científicos com curadoria por IA:\n",
            f"• `{COMMAND_PREFIX}radar assinar <fonte> [--tempo-real] [--boletim HH:MM] [--filtro 'regex']`",
            "  Cadastra o monitoramento de uma fonte técnica no canal atual.",
            "  *Exemplos:*",
            f"  └ ArXiv: `{COMMAND_PREFIX}radar assinar arxiv:cs.AI --tempo-real`",
            f"  └ ArXiv com Filtro: `{COMMAND_PREFIX}radar assinar arxiv:cs.CL --boletim 09:00 --filtro 'reasoning|agents'`",
            f"  └ GitHub Releases: `{COMMAND_PREFIX}radar assinar vllm-project/vllm --tempo-real`",
            f"  └ Feed RSS/Atom: `{COMMAND_PREFIX}radar assinar https://huggingface.co/blog/feed.xml`\n",
            "🔬 **Categorias Populares do ArXiv:**",
            "  • `arxiv:cs.AI` — Inteligência Artificial Geral",
            "  • `arxiv:cs.CL` — NLP, Linguagem e Grandes Modelos (LLMs)",
            "  • `arxiv:cs.LG` — Machine Learning / Aprendizado de Máquina",
            "  • `arxiv:cs.CV` — Visão Computacional",
            "  • `arxiv:cs.SE` — Engenharia de Software\n",
            f"• `{COMMAND_PREFIX}radar listar`",
            "  Lista todas as assinaturas ativas do seu usuário e seus canais de entrega.\n",
            f"• `{COMMAND_PREFIX}radar remover <id>`",
            "  Cancela o monitoramento de uma assinatura pelo ID.\n",
            f"• `{COMMAND_PREFIX}radar agora`",
            "  Força varredura e processamento imediato dos feeds agendados.\n",
            f"• `{COMMAND_PREFIX}radar boletim`",
            "  Consolida e envia na hora as novidades acumuladas para este canal.\n",
            "💡 *Dica:* A IA conta com a tool `pesquisar_novidades_radar` para responder sobre novidades capturadas via chat normal!",
        ]
        await ctx.reply("\n".join(linhas))
        return

    # Módulo: FinOps & Custos LLM (IDEA-28)
    if modulo in ("finops", "tokens", "custos", "telemetria", "cota", "cotas"):
        linhas = [
            "💰 **AJUDA: MÓDULO FINOPS & TELEMETRIA DE TOKENS**",
            "Observabilidade financeira e controle de gastos com modelos de linguagem em tempo real:\n",
            f"• `{COMMAND_PREFIX}finops status` *(ou apenas `{COMMAND_PREFIX}finops`)*",
            "  Resumo financeiro: total de tokens (prompt/completion), custo acumulado em USD e economia gerada pelo modelo local.\n",
            f"• `{COMMAND_PREFIX}finops cotas`",
            "  Exibe o saldo da sua cota diária (200k tokens) e a cota do sistema de background (500k tokens).\n",
            f"• `{COMMAND_PREFIX}finops modelos`",
            "  Tabela de preços oficial por milhão de tokens (Gemini Flash, Gemini Pro e LM Studio Local).\n",
            f"• `{COMMAND_PREFIX}finops reset`",
            "  Zera a contagem e restaura as cotas diárias para testes.\n",
            "💡 *Proteção:* Quando sua cota é atingida, o bot faz fallback automático e gratuito para o LM Studio local sem interromper o serviço!",
        ]
        await ctx.reply("\n".join(linhas))
        return

    # 2. Resolução Dinâmica por Categoria do CommandRegistry
    cmds_categoria = commands_registry.get_commands_by_category(modulo)
    if cmds_categoria:
        nome_categoria = cmds_categoria[0].category
        linhas_cat = [
            f"📂 **AJUDA: CATEGORIA `{nome_categoria.upper()}`**",
            f"*(Comandos registrados sob esta categoria no CommandRegistry)*\n",
        ]
        for cmd in cmds_categoria:
            ex_txt = f"\n  └ 💡 Exemplo: `{cmd.example}`" if cmd.example else ""
            linhas_cat.append(f"• **`{cmd.usage}`**\n  └ {cmd.description}{ex_txt}")
        linhas_cat.append(f"\n💡 *Para detalhes de um comando específico, use: `{COMMAND_PREFIX}ajuda <nome_comando>`*")
        await ctx.reply("\n".join(linhas_cat))
        return

    # Módulo desconhecido — lista todas as categorias dinamicamente
    categorias_registradas = commands_registry.get_categories()
    linhas = [
        f"❓ **Módulo ou comando '{modulo}' não reconhecido.**\n",
        "**Categorias disponíveis no bot:**",
    ]
    for cat in categorias_registradas:
        slug_sugerido = cat.lower().split("&")[0].split()[0]
        linhas.append(f"• **{cat}:** `{COMMAND_PREFIX}ajuda {slug_sugerido}`")

    linhas.append(f"\n💡 *Você também pode digitar `{COMMAND_PREFIX}ajuda <comando>` para ver o manual de qualquer comando específico.*")
    await ctx.reply("\n".join(linhas))


@register_command(
    name="ping",
    description="Verifica se o bot está online e mede a latência da conexão com o Discord.",
    usage=f"{COMMAND_PREFIX}ping",
    aliases=["latencia"],
)
async def cmd_ping(ctx: CommandContext) -> None:
    """Responde com a latência do gateway."""
    latencia_ms = ctx.client.latency * 1000.0
    await ctx.reply(f"🏓 **Pong!** Latência do Gateway: `{latencia_ms:.1f}ms`")


@register_command(
    name="limpar",
    description="Limpa todo o histórico de conversas armazenado no banco para o seu usuário.",
    usage=f"{COMMAND_PREFIX}limpar",
    aliases=["clear", "reset"],
)
async def cmd_limpar(ctx: CommandContext) -> None:
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
async def cmd_historico(ctx: CommandContext) -> None:
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
async def cmd_hora(ctx: CommandContext) -> None:
    """Consulta rápida de data e hora."""
    fuso = ctx.args[0] if ctx.args else "America/Sao_Paulo"
    hora_str = obter_hora_formatada(fuso)
    await ctx.reply(f"⏰ **Horário Atual:** `{hora_str}`")


@register_command(
    name="status",
    description="Apresenta um diagnóstico geral do estado operacional do bot.",
    usage=f"{COMMAND_PREFIX}status",
    aliases=["info"],
)
async def cmd_status(ctx: CommandContext) -> None:
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
    name="voz",
    description="Configura o modo de resposta do bot (texto, áudio com Francisca pt-BR, ou ambos).",
    usage=f"{COMMAND_PREFIX}voz [texto|audio|ambos]",
    aliases=["modo", "resposta", "modo_resposta", "audio"],
)
async def cmd_voz(ctx: CommandContext) -> None:
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
async def cmd_digest(ctx: CommandContext) -> None:
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


@register_command(
    name="gateway",
    description="Diagnóstico, telemetria e controle do Barramento Unificado de Mensagens e Outbox Anti-Spam (IDEA-24).",
    usage=f"{COMMAND_PREFIX}gateway [status|pausar|retomar|limpar]",
    aliases=["outbox", "antispam", "barramento"],
)
async def cmd_gateway(ctx: CommandContext) -> None:
    """Comando administrativo de controle e telemetria do Message Gateway."""
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


@register_command(
    name="agy",
    description="Controlador do Antigravity Remote Runner (Leitura, Telemetria & Consulta de Agentes — IDEA-23).",
    usage=f"{COMMAND_PREFIX}agy [skills|info|status|consultar] [argumentos]",
    category="Agentes & Skills (AGY)",
    example=f"{COMMAND_PREFIX}agy skills",
    aliases=["agentes", "skills_locais"],
)
async def cmd_agy(ctx: CommandContext) -> None:
    """Gerencia a inspeção e consultas analíticas aos agentes e skills locais."""
    sub = ctx.args[0].lower() if ctx.args else "skills"

    if sub in ("skills", "listar", "list"):
        skills = agy_manager.listar_skills()
        if not skills:
            await ctx.reply("⚠️ Nenhuma skill ou agente encontrado no diretório `.agents/skills/`.")
            return

        linhas = [
            f"🧠 **CATÁLOGO DE SKILLS & AGENTES LOCAIS ({len(skills)}):**",
            "*(Para consultar a persona de um agente, use: `!agy consultar <nome> <sua dúvida>`)*\n",
        ]
        for s in skills:
            desc_curta = (s["description"][:110] + "...") if len(s["description"]) > 110 else s["description"]
            linhas.append(f"• **`{s['name']}`** (`.agents/skills/{s['pasta']}/`)\n  └ {desc_curta}")

        await ctx.reply("\n".join(linhas))
        return

    if sub in ("info", "detalhes"):
        if len(ctx.args) < 2:
            await ctx.reply(f"❌ Informe o nome da skill. Exemplo: `{COMMAND_PREFIX}agy info critic`")
            return

        nome_alvo = ctx.args[1]
        skill = agy_manager.obter_skill(nome_alvo)
        if not skill:
            await ctx.reply(f"❌ Skill ou agente `{nome_alvo}` não encontrado em `.agents/skills/`.")
            return

        corpo_preview = skill["corpo"][:900] + ("..." if len(skill["corpo"]) > 900 else "")
        msg = (
            f"📋 **INSPEÇÃO DE SKILL: `{skill['name']}`**\n"
            f"📁 **Pasta:** `{skill['pasta']}`\n"
            f"📄 **Arquivo:** `{skill['path']}`\n\n"
            f"📝 **Descrição:**\n{skill['description']}\n\n"
            f"📜 **Diretrizes (Trecho):**\n```markdown\n{corpo_preview}\n```"
        )
        await ctx.reply(msg)
        return

    if sub in ("status", "telemetria"):
        st = agy_manager.obter_status_telemetria()
        msg = (
            "⚡ **TELEMETRIA DO RUNTIME LOCAL (AGY Remote Runner)**\n"
            f"• **Modo:** `{st['modo_execucao']}`\n"
            f"• **Uptime do Processo:** `{st['uptime']}`\n"
            f"• **Memória RAM Alocada:** `{st['memoria_processo_mb']} MB`\n"
            f"• **Plataforma / CPU:** `{st['plataforma']} ({st['arquitetura']})`\n"
            f"• **PID do Processo:** `{st['pid']}`\n"
            f"• **Tarefas Assíncronas Ativas:** `{st['tarefas_async_ativas']}`\n"
            f"• **Skills Locais Prontas:** `{st['total_skills_locais']}`"
        )
        await ctx.reply(msg)
        return

    if sub in ("consultar", "ask", "perguntar"):
        if len(ctx.args) < 3:
            await ctx.reply(
                f"❌ Uso correto: `{COMMAND_PREFIX}agy consultar <skill> <sua dúvida ou tema>`\n"
                f"Exemplo: `{COMMAND_PREFIX}agy consultar critic Quais os riscos de concorrência no SQLite WAL?`"
            )
            return

        nome_skill = ctx.args[1]
        consulta = " ".join(ctx.args[2:])

        await ctx.reply(f"⏳ **Consultando o especialista `{nome_skill}`...** Aguarde a análise.")
        res = await agy_manager.consultar_skill(
            nome_skill=nome_skill,
            consulta=consulta,
            user_id=str(ctx.author.id),
        )

        if not res.get("sucesso"):
            await ctx.reply(f"❌ **Falha na consulta:** {res.get('erro')}")
            return

        dados = res["dados"]
        resposta_texto = dados["resposta"]
        if len(resposta_texto) > 1850:
            resposta_texto = resposta_texto[:1840] + "\n\n*(Resposta truncada devido ao limite de caracteres do Discord)*"

        msg = (
            f"🎭 **PARECER DO ESPECIALISTA (`{dados['skill']}`):**\n\n"
            f"{resposta_texto}"
        )
        await ctx.reply(msg)
        return

    await ctx.reply(f"❓ Subcomando desconhecido. Use: `{COMMAND_PREFIX}agy [skills|info|status|consultar]`")


def _render_ascii_bar(pct: float, tamanho: int = 14) -> str:
    """Renderiza uma barra de progresso simples em caracteres ASCII."""
    preenchido = int(round((min(100.0, max(0.0, pct)) / 100.0) * tamanho))
    return "█" * preenchido + "░" * (tamanho - preenchido)


@register_command(
    name="finops",
    description="Painel FinOps, telemetria de tokens, custos de IA e controle de cotas.",
    usage=f"{COMMAND_PREFIX}finops [status|cotas|modelos|reset]",
    aliases=["tokens", "custos", "tokenomics"],
    category="FinOps & Custos",
    example=f"{COMMAND_PREFIX}finops status",
)
async def cmd_finops(ctx: CommandContext) -> None:
    """Gerencia a observabilidade de custos, limites de tokens e economia local."""
    subcomando = ctx.args[0].lower() if ctx.args else "status"

    # Força flush de itens pendentes na fila antes de exibir relatórios
    await finops_manager.flush()

    if subcomando in ("status", "resumo"):
        res = finops_manager.obter_resumo_finops(dias=30)
        total_tokens = res["total_tokens"]
        custo_usd = res["total_cost_usd"]
        custo_brl = res["total_cost_brl"]
        econ_brl = res["economia_local_brl"]
        pct_loc = res["pct_local"]
        calls = res["total_calls"]
        fallbacks = res["total_fallbacks"]

        # Obtém também o consumo do dia do usuário
        saldo = finops_manager.obter_saldo_cotas(ctx.author.id)
        barra_user = _render_ascii_bar(saldo["user_pct"])

        linhas = [
            "📊 **PAINEL FINOPS & OBSERVABILIDADE DE TOKENS (ÚLTIMOS 30 DIAS)**",
            "──────────────────────────────────────────────",
            f"🪙 **Tokens Totais Processados:** `{total_tokens:,}` across `{calls}` chamadas",
            f"💰 **Custo Nuvem Estimado:** `$ {custo_usd:.4f}` (~`R$ {custo_brl:.2f}`)",
            f"🛡️ **Economia Gerada pelo Nó Local:** `R$ {econ_brl:.2f}` (`{pct_loc}%` das inferências)",
            f"⚡ **Fallbacks por Cota Executados:** `{fallbacks}`",
            "──────────────────────────────────────────────",
            f"📈 **Sua Cota Diária ({ctx.author.display_name}):**",
            f"`[{barra_user}]` **{saldo['user_pct']}%** (`{saldo['user_consumed']:,}` / `{saldo['user_limit']:,}` tokens)",
            f"🤖 **Cota Diária de Background:** `{saldo['bg_consumed']:,}` / `{saldo['bg_limit']:,}` tokens (`{saldo['bg_pct']}%`)",
            "──────────────────────────────────────────────",
            f"💡 *Dica:* Use `{COMMAND_PREFIX}finops cotas` ou `{COMMAND_PREFIX}finops modelos` para detalhes.",
        ]
        await ctx.reply("\n".join(linhas))
        return

    if subcomando in ("cotas", "cota", "limite", "saldo"):
        saldo = finops_manager.obter_saldo_cotas(ctx.author.id)
        b_user = _render_ascii_bar(saldo["user_pct"], 18)
        b_bg = _render_ascii_bar(saldo["bg_pct"], 18)

        status_user = "⚠️ **COTA EXCEDIDA!** (Operando em Fallback Local)" if saldo["user_exceeded"] else "🟢 **Dentro do Limite**"
        status_bg = "⚠️ **COTA BACKGROUND EXCEDIDA!**" if saldo["bg_exceeded"] else "🟢 **Dentro do Limite**"

        linhas = [
            f"📈 **BALANÇO DE COTAS DIÁRIAS — {ctx.author.display_name}**",
            "──────────────────────────────────────────────",
            f"👤 **Cota Interativa do Usuário:** {status_user}",
            f"`[{b_user}]` **{saldo['user_pct']}%**",
            f"• Consumo Hoje: `{saldo['user_consumed']:,}` tokens",
            f"• Teto Diário: `{saldo['user_limit']:,}` tokens",
            f"• Restante Nuvem: `{max(0, saldo['user_limit'] - saldo['user_consumed']):,}` tokens",
            "",
            f"🤖 **Cota do Sistema (Tarefas em Background):** {status_bg}",
            f"`[{b_bg}]` **{saldo['bg_pct']}%**",
            f"• Consumo Hoje: `{saldo['bg_consumed']:,}` tokens",
            f"• Teto Diário: `{saldo['bg_limit']:,}` tokens",
            "──────────────────────────────────────────────",
            "🛡️ *Garantia:* Ao atingir 100% da cota, o bot chaveia automaticamente para o modelo local do LM Studio sem travar a conversa.",
        ]
        await ctx.reply("\n".join(linhas))
        return

    if subcomando in ("modelos", "ranking"):
        ranking = finops_manager.obter_ranking_modelos(dias=30)
        if not ranking:
            await ctx.reply("ℹ️ Nenhum registro de inferência encontrado nos últimos 30 dias.")
            return

        linhas = [
            "🏆 **RANKING DE CONSUMO POR MODELO (ÚLTIMOS 30 DIAS)**",
            "──────────────────────────────────────────────",
        ]
        for idx, item in enumerate(ranking[:10], start=1):
            tipo = "🏠 Local" if item["is_local"] else "⚡ Cloud"
            linhas.append(
                f"`#{idx:02d}` **{item['model']}** ({tipo})\n"
                f"     • `{item['tokens']:,}` tokens | `{item['calls']}` chamadas | Custo: `$ {item['cost_usd']:.4f}`"
            )
        linhas.append("──────────────────────────────────────────────")
        await ctx.reply("\n".join(linhas))
        return

    if subcomando in ("reset", "resetar"):
        alvo_id = ctx.args[1] if len(ctx.args) > 1 else str(ctx.author.id)
        finops_manager.resetar_cota_usuario(alvo_id)
        await ctx.reply(f"✅ **Cota diária resetada com sucesso para o identificador:** `{alvo_id}`.")
        return

    await ctx.reply(
        f"❓ Subcomando FinOps não reconhecido.\n"
        f"Use: `{COMMAND_PREFIX}finops [status | cotas | modelos | reset]`"
    )


