# Especificações Gerais do Sistema — Discord AI Bot (Antigravity)

**Versão da Especificação:** 1.0.0  
**Data:** 18 de Outubro de 2026  
**Status:** Aprovado / Em Produção  
**Escopo:** Módulo do Discord Bot integrado ao LM Studio (OpenAI-compatible API)

---

## 1. Visão Geral e Propósito

O subsistema **Discord AI Bot** é um assistente conversacional inteligente que opera na plataforma Discord. Ele conecta canais de texto e mensagens diretas a instâncias locais de Modelos de Linguagem de Larga Escala (LLMs) executados via **LM Studio** (ou qualquer endpoint compatível com a API OpenAI Chat Completions), com memória persistente de conversação e suporte completo a **Function Calling** (Tools) e **Comandos de Prefixo** (`!`).

### 1.1 Objetivos Principais
1. **Desacoplamento e Modularidade:** Separação estrita de responsabilidades entre infraestrutura de rede (Discord.py), persistência de dados (SQLite), barramento de ferramentas (Tools Registry), barramento de comandos (`!`), cliente LLM assíncrono e formatação de saída.
2. **Alta Extensibilidade:**
   - Adição trivial de novas ferramentas para a LLM via decorador `@register_tool`.
   - Adição trivial de novos comandos de chat via decorador `@register_command`.
3. **Resiliência do Event Loop (Prevenção de Queda de Heartbeat):**
   - Eliminação de bloqueios síncronos na thread principal do `asyncio`. Chamadas de inferência à LLM e execução de ferramentas síncronas rodam de forma não-bloqueante (`AsyncOpenAI` e `asyncio.to_thread`), impedindo que o Discord Gateway encerre a sessão do bot (`heartbeat blocked`).
4. **Persistência Histórica Inteligente:**
   - Armazenamento em SQLite de mensagens por usuário com concatenação de envios consecutivos da mesma role e truncamento seguro respeitando os limites da janela de contexto.
5. **Divisão e Formatação Automática de Saída:**
   - Respeito ao limite estrito de 2000 caracteres do Discord, dividindo parágrafos longos sem truncar palavras no meio.

---

## 2. Arquitetura de Alto Nível

```mermaid
graph TD
    User([Usuário no Discord]) -->|Envia Mensagem| DiscordGateway[Discord Gateway / discord.py]
    DiscordGateway -->|on_message| MessageHandler[Message Handler]
    
    MessageHandler -->|Começa com '!'?| CommandRouter{Roteador de Comandos}
    CommandRouter -->|Sim| CommandRegistry[Command Registry]
    CommandRegistry -->|Executa| BuiltinCommands[Comandos !ajuda, !ping, !limpar, etc.]
    BuiltinCommands -->|Resposta Imediata| DiscordGateway

    CommandRouter -->|Não| DB_SaveUser[database.salvar_mensagem(user)]
    DB_SaveUser --> DB_GetHist[database.obter_historico]
    DB_GetHist --> SQLite[(SQLite: chat_memory.db)]

    DB_GetHist --> Typing[Ativa message.channel.typing]
    Typing --> LLMClient[llm_client.gerar_resposta]
    
    LLMClient -->|Async Request| LMStudio[LM Studio / LLM API]
    LMStudio -->|Tool Calls Solicitadas?| ToolCheck{Requer Tool?}
    
    ToolCheck -->|Sim| ToolsRegistry[Tools Registry]
    ToolsRegistry -->|Executa Tool| ToolExec[datetime_tools / custom_tools]
    ToolExec -->|Resultado da Tool| LLMClient
    
    ToolCheck -->|Não| FinalText[Resposta Textual Final]
    FinalText --> DB_SaveAssistant[database.salvar_mensagem(assistant)]
    DB_SaveAssistant --> SQLite
    FinalText --> ChunkSplit[utils.dividir_mensagem]
    ChunkSplit -->|Envia em Blocos <= 1900 chars| DiscordGateway
```

---

## 3. Fluxo de Vida de uma Mensagem

1. **Recepção:** O evento `on_message` é capturado pelo `client` Discord e repassado para `message_handler.processar_mensagem`.
2. **Validações Iniciais:**
   - Se o autor for o próprio bot (`message.author == client.user`), a mensagem é imediatamente descartada.
   - Mensagens vazias são ignoradas.
3. **Avaliação de Comandos (`!`):**
   - Se o conteúdo inicia com `COMMAND_PREFIX` (padrão `!`):
     - O texto é decomposto em nome do comando e argumentos.
     - Se o comando existir no registro, é executado e o processamento é finalizado sem acionar a LLM.
4. **Mensagens Especiais de Controle:**
   - Mensagens clássicas como `hello bot` recebem resposta instantânea (`Hello <Nome>!`).
5. **Persistência de Entrada:**
   - A mensagem do usuário é registrada no banco SQLite associada ao `message.author.id`.
6. **Sinalização Visual de Processamento:**
   - O bot entra em estado de digitação (`message.channel.typing()`).
7. **Montagem de Contexto:**
   - O histórico recente (últimas $N$ mensagens, padrão 10) é extraído do banco.
   - O histórico é higienizado para garantir que a primeira mensagem seja sempre `user`.
   - O `SYSTEM_PROMPT` configurado é inserido no topo da pilha de mensagens.
8. **Inferência LLM & Function Calling Loop:**
   - As mensagens e a lista de schemas de ferramentas ativas são enviadas ao LM Studio via `AsyncOpenAI`.
   - Caso o modelo emita `tool_calls`, cada ferramenta é executada via `tools.execute_tool` e seu resultado é injetado como mensagem de role `tool`.
   - O ciclo se repete até a obtenção da resposta final ou até atingir `MAX_TOOL_CALL_ITERATIONS` (padrão 5).
9. **Persistência de Saída:**
   - A resposta final gerada pelo assistente é gravada no banco SQLite sob a role `assistant`.
10. **Envio Dividido (Chunking):**
    - Se a resposta for superior a 1900 caracteres, a função `dividir_mensagem` quebra o texto respeitando parágrafos e pontuações, enviando sequencialmente no canal.

---

## 4. Camada de Persistência (SQLite)

O banco de dados é mantido no arquivo configurável `chat_memory.db` (local padrão: `discord/chat_memory.db`).

### 4.1 Esquema da Tabela `messages`

```sql
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_messages_user_id 
ON messages (user_id, id DESC);
```

### 4.2 Regras de Persistência e Concatenação
- **Concatenação de Mensagens Consecutivas:**
  - Quando um usuário envia várias mensagens seguidas sem resposta da LLM, o sistema localiza a última mensagem gravada. Se a `role` for idêntica, concatena o novo texto ao registro anterior utilizando duas quebras de linha (`\n\n`), reduzindo a fragmentação no prompt da LLM.
- **Higienização de Histórico:**
  - Modelos instrucionais exigem que a primeira mensagem após o `system prompt` pertença ao `user`. A função `obter_historico` descarta quaisquer mensagens de `assistant` órfãs no topo do histórico selecionado.
- **Limpeza Sob Demanda:**
  - Usuários podem resetar seu contexto a qualquer momento usando o comando `!limpar`.

---

## 5. Memória Vetorial de Longo Prazo (ChromaDB + Embeddings LM Studio)

Além do armazenamento estruturado no SQLite para o contexto imediato (últimas mensagens), o bot utiliza uma arquitetura **Dual-Memory** persistindo cada mensagem do usuário e resposta do assistente no **ChromaDB**.

### 5.1 Servidor de Embeddings
- **Provedor:** LM Studio Servidor Local (`http://127.0.0.1:1234/v1/embeddings`).
- **Modelo:** `text-embedding-qwen3-embedding-4b`.
- **Dimensão Vetorial:** 2560 dimensões.
- **Chamada Assíncrona:** Realizada via `AsyncOpenAI.embeddings.create` com tolerância a falhas.

### 5.2 Isolamento de Coleções por Usuário
- Para garantir privacidade e evitar contaminação cruzada de memórias, cada usuário possui sua própria coleção nomeada estritamente como `{user}_memory` (ex: `rodrigomodel_memory`).
- As coleções são armazenadas no diretório persistente `discord/chroma_db/`.

### 5.3 Mecanismo de RAG (Retrieval-Augmented Generation)
1. **Busca Semântica Preventiva:** Quando o usuário envia uma nova mensagem, o sistema consulta a coleção `{user}_memory` para encontrar os fragmentos mais similares antes de registrar a mensagem atual.
2. **Deduplicação Inteligente:** Fragmentos recuperados que já estejam presentes no histórico imediato do SQLite são filtrados para não inflar desnecessariamente o prompt.
3. **Injeção Contextual:** Os trechos mais relevantes são formatados em um bloco de sistema `[MEMÓRIA SEMÂNTICA DE LONGO PRAZO DO USUÁRIO - CHROMADB]` injetado nas chamadas à LLM, permitindo que o modelo se recorde de preferências, detalhes e projetos citados dias ou semanas atrás.
4. **Persistência Dupla Contínua:** Após a conclusão da resposta pela LLM, tanto a mensagem de entrada quanto a de saída são vetorizadas e salvas no ChromaDB.

---

## 6. Sistema de Comandos com Prefixo (`!`)

O sistema permite criar novos comandos de bot inspirados em bots de mensageria (Discord/Telegram), ativados por prefixo customizável (padrão `!`).

### 6.1 Especificação do Contexto (`CommandContext`)
Cada função de comando recebe uma instância de `CommandContext` contendo:
- `message`: Objeto `discord.Message` nativo.
- `client`: Objeto `discord.Client` nativo.
- `command_name`: Nome invocado em minúsculas.
- `args`: Lista de argumentos separados por espaço (`List[str]`).
- `arg_str`: String contínua de argumentos após o comando.
- `author`: Atalho para `message.author`.
- `channel`: Atalho para `message.channel`.
- `reply(text)`: Método assíncrono para responder marcando a mensagem original (com fallback de menção se faltar permissão de histórico).
- `send(text)`: Método assíncrono para enviar no canal sem marcação.

### 6.2 Catálogo de Comandos Nativos

| Comando | Aliases | Descrição |
|---|---|---|
| `!ajuda [modulo]` | `!help`, `!comandos` | Central de ajuda em 2 etapas: visão geral de blocos ou detalhada por módulo (`geral`, `agenda`, `lista`, `lembrete`, `pdf`, `memoria`) |
| `!ping` | `!latencia` | Mede o tempo de resposta do Gateway Discord em milissegundos |
| `!limpar` | `!clear`, `!reset` | Remove todo o histórico de conversas do usuário no SQLite |
| `!historico` | `!contexto` | Exibe quantidade de mensagens salvas e prévia das últimas |
| `!hora [fuso]` | `!time`, `!data` | Consulta a data e hora atual em um fuso horário IANA |
| `!modelo` | `!llm`, `!ia` | Mostra o modelo LLM ativo e o endpoint do LM Studio |
| `!status` | `!info` | Exibe resumo geral de saúde, latência, servidores e memória |
| `!pdfs` | `!listar_pdfs`, `!meus_pdfs` | Lista todos os PDFs salvos na pasta pessoal `discord/pdf/{user}/` |
| `!enviar <nome>` | `!baixar`, `!disponibilizar` | Envia o PDF correspondente de volta como anexo no chat |
| `!memoria <termo>` | `!lembrar`, `!rag` | Realiza busca semântica na coleção `{user}_memory` do ChromaDB |
| `!limpar_memoria` | `!reset_memoria` | Reseta a coleção vetorial `{user}_memory` do usuário |
| `!agenda [dias]` | `!calendario`, `!eventos` | Consulta os próximos compromissos da agenda Google |
| `!agendar <titulo> \| <data>` | `!marcar`, `!novo_evento` | Adiciona um novo compromisso no Google Calendar |
| `!desmarcar <nome_ou_id>` | `!cancelar_evento` | Remove ou cancela um compromisso do Google Calendar |

### 6.3 Arquitetura de Ajuda em Duas Etapas (Two-Stage Help)
Para contornar o limite rígido de 2000 caracteres do Discord e melhorar a usabilidade:
1. **Etapa 1 (Visão Geral de Blocos):** Se chamado sem argumentos (`!ajuda`), o bot renderiza uma visão geral modular dos blocos temáticos com descrições concisas (< 1100 caracteres).
2. **Etapa 2 (Aprofundamento por Módulo):** Se chamado com o nome do módulo (`!ajuda <modulo>`, ex: `!ajuda agenda`), renderiza a listagem completa de comandos, sintaxe detalhada e exemplos de uso do módulo específico.

---

## 7. Sistema de Ferramentas da LLM (Function Calling)

A LLM tem a capacidade de invocar código Python em tempo de execução para obter dados em tempo real ou executar cálculos precisos.

### 7.1 Contrato da API
Cada ferramenta expõe um schema no padrão JSON Schema da OpenAI:
```json
{
  "type": "function",
  "function": {
    "name": "<nome_da_funcao>",
    "description": "<descricao_para_a_llm>",
    "parameters": {
      "type": "object",
      "properties": { ... },
      "required": [ ... ]
    }
  }
}
```

### 7.2 Execução Não-Bloqueante
- Ferramentas assíncronas (`async def`) são aguardadas diretamente no loop (`await func(**args)`).
- Ferramentas síncronas (`def`) são executadas em thread pool gerenciada pelo Python (`await asyncio.to_thread(func, **args)`).
- Erros de execução são capturados e devolvidos como texto legível no retorno da tool, permitindo que a LLM compreenda o erro e tente alternativas sem crashar a aplicação.

### 7.3 Filtragem Semântica de Ferramentas (Tool RAG / Dynamic Tool Selection)
Para evitar sobrecarga de contexto e latência excessiva ao registrar dezenas de ferramentas:
1. **Pré-computação Vetorial:** As descrições e parâmetros das ferramentas são vetorizadas na inicialização (`inicializar_cache_ferramentas`) usando o endpoint de embeddings do LM Studio (`text-embedding-qwen3-embedding-4b`).
2. **Rankeamento Semântico:** A mensagem do usuário é convertida em embedding e comparada via similaridade de cosseno com as ferramentas.
3. **Seleção Top-$K$:** Apenas as Top-$K$ ferramentas mais relevantes (padrão 5) que superam a similaridade mínima (`TOOL_FILTER_MIN_SIMILARITY=0.20`) são repassadas no parâmetro `tools` da chamada `llm_client.gerar_resposta`.
4. **Fallback:** Caso ocorra falha na geração do embedding, o sistema recorre ao envio de todas as ferramentas para não interromper o atendimento.

---

## 7. Sistema de Gerenciamento e Disponibilização de PDFs

O subsistema de arquivos fornece armazenamento pessoal isolado, recuperação flexível e entrega automática de documentos PDF via Discord.

### 7.1 Estrutura de Diretórios
- Cada usuário possui uma pasta dedicada sob `discord/pdf/{user}/`, onde `{user}` é o nome de usuário do Discord sanitizado (`sanitizar_nome_usuario`), garantindo que usuários não acessem arquivos de outros membros.
- Proteção estrita contra *Path Traversal* via `path.resolve().is_relative_to(pasta_usuario.resolve())`.

### 7.2 Fluxo de Upload de PDF
1. O usuário anexa um ou mais arquivos com extensão `.pdf` ou MIME type `application/pdf`.
2. O `message_handler` intercepta os anexos antes de processar texto, salva o arquivo de forma assíncrona na pasta do usuário via `pdf_manager.salvar_anexo_pdf` e envia recibo de confirmação com nome, tamanho formatado e pasta de destino.
3. Se a mensagem não contiver texto adicional, a execução é encerrada poupando tokens da LLM.

### 7.3 Fluxo de Listagem de PDFs
- **Via Comando Manual:** O usuário envia `!pdfs` (ou `!listar_pdfs`). O bot responde com a listagem de arquivos, tamanhos legíveis e datas.
- **Via Linguagem Natural / LLM:** Ao receber perguntas como *"quais pdfs estão disponíveis?"*, a LLM aciona a tool `listar_meus_pdfs` e formata a resposta no chat.
- **Fallback Resiliente:** Caso o LM Studio esteja temporariamente inacessível, o handler detecta a intenção e lista os PDFs diretamente.

### 7.4 Fluxo de Envio / Disponibilização de PDF
- **Via Comando Manual:** O usuário envia `!enviar <nome>` (ou `!baixar`, `!disponibilizar`). O arquivo é localizado por correspondência flexível (exata, sem extensão, case-insensitive ou parcial) e entregue como anexo via `discord.File`.
- **Via Linguagem Natural / LLM:** Ao receber solicitações como *"me envia o pdf de contrato"* ou *"disponibiliza o arquivo X"*, a LLM aciona a tool `disponibilizar_pdf_usuario(nome_arquivo=...)`. A tool registra o arquivo em `context_manager.add_pending_file` e o `message_handler` realiza o envio físico do anexo no Discord.

---

## 8. Sistema de Integração com o Google Calendar

Permite consultar, adicionar e cancelar compromissos diretamente no calendário oficial do usuário (Primary Calendar) via OAuth 2.0.

### 8.1 Mecanismo de Autenticação
- **Protocolo:** OAuth 2.0 User Credentials (escopo `https://www.googleapis.com/auth/calendar`).
- **Arquivos:**
  - `credentials.json`: Baixado do Google Cloud Console (Desktop App).
  - `token.json`: Gerado uma única vez via `python3 discord/auth_calendar.py` e renovado automaticamente via refresh token sem intervenção humana.
- **Isolamento de Segurança:** Ambos os arquivos são protegidos no `.gitignore`.

### 8.2 Operações Suportadas
1. **Listagem de Eventos (`listar_compromissos` / `!agenda`):**
   - Filtra eventos a partir do momento atual para os próximos $N$ dias (padrão 7 dias) ordenados por data de início.
2. **Criação de Compromissos (`adicionar_compromisso` / `!agendar`):**
   - Criação com título, data/hora de início e fim, descrição e localização. Caso o fim não seja especificado, assume 1 hora de duração.
3. **Exclusão de Compromissos (`remover_compromisso` / `!desmarcar`):**
   - Permite cancelar eventos informando o ID exato ou o nome/título com busca flexível.

---

---

## 9. Sistema de Listas (Compras, Mercado e Tarefas)

Permite ao usuário gerenciar múltiplas listas nomeadas com persistência relacional no SQLite, rastreamento de itens concluídos/pendentes e exclusão de itens finalizados.

### 9.1 Esquema Relacional no SQLite
```sql
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
```

### 9.2 Recursos do Módulo `list_manager.py`
- Criação implícita ou explícita de listas isoladas por usuário (`user_id`).
- Adição de novos itens com status pendente (`concluido=0`).
- Alternância ou definição de status (ticar item) identificando o item por ID numérico ou texto.
- Limpeza em lote: exclusão definitiva de todos os itens com `concluido=1` em uma lista.
- Consulta estruturada com retorno de contadores (`total`, `pendentes`, `concluidos`) e formatação Markdown com caixas de seleção (`⬜` e `✅`).

---

## 10. Sistema de Lembretes e Notificações Ativas (Reminders)

Possibilita a programação de avisos e lembretes com notificação ativa no Discord através de um worker assíncrono executado em segundo plano.

### 10.1 Esquema da Tabela `reminders`
```sql
CREATE TABLE IF NOT EXISTS reminders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    channel_id TEXT NOT NULL,
    message TEXT NOT NULL,
    remind_at TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pendente',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_reminders_status_time 
ON reminders (status, remind_at);
```

### 10.2 Processamento de Tempo e Formatos Suportados
O analisador `interpretar_expressao_tempo` processa:
1. **Tempos Relativos:** `15m`, `15 min`, `15 minutos`, `2h`, `2 horas`, `30s`, `1d`.
2. **Horários Simples:** `09:00`, `14:30` (se o horário já passou hoje, projeta automaticamente para o dia seguinte).
3. **Datas e Horários Absolutos:** `19/10/2026 09:00`, `19/10 09:00`, `2026-10-19 09:00:00`.

### 10.3 Background Worker Assíncrono (`iniciar_worker_lembretes`)
- Disparado no evento `on_ready` via `asyncio.create_task`.
- Executa a cada 10 segundos buscando registros pendentes com `remind_at <= datetime.now()`.
- Tenta enviar notificação citando o usuário (`<@user_id>`) no canal de origem da solicitação.
- Possui fallback para envio direto via DM caso o bot não tenha acesso ao canal.
- Atualiza atomicamente o status no banco para `disparado` prevenindo re-disparos e garantindo sobrevivência a reinicializações.

---

## 11. Sistema de Transcrição de Áudio e Mensagens de Voz (faster-whisper)

Permite ao usuário enviar áudios e mensagens de voz no Discord, realizando a transcrição automática para português (`pt-br`) e integrando diretamente o texto transcrito ao ciclo conversacional da LLM.

### 11.1 Arquitetura e Ciclo de Vida do Áudio
1. **Recepção do Anexo:** O bot detecta anexos de áudio via `eh_anexo_audio` (verificando flag de mensagem de voz nativa do Discord, `content_type` ou extensão do arquivo).
2. **Download Temporário Seguro:** O arquivo de áudio é salvo em disco usando um arquivo temporário (`tempfile.NamedTemporaryFile`).
3. **Transcrição Não-Bloqueante:** O método `transcrever_arquivo_audio` invoca o `WhisperModel` do `faster-whisper` em thread pool assíncrona (`asyncio.to_thread`), preservando a responsividade do gateway do Discord.
4. **Alimentação Conversacional:** O texto transcrito é exibido no canal com aviso visual e passa a ser o `conteudo` da mensagem para a LLM, executando busca vetorial, ferramentas e gerando resposta normalmente por texto.
5. **Limpeza Obrigatória de Arquivos:** Todo arquivo de áudio baixado temporariamente é **obrigatoriamente excluído em bloco `finally`**, impedindo vazamento de espaço em disco e garantindo a privacidade dos dados do usuário.

---

## 12. Sistema de Síntese de Voz (TTS) e Opções de Resposta (edge-tts)

Permite ao usuário configurar como o bot responde através de 3 modos:
1. `texto`: Apenas respostas escritas convencionais (padrão).
2. `audio`: Apenas mensagens de voz narradas pela voz feminina Francisca Brasil (`pt-BR-FranciscaNeural`) via `edge-tts`.
3. `ambos`: Respostas escritas acompanhadas de áudio narrado simultâneo.

### 12.1 Métodos de Alteração de Preferência
- **Via Comando:** `!voz <texto|audio|ambos>` (ou aliases `!modo`, `!resposta`).
- **Via Linguagem Natural / Chat:** Reconhecido automaticamente pelo processador de mensagens e pela tool da LLM `configurar_modo_resposta`.
- **Persistência Individual:** Gravado em SQLite na tabela `user_settings`.
- **Limpeza de Arquivos Temporários:** Todo arquivo MP3 sintetizado para envio é destruído imediatamente após o despacho (`finally`).

---

## 13. Requisitos Não-Funcionais e Resiliência

1. **Gateway Heartbeat Safety:**
   - **Causa Raiz do Problema Anterior:** Chamadas síncronas com o cliente `OpenAI` nativo bloqueavam o loop do `asyncio` durante a inferência do modelo local (geralmente entre 10s e 40s), gerando `WARNING: heartbeat blocked for more than 10 seconds` e desconexão do Discord.
   - **Solução Implementada:** Utilização de `openai.AsyncOpenAI` para chamadas HTTP assíncronas e `asyncio.to_thread` para inferência de áudio e ferramentas. O loop do Discord permanece responsivo e processa heartbeats a cada pulso sem atraso.
2. **Proteção de Rate Limit e Quota:**
   - Limite máximo de 5 iterações de chamadas de tools por mensagem para mitigar loops infinitos caso a LLM insista em chamar a mesma tool repetidamente.
3. **Divisão de Mensagens Longas:**
   - O Discord rejeita mensagens com tamanho $> 2000$ caracteres (HTTP 400). O utilitário `dividir_mensagem` quebra o texto em blocos de até 1900 caracteres, priorizando quebras de parágrafo (`\n\n`) e linhas (`\n`).
4. **Isolamento de Erros:**
   - Exceções na LLM, no banco de dados ou em comandos enviam feedback amigável no canal do Discord e gravam stacktraces detalhadas nos logs do console.

---

## 14. Variáveis de Ambiente Suportadas

| Variável | Padrão | Descrição |
|---|---|---|
| `DISCORD_TOKEN` | *Obrigatório* | Token de autenticação da aplicação Bot no Discord Developer Portal |
| `DISCORD_USER` | *Opcional* | ID numérico do usuário principal para filtros de permissão |
| `LM_STUDIO_URL` | `http://localhost:1234/v1` | URL base do servidor OpenAI-compatible no LM Studio |
| `LM_STUDIO_API_KEY` | `lm-studio` | Chave de API enviada no cabeçalho (pode ser dummy para LM Studio) |
| `MODELO_LLM` | `qwen/qwen3.5-9b` | Identificador do modelo carregado no LM Studio |
| `COMMAND_PREFIX` | `!` | Caractere ou sequência de prefixo de comandos |
| `DB_FILE` | `chat_memory.db` | Caminho do arquivo de banco de dados SQLite |
| `SYSTEM_PROMPT` | *Definido em config.py* | Instruções de comportamento e persona do assistente |
| `MAX_TOOL_CALL_ITERATIONS` | `5` | Máximo de iterações consecutivas de tools por mensagem |
| `HISTORICO_LIMITE_PADRAO` | `10` | Quantidade máxima de mensagens recuperadas para contexto |
| `GOOGLE_CREDENTIALS_FILE` | `discord/credentials.json` | Caminho das credenciais OAuth do Google Calendar |
| `GOOGLE_TOKEN_FILE` | `discord/token.json` | Caminho do token de acesso do Google Calendar |
| `CALENDAR_DEFAULT_TIMEZONE`| `America/Sao_Paulo` | Fuso horário padrão para compromissos e lembretes |
| `TOOL_FILTER_ENABLED` | `true` | Ativa a seleção semântica dinâmica de ferramentas por embeddings |
| `TOOL_FILTER_TOP_K` | `5` | Número máximo de ferramentas mais relevantes enviadas para a LLM |
| `TOOL_FILTER_MIN_SIMILARITY` | `0.20` | Limiar mínimo de similaridade de cosseno para inclusão da ferramenta |
| `WHISPER_MODEL_SIZE` | `base` | Tamanho do modelo Whisper (`tiny`, `base`, `small`, etc.) |
| `WHISPER_LANGUAGE` | `pt` | Idioma padrão para transcrição de áudio (`pt` para pt-br) |
| `WHISPER_DEVICE` | `cpu` | Dispositivo de processamento do faster-whisper (`cpu`) |
| `WHISPER_COMPUTE_TYPE` | `int8` | Tipo de quantização numérica para execução rápida no Mac |
| `TTS_ENABLED` | `true` | Habilita o motor de Text-to-Speech edge-tts para respostas em áudio |
| `TTS_VOICE` | `pt-BR-FranciscaNeural` | Voz neural padrão utilizada na síntese de áudio (Francisca Brasil) |
| `TTS_DEFAULT_MODE` | `texto` | Modo de resposta padrão para novos usuários (`texto`, `audio`, `ambos`) |

