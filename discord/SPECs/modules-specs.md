# Especificação Detalhada por Módulo / Arquivo — Discord AI Bot

Este documento descreve detalhadamente cada módulo, classe, função e contrato de interface do subsistema do Discord Bot, servindo como guia de referência técnica para desenvolvedores e mantenedores.

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
| `MODELO_LLM` | `str` | `"qwen/qwen3.5-9b"` | Identificador do modelo de linguagem em execução |
| `DB_FILE` | `str` | `str(BASE_DIR / "chat_memory.db")` | Caminho do arquivo SQLite de histórico |
| `COMMAND_PREFIX` | `str` | `"!"` | Prefixo usado para disparar comandos de bot |
| `MAX_DISCORD_MSG_LENGTH` | `int` | `2000` | Limite absoluto de caracteres por mensagem do Discord |
| `MAX_CHUNK_LENGTH` | `int` | `1900` | Limite de segurança para divisão de blocos de texto |
| `MAX_TOOL_CALL_ITERATIONS` | `int` | `5` | Quantidade máxima de iterações consecutivas de tools |
| `HISTORICO_LIMITE_PADRAO` | `int` | `10` | Quantidade de mensagens recuperadas para contexto |
| `LLM_TEMPERATURE` | `float` | `0.7` | Temperatura para amostragem probabilística da LLM |
| `LLM_TIMEOUT_SECONDS` | `float` | `60.0` | Timeout máximo em segundos por chamada HTTP à LLM |
| `SYSTEM_PROMPT` | `str` | Persona padrão com instruções de concisão e bom humor | Prompt do sistema injetado no início de cada chamada |

---

## 2. `database.py`

### Propósito
Encapsular a persistência relacional do histórico conversacional no SQLite, garantindo integridade transacional, consultas ordenadas e agrupamento de mensagens consecutivas.

### Funções Públicas

#### `init_db(db_path: Optional[str] = None) -> None`
- **Descrição:** Cria a tabela `messages` e o índice `idx_messages_user_id` caso não existam.
- **Entradas:** `db_path` opcional (se omitido, utiliza `DB_FILE`).
- **Garantias:** Cria diretórios pais automaticamente caso o caminho do arquivo envolva novas pastas.

#### `salvar_mensagem(user_id: str | int, role: str, content: str, db_path: Optional[str] = None) -> None`
- **Descrição:** Persiste uma nova mensagem no histórico.
- **Regra de Concatenação:** Busca a mensagem mais recente do usuário especificado. Se a `role` for idêntica (ex: `user` seguido de outro `user`), concatena o texto (`conteudo_anterior + "\n\n" + novo_conteudo`) atualizando o registro existente. Se a `role` for diferente ou for o primeiro envio, realiza `INSERT`.
- **Validação:** Rejeita strings vazias ou compostas apenas por espaços em branco.

#### `obter_historico(user_id: str | int, limite: int = 10, db_path: Optional[str] = None) -> List[Dict[str, str]]`
- **Descrição:** Recupera as últimas `limite` mensagens para alimentar a LLM.
- **Formato de Retorno:** Lista de dicionários no formato `[{"role": str, "content": str}, ...]`, em ordem cronológica (mais antiga para mais recente).
- **Sanitização:** Descarta mensagens inaugurais que não sejam de role `user`, garantindo aderência estrita às especificações de chat da OpenAI.

#### `limpar_historico(user_id: str | int, db_path: Optional[str] = None) -> int`
- **Descrição:** Exclui todos os registros da tabela `messages` onde `user_id == ?`.
- **Retorno:** Número inteiro de linhas removidas (`cursor.rowcount`).

#### `contar_mensagens(user_id: str | int, db_path: Optional[str] = None) -> int`
- **Descrição:** Retorna a contagem total de registros do usuário.

---

## 3. `utils.py`

### Propósito
Fornecer utilitários puros (sem estado) para divisão de strings, formatação markdown, manipulação de fusos horários e análise sintática de comandos.

### Funções Públicas

#### `dividir_mensagem(texto: str, limite: int = 1900) -> List[str]`
- **Descrição:** Divide textos arbitrários que excedem o tamanho máximo aceito pelo Discord.
- **Algoritmo de Divisão Inteligente:**
  1. Procura pela última quebra de parágrafo duplo (`\n\n`) nos dois terços finais do bloco.
  2. Caso não exista, busca por quebra de linha simples (`\n`).
  3. Caso não exista, busca pelo último espaço em branco (`" "`).
  4. Como último recurso, fatia no índice exato do limite.
- **Retorno:** Lista de segmentos com comprimento $\le \text{limite}$.

#### `parse_comando(conteudo: str, prefixo: str = "!") -> Tuple[Optional[str], str, List[str]]`
- **Descrição:** Avalia se um texto inicia com o prefixo de comando.
- **Retorno:** Tupla `(nome_comando, argumento_bruto, lista_argumentos)`. Retorna `(None, "", [])` se não for comando.

#### `obter_hora_formatada(fuso_horario: str = "America/Sao_Paulo") -> str`
- **Descrição:** Retorna a data e hora formatada (`YYYY-MM-DD HH:MM:SS (Fuso)`).
- **Tratamento:** Captura erros de fuso inválido e devolve mensagem informativa amigável.

#### `formatar_bloco_codigo(conteudo: str, linguagem: str = "") -> str`
- **Descrição:** Envolve o texto em crases triplas com identificador de sintaxe markdown.

---

## 4. `tools/registry.py`

### Propósito
Fornecer o mecanismo desacoplado para declaração, inspeção e execução de ferramentas invocáveis pela LLM via Function Calling.

### Classes e Estruturas

#### `ToolDefinition` (Dataclass)
- `name: str`: Identificador único da função.
- `description: str`: Texto de ajuda instrucional para a LLM entender quando usar.
- `parameters: Dict[str, Any]`: JSON Schema dos parâmetros aceitos.
- `func: Callable`: Referência para a função Python executável.
- `is_async: bool`: Booleano identificando se a função é uma corrotina (`async def`).

#### `ToolRegistry`
- `register(name=None, description=None, parameters=None)`: Decorador para registrar funções. Se `name` for omitido, usa `func.__name__`. Se `description` for omitido, extrai de `func.__doc__`.
- `get_schemas() -> List[Dict[str, Any]]`: Gera a lista completa de schemas no padrão OpenAI Function Calling (`{"type": "function", "function": {...}}`).
- `async execute(name: str, arguments: Any) -> str`: Executa a função pelo nome. Converte automaticamente strings JSON em dicionários. Se a função for síncrona, delega para `asyncio.to_thread` para não bloquear a thread principal. Captura exceções e retorna o erro como texto.

---

## 5. `tools/datetime_tools.py`

### Propósito
Implementar ferramentas operacionais de data, hora e cálculos matemáticos.

### Tools Registradas

#### `obter_hora_atual(fuso_horario: str = "America/Sao_Paulo") -> str`
- Informa o horário oficial com suporte a qualquer identificador IANA (ex: `UTC`, `America/New_York`).

#### `calcular_expressao(expressao: str) -> str`
- Avalia expressões matemáticas aritméticas e científicas com segurança em ambiente isolado (sem acesso a `__builtins__`), disponibilizando funções matemáticas como `sqrt`, `sin`, `cos`, `round`, `abs`, `pi`, `e`.

---

## 6. `commands/registry.py`

### Propósito
Estruturar o sistema de comandos manuais iniciados pelo caractere `!`, desacoplando os comandos do loop principal de mensagens.

### Classes e Estruturas

#### `CommandContext`
- Fornece o contexto de invocação do comando:
  - `message`: Instância da mensagem recebida.
  - `client`: Instância do cliente Discord.
  - `command_name`: Nome acionado.
  - `args`: Lista de argumentos parsed (`List[str]`).
  - `arg_str`: Texto contínuo dos argumentos.
  - `reply(content)`: Envia resposta referenciando a mensagem do autor.
  - `send(content)`: Envia mensagem simples no canal.

#### `CommandDefinition` (Dataclass)
- Representa um comando registrado com metadados de nome, função executora, descrição, sintaxe de uso (`usage`), apelidos (`aliases`) e status assíncrono.

#### `CommandRegistry`
- `register(name=None, description=None, usage=None, aliases=None)`: Decorador de registro.
- `get_command(name: str) -> Optional[CommandDefinition]`: Busca por nome exato ou apelido cadastrado.
- `async dispatch(message: discord.Message, client: discord.Client) -> bool`: Executa o comando caso a mensagem inicie com o prefixo configurado. Retorna `True` se a mensagem foi tratada.
- `get_all_commands() -> List[CommandDefinition]`: Retorna a lista completa ordenada para montagem de telas de ajuda.

---

## 7. `commands/builtins.py`

### Propósito
Implementar os comandos utilitários e administrativos nativos do bot.

### Catálogo de Comandos Implementados

1. **`cmd_ajuda` (`!ajuda`, `!help`, `!comandos`):** Gera dinamicamente o catálogo de todos os comandos registrados, sua sintaxe e descrição.
2. **`cmd_ping` (`!ping`, `!latencia`):** Calcula e responde com a latência real do Discord Gateway em ms (`client.latency * 1000`).
3. **`cmd_limpar` (`!limpar`, `!clear`, `!reset`):** Remove o histórico de mensagens do usuário chamador no SQLite via `database.limpar_historico`.
4. **`cmd_historico` (`!historico`, `!contexto`):** Apresenta o total de mensagens persistidas e uma prévia truncada dos últimos diálogos.
5. **`cmd_hora` (`!hora`, `!time`, `!data`):** Consulta direta de data e hora atual.
6. **`cmd_modelo` (`!modelo`, `!llm`, `!ia`):** Exibe o nome do modelo LLM configurado e o endereço do endpoint LM Studio.
7. **`cmd_status` (`!status`, `!info`):** Exibe painel com diagnóstico geral de conectividade, servidores ativos, latência e usuário do bot.
8. **`cmd_pdfs` (`!pdfs`, `!listar_pdfs`, `!meus_pdfs`):** Consulta a pasta pessoal do usuário e lista os nomes dos PDFs, tamanhos formatados e datas de modificação.
9. **`cmd_enviar` (`!enviar <nome>`, `!baixar`, `!disponibilizar`):** Localiza o PDF por correspondência flexível e envia o arquivo original no canal como anexo (`discord.File`).
10. **`cmd_memoria` (`!memoria <termo>`, `!lembrar`, `!rag`):** Realiza busca semântica na coleção `{user}_memory` do ChromaDB exibindo os fragmentos recuperados.
11. **`cmd_limpar_memoria` (`!limpar_memoria`, `!reset_memoria`):** Exclui e recria a coleção vetorial do usuário no ChromaDB.
12. **`cmd_agenda` (`!agenda [dias]`, `!calendario`, `!eventos`):** Consulta e lista os próximos compromissos da agenda do Google.
13. **`cmd_agendar` (`!agendar <titulo> | <inicio> [| <fim>]`):** Cria um novo evento na agenda Google.
14. **`cmd_desmarcar` (`!desmarcar <termo>`, `!cancelar_evento`):** Remove um compromisso da agenda do Google por ID ou correspondência de título.

---

## 8. `llm_client.py`

### Propósito
Gerenciar a comunicação HTTP com a API compatível com OpenAI (LM Studio) de forma 100% assíncrona e orquestrar o loop iterativo de Function Calling.

### Classe `LLMClient`
- **Atributos:** `base_url`, `api_key`, `model`, `client` (instância de `openai.AsyncOpenAI`).
- **Método `gerar_resposta(mensagens, tools=None, temperatura=0.7) -> str`:**
  - Realiza chamadas HTTP assíncronas através de `await self.client.chat.completions.create(...)`.
  - Se a resposta contiver `tool_calls`, itera sobre as chamadas solicitadas, executa cada uma através de `tools.execute_tool(nome, argumentos)` e alimenta o histórico com mensagens de role `tool` contendo o respectivo `tool_call_id`.
  - Reenvia a requisição para a LLM com o acervo probatório da ferramenta até obter texto conclusivo ou até atingir o limite `MAX_TOOL_CALL_ITERATIONS`.
  - Trata falhas de rede (`ConnectionError`) quando o servidor do LM Studio estiver indisponível.

---

## 9. `message_handler.py`

### Propósito
Controlar o pipeline completo de eventos de mensagem do Discord.

### Função Principal
#### `async processar_mensagem(message: discord.Message, client: discord.Client) -> None`
- **Etapas do Pipeline:**
  1. Rejeição de mensagens próprias (`message.author == client.user`).
  2. Interceptação e salvamento de anexos PDF em `discord/pdf/{user}/` com confirmação visual no canal.
  3. Descarte de mensagens que não possuam conteúdo textual nem anexos.
  4. Configuração de contexto da requisição (`set_current_user` e `clear_pending_files`).
  5. Despacho prioritário para o barramento de comandos (`commands.handle_command`). Caso seja comando, encerra imediatamente.
  6. Reconhecimento de saudações rápidas (ex: `hello bot`).
  7. Gravação da mensagem do usuário no banco SQLite.
  8. Abertura do indicador de digitação no canal (`async with message.channel.typing()`).
  9. Recuperação do histórico higienizado no SQLite.
  10. Envio da solicitação assíncrona ao `llm_client`.
  11. Gravação da resposta da LLM no SQLite.
  12. Divisão em pedaços seguros com `dividir_mensagem` e transmissão final no canal Discord.
  13. Envio físico de quaisquer arquivos PDF anexados solicitados pelas tools (`get_pending_files`).
  14. Captura resiliente de erros com fallbacks automáticos para listagem e entrega de PDFs caso a LLM esteja offline.

---

## 10. `chat_discord.py`

### Propósito
Ponto de entrada operacional do aplicativo.

### Responsabilidades
- Inicialização de logging com formato `%(asctime)s [%(levelname)s] %(name)s: %(message)s`.
- Chamada de inicialização do esquema do banco de dados (`database.init_db()`).
- Configuração de `discord.Intents` com ativação de `message_content = True`.
- Instanciação de `discord.Client`.
- Registro dos listeners de evento `on_ready` (imprimindo resumo completo de configuração, modelo e ferramentas carregadas) e `on_message` (delegando para `processar_mensagem`).
- Validação do token de autenticação e execução com `client.run(DISCORD_TOKEN)`.

---

## 11. `pdf_manager.py`

### Propósito
Isolamento do acervo documental dos usuários, persistência de arquivos enviados e mecanismo de busca inteligente de PDFs.

### Funções Públicas
- `sanitizar_nome_usuario(usuario: str | discord.User) -> str`: Normaliza nomes para paths seguros no sistema de arquivos.
- `obter_pasta_usuario(usuario) -> pathlib.Path`: Resolve e cria a pasta `discord/pdf/{user}/`.
- `formatar_tamanho(bytes_qty: int) -> str`: Retorna tamanhos legíveis (`B`, `KB`, `MB`).
- `async salvar_anexo_pdf(attachment, usuario) -> Tuple[Path, int]`: Salva o arquivo no disco de forma assíncrona.
- `listar_pdfs_usuario(usuario) -> List[Dict[str, Any]]`: Lista metadados de todos os PDFs do usuário.
- `localizar_pdf_usuario(usuario, termo_busca) -> Optional[Path]`: Localiza o arquivo com busca exata, sem extensão, insensível a maiúsculas/minúsculas ou parcial, garantindo proteção contra path traversal.

---

## 12. `context_manager.py`

### Propósito
Gerenciar variáveis de contexto com suporte thread-safe e isolamento por usuário durante o ciclo de vida da requisição.

### Funções Públicas
- `set_current_user(user: str) -> None`: Define o usuário da requisição ativa.
- `get_current_user() -> str`: Obtém o usuário ativo.
- `clear_pending_files(user=None) -> None`: Limpa a fila de anexos pendentes de entrega.
- `add_pending_file(path: Path, user=None) -> None`: Adiciona um arquivo à fila de entrega como anexo no Discord.
- `get_pending_files(user=None) -> List[Path]`: Recupera os arquivos pendentes de entrega para envio via `discord.File`.

---

## 13. `tools/pdf_tools.py`

### Propósito
Implementar as ferramentas de Function Calling que concedem à LLM a capacidade de listar e entregar documentos PDF.

### Tools Registradas
- **`listar_meus_pdfs()`:** Consulta os arquivos na pasta do usuário via `pdf_manager.listar_pdfs_usuario` e retorna texto estruturado para a LLM.
- **`disponibilizar_pdf_usuario(nome_arquivo: str)`:** Localiza o documento especificado e chama `context_manager.add_pending_file`, sinalizando ao `message_handler` para enviar o arquivo como anexo no canal.

---

## 14. `vector_db.py`

### Propósito
Camada de abstração e persistência vetorial com ChromaDB e geração de embeddings via LM Studio.

### Funções Públicas
- `sanitizar_nome_colecao(usuario) -> str`: Normaliza o identificador do usuário para o padrão `{user}_memory` compatível com ChromaDB.
- `obter_colecao_usuario(usuario) -> Collection`: Obtém ou cria a coleção vetorial isolada do usuário.
- `async gerar_embedding(texto: str) -> Optional[List[float]]`: Gera vetor denso de 2560 dimensões usando o modelo `text-embedding-qwen3-embedding-4b` via endpoint `/v1/embeddings` do LM Studio.
- `async salvar_memoria_vetorial(usuario: str, role: str, content: str, metadata_extra=None) -> Optional[str]`: Insere documento vetorizado na coleção `{user}_memory` com ID UUID e metadados.
- `async buscar_memorias_relevantes(usuario: str, query: str, top_k=3) -> List[Dict[str, Any]]`: Realiza busca por similaridade semântica (cosseno/distância L2) retornando os fragmentos mais pertinentes.
- `contar_memorias(usuario: str) -> int`: Retorna a contagem de fragmentos gravados para o usuário.
- `limpar_memoria_vetorial(usuario: str) -> bool`: Exclui e recria a coleção vetorial do usuário.

---

## 15. `tools/memory_tools.py`

### Propósito
Implementar ferramentas de busca ativa na memória de longo prazo para a LLM.

### Tools Registradas
- **`consultar_memoria_passada(termo_ou_pergunta: str)`:** Permite à LLM interrogar explicitamente o ChromaDB para lembrar preferências, detalhes e acontecimentos relatados pelo usuário no passado.

---

## 16. `google_calendar.py`

### Propósito
Camada de integração com a API v3 do Google Calendar para autenticação OAuth 2.0, consulta, agendamento e cancelamento de eventos.

### Funções Públicas
- `verificar_status_autenticacao() -> Dict[str, Any]`: Diagnostica a presença de `credentials.json`, `token.json` e a validade da sessão.
- `obter_servico_calendar() -> Resource`: Retorna a instância autenticada da Google Calendar API com renovação automática de token.
- `listar_compromissos(dias_a_frente=7, data_inicio=None, max_resultados=15) -> Dict[str, Any]`: Consulta e formata os próximos eventos do calendário principal.
- `adicionar_compromisso(titulo, inicio, fim=None, descricao='', localizacao='') -> Dict[str, Any]`: Cria um evento na agenda com validação de datas.
- `remover_compromisso(termo_ou_id) -> Dict[str, Any]`: Remove um evento por ID direto ou busca por título.

---

## 17. `auth_calendar.py`

### Propósito
Script utilitário CLI para executar o fluxo interativo de autenticação OAuth 2.0 (Google InstalledAppFlow) e salvar o `token.json`.

---

## 18. `tools/calendar_tools.py`

### Propósito
Ferramentas de Function Calling para a LLM operar sobre a agenda do Google.

### Tools Registradas
- **`listar_agenda_google(dias_a_frente=7, data_inicio='')`:** Retorna compromissos agendados.
- **`adicionar_evento_google(titulo, data_hora_inicio, data_hora_fim='', descricao='', localizacao='')`:** Agenda um compromisso no Google Calendar.
- **`remover_evento_google(termo_ou_id)`:** Cancela ou remove um compromisso da agenda.

---

## 19. `list_manager.py`

### Propósito
Gerenciar listas personalizadas (compras, mercado, tarefas) isoladas por usuário com armazenamento relacional no SQLite.

### Funções Públicas
- `init_list_db(db_path=None) -> None`: Inicializa as tabelas `user_lists` e `list_items` com chave estrangeira e deleção em cascata.
- `obter_ou_criar_lista(user_id: str, nome_lista: str, db_path=None) -> int`: Recupera o ID da lista ou a cria sob demanda.
- `adicionar_item_lista(user_id: str, nome_lista: str, item_text: str, db_path=None) -> Dict[str, Any]`: Adiciona item pendente à lista indicada.
- `obter_itens_lista(user_id: str, nome_lista: str, db_path=None) -> Dict[str, Any]`: Retorna a coleção de itens com contadores e status.
- `listar_todas_listas(user_id: str, db_path=None) -> List[Dict[str, Any]]`: Lista todas as listas ativas do usuário com total e pendências.
- `ticar_item_lista(user_id: str, nome_lista: str, item_identificador: str | int, concluido=None, db_path=None) -> Dict[str, Any]`: Marca/desmarca ou alterna o status de um item (por ID numérico ou busca por texto).
- `remover_item_lista(user_id: str, nome_lista: str, item_identificador: str | int, db_path=None) -> Dict[str, Any]`: Remove um item individual da lista.
- `limpar_itens_concluidos(user_id: str, nome_lista: str, db_path=None) -> Dict[str, Any]`: Apaga permanentemente todos os itens ticados/finalizados.
- `excluir_lista(user_id: str, nome_lista: str, db_path=None) -> Dict[str, Any]`: Exclui a lista inteira e todos os seus itens associados.
- `formatar_lista_para_exibicao(dados_lista: Dict[str, Any]) -> str`: Gera formatação rica em Markdown para o Discord com caixas de seleção.

---

## 20. `tools/list_tools.py`

### Propósito
Fornecer ferramentas de Function Calling à LLM para manipulação de listas pessoais.

### Tools Registradas
- **`adicionar_item_lista(nome_lista: str, item: str)`:** Adiciona novo item à lista informada.
- **`ver_itens_lista(nome_lista: str)`:** Retorna a lista completa com caixas de status (`⬜` e `✅`).
- **`listar_minhas_listas()`:** Retorna o catálogo de listas do usuário com contadores.
- **`ticar_item_lista(nome_lista: str, item_ou_id: str, concluido=True)`:** Marca item como concluído/reabre.
- **`remover_item_lista(nome_lista: str, item_ou_id: str)`:** Exclui um item específico.
- **`limpar_itens_concluidos_lista(nome_lista: str)`:** Exclui permanentemente os itens finalizados.
- **`excluir_lista(nome_lista: str)`:** Exclui a lista inteira.

---

## 21. `reminder_manager.py`

### Propósito
Agendar e despachar avisos automáticos no Discord através de persistência SQLite e um background worker assíncrono contínuo.

### Funções Públicas
- `init_reminder_db(db_path=None) -> None`: Inicializa a tabela `reminders` no SQLite com índices temporais.
- `interpretar_expressao_tempo(expressao: str, agora=None) -> Optional[datetime]`: Interpreta expressões temporais relativas (`15m`, `2h`, `1 dia`) e absolutas (`09:00`, `19/10/2026 09:00`).
- `criar_lembrete(user_id: str, channel_id: str, mensagem: str, quando_dt: datetime, db_path=None) -> Dict[str, Any]`: Grava um novo lembrete com status `pendente`.
- `obter_lembretes_vencidos(db_path=None) -> List[Dict[str, Any]]`: Consulta lembretes cujo horário agendado já chegou.
- `atualizar_status_lembrete(lembrete_id: int, novo_status: str, db_path=None) -> None`: Atualiza status para `disparado`, `cancelado` ou `falha`.
- `listar_lembretes_usuario(user_id: str, apenas_pendentes=True, db_path=None) -> List[Dict[str, Any]]`: Retorna os lembretes do usuário.
- `cancelar_lembrete(user_id: str, lembrete_id: int, db_path=None) -> Dict[str, Any]`: Cancela um lembrete pendente.
- `async iniciar_worker_lembretes(client: discord.Client, intervalo_segundos=10) -> None`: Loop assíncrono de verificação e envio ativo de avisos no Discord citando o autor.

---

---

## 22. `tools/reminder_tools.py`

### Propósito
Ferramentas de Function Calling para a LLM interpretar comandos naturais de agendamento de avisos.

### Tools Registradas
- **`criar_lembrete(mensagem: str, quando: str)`:** Agenda um aviso aceitando tempo relativo ou absoluto.
- **`listar_meus_lembretes()`:** Lista os lembretes pendentes agendados.
- **`cancelar_lembrete(lembrete_id: int)`:** Cancela um lembrete pendente pelo ID.

---

## 23. `tools/tool_filter.py`

### Propósito
Executar filtragem semântica inteligente de ferramentas (Tool RAG / Dynamic Tool Selection) comparando embeddings da mensagem do usuário com descrições de ferramentas para enviar apenas as mais relevantes à LLM.

### Constantes e Configurações
- `TOOL_FILTER_ENABLED`: Ativação do filtro (padrão: `True`).
- `TOOL_FILTER_TOP_K`: Quantidade máxima de ferramentas enviadas por rodada (padrão: `5`).
- `TOOL_FILTER_MIN_SIMILARITY`: Limiar mínimo de similaridade de cosseno (padrão: `0.20`).

### Funções Públicas
- `similaridade_cosseno(v1: List[float], v2: List[float]) -> float`: Calcula produto escalar normalizado entre dois vetores densos.
- `async inicializar_cache_ferramentas(force_reload: bool = False) -> None`: Pré-computa e armazena em cache os embeddings das ferramentas na inicialização.
- `async filtrar_ferramentas_relevantes(query: str, top_k: Optional[int] = None, min_score: Optional[float] = None) -> List[Dict[str, Any]]`: Seleciona dinamicamente as ferramentas mais aderentes à mensagem do usuário em formato de schema OpenAI.

---

## 24. `commands/builtins.py` (Central de Ajuda em 2 Etapas)

### Propósito
Implementação do comando `!ajuda` dividido em duas etapas para garantir mensagens organizadas e sem risco de estourar os 2000 caracteres do Discord:
1. **Etapa 1 (`!ajuda`):** Visão geral modular com resumo dos grandes blocos (`geral`, `agenda`, `lista`, `lembrete`, `pdf`, `memoria`).
2. **Etapa 2 (`!ajuda <modulo>`):** Detalhamento aprofundado dos comandos, opções e exemplos específicos daquele bloco temático.

---

## 25. `audio_manager.py`

### Propósito
Gerenciar a detecção, download temporário, transcrição assíncrona com `faster-whisper` em português (`pt-br`) e a exclusão imediata e garantida de arquivos de áudio temporários.

### Funções Públicas
- `get_whisper_model() -> WhisperModel`: Retorna ou inicializa o modelo singleton `faster-whisper` em memória (`cpu`, `int8`).
- `eh_anexo_audio(attachment: discord.Attachment) -> bool`: Identifica se o anexo é uma mensagem de voz ou arquivo de áudio (`.ogg`, `.mp3`, `.wav`, `.m4a`, etc.).
- `transcrever_arquivo_audio(caminho_arquivo: Path | str, idioma: str = 'pt') -> str`: Transcreve o arquivo de áudio síncronamente via `WhisperModel.transcribe`.
- `async baixar_e_transcrever_anexo_audio(attachment: discord.Attachment, idioma: str = 'pt') -> Tuple[Optional[str], Optional[str]]`: Baixa o arquivo em caminho temporário (`tempfile`), executa a transcrição em thread pool não-bloqueante (`asyncio.to_thread`) e, em bloco `finally`, apaga imediatamente o arquivo temporário do disco.

---

## 26. `tts_manager.py`

### Propósito
Encapsular a síntese de voz (TTS) utilizando o serviço `edge-tts` com a voz neural `pt-BR-FranciscaNeural`, limpar artefatos de formatação Markdown para garantir uma pronúncia natural e gerenciar a criação/exclusão de arquivos MP3 temporários.

### Funções Públicas
- `limpar_texto_para_tts(texto: str) -> str`: Remove blocos de código, URLs, links markdown, menções e caracteres de formatação para alimentar o motor TTS.
- `async sintetizar_fala_edge(texto: str, voz: str = TTS_VOICE) -> Tuple[Optional[Path], Optional[str]]`: Gera assincronamente um arquivo MP3 temporário pronto para envio como anexo no Discord.

---

## 27. `tools/settings_tools.py`

### Propósito
Disponibilizar ferramentas de Function Calling para que a LLM compreenda e configure a preferência de resposta do usuário (texto, áudio ou ambos).

### Tools Registradas
- **`configurar_modo_resposta(modo: str)`:** Altera a preferência de resposta do usuário entre `'texto'`, `'audio'` e `'ambos'`.
- **`consultar_modo_resposta()`:** Retorna o modo de resposta atualmente ativo para o usuário.


