# Especificação Detalhada por Módulo / Arquivo — Discord AI Bot (Antigravity)

**Versão da Especificação:** 3.6.0  
**Data:** 14 de Novembro de 2026  
**Status:** Aprovado / Em Produção (v3.6.0)  
**Escopo:** Catálogo de referência técnica detalhando todos os 45 módulos, arquivos, classes, funções e contratos de interface do subsistema do Discord Bot.

---

## 1. `config.py`

### Propósito
Centralizar a leitura de variáveis de ambiente do arquivo `.env`, normalizar caminhos relativos ao diretório base (`BASE_DIR`) e definir valores padrão seguros para todas as constantes operacionais.

### Constantes Exportadas

| Constante | Tipo | Valor Padrão / Fonte | Descrição |
|---|---|---|---|
| `BASE_DIR` | `pathlib.Path` | Diretório onde `config.py` está localizado | Ponto de ancoragem para caminhos de arquivos relativos |
| `DISCORD_TOKEN` | `str | None` | `os.getenv("DISCORD_TOKEN")` | Token de autenticação da API do Discord |
| `DISCORD_USER` | `str | None` | `os.getenv("DISCORD_USER")` | Identificador do usuário principal (opcional) |
| `LM_STUDIO_URL` | `str` | `"http://localhost:1234/v1"` | URL base para o endpoint compatível com OpenAI |
| `LM_STUDIO_API_KEY` | `str` | `"lm-studio"` | Chave enviada nos cabeçalhos de requisição HTTP |
| `MODELO_LLM` | `str` | `"qwen/qwen3.5-9b"` | Identificador do modelo de linguagem local em execução |
| `GEMINI_API_KEY` | `str | None` | `os.getenv("GEMINI_API_KEY")` | Chave de API para failover com a Google Gemini API |
| `GEMINI_FALLBACK_MODEL` | `str` | `"gemini-1.5-flash"` | Modelo em nuvem acionado em contingência de failover |
| `DB_FILE` | `str` | `str(BASE_DIR / "chat_memory.db")` | Caminho do arquivo SQLite de histórico em WAL mode |
| `COMMAND_PREFIX` | `str` | `"!"` | Prefixo usado para disparar comandos de bot |
| `MAX_DISCORD_MSG_LENGTH` | `int` | `2000` | Limite absoluto de caracteres por mensagem do Discord |
| `MAX_CHUNK_LENGTH` | `int` | `1900` | Limite de segurança para divisão de blocos de texto |
| `MAX_TOOL_CALL_ITERATIONS` | `int` | `5` | Quantidade máxima de iterações consecutivas de tools |
| `HISTORICO_LIMITE_PADRAO` | `int` | `10` | Quantidade de mensagens recuperadas para contexto |
| `LLM_TEMPERATURE` | `float` | `0.7` | Temperatura para amostragem probabilística da LLM |
| `LLM_TIMEOUT_SECONDS` | `float` | `60.0` | Timeout máximo em segundos por chamada HTTP à LLM |
| `SYSTEM_PROMPT` | `str` | Persona base com instruções operacionais | Prompt do sistema injetado no início de cada chamada |

---

## 2. `database.py`

### Propósito
Encapsular a persistência relacional do bot no SQLite com journaling em modo **WAL (Write-Ahead Logging)**, integridade referencial (*Foreign Keys* ativadas) e gerenciamento de 10 tabelas de dados.

### Funções Públicas
- `get_connection(db_path: Optional[str] = None) -> sqlite3.Connection`: Retorna conexão configurada com `row_factory = sqlite3.Row`, `timeout = 30.0` e `PRAGMA foreign_keys = ON`.
- `init_db(db_path: Optional[str] = None) -> None`: Inicializa as tabelas relacionais do sistema (`messages`, `user_settings`, `user_lists`, `list_items`, `reminders`, `morning_digest_subscriptions`, `topic_notes`, `prompts`, `channel_personas`, `persona_evolution_history`) e seus respectivos índices.
- `salvar_mensagem(user_id: str | int, role: str, content: str, db_path: Optional[str] = None) -> None`: Persiste uma mensagem no histórico. Concatena envios consecutivos da mesma role (`\n\n`) para reduzir fragmentação de contexto.
- `obter_historico(user_id: str | int, limite: int = 10, db_path: Optional[str] = None) -> List[Dict[str, str]]`: Recupera as últimas mensagens em ordem cronológica, garantindo que o diálogo inicie obrigatoriamente com a role `user`.
- `limpar_historico(user_id: str | int, db_path: Optional[str] = None) -> int`: Exclui todos os registros conversacionais do usuário.
- `contar_mensagens(user_id: str | int, db_path: Optional[str] = None) -> int`: Retorna a contagem total de mensagens registradas.

---

## 3. `utils.py`

### Propósito
Fornecer utilitários puros (sem estado) para divisão de strings, formatação markdown, manipulação de fusos horários e análise sintática de comandos.

### Funções Públicas
- `dividir_mensagem(texto: str, limite: int = 1900) -> List[str]`: Divide textos que excedem o limite do Discord priorizando quebras de parágrafo (`\n\n`), linhas (`\n`) ou espaços sem truncar palavras no meio.
- `parse_comando(conteudo: str, prefixo: str = "!") -> Tuple[Optional[str], str, List[str]]`: Avalia se o texto inicia com o prefixo e extrai `(nome_comando, argumento_bruto, lista_argumentos)`.
- `obter_hora_formatada(fuso_horario: str = "America/Sao_Paulo") -> str`: Retorna a data e hora formatada (`YYYY-MM-DD HH:MM:SS (Fuso)`).
- `formatar_bloco_codigo(conteudo: str, linguagem: str = "") -> str`: Envolve o texto em crases triplas com identificador de sintaxe markdown.

---

## 4. `tools/registry.py`

### Propósito
Mecanismo desacoplado para declaração, inspeção, sanitização e execução de ferramentas invocáveis pela LLM via Function Calling.

### Classes e Estruturas
- `ToolDefinition` (Dataclass): Armazena `name`, `description`, `parameters`, `func` e `is_async`.
- `ToolRegistry`:
  - `register(name=None, description=None, parameters=None)`: Decorador de registro de ferramentas.
  - `get_schemas() -> List[Dict[str, Any]]`: Gera a lista completa de schemas no formato padrão OpenAI Function Calling.
  - `async execute(name: str, arguments: Any) -> str`: Executa a ferramenta de forma não-bloqueante (`asyncio.to_thread` se síncrona), capturando exceções e retornando JSON estruturado (`{"sucesso": bool, "dados": Any, "erro": Optional[str]}`).

---

## 5. `tools/tool_filter.py` (Tool RAG)

### Propósito
Executar filtragem semântica inteligente de ferramentas comparando embeddings da mensagem do usuário com descrições das ferramentas para enviar apenas as mais relevantes à LLM.

### Funções Públicas
- `similaridade_cosseno(v1: List[float], v2: List[float]) -> float`: Calcula produto escalar normalizado entre dois vetores densos.
- `async inicializar_cache_ferramentas(force_reload: bool = False) -> None`: Pré-computa e armazena em cache os embeddings das ferramentas na inicialização.
- `async filtrar_ferramentas_relevantes(query: str, top_k: Optional[int] = None, min_score: Optional[float] = None) -> List[Dict[str, Any]]`: Seleciona dinamicamente as ferramentas mais aderentes (Top-5 por padrão, cosseno $\ge 0.20$).

---

## 6. `commands/registry.py`

### Propósito
Estruturar o sistema de comandos manuais iniciados pelo prefixo `!`, desacoplando os comandos do loop principal de mensagens.

### Classes e Estruturas
- `CommandContext`: Encapsula a invocação do comando com referências a `message`, `client`, `command_name`, `args`, `arg_str`, `reply(content)` e `send(content)`.
- `CommandDefinition` (Dataclass): Metadados de nome, função executora, descrição, sintaxe (`usage`), apelidos (`aliases`) e categoria.
- `CommandRegistry`:
  - `register(name=None, description=None, usage=None, aliases=None, category=None)`: Decorador de registro.
  - `get_command(name: str) -> Optional[CommandDefinition]`: Busca por nome exato ou alias cadastrado.
  - `async dispatch(message: discord.Message, client: discord.Client) -> bool`: Executa o comando caso a mensagem inicie com o prefixo. Retorna `True` se tratada.
  - `get_all_commands() -> List[CommandDefinition]`: Retorna a lista completa ordenada para a central de ajuda.

---

## 7. `commands/builtins.py`

### Propósito
Barrel exporter retrocompatível para reexportar comandos nativos dos 6 módulos temáticos em `discord/commands/` (`ai`, `calendar`, `knowledge`, `productivity`, `system`, `web`), implementando o comando `!ajuda` em duas etapas.

---

## 8. `llm_client.py`

### Propósito
Gerenciar a comunicação HTTP com APIs de LLM de forma 100% assíncrona com **Roteamento Híbrido** e failover transparente:
- **Provedor Primário:** LM Studio Local (`AsyncOpenAI`).
- **Provedor de Contingência (Failover):** Google Gemini API (`gemini-1.5-flash` ou `gemini-1.5-pro`) acionada automaticamente em caso de indisponibilidade ou timeout local.

### Métodos Principais
- `async gerar_resposta(mensagens, tools=None, temperatura=0.7, model_override=None) -> str`: Orquestra chamadas com loop de até 5 iterações de Function Calling, capturando erros e despachando ferramentas.

---

## 9. `message_handler.py`

### Propósito
Controlador central do ciclo de vida de mensagens recebidas do Discord Gateway.

### Responsabilidades
1. Descarte de mensagens do próprio bot ou vazias.
2. Isolamento de sessão via `context_manager.py` (ContextVars e lock por usuário).
3. Interceptação assíncrona de áudios (faster-whisper) e PDFs (PyMuPDF / armazenamento seguro).
4. Despacho prioritário para comandos manuais (`commands.dispatch`).
5. Reconhecimento de personas configuradas por canal (`channel_personas`), aplicando overrides de modelo/temperatura e despacho via **Webhook Masquerade** (nome e avatar temáticos) com fallback gracioso para Embeds.
6. Consulta preventiva de memória RAG no ChromaDB (`{user}_memory` e `topic_notes_{channel_id}`).
7. Seleção dinâmica de ferramentas via Tool RAG (`tool_filter.py`).
8. Inferência com `llm_client.py` e despacho de saída formatada via **Message Gateway Outbox**.

---

## 10. `chat_discord.py`

### Propósito
Ponto de entrada operacional do bot Discord (`discord.Client`).

### Responsabilidades
- Inicialização de logging assíncrono.
- Criação e validação do esquema de banco de dados (`database.init_db()`).
- Instanciação de intents com ativação obrigatória de `message_content = True`.
- Inicialização dos workers de background (`iniciar_worker_lembretes`, `iniciar_worker_digest`, `iniciar_worker_outbox`).
- Conexão e manutenção de heartbeat com o Discord Gateway (`client.run(DISCORD_TOKEN)`).

---

## 11. `message_gateway.py`

### Propósito
Implementar o padrão **Outbox Gateway** para o envio seguro, resiliente e ordenado de mensagens e anexos à API do Discord.

### Funcionalidades
- **Fila com Prioridades:**
  - `PRIORITY_HIGH` (0): Comandos manuais imediatos do usuário.
  - `PRIORITY_NORMAL` (1): Respostas conversacionais padrão da LLM.
  - `PRIORITY_LOW` (2): Lembretes e digests matinais de background.
- **Rate Limiting Adaptativo (Leaky Bucket):** Taxa máxima controlada de até 4 requisições por segundo.
- **Anti-Spam & Deduplicação:** Hash SHA-256 de mensagens recentes com descarte automático de duplicatas em janela móvel de 5 segundos.
- **Método `dispatch(target, content, embed=None, file=None, view=None, priority=PRIORITY_NORMAL)`:** Ponto de entrada assíncrono para despachar mensagens de qualquer camada.

---

## 12. `ui_components.py`

### Propósito
Fornecer componentes interativos ricos baseados no `discord.ui` (Views, Buttons, Dynamic Select Menus e Modais).

### Classes Principais
- `PaginatorView`: Navegação com botões anterior/próximo e indicador de página `1/N`.
- `ConfigMenuView`: Menu suspenso interativo para seleção de modos de resposta (`texto`, `audio`, `ambos`) e modelos de LLM.
- `PromptSelectView`: Dropdown dinâmico listando os templates cadastrados no Prompt Hub com botão de execução.
- `TopicSelectView`: Dropdown para consulta rápida de tópicos do Knowledge Hub do canal.
- `PersonaSelectView`: Dropdown para seleção e ativação de personas por canal.
- `ModalPromptCreate`: Formulário modal para criação de templates com campos de nome, descrição e template com variáveis `{var}`.

---

## 13. `prompt_hub.py`

### Propósito
Gerenciar a central relacional de prompts e templates reutilizáveis no SQLite (`prompts`).

### Funções Públicas
- `salvar_prompt(name: str, template: str, description: Optional[str], created_by: str) -> Dict[str, Any]`: Cadastra ou atualiza um template de prompt.
- `obter_prompt(name: str) -> Optional[Dict[str, Any]]`: Recupera o template cadastrado.
- `listar_prompts() -> List[Dict[str, Any]]`: Lista todos os templates cadastrados.
- `deletar_prompt(name: str) -> bool`: Remove um template do banco de dados.
- `renderizar_prompt(template: str, variaveis: Dict[str, str]) -> str`: Substitui com segurança as tags `{var}` pelos valores fornecidos.

---

## 14. `topic_manager.py`

### Propósito
Implementar o **Knowledge Hub** por canal, gerenciando tópicos e notas compartilhadas no SQLite (`topic_notes`) com busca semântica no ChromaDB (`topic_notes_{channel_id}`).

### Funções Públicas
- `adicionar_nota_topico(channel_id: str, topic: str, note: str, created_by: str) -> Dict[str, Any]`: Salva nota relacional e insere vetor na coleção do canal no ChromaDB.
- `listar_topicos_canal(channel_id: str) -> List[str]`: Retorna a lista de tópicos únicos do canal.
- `buscar_notas_topico(channel_id: str, topic: str) -> List[Dict[str, Any]]`: Consulta notas de um tópico específico.
- `buscar_notas_semanticamente(channel_id: str, query: str, top_k=3) -> List[Dict[str, Any]]`: Realiza busca semântica na coleção ChromaDB do canal.
- `limpar_topico(channel_id: str, topic: str) -> int`: Exclui as notas e vetores de um tópico no canal.

---

## 15. `persona_manager.py`

### Propósito
Gerenciar as identidades customizadas, prompts de sistema, temperaturas e modelos específicos por canal ou thread (`channel_personas`).

### Funções Públicas
- `obter_persona_canal(channel_id: str) -> Optional[Dict[str, Any]]`: Recupera a persona ativa no canal.
- `definir_identidade_canal(channel_id: str, display_name: str, age: int, bio: str, system_prompt: str) -> None`: Configura a persona multimodal do canal.
- `definir_avatar_canal(channel_id: str, avatar_url: str) -> None`: Configura a URL do avatar (ex: DiceBear).
- `definir_trava_persona_canal(channel_id: str, is_locked: bool) -> None`: Trava/destrava a persona contra metamorfoses automáticas.
- `definir_temperatura_canal(channel_id: str, temperature: float) -> None`: Ajusta a temperatura de inferência do canal.
- `definir_modelo_canal(channel_id: str, model_override: str) -> None`: Configura o modelo específico (`local`, `gemini-flash`, `gemini-pro`).
- `resetar_persona_canal(channel_id: str) -> bool`: Restaura as configurações padrão do bot no canal.

---

## 16. `persona_evolution_manager.py`

### Propósito
Controlar o ciclo semanal de metamorfose adaptativa de personas não travadas com base nas mensagens do canal.

### Funções Públicas
- `verificar_canais_para_metamorfose() -> List[str]`: Identifica canais cuja última evolução ocorreu há mais de 7 dias e que não estejam travados (`is_locked = 0`).
- `async executar_metamorfose_canal(channel_id: str, client: discord.Client) -> Dict[str, Any]`: Extrai palavras-chave do canal via `text_frequency.py`, gera nova identidade via síntese rápida e persiste o histórico em `persona_evolution_history`.
- `obter_historico_metamorfoses(channel_id: str) -> List[Dict[str, Any]]`: Recupera o álbum histórico de mutações passadas do canal.

---

## 17. `text_frequency.py`

### Propósito
Extrair termos e tópicos frequentes de conversas utilizando processamento local Bag-of-Words com remoção de stopwords em português, operando com **zero consumo de tokens de LLM**.

### Funções Públicas
- `extrair_palavras_frequentes(mensagens: List[str], top_n: int = 10) -> List[Tuple[str, int]]`: Retorna os substantivos e tópicos mais frequentes sanitizados.

---

## 18. `web_search_manager.py`

### Propósito
Realizar pesquisas ao vivo na Web via DuckDuckGo e extração de conteúdo textual limpo de URLs para enriquecer o contexto da LLM.

### Funções Públicas
- `async pesquisar_duckduckgo(query: str, max_resultados: int = 5) -> List[Dict[str, str]]`: Executa busca assíncrona retornando títulos, snippets e links.
- `async extrair_conteudo_pagina(url: str, max_chars: int = 4000) -> Dict[str, Any]`: Realiza download seguro da página HTML com `aiohttp`, parse com `BeautifulSoup` e sanitização de tags para extrair o texto principal.

---

## 19. `deep_research_manager.py`

### Propósito
Orquestrar pesquisas aprofundadas com desdobramento iterativo de sub-perguntas, consolidação de múltiplas fontes e geração de relatórios investigativos em Markdown salvos em `discord/relatorios_pesquisa/`.

### Funções Públicas
- `async executar_deep_research(tema: str, profundidade: int = 3) -> Dict[str, Any]`: Conduz pesquisa multi-round, gera síntese analítica estruturada e anexa o relatório para download no Discord.

---

## 20. `digest_manager.py`

### Propósito
Gerenciar as assinaturas de **Resumo Matinal (Morning Digest)** e o worker de envio diário agendado no canal configurado.

### Funções Públicas
- `assinar_resumo(user_id: str, channel_id: str, scheduled_time: str = "08:00") -> None`: Registra ou atualiza a assinatura do resumo matinal em `morning_digest_subscriptions`.
- `cancelar_resumo(user_id: str) -> bool`: Desativa o envio do resumo diário.
- `async iniciar_worker_digest(client: discord.Client) -> None`: Loop de verificação matinal que consolida compromissos do Google Calendar, lembretes do dia e pendências de listas, despachando via Message Gateway.

---

## 21. `vector_db.py`

### Propósito
Camada de abstração vetorial com ChromaDB e geração de embeddings via LM Studio (`text-embedding-qwen3-embedding-4b`, 2560 dimensões).

### Coleções Gerenciadas
- `{user}_memory`: Memória conversacional contínua de longo prazo isolada por usuário.
- `pdf_{user}_{doc_id}`: Indexação de documentos PDF chunked via PyMuPDF para consultas detalhadas via `!perguntar_pdf`.
- `topic_notes_{channel_id}`: Base de tópicos compartilhada por canal/thread.

### Funções Públicas
- `async gerar_embedding(texto: str) -> Optional[List[float]]`: Gera vetor denso de 2560 dimensões via endpoint local `/v1/embeddings`.
- `async salvar_memoria_vetorial(usuario: str, role: str, content: str, metadata_extra=None) -> Optional[str]`: Insere documento vetorizado na coleção.
- `async buscar_memorias_relevantes(usuario: str, query: str, top_k=3) -> List[Dict[str, Any]]`: Realiza busca semântica por similaridade de cosseno.

---

## 22. `pdf_manager.py` & `pdf_rag_manager.py`

### Propósito
Armazenamento seguro de arquivos PDF em `discord/pdf/{user}/`, proteção contra *path traversal*, indexação estruturada com PyMuPDF e resposta a perguntas analíticas sobre documentos.

### Funções Públicas
- `sanitizar_nome_usuario(usuario) -> str`: Normaliza o nome do usuário para caminhos de arquivo seguros.
- `async salvar_anexo_pdf(attachment, usuario) -> Tuple[Path, int]`: Salva anexo em disco de forma não-bloqueante.
- `listar_pdfs_usuario(usuario) -> List[Dict[str, Any]]`: Lista metadados de PDFs salvos.
- `localizar_pdf_usuario(usuario, termo) -> Optional[Path]`: Localização flexível de arquivos.
- `async indexar_pdf_para_rag(caminho_pdf: Path, usuario: str, doc_id: str) -> int`: Extrai texto por páginas via PyMuPDF e indexa chunks no ChromaDB.
- `async consultar_pdf_rag(usuario: str, doc_id: str, pergunta: str, top_k=4) -> List[str]`: Consulta semântica nos trechos do documento.

---

## 23. `google_calendar.py` & `auth_calendar.py`

### Propósito
Autenticação OAuth 2.0 (escopo Google Calendar) e operações completas na agenda oficial do usuário.

### Funções Públicas
- `verificar_status_autenticacao() -> Dict[str, Any]`: Diagnostica a presença de `credentials.json` e `token.json`.
- `obter_servico_calendar() -> Resource`: Retorna cliente autenticado da Google Calendar API v3.
- `listar_compromissos(dias_a_frente=7, data_inicio=None, max_resultados=15) -> Dict[str, Any]`: Lista eventos agendados.
- `adicionar_compromisso(titulo, inicio, fim=None, descricao='', localizacao='') -> Dict[str, Any]`: Cria novos eventos com validação de datas.
- `remover_compromisso(termo_ou_id) -> Dict[str, Any]`: Cancela compromissos existentes.

---

## 24. `list_manager.py`

### Propósito
Gestão relacional de listas personalizadas (compras, mercado, tarefas) isoladas por usuário (`user_lists` e `list_items`).

### Funções Públicas
- `obter_ou_criar_lista(user_id: str, nome_lista: str) -> int`: Criação ou recuperação de lista.
- `adicionar_item_lista(user_id: str, nome_lista: str, item_text: str) -> Dict[str, Any]`: Adiciona item pendente.
- `ticar_item_lista(user_id: str, nome_lista: str, item_identificador: str | int, concluido=None) -> Dict[str, Any]`: Alterna status de item.
- `limpar_itens_concluidos(user_id: str, nome_lista: str) -> Dict[str, Any]`: Exclui itens finalizados.
- `formatar_lista_para_exibicao(dados_lista: Dict[str, Any]) -> str`: Formata lista em Markdown com `⬜` e `✅`.

---

## 25. `reminder_manager.py`

### Propósito
Programação de avisos temporais com background worker contínuo de despacho ativo (`reminders`).

### Funções Públicas
- `interpretar_expressao_tempo(expressao: str, agora=None) -> Optional[datetime]`: Parsing de tempos relativos (`15m`, `2h`) e absolutos (`09:00`, `19/10/2026`).
- `criar_lembrete(user_id: str, channel_id: str, mensagem: str, quando_dt: datetime) -> Dict[str, Any]`: Grava novo lembrete com status `pendente`.
- `async iniciar_worker_lembretes(client: discord.Client, intervalo_segundos=10) -> None`: Loop de verificação a cada 10s e despacho citando `<@user_id>`.

---

## 26. `voice_manager.py` (Áudio faster-whisper e Voz edge-tts)

### Propósito
Transcrição assíncrona de mensagens de voz (`pt-br`) e síntese vocal neural (Francisca Brasil).

### Funções Públicas
- `eh_anexo_audio(attachment: discord.Attachment) -> bool`: Detecta arquivos de áudio e voice notes.
- `async baixar_e_transcrever_anexo_audio(attachment, idioma='pt') -> Tuple[Optional[str], Optional[str]]`: Transcreve áudio em thread pool e apaga arquivo temporário no bloco `finally`.
- `limpar_texto_para_tts(texto: str) -> str`: Higieniza formatação markdown para fala natural.
- `async sintetizar_fala_edge(texto: str, voz=TTS_VOICE) -> Tuple[Optional[Path], Optional[str]]`: Gera MP3 temporário para envio via Message Gateway.

---

## 27. Catálogo de Comandos por Módulos Temáticos (`discord/commands/`)

Os 35+ comandos do sistema dividem-se em 6 arquivos temáticos registrados com `@register_command`:

1. **`system_commands.py`:** `!ajuda`, `!ping`, `!limpar`, `!historico`, `!hora`, `!modelo`, `!status`, `!voz`, `!painel`, `!ui_menu`.
2. **`calendar_commands.py`:** `!agenda`, `!agendar`, `!desmarcar`.
3. **`productivity_commands.py`:** `!listas`, `!lista`, `!ticar`, `!limpar_lista`, `!lembrete`, `!lembretes`, `!cancelar_lembrete`, `!resumo`, `!assinar_resumo`, `!cancelar_resumo`.
4. **`knowledge_commands.py`:** `!pdfs`, `!enviar`, `!memoria`, `!limpar_memoria`, `!perguntar_pdf`, `!topico`, `!topicos`, `!salvar_topico`, `!limpar_topico`, `!buscar_topico`.
5. **`web_commands.py`:** `!buscar_web`, `!pesquisa_profunda`.
6. **`ai_commands.py`:** `!prompt`, `!prompts`, `!salvar_prompt`, `!deletar_prompt`, `!executar_prompt`, `!persona`, `!personas`, `!set_persona`, `!clear_persona`, `!persona_evolucao`.

---

## 28. Catálogo de Ferramentas de IA por Domínio (`discord/tools/`)

As 30+ ferramentas de Function Calling dividem-se em 11 módulos de domínio registrados com `@register_tool`:

1. **`calendar_tools.py`:** `listar_compromissos`, `adicionar_compromisso`, `remover_compromisso`.
2. **`datetime_tools.py`:** `obter_data_hora_atual`, `calcular_expressao`.
3. **`list_tools.py`:** `gerenciar_listas_compras_tarefas`.
4. **`pdf_tools.py`:** `listar_meus_pdfs`, `disponibilizar_pdf_usuario`, `consultar_conteudo_pdf`.
5. **`reminder_tools.py`:** `criar_lembrete_ativo`, `listar_lembretes_ativos`, `cancelar_lembrete_ativo`.
6. **`settings_tools.py`:** `configurar_modo_resposta`, `consultar_configuracoes_usuario`.
7. **`topic_tools.py`:** `adicionar_nota_topico`, `listar_topicos_canal`, `buscar_notas_topico`.
8. **`prompt_tools.py`:** `salvar_template_prompt`, `obter_template_prompt`, `listar_templates_prompts`.
9. **`persona_tools.py`:** `obter_persona_canal`, `definir_persona_canal`, `resetar_persona_canal`, `forcar_evolucao_persona`.
10. **`web_tools.py`:** `pesquisar_na_web`, `ler_pagina_web`.
11. **`research_tools.py`:** `executar_deep_research`.

---

## 📋 Matriz de Rastreabilidade & Aderência (Auditada em 2026-11-14)

| ID | Módulo / Arquivo | Status | Implementação no Código | Notas de Auditoria |
| :---: | :--- | :---: | :--- | :--- |
| **MOD-01** | `config.py` | 🟢 Aderente | [`discord/config.py:L1-L120`](file:///Users/rodrigomodel/antigravity/discord/config.py#L1-L120) | Variáveis de ambiente e caminhos validados |
| **MOD-02** | `database.py` | 🟢 Aderente | [`discord/database.py:L1-L245`](file:///Users/rodrigomodel/antigravity/discord/database.py#L1-L245) | DDL de 10 tabelas e WAL mode ativo |
| **MOD-03** | `utils.py` | 🟢 Aderente | [`discord/utils.py:L1-L90`](file:///Users/rodrigomodel/antigravity/discord/utils.py#L1-L90) | Funções puras de divisão de strings e parsing |
| **MOD-04** | `tools/registry.py` | 🟢 Aderente | [`discord/tools/registry.py:L1-L185`](file:///Users/rodrigomodel/antigravity/discord/tools/registry.py#L1-L185) | Registry assíncrono de Function Calling |
| **MOD-05** | `tools/tool_filter.py` | 🟢 Aderente | [`discord/tools/tool_filter.py:L1-L140`](file:///Users/rodrigomodel/antigravity/discord/tools/tool_filter.py#L1-L140) | Tool RAG semântico Top-K via embeddings |
| **MOD-06** | `commands/registry.py` | 🟢 Aderente | [`discord/commands/registry.py:L1-L135`](file:///Users/rodrigomodel/antigravity/discord/commands/registry.py#L1-L135) | Barramento e contexto de comandos |
| **MOD-07** | `commands/builtins.py` | 🟢 Aderente | [`discord/commands/builtins.py:L1-L40`](file:///Users/rodrigomodel/antigravity/discord/commands/builtins.py#L1-L40) | Barrel export e central de ajuda em 2 etapas |
| **MOD-08** | `llm_client.py` | 🟢 Aderente | [`discord/llm_client.py:L1-L320`](file:///Users/rodrigomodel/antigravity/discord/llm_client.py#L1-L320) | Roteamento Híbrido LM Studio $\leftrightarrow$ Gemini |
| **MOD-09** | `message_handler.py` | 🟢 Aderente | [`discord/message_handler.py:L1-L600`](file:///Users/rodrigomodel/antigravity/discord/message_handler.py#L1-L600) | Pipeline de eventos, Webhook Masquerade e RAG |
| **MOD-10** | `chat_discord.py` | 🟢 Aderente | [`discord/chat_discord.py:L1-L180`](file:///Users/rodrigomodel/antigravity/discord/chat_discord.py#L1-L180) | Entry point do bot e inicialização de workers |
| **MOD-11** | `message_gateway.py` | 🟢 Aderente | [`discord/message_gateway.py:L1-L260`](file:///Users/rodrigomodel/antigravity/discord/message_gateway.py#L1-L260) | Outbox, Leaky Bucket e Anti-Spam |
| **MOD-12** | `ui_components.py` | 🟢 Aderente | [`discord/ui_components.py:L1-L320`](file:///Users/rodrigomodel/antigravity/discord/ui_components.py#L1-L320) | Views interativas nativas do `discord.ui` |
| **MOD-13** | `prompt_hub.py` | 🟢 Aderente | [`discord/prompt_hub.py:L1-L180`](file:///Users/rodrigomodel/antigravity/discord/prompt_hub.py#L1-L180) | Templates relacionais e interpolação de `{var}` |
| **MOD-14** | `topic_manager.py` | 🟢 Aderente | [`discord/topic_manager.py:L1-L210`](file:///Users/rodrigomodel/antigravity/discord/topic_manager.py#L1-L210) | Knowledge Hub por canal com ChromaDB |
| **MOD-15** | `persona_manager.py` | 🟢 Aderente | [`discord/persona_manager.py:L1-L230`](file:///Users/rodrigomodel/antigravity/discord/persona_manager.py#L1-L230) | Identidade multimodal e Webhook Masquerade |
| **MOD-16** | `persona_evolution_manager.py` | 🟢 Aderente | [`discord/persona_evolution_manager.py:L1-L150`](file:///Users/rodrigomodel/antigravity/discord/persona_evolution_manager.py#L1-L150) | Metamorfose semanal e álbum histórico |
| **MOD-17** | `text_frequency.py` | 🟢 Aderente | [`discord/text_frequency.py:L1-L80`](file:///Users/rodrigomodel/antigravity/discord/text_frequency.py#L1-L80) | Bag-of-Words local zero-token |
| **MOD-18** | `web_search_manager.py` | 🟢 Aderente | [`discord/web_search_manager.py:L1-L180`](file:///Users/rodrigomodel/antigravity/discord/web_search_manager.py#L1-L180) | Busca DuckDuckGo e extração de páginas |
| **MOD-19** | `deep_research_manager.py` | 🟢 Aderente | [`discord/deep_research_manager.py:L1-L220`](file:///Users/rodrigomodel/antigravity/discord/deep_research_manager.py#L1-L220) | Deep Research analítico multi-round |
| **MOD-20** | `digest_manager.py` | 🟢 Aderente | [`discord/digest_manager.py:L1-L230`](file:///Users/rodrigomodel/antigravity/discord/digest_manager.py#L1-L230) | Assinaturas e worker do resumo matinal |
| **MOD-21** | `vector_db.py` | 🟢 Aderente | [`discord/vector_db.py:L1-L180`](file:///Users/rodrigomodel/antigravity/discord/vector_db.py#L1-L180) | ChromaDB persistente com 3 coleções isoladas |
| **MOD-22** | `pdf_manager.py` | 🟢 Aderente | [`discord/pdf_manager.py:L1-L160`](file:///Users/rodrigomodel/antigravity/discord/pdf_manager.py#L1-L160) | Armazenamento seguro de PDFs |
| **MOD-23** | `pdf_rag_manager.py` | 🟢 Aderente | [`discord/pdf_rag_manager.py:L1-L195`](file:///Users/rodrigomodel/antigravity/discord/pdf_rag_manager.py#L1-L195) | Indexação PyMuPDF e RAG de documentos |
| **MOD-24** | `google_calendar.py` | 🟢 Aderente | [`discord/calendar_manager.py:L1-L195`](file:///Users/rodrigomodel/antigravity/discord/calendar_manager.py#L1-L195) | Google Calendar API OAuth 2.0 |
| **MOD-25** | `list_manager.py` | 🟢 Aderente | [`discord/list_manager.py:L1-L185`](file:///Users/rodrigomodel/antigravity/discord/list_manager.py#L1-L185) | Listas relacionais de compras e tarefas |
| **MOD-26** | `reminder_manager.py` | 🟢 Aderente | [`discord/reminder_manager.py:L1-L210`](file:///Users/rodrigomodel/antigravity/discord/reminder_manager.py#L1-L210) | Worker ativo a cada 10s e parsing temporal |
| **MOD-27** | `voice_manager.py` | 🟢 Aderente | [`discord/voice_manager.py:L1-L220`](file:///Users/rodrigomodel/antigravity/discord/voice_manager.py#L1-L220) | Áudio faster-whisper e voz edge-tts |
| **MOD-28** | `commands/ai_commands.py` | 🟢 Aderente | [`discord/commands/ai_commands.py:L1-L760`](file:///Users/rodrigomodel/antigravity/discord/commands/ai_commands.py#L1-L760) | Comandos de prompts e personas |
| **MOD-29** | `commands/calendar_commands.py` | 🟢 Aderente | [`discord/commands/calendar_commands.py:L1-L120`](file:///Users/rodrigomodel/antigravity/discord/commands/calendar_commands.py#L1-L120) | Comandos da agenda Google |
| **MOD-30** | `commands/knowledge_commands.py` | 🟢 Aderente | [`discord/commands/knowledge_commands.py:L1-L320`](file:///Users/rodrigomodel/antigravity/discord/commands/knowledge_commands.py#L1-L320) | Comandos de PDFs, memória e tópicos |
| **MOD-31** | `commands/productivity_commands.py`| 🟢 Aderente | [`discord/commands/productivity_commands.py:L1-L320`](file:///Users/rodrigomodel/antigravity/discord/commands/productivity_commands.py#L1-L320) | Comandos de listas, lembretes e digest |
| **MOD-32** | `commands/system_commands.py` | 🟢 Aderente | [`discord/commands/system_commands.py:L1-L180`](file:///Users/rodrigomodel/antigravity/discord/commands/system_commands.py#L1-L180) | Comandos utilitários e diagnósticos |
| **MOD-33** | `commands/web_commands.py` | 🟢 Aderente | [`discord/commands/web_commands.py:L1-L140`](file:///Users/rodrigomodel/antigravity/discord/commands/web_commands.py#L1-L140) | Comandos de busca web e Deep Research |
| **MOD-34** | `tools/persona_tools.py` | 🟢 Aderente | [`discord/tools/persona_tools.py:L1-L300`](file:///Users/rodrigomodel/antigravity/discord/tools/persona_tools.py#L1-L300) | Tools de gestão e evolução de personas |
| **MOD-35** | `tools/prompt_tools.py` | 🟢 Aderente | [`discord/tools/prompt_tools.py:L1-L160`](file:///Users/rodrigomodel/antigravity/discord/tools/prompt_tools.py#L1-L160) | Tools de templates de prompts |
| **MOD-36** | `tools/research_tools.py` | 🟢 Aderente | [`discord/tools/research_tools.py:L1-L90`](file:///Users/rodrigomodel/antigravity/discord/tools/research_tools.py#L1-L90) | Tools de Deep Research analítico |
| **MOD-37** | `tools/topic_tools.py` | 🟢 Aderente | [`discord/tools/topic_tools.py:L1-L180`](file:///Users/rodrigomodel/antigravity/discord/tools/topic_tools.py#L1-L180) | Tools de Knowledge Hub e notas |
| **MOD-38** | `tools/web_tools.py` | 🟢 Aderente | [`discord/tools/web_tools.py:L1-L120`](file:///Users/rodrigomodel/antigravity/discord/tools/web_tools.py#L1-L120) | Tools de busca web e scraping |
