# Especificações Gerais do Sistema — Discord AI Bot (Antigravity)

**Versão da Especificação:** 3.6.0  
**Data:** 14 de Novembro de 2026  
**Status:** Aprovado / Em Produção (v3.6.0)  
**Escopo:** Módulo do Discord Bot integrado ao LM Studio (OpenAI-compatible API) e Google Gemini API (Roteamento Híbrido Local/Nuvem) com Message Gateway Outbox, Memória Dual SQLite WAL / ChromaDB e Arquitetura Modular

---

## 1. Visão Geral e Propósito

O subsistema **Discord AI Bot (Antigravity)** é um assistente conversacional inteligente que opera na plataforma Discord. Ele conecta canais de texto, mensagens diretas e threads a instâncias locais de Modelos de Linguagem de Larga Escala (LLMs) executadas via **LM Studio** com failover automático para a **Google Gemini API**, com memória persistente de conversação, suporte a **Function Calling** (Tools com Tool RAG semântico), **Comandos de Prefixo** (`!`) modularizados e **UI Interativa** (`discord.ui`).

### 1.1 Objetivos Principais
1. **Desacoplamento e Arquitetura Hexagonal:** Separação estrita de responsabilidades entre infraestrutura de rede (Discord.py / Message Gateway Outbox), persistência de dados (SQLite WAL), memória vetorial semântica (ChromaDB), barramento de ferramentas (Tools Registry modular), barramento de comandos (`!`), cliente LLM assíncrono híbrido e componentes visuais de UI.
2. **Alta Extensibilidade:**
   - Adição trivial de novas ferramentas para a LLM via decorador `@register_tool` organizado em 11 módulos de domínio sob `discord/tools/`.
   - Adição trivial de novos comandos de chat via decorador `@register_command` organizado em 6 módulos temáticos sob `discord/commands/`.
3. **Resiliência Máxima do Event Loop (Prevenção de Queda de Heartbeat):**
   - Eliminação absoluta de bloqueios síncronos na thread principal do `asyncio`. Todas as chamadas de inferência à LLM, operações de disco, SQLite WAL, PyMuPDF, ChromaDB e processamento de áudio (faster-whisper / edge-tts) rodam de forma não-bloqueante (`AsyncOpenAI`, `aiohttp` e `asyncio.to_thread`), impedindo que o Discord Gateway encerre a sessão do bot (`heartbeat blocked`).
4. **Resiliência de Rede & Anti-Spam (Message Gateway Outbox):**
   - Despacho físico de mensagens desacoplado através de um worker em segundo plano com fila de prioridades (`PRIORITY_HIGH`, `PRIORITY_NORMAL`, `PRIORITY_LOW`), rate limiting adaptativo no modelo Leaky Bucket (máx. 4 req/s) e descarte determinístico de mensagens duplicadas em rajadas (janela de 5 segundos).
5. **Persistência Histórica & Dual Memory:**
   - Armazenamento relacional em SQLite WAL de mensagens por usuário com concatenação de envios consecutivos da mesma role e truncamento seguro.
   - Indexação vetorial semântica no ChromaDB isolada em três coleções: memória conversacional de longo prazo (`{user}_memory`), base documental de leitura profunda (`pdf_{user}_{doc_id}`) e tópicos compartilhados por canal (`topic_notes_{channel_id}`).
6. **Divisão e Formatação Automática de Saída:**
   - Respeito ao limite estrito de 2000 caracteres do Discord, dividindo parágrafos longos em blocos de até 1900 caracteres sem truncar palavras no meio.

---

## 2. Arquitetura de Alto Nível (v3.6.0)

```mermaid
graph TD
    User([Usuário no Discord]) -->|Envia Mensagem / Anexo / Clique| DiscordGateway[Discord Gateway / discord.py]
    DiscordGateway -->|on_message / on_interaction| MessageHandler[Message Handler]
    
    MessageHandler --> ContextIsolation[Context Isolation - ContextVars & Lock]
    
    ContextIsolation -->|Anexo de Áudio?| AudioPipeline[Pipeline faster-whisper / Transcrição]
    ContextIsolation -->|Anexo de PDF?| PDFPipeline[Pipeline PDF Manager / PyMuPDF]
    ContextIsolation -->|Interação UI?| UIComponents[UI Components - discord.ui Views]
    
    ContextIsolation -->|Começa com '!'?| CommandRouter{Roteador de Comandos}
    CommandRouter -->|Sim| CommandRegistry[Command Registry - commands/]
    CommandRegistry -->|Executa| ThematicCommands[6 Módulos: ai, calendar, knowledge, productivity, system, web]
    ThematicCommands -->|Despacha via Outbox| MessageGateway[Message Gateway Outbox]

    CommandRouter -->|Não / Conversação Natural| DB_SaveUser[database.salvar_mensagem - SQLite WAL]
    DB_SaveUser --> DB_GetHist[database.obter_historico]
    DB_GetHist --> SQLite[(SQLite WAL: chat_memory.db)]

    DB_GetHist --> PersonaCheck[Persona & Override por Canal]
    PersonaCheck --> ChromaRAG[ChromaDB Dual RAG: {user}_memory, topic_notes_{channel}]
    ChromaRAG --> Chroma[(ChromaDB: vector_db/)]

    ChromaRAG --> ToolFilter[Tool RAG - Seleção Dinâmica Top-K via Embeddings]
    ToolFilter --> Typing[Ativa message.channel.typing]
    Typing --> LLMClient[llm_client.gerar_resposta]
    
    LLMClient -->|Primário: Local Request| LMStudio[LM Studio / LLM API Local]
    LMStudio -.->|Timeout / Falha| GeminiAPI[Failover: Google Gemini API Nuvem]
    
    LLMClient -->|Tool Calls Solicitadas?| ToolCheck{Requer Tool?}
    ToolCheck -->|Sim| ToolsRegistry[Tools Registry - tools/]
    ToolsRegistry -->|Executa em thread pool| ToolsExecution[11 Módulos de Domínio]
    ToolsExecution -->|Retorno Estruturado| LLMClient
    
    ToolCheck -->|Não| FinalProcessing[Processamento da Resposta Final]
    FinalProcessing --> DB_SaveAssistant[database.salvar_mensagem - assistant]
    FinalProcessing --> Chroma_Save[Vetorização Assíncrona no ChromaDB]
    FinalProcessing --> TTSCheck{Modo Áudio / Ambos?}
    TTSCheck -->|Sim| TTSPipeline[Síntese Vocal edge-tts - Francisca]
    TTSCheck -->|Não| ChunkSplit[utils.dividir_mensagem <= 1900 chars]
    
    TTSPipeline --> MessageGateway
    ChunkSplit --> MessageGateway
    UIComponents --> MessageGateway
    
    MessageGateway -->|Fila com Prioridades + Leaky Bucket 4 req/s + Anti-Spam| DiscordGateway
```

---

## 3. Fluxo de Vida de uma Mensagem

1. **Recepção:** O evento `on_message` é capturado pelo `client` Discord e repassado para `message_handler.processar_mensagem`.
2. **Validações Iniciais:**
   - Se o autor for o próprio bot (`message.author == client.user`), a mensagem é imediatamente descartada.
   - Mensagens vazias são ignoradas.
3. **Isolamento de Sessão:** As variáveis de contexto (`ContextVars`) são inicializadas via `context_manager.py` e um lock por usuário/canal é adquirido para mitigar race conditions.
4. **Processamento Especial de Anexos:**
   - **Áudio:** Se o anexo for mensagem de voz ou áudio, é transcrito em segundo plano via `faster-whisper` (`voice_manager.py`) e seu texto alimenta o fluxo conversacional normal.
   - **PDF:** Se o anexo for `.pdf`, é salvo assíncronamente na pasta dedicada do usuário `discord/pdf/{user}/` e indexado para leitura profunda (`pdf_rag_manager.py`).
5. **Avaliação de Comandos (`!`):**
   - Se o conteúdo inicia com `COMMAND_PREFIX` (padrão `!`):
     - O texto é decomposto em nome do comando e argumentos.
     - Se o comando existir no registro modular em `discord/commands/`, é executado e a resposta é despachada via `message_gateway.dispatch(...)` sem acionar a LLM.
6. **Persistência de Entrada:** A mensagem do usuário é registrada no banco SQLite WAL associada ao `user_id`.
7. **Identidade & Personas por Canal:**
   - O handler verifica se o canal possui uma persona customizada configurada em `channel_personas`. Se positivo, aplica overrides de `system_prompt`, `temperature` e modelo LLM, acionando o envio por **Webhook Masquerade** (nome e avatar temáticos).
8. **Montagem de Contexto e Memória RAG:**
   - O histórico recente (últimas $N$ mensagens, padrão 10) é extraído do banco SQLite e higienizado.
   - Uma busca preventiva no ChromaDB recupera memórias relevantes de `{user}_memory` e tópicos do canal `topic_notes_{channel_id}`, injetando-os no prompt.
9. **Filtragem Semântica de Ferramentas (Tool RAG):**
   - O vetor da mensagem do usuário é comparado com os embeddings das 30+ ferramentas registradas. As Top-5 ferramentas mais relevantes ($\ge 0.20$ de similaridade) são selecionadas dinamicamente.
10. **Inferência LLM & Roteamento Híbrido:**
    - A solicitação é enviada primariamente ao endpoint local do LM Studio via `AsyncOpenAI`.
    - Se o LM Studio estiver inacessível ou sofrer timeout, o `llm_client.py` executa failover automático para a **Google Gemini API** (`gemini-1.5-flash` ou `gemini-1.5-pro`).
11. **Ciclo de Function Calling:**
    - Caso a LLM retorne `tool_calls`, o `ToolRegistry` despacha as funções não-bloqueantes em thread pool e reenvia os resultados até a resposta final (máx. 5 iterações).
12. **Persistência de Saída & Despacho Outbox:**
    - A resposta do assistente é gravada no SQLite WAL e indexada no ChromaDB.
    - Se o usuário estiver no modo `audio` ou `ambos`, sintetiza áudio via `edge-tts`.
    - As mensagens finais são divididas em blocos $\le 1900$ caracteres e enfileiradas no **Message Gateway Outbox** para entrega confiável no Discord.

---

## 4. Camada de Persistência (SQLite WAL)

O banco de dados relacional é mantido no arquivo configurável `chat_memory.db` com journaling em modo **WAL (Write-Ahead Logging)** e *Foreign Keys* ativadas compulsoriamente.

### 4.1 Esquema Relacional Consolidado (10 Tabelas)

```sql
-- Histórico Conversacional
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_messages_user_id ON messages (user_id, id DESC);

-- Preferências de Usuário (Modo de Resposta, Modelo Preferido)
CREATE TABLE IF NOT EXISTS user_settings (
    user_id TEXT PRIMARY KEY,
    response_mode TEXT NOT NULL DEFAULT 'texto',
    preferred_model TEXT,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Sistema de Listas Relacionais
CREATE TABLE IF NOT EXISTS user_lists (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    name TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, name)
);

CREATE TABLE IF NOT EXISTS list_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    list_id INTEGER NOT NULL REFERENCES user_lists(id) ON DELETE CASCADE,
    item_text TEXT NOT NULL,
    concluido INTEGER NOT NULL DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Lembretes Agendados
CREATE TABLE IF NOT EXISTS reminders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    channel_id TEXT NOT NULL,
    message TEXT NOT NULL,
    remind_at TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pendente',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_reminders_status_time ON reminders (status, remind_at);

-- Assinaturas do Resumo Matinal (Morning Digest)
CREATE TABLE IF NOT EXISTS morning_digest_subscriptions (
    user_id TEXT PRIMARY KEY,
    channel_id TEXT NOT NULL,
    scheduled_time TEXT NOT NULL DEFAULT '08:00',
    enabled INTEGER NOT NULL DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Knowledge Hub & Tópicos por Canal
CREATE TABLE IF NOT EXISTS topic_notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    channel_id TEXT NOT NULL,
    topic TEXT NOT NULL,
    note TEXT NOT NULL,
    created_by TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_topic_notes_channel_topic ON topic_notes (channel_id, topic);

-- Central de Prompts & Templates
CREATE TABLE IF NOT EXISTS prompts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    template TEXT NOT NULL,
    description TEXT,
    created_by TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Personas por Canal & Overrides Cognitivos
CREATE TABLE IF NOT EXISTS channel_personas (
    channel_id TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    avatar_url TEXT,
    system_prompt TEXT NOT NULL,
    temperature REAL DEFAULT 0.7,
    model_override TEXT,
    is_locked INTEGER NOT NULL DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Histórico de Evolução Semanal de Personas (Metamorfose)
CREATE TABLE IF NOT EXISTS persona_evolution_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    channel_id TEXT NOT NULL,
    previous_name TEXT NOT NULL,
    previous_prompt TEXT NOT NULL,
    summary_of_changes TEXT NOT NULL,
    evolved_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

---

## 5. Memória Vetorial & RAG Semântico (ChromaDB)

O subsistema vetorial gerencia representações densas calculadas localmente pelo LM Studio (`text-embedding-qwen3-embedding-4b`, 2560 dimensões) e indexadas em coleções dedicadas:

1. **`{user}_memory`:** Memória conversacional de longo prazo isolada por usuário, permitindo recordar fatos, projetos e preferências passadas com busca preventiva e deduplicação semântica.
2. **`pdf_{user}_{doc_id}`:** Indexação estruturada de documentos PDF chunked pelo PyMuPDF, permitindo leitura aprofundada via comando `!perguntar_pdf` e ferramenta de busca em documentos.
3. **`topic_notes_{channel_id}`:** Base de conhecimento contextual compartilhada entre os participantes de um canal ou thread, permitindo consultas semânticas por tópicos via `!buscar_topico`.

---

## 6. Sistema Modular de Comandos com Prefixo (`!`)

Os comandos são estruturados em 6 módulos temáticos sob [`discord/commands/`](file:///Users/rodrigomodel/antigravity/discord/commands/), registrados através do decorador `@register_command` e catalogados automaticamente na ajuda em duas etapas (`!ajuda`):

| Módulo | Arquivo de Origem | Comandos Suportados |
| :--- | :--- | :--- |
| **Geral & Diagnóstico** | [`system_commands.py`](file:///Users/rodrigomodel/antigravity/discord/commands/system_commands.py) | `!ajuda`, `!ping`, `!limpar`, `!historico`, `!hora`, `!modelo`, `!status`, `!voz`, `!painel`, `!ui_menu` |
| **Agenda Google** | [`calendar_commands.py`](file:///Users/rodrigomodel/antigravity/discord/commands/calendar_commands.py) | `!agenda`, `!agendar`, `!desmarcar` |
| **Listas & Produtividade** | [`productivity_commands.py`](file:///Users/rodrigomodel/antigravity/discord/commands/productivity_commands.py) | `!listas`, `!lista`, `!ticar`, `!limpar_lista`, `!lembrete`, `!lembretes`, `!cancelar_lembrete`, `!resumo`, `!assinar_resumo`, `!cancelar_resumo` |
| **Arquivos & Conhecimento**| [`knowledge_commands.py`](file:///Users/rodrigomodel/antigravity/discord/commands/knowledge_commands.py) | `!pdfs`, `!enviar`, `!memoria`, `!limpar_memoria`, `!perguntar_pdf`, `!topico`, `!topicos`, `!salvar_topico`, `!limpar_topico`, `!buscar_topico` |
| **Web & Pesquisa** | [`web_commands.py`](file:///Users/rodrigomodel/antigravity/discord/commands/web_commands.py) | `!buscar_web`, `!pesquisa_profunda` |
| **IA, Prompts & Personas** | [`ai_commands.py`](file:///Users/rodrigomodel/antigravity/discord/commands/ai_commands.py) | `!prompt`, `!prompts`, `!salvar_prompt`, `!deletar_prompt`, `!executar_prompt`, `!persona`, `!personas`, `!set_persona`, `!clear_persona`, `!persona_evolucao` |

---

## 7. Barramento de Ferramentas da LLM (Function Calling)

As ferramentas de IA são organizadas em 11 módulos de domínio sob [`discord/tools/`](file:///Users/rodrigomodel/antigravity/discord/tools/) com registro padronizado via `@register_tool` e retornos JSON estritos (`{"sucesso": bool, "dados": Any, "erro": Optional[str]}`):

1. **`calendar_tools.py`:** Integração com Google Calendar (`listar_compromissos`, `adicionar_compromisso`, `remover_compromisso`).
2. **`datetime_tools.py`:** Consulta de fusos horários e datas (`obter_data_hora_atual`).
3. **`list_tools.py`:** Gestão de listas relacionais (`gerenciar_listas_compras_tarefas`).
4. **`pdf_tools.py`:** Operações em arquivos PDF (`listar_meus_pdfs`, `disponibilizar_pdf_usuario`, `consultar_conteudo_pdf`).
5. **`reminder_tools.py`:** Programação de lembretes ativos (`criar_lembrete_ativo`, `listar_lembretes_ativos`, `cancelar_lembrete_ativo`).
6. **`settings_tools.py`:** Preferências de áudio e modelo (`configurar_modo_resposta`, `consultar_configuracoes_usuario`).
7. **`topic_tools.py`:** Knowledge Hub por canal (`adicionar_nota_topico`, `listar_topicos_canal`, `buscar_notas_topico`).
8. **`prompt_tools.py`:** Central de templates (`salvar_template_prompt`, `obter_template_prompt`, `listar_templates_prompts`).
9. **`persona_tools.py`:** Identidade por canal (`obter_persona_canal`, `definir_persona_canal`, `resetar_persona_canal`, `forcar_evolucao_persona`).
10. **`web_tools.py`:** Pesquisa web ao vivo e leitura de URLs (`pesquisar_na_web`, `ler_pagina_web`).
11. **`research_tools.py`:** Relatórios analíticos sintetizados (`executar_deep_research`).

---

## 8. Subsistemas e Especificações de Detalhe

O ecossistema divide-se formalmente em 24 especificações granulares auditadas:

### 8.1 Módulos Internos de Infraestrutura (`discord/SPECs/modulos_internos/`)
- [`01_BANCO_DE_DADOS_SQLITE.md`](file:///Users/rodrigomodel/antigravity/discord/SPECs/modulos_internos/01_BANCO_DE_DADOS_SQLITE.md) — SQLite WAL, DDL de 10 tabelas e migrações.
- [`02_PIPELINE_AUDIO_E_VOZ.md`](file:///Users/rodrigomodel/antigravity/discord/SPECs/modulos_internos/02_PIPELINE_AUDIO_E_VOZ.md) — faster-whisper e síntese vocal edge-tts.
- [`03_LLM_CLIENT_E_TOOL_CALLING.md`](file:///Users/rodrigomodel/antigravity/discord/SPECs/modulos_internos/03_LLM_CLIENT_E_TOOL_CALLING.md) — AsyncOpenAI, Function Calling loop e fallback.
- [`04_TOOL_FILTERING_RAG.md`](file:///Users/rodrigomodel/antigravity/discord/SPECs/modulos_internos/04_TOOL_FILTERING_RAG.md) — Tool RAG Top-5 via similaridade de cosseno.
- [`05_CHROMA_VECTOR_DB.md`](file:///Users/rodrigomodel/antigravity/discord/SPECs/modulos_internos/05_CHROMA_VECTOR_DB.md) — ChromaDB persistente e coleções isoladas.
- [`06_CONTEXTO_E_ISOLAMENTO_SESSAO.md`](file:///Users/rodrigomodel/antigravity/discord/SPECs/modulos_internos/06_CONTEXTO_E_ISOLAMENTO_SESSAO.md) — ContextVars e locks por canal/usuário.
- [`07_MESSAGE_GATEWAY_OUTBOX.md`](file:///Users/rodrigomodel/antigravity/discord/SPECs/modulos_internos/07_MESSAGE_GATEWAY_OUTBOX.md) — Fila de envio Outbox, Leaky Bucket e Anti-Spam.

### 8.2 Módulos Visíveis de Funcionalidade (`discord/SPECs/modulos_visiveis/`)
- [`01_GERAL_E_DIAGNOSTICO.md`](file:///Users/rodrigomodel/antigravity/discord/SPECs/modulos_visiveis/01_GERAL_E_DIAGNOSTICO.md) — Comandos diagnósticos, status e ajuda em 2 etapas.
- [`02_GOOGLE_CALENDAR.md`](file:///Users/rodrigomodel/antigravity/discord/SPECs/modulos_visiveis/02_GOOGLE_CALENDAR.md) — Sincronização e operações no Google Calendar OAuth.
- [`03_LISTAS_E_MERCADO.md`](file:///Users/rodrigomodel/antigravity/discord/SPECs/modulos_visiveis/03_LISTAS_E_MERCADO.md) — Gestão de listas de compras e tarefas relacionais.
- [`04_LEMBRETES_AGENDADOS.md`](file:///Users/rodrigomodel/antigravity/discord/SPECs/modulos_visiveis/04_LEMBRETES_AGENDADOS.md) — Lembretes ativos via background worker assíncrono.
- [`05_ARQUIVOS_E_PDFS.md`](file:///Users/rodrigomodel/antigravity/discord/SPECs/modulos_visiveis/05_ARQUIVOS_E_PDFS.md) — Armazenamento pessoal isolado e envio de anexos.
- [`06_MEMORIA_DE_LONGO_PRAZO.md`](file:///Users/rodrigomodel/antigravity/discord/SPECs/modulos_visiveis/06_MEMORIA_DE_LONGO_PRAZO.md) — Vetorização contínua e recuperação contextual do usuário.
- [`07_MODO_RESPOSTA_E_VOZ.md`](file:///Users/rodrigomodel/antigravity/discord/SPECs/modulos_visiveis/07_MODO_RESPOSTA_E_VOZ.md) — Configuração dinâmica de modos `texto`, `audio` e `ambos`.
- [`08_RESUMO_MATINAL_DIGEST.md`](file:///Users/rodrigomodel/antigravity/discord/SPECs/modulos_visiveis/08_RESUMO_MATINAL_DIGEST.md) — Worker agendado diário com briefing do dia.
- [`09_LEITURA_INTELIGENTE_E_RAG_PDFS.md`](file:///Users/rodrigomodel/antigravity/discord/SPECs/modulos_visiveis/09_LEITURA_INTELIGENTE_E_RAG_PDFS.md) — Parsing PyMuPDF e RAG dedicado de PDFs.
- [`10_ROTEAMENTO_HIBRIDO_E_GOOGLE_GEMINI.md`](file:///Users/rodrigomodel/antigravity/discord/SPECs/modulos_visiveis/10_ROTEAMENTO_HIBRIDO_E_GOOGLE_GEMINI.md) — Roteamento LM Studio $\leftrightarrow$ Google Gemini API.
- [`11_PESQUISA_WEB_E_BROWSING.md`](file:///Users/rodrigomodel/antigravity/discord/SPECs/modulos_visiveis/11_PESQUISA_WEB_E_BROWSING.md) — DuckDuckGo scraping, leitura de páginas e busca web ao vivo.
- [`12_UI_INTERATIVA_BUTTONS_E_MODALS.md`](file:///Users/rodrigomodel/antigravity/discord/SPECs/modulos_visiveis/12_UI_INTERATIVA_BUTTONS_E_MODALS.md) — Componentes visuais ricos do `discord.ui`.
- [`13_CENTRAL_DE_PROMPTS_E_TEMPLATES.md`](file:///Users/rodrigomodel/antigravity/discord/SPECs/modulos_visiveis/13_CENTRAL_DE_PROMPTS_E_TEMPLATES.md) — Biblioteca de templates interpolados por variáveis `{var}`.
- [`14_KNOWLEDGE_HUB_E_TOPICOS_POR_CANAL.md`](file:///Users/rodrigomodel/antigravity/discord/SPECs/modulos_visiveis/14_KNOWLEDGE_HUB_E_TOPICOS_POR_CANAL.md) — Base de tópicos isolada por canal com RAG.
- [`15_PERSONAS_E_OVERRIDES_POR_CANAL.md`](file:///Users/rodrigomodel/antigravity/discord/SPECs/modulos_visiveis/15_PERSONAS_E_OVERRIDES_POR_CANAL.md) — Identidade por canal, Webhook Masquerade e Metamorfose Semanal.
- [`16_PESQUISA_PROFUNDA_DEEP_RESEARCH.md`](file:///Users/rodrigomodel/antigravity/discord/SPECs/modulos_visiveis/16_PESQUISA_PROFUNDA_DEEP_RESEARCH.md) — Varredura concorrente paralela, semáforos e dossiês em Markdown.
- [`17_EXECUCAO_LOCAL_DE_SKILLS_E_TELEMETRIA_AGY.md`](file:///Users/rodrigomodel/antigravity/discord/SPECs/modulos_visiveis/17_EXECUCAO_LOCAL_DE_SKILLS_E_TELEMETRIA_AGY.md) — Antigravity Remote Runner em modo Read-Only e telemetria de processo.

---

## 9. Requisitos Não-Funcionais e Resiliência

1. **Prevenção de Queda de Gateway (Heartbeat Protection):** Todas as operações de inferência local ou em nuvem utilizam chamadas HTTP assíncronas (`AsyncOpenAI`, `aiohttp`). Nenhuma operação síncrona roda no event loop principal.
2. **Taxa Segura de Envio (Rate Limit):** O Message Gateway Outbox controla o fluxo em até 4 req/s com Leaky Bucket, mitigando HTTP 429 (`Too Many Requests`).
3. **Anti-Spam & Idempotência:** Deduplicação hash em janela móvel de 5 segundos descarta cliques ou retransmissões duplicadas.
4. **Chunking Conforme Limite do Discord:** Respostas superiores a 1900 caracteres são divididas sem truncamento de palavras via `dividir_mensagem`.
5. **Sanitização de Diretórios (Path Traversal):** Toda manipulação de arquivos utiliza `path.resolve().is_relative_to(...)`.
6. **Limpeza de Recursos Temporários:** Arquivos de áudio e PDFs transitórios são apagados compulsoriamente em blocos `finally`.

---

## 10. Variáveis de Ambiente Suportadas

| Variável | Padrão | Descrição |
| :--- | :--- | :--- |
| `DISCORD_TOKEN` | *Obrigatório* | Token de autenticação da aplicação Bot no Discord Developer Portal |
| `DISCORD_USER` | *Opcional* | ID numérico do usuário principal para filtros de permissão |
| `LM_STUDIO_URL` | `http://localhost:1234/v1` | URL base do servidor OpenAI-compatible no LM Studio |
| `LM_STUDIO_API_KEY` | `lm-studio` | Chave de API enviada no cabeçalho para o LM Studio |
| `MODELO_LLM` | `qwen/qwen3.5-9b` | Identificador do modelo principal carregado no LM Studio |
| `GEMINI_API_KEY` | *Opcional* | Chave de API para failover com a Google Gemini API |
| `GEMINI_FALLBACK_MODEL` | `gemini-1.5-flash` | Modelo de nuvem acionado em contingência de failover |
| `COMMAND_PREFIX` | `!` | Caractere ou sequência de prefixo de comandos |
| `DB_FILE` | `chat_memory.db` | Caminho do arquivo de banco de dados SQLite WAL |
| `SYSTEM_PROMPT` | *Definido em config.py* | Instruções de comportamento e persona base do assistente |
| `MAX_TOOL_CALL_ITERATIONS` | `5` | Máximo de iterações consecutivas de tools por mensagem |
| `HISTORICO_LIMITE_PADRAO` | `10` | Quantidade máxima de mensagens recuperadas para contexto |
| `GOOGLE_CREDENTIALS_FILE` | `discord/credentials.json` | Caminho das credenciais OAuth do Google Calendar |
| `GOOGLE_TOKEN_FILE` | `discord/token.json` | Caminho do token de acesso do Google Calendar |
| `CALENDAR_DEFAULT_TIMEZONE`| `America/Sao_Paulo` | Fuso horário padrão para compromissos e lembretes |
| `TOOL_FILTER_ENABLED` | `true` | Ativa a seleção semântica dinâmica de ferramentas por embeddings |
| `TOOL_FILTER_TOP_K` | `5` | Número máximo de ferramentas enviadas para a LLM |
| `TOOL_FILTER_MIN_SIMILARITY` | `0.20` | Limiar mínimo de similaridade de cosseno para inclusão da tool |
| `WHISPER_MODEL_SIZE` | `base` | Tamanho do modelo Whisper (`tiny`, `base`, `small`, etc.) |
| `WHISPER_LANGUAGE` | `pt` | Idioma padrão para transcrição de áudio (`pt` para pt-br) |
| `WHISPER_DEVICE` | `cpu` | Dispositivo de processamento do faster-whisper (`cpu`) |
| `WHISPER_COMPUTE_TYPE` | `int8` | Tipo de quantização numérica para execução rápida no Mac |
| `TTS_ENABLED` | `true` | Habilita o motor de Text-to-Speech edge-tts |
| `TTS_VOICE` | `pt-BR-FranciscaNeural` | Voz neural padrão utilizada na síntese de áudio (Francisca Brasil) |
| `TTS_DEFAULT_MODE` | `texto` | Modo de resposta padrão para novos usuários (`texto`, `audio`, `ambos`) |

---

## 📋 Matriz de Rastreabilidade & Aderência (Auditada em 2026-11-14)

| ID | Requisito da Spec | Status | Implementação no Código | Notas de Auditoria |
| :---: | :--- | :---: | :--- | :--- |
| **REQ-01** | Desacoplamento & Modularidade Hexagonal | 🟢 Aderente | [`discord/chat_discord.py:L1-L180`](file:///Users/rodrigomodel/antigravity/discord/chat_discord.py#L1-L180) | Camadas de Gateway, Handlers e Managers isoladas |
| **REQ-02** | Prevenção de Queda de Heartbeat | 🟢 Aderente | [`discord/llm_client.py:L40-L120`](file:///Users/rodrigomodel/antigravity/discord/llm_client.py#L40-L120) | `AsyncOpenAI` e `asyncio.to_thread` em 100% dos bloqueios |
| **REQ-03** | Message Gateway Outbox com Leaky Bucket | 🟢 Aderente | [`discord/message_gateway.py:L1-L260`](file:///Users/rodrigomodel/antigravity/discord/message_gateway.py#L1-L260) | Fila de prioridades, Leaky Bucket 4 req/s e Anti-Spam |
| **REQ-04** | Persistência Relacional em SQLite WAL | 🟢 Aderente | [`discord/database.py:L30-L245`](file:///Users/rodrigomodel/antigravity/discord/database.py#L30-L245) | DDL de 10 tabelas, índices e WAL mode ativo |
| **REQ-05** | Memória Vetorial de Longo Prazo | 🟢 Aderente | [`discord/vector_db.py:L25-L160`](file:///Users/rodrigomodel/antigravity/discord/vector_db.py#L25-L160) | Coleção `{user}_memory`, busca preventiva e deduplicação |
| **REQ-06** | Sistema de Comandos Modularizado (6 Módulos) | 🟢 Aderente | [`discord/commands/`](file:///Users/rodrigomodel/antigravity/discord/commands/) | 35+ comandos com `@register_command` e barrel export |
| **REQ-07** | Barramento de Ferramentas (11 Módulos) | 🟢 Aderente | [`discord/tools/`](file:///Users/rodrigomodel/antigravity/discord/tools/) | 30+ tools com `@register_tool` e retornos estruturados |
| **REQ-08** | Tool RAG Semântico Top-K | 🟢 Aderente | [`discord/tools/registry.py:L40-L180`](file:///Users/rodrigomodel/antigravity/discord/tools/registry.py#L40-L180) | Embeddings pré-computados e filtro de cosseno $\ge 0.20$ |
| **REQ-09** | Google Calendar OAuth 2.0 | 🟢 Aderente | [`discord/calendar_manager.py:L40-L195`](file:///Users/rodrigomodel/antigravity/discord/calendar_manager.py#L40-L195) | Gestão de eventos e renovação de token assíncrona |
| **REQ-10** | Listas e Tarefas Relacionais | 🟢 Aderente | [`discord/list_manager.py:L30-L185`](file:///Users/rodrigomodel/antigravity/discord/list_manager.py#L30-L185) | `user_lists` e `list_items` com formatação `⬜`/`✅` |
| **REQ-11** | Lembretes Ativos & Worker Assíncrono | 🟢 Aderente | [`discord/reminder_manager.py:L45-L210`](file:///Users/rodrigomodel/antigravity/discord/reminder_manager.py#L45-L210) | Worker a cada 10s e parsing temporal relativo/absoluto |
| **REQ-12** | Transcrição faster-whisper e Voz edge-tts | 🟢 Aderente | [`discord/voice_manager.py:L40-L220`](file:///Users/rodrigomodel/antigravity/discord/voice_manager.py#L40-L220) | Áudio `pt-br` em thread pool e síntese vocal Francisca |
| **REQ-13** | Armazenamento & Disponibilização de PDFs | 🟢 Aderente | [`discord/pdf_manager.py:L30-L140`](file:///Users/rodrigomodel/antigravity/discord/pdf_manager.py#L30-L140) | Diretório `discord/pdf/{user}/` e entrega como `discord.File` |
| **REQ-14** | Leitura Profunda e RAG de PDFs | 🟢 Aderente | [`discord/pdf_rag_manager.py:L1-L195`](file:///Users/rodrigomodel/antigravity/discord/pdf_rag_manager.py#L1-L195) | PyMuPDF + ChromaDB `pdf_{user}_{doc_id}` para `!perguntar_pdf` |
| **REQ-15** | Roteamento Híbrido Local / Google Gemini | 🟢 Aderente | [`discord/llm_client.py:L1-L320`](file:///Users/rodrigomodel/antigravity/discord/llm_client.py#L1-L320) | Failover automático de LM Studio para Gemini API |
| **REQ-16** | Pesquisa Web, Browsing & Deep Research | 🟢 Aderente | [`discord/web_search_manager.py:L1-L180`](file:///Users/rodrigomodel/antigravity/discord/web_search_manager.py#L1-L180) | Busca DuckDuckGo, scraping de URLs e relatórios analíticos |
| **REQ-17** | UI Interativa Buttons, Selects & Modals | 🟢 Aderente | [`discord/ui_components.py:L1-L220`](file:///Users/rodrigomodel/antigravity/discord/ui_components.py#L1-L220) | Views interativas nativas do `discord.ui` |
| **REQ-18** | Central de Prompts & Templates | 🟢 Aderente | [`discord/prompt_hub.py:L1-L180`](file:///Users/rodrigomodel/antigravity/discord/prompt_hub.py#L1-L180) | Gerenciamento de templates com interpolação de `{var}` |
| **REQ-19** | Knowledge Hub & Tópicos por Canal | 🟢 Aderente | [`discord/topic_manager.py:L1-L210`](file:///Users/rodrigomodel/antigravity/discord/topic_manager.py#L1-L210) | Memória contextual por canal com ChromaDB isolado |
| **REQ-20** | Personas por Canal & Metamorfose Semanal | 🟢 Aderente | [`discord/persona_manager.py:L1-L230`](file:///Users/rodrigomodel/antigravity/discord/persona_manager.py#L1-L230) | Identidade customizada, Webhook Masquerade e evolução |
| **REQ-21** | Resumo Matinal Programado (Digest) | 🟢 Aderente | [`discord/morning_digest_manager.py:L1-L230`](file:///Users/rodrigomodel/antigravity/discord/morning_digest_manager.py#L1-L230) | Briefing diário com worker matinal assíncrono |
| **REQ-22** | Chunking Conforme Limite de 2000 Chars | 🟢 Aderente | [`discord/utils.py:L20-L75`](file:///Users/rodrigomodel/antigravity/discord/utils.py#L20-L75) | Quebra em blocos de até 1900 caracteres sem truncar palavras |
| **REQ-23** | Deep Research Analítico Autônomo | 🟢 Aderente | [`discord/deep_research_manager.py:L1-L405`](file:///Users/rodrigomodel/antigravity/discord/deep_research_manager.py#L1-L405) | Varredura paralela, semáforos e dossiês Markdown |
| **REQ-24** | Antigravity Remote Runner & Telemetria Read-Only | 🟢 Aderente | [`discord/agy_manager.py:L1-L211`](file:///Users/rodrigomodel/antigravity/discord/agy_manager.py#L1-L211) | Telemetria de processo e consultas a skills locais |
| **REQ-25** | FinOps, Telemetria de Tokens & Fallback Gracioso | 🟢 Aderente | [`discord/finops_manager.py:L1-L280`](file:///Users/rodrigomodel/antigravity/discord/finops_manager.py#L1-L280) | Contabilidade de tokens, buffer SQLite WAL, circuit breaker e fallback LM Studio |
| **REQ-26** | Radar Autônomo de RSS, ArXiv e Releases GitHub | 🟢 Aderente | [`discord/radar_manager.py:L1-L640`](file:///Users/rodrigomodel/antigravity/discord/radar_manager.py#L1-L640) | Curadoria proativa de feeds, filtragem Regex -> LLM e alertas tempo real / boletim |
