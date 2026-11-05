# 🤖 Discord AI Bot — Antigravity

Bot conversacional inteligente para Discord com integração assíncrona ao **LM Studio** (ou qualquer servidor compatível com a API da OpenAI), memória de conversação persistente em **SQLite**, arquitetura modular de **Function Calling (Tools)** e sistema extensível de **Comandos com Prefixo (`!`)**.

> 📚 **Especificações & Arquitetura Completa:**
> - 📖 **[Especificações Gerais (Índice)](SPECs/README.md)**
> - 🏛️ **[Arquitetura do Sistema & Diagramas](SPECs/ARQUITETURA.md)**
> - 🗺️ **[Roadmap de Desenvolvimento](SPECs/ROADMAP.md)**
> - 💡 **[Ideias Propostas para Expansão (SPECS_IDEIAS)](SPECs/SPECS_IDEIAS/)**
> - ✅ **[Ideias Entregues em Produção (SPECS_IDEIAS_IMPLEMENTADAS)](SPECs/SPECS_IDEIAS_IMPLEMENTADAS/)**

---

## 🌟 Principais Recursos

- **🚀 100% Assíncrono e Não-Bloqueante:** Utiliza `AsyncOpenAI` para requisições de inferência e `asyncio.to_thread` para ferramentas síncronas. O loop de eventos do Discord permanece sempre livre, eliminando o erro de bloqueio de heartbeat (`heartbeat blocked for more than 10 seconds`).
- **🔧 Catálogo de Tools (Function Calling):** Permite que a LLM decida quando executar funções Python locais (como obter data/hora atual ou calcular expressões matemáticas) e use o resultado para responder.
- **⚡ Sistema de Comandos com Prefixo (`!`):** Suporte nativo a comandos estilo bot de mensageria (`!ajuda`, `!ping`, `!limpar`, `!historico`, `!hora`, `!modelo`, `!status`).
- **🧠 Memória Persistente Inteligente (SQLite):** Armazena o histórico por usuário com concatenação de mensagens consecutivas da mesma role e garante sanitização do contexto.
- **🎙️ Transcrição de Áudio e Voz (faster-whisper em pt-br):** Envie mensagens de voz ou arquivos de áudio (.ogg, .mp3, .wav, etc.) no Discord. O bot transcreve para texto usando `faster-whisper`, responde normalmente via texto e apaga os arquivos temporários imediatamente após o processamento.
- **✂️ Divisão Automática de Mensagens (Chunking):** Respostas maiores que o limite do Discord (2000 caracteres) são automaticamente segmentadas respeitando parágrafos e linhas.

---

## 📁 Estrutura do Projeto

```
discord/
├── .env                       # Variáveis de ambiente e tokens de acesso
├── README.md                  # Este guia completo de operação e desenvolvimento
├── chat_discord.py            # Ponto de entrada principal do bot
├── config.py                  # Configurações globais e carregamento de variáveis
├── context_manager.py         # Gerenciamento de contexto e anexos pendentes
├── database.py                # Camada SQLite (tabelas, histórico, contagem e limpeza)
├── pdf_manager.py             # Armazenamento, isolamento e busca de PDFs por usuário
├── vector_db.py               # Banco Vetorial ChromaDB com embeddings do LM Studio
├── google_calendar.py         # Integração com a API do Google Calendar v3
├── auth_calendar.py           # Assistente CLI de autenticação OAuth 2.0
├── utils.py                   # Utilitários de texto, divisão de blocos e hora
├── audio_manager.py           # Transcrição de áudio/voz (faster-whisper) e limpeza temporária
├── llm_client.py              # Cliente assíncrono para LM Studio com loop de tools
├── message_handler.py         # Orquestrador do fluxo de mensagens do Discord
├── chroma_db/                 # Armazenamento persistente das coleções {user}_memory
├── pdf/                       # Pastas de PDFs isoladas por usuário (discord/pdf/{user}/)
├── commands/                  # Subsistema de Comandos de Prefixo (!)
│   ├── __init__.py            # Exportação e inicialização
│   ├── registry.py            # Decorador @register_command e despachante
│   └── builtins.py            # Comandos padrão (!ajuda, !pdfs, !agenda, !memoria, etc.)
├── tools/                     # Subsistema de Ferramentas da LLM (Function Calling)
│   ├── __init__.py            # Exportação de schemas e executor
│   ├── registry.py            # Decorador @register_tool e conversor de schema
│   ├── datetime_tools.py      # Implementação de data/hora e calculadora
│   ├── pdf_tools.py           # Ferramentas de listagem e disponibilização de PDFs
│   ├── memory_tools.py        # Ferramentas de busca semântica na memória vetorial
│   └── calendar_tools.py      # Ferramentas de consulta e gestão da agenda Google
└── SPECs/                     # Especificações Técnicas Formais
    ├── discord-specs.md       # Especificação geral do sistema e fluxos
    └── modules-specs.md       # Especificação detalhada de cada módulo e função
```

---

## ⚙️ Pré-requisitos e Dependências

- **Python 3.10+**
- Pacotes Python necessários:
  ```bash
  pip install discord.py openai chromadb python-dotenv google-api-python-client google-auth-oauthlib google-auth-httplib2
  ```
- **Discord Developer Portal:**
  - O bot precisa da intent **Message Content Intent** habilitada no painel do Discord Developer (`Bot -> Privileged Gateway Intents -> Message Content Intent`).
- **LM Studio:**
  - Baixe e abra o [LM Studio](https://lmstudio.ai/).
  - Carregue o modelo desejado (ex: `qwen/qwen3.5-9b` ou `mistralai/mistral-7b-instruct`).
  - Inicie o servidor local na aba **Local Server** (porta padrão: `1234`).

---

## 🔐 Configuração do `.env`

Crie ou edite o arquivo `discord/.env`:

```env
# Token do seu bot no Discord (obrigatório)
DISCORD_TOKEN=seu_token_do_discord_aqui

# ID do usuário Discord (opcional, para testes ou filtros)
DISCORD_USER=seu_id_aqui

# Endereço e modelo do LM Studio
LM_STUDIO_URL=http://localhost:1234/v1
LM_STUDIO_API_KEY=lm-studio
MODELO_LLM=qwen/qwen3.5-9b

# Configuração de Comandos e Banco
COMMAND_PREFIX=!
DB_FILE=discord/chat_memory.db
```

---

## 🚀 Como Executar

No terminal, a partir da raiz do repositório:

```bash
# Com o ambiente virtual ativado:
python3 discord/chat_discord.py
```

Você verá a saída de inicialização confirmando os comandos e tools ativas:

```text
2026-10-18 16:30:00 [INFO] discord_bot: ============================================================
2026-10-18 16:30:00 [INFO] discord_bot: 🤖 Bot conectado com sucesso como: SeuBot#0000
2026-10-18 16:30:00 [INFO] discord_bot: 🧠 Modelo LLM: qwen/qwen3.5-9b
2026-10-18 16:30:00 [INFO] discord_bot: 🌐 LM Studio Endpoint: http://localhost:1234/v1
2026-10-18 16:30:00 [INFO] discord_bot: ⚙️  Prefixo de Comandos: !
2026-10-18 16:30:00 [INFO] discord_bot: 🔧 Tools ativas (2): ['obter_hora_atual', 'calcular_expressao']
2026-10-18 16:30:00 [INFO] discord_bot: ⚡ Comandos ativos (7): ['ajuda', 'historico', 'hora', 'limpar', 'modelo', 'ping', 'status']
2026-10-18 16:30:00 [INFO] discord_bot: ============================================================
```

---

## 🎮 Comandos Disponíveis no Discord

Envie qualquer um dos comandos abaixo diretamente em um canal onde o bot esteja presente:

| Comando | Descrição | Exemplo de Uso |
|---|---|---|
| `!ajuda [modulo]` | Central de ajuda em 2 etapas (visão geral ou módulos: `geral`, `agenda`, `lista`, `lembrete`, `pdf`, `memoria`) | `!ajuda` ou `!ajuda agenda` |
| `!ping` | Mede a latência da conexão com o Discord | `!ping` |
| `!limpar` | Apaga o histórico de conversação do usuário no banco SQLite | `!limpar` |
| `!historico` | Exibe o total de mensagens e prévia do contexto recente | `!historico` |
| `!hora [fuso]` | Exibe a data e hora do servidor ou de um fuso horário | `!hora America/Sao_Paulo` |
| `!modelo` | Exibe o modelo LLM e endpoint configurados | `!modelo` |
| `!status` | Exibe diagnóstico geral do sistema | `!status` |
| `!pdfs` | Lista todos os PDFs salvos na sua pasta pessoal | `!pdfs` |
| `!enviar <nome>` | Envia de volta o arquivo PDF solicitado como anexo | `!enviar relatorio` |
| `!memoria <termo>` | Busca semanticamente memórias passadas no ChromaDB | `!memoria carro` |
| `!limpar_memoria` | Reseta a coleção vetorial `{user}_memory` no ChromaDB | `!limpar_memoria` |
| `!agenda [dias]` | Consulta compromissos agendados no Google Calendar | `!agenda 7` |
| `!agendar <titulo> \| <data>` | Adiciona um novo compromisso na agenda do Google | `!agendar Reunião \| 2026-10-22 15:00` |
| `!desmarcar <termo>` | Cancela ou remove um compromisso do calendário | `!desmarcar Dentista` |
| `!lista [ver\|add\|ticar\|remover\|limpar\|excluir]` | Gerencia itens de listas pessoais (mercado, tarefas, etc.) | `!lista add mercado 2L de leite` |
| `!listas` | Lista todas as listas pessoais cadastradas pelo usuário | `!listas` |
| `!lembrete <quando> <msg>` | Programa um aviso no Discord por tempo relativo ou data/hora | `!lembrete em 15m tirar bolo do forno` |
| `!lembretes` | Lista todos os seus lembretes pendentes agendados | `!lembretes` |
| `!cancelar_lembrete <id>` | Cancela um lembrete pendente através do ID | `!cancelar_lembrete 2` |
| `!voz [texto\|audio\|ambos]` | Configura o modo de resposta do bot (texto, áudio com Francisca pt-BR ou ambos) | `!voz audio` |

> 💬 **Conversa com a IA:** Basta enviar qualquer mensagem comum **sem o prefixo `!`** para bater papo normalmente com o assistente inteligente!

---

### 📖 Central de Ajuda em Duas Etapas (`!ajuda`)

Para eliminar o risco de estourar o limite de 2000 caracteres do Discord e oferecer uma experiência organizada e legível:
1. **Etapa 1 (Visão Geral dos Grandes Blocos):** Digitar apenas `!ajuda` apresenta os 6 grandes blocos do sistema (`geral`, `agenda`, `lista`, `lembrete`, `pdf`, `memoria`) com um resumo conciso de cada um.
2. **Etapa 2 (Aprofundamento Modular):** Ao solicitar `!ajuda <modulo>` (ex: `!ajuda agenda` ou `!ajuda lista`), o bot retorna os comandos detalhados, argumentos e exemplos práticos daquele módulo específico.

---

### 🎯 Filtragem Semântica de Ferramentas (Tool RAG / Dynamic Tool Selection)

Em vez de enviar a lista completa com todas as 18 ferramentas para a LLM em cada mensagem (o que causaria sobrecarga de contexto, aumento de latência e consumo excessivo de tokens), o bot utiliza um pipeline semântico inteligente:
1. **Pré-computação de Embeddings:** Na inicialização do bot, as descrições e parâmetros de todas as ferramentas registradas são convertidos em vetores densos através do endpoint de embeddings do LM Studio (`text-embedding-qwen3-embedding-4b`).
2. **Cálculo de Similaridade de Cosseno:** Ao receber uma mensagem do usuário, o vetor da mensagem é comparado contra o catálogo de ferramentas.
3. **Seleção Dinâmica Top-$K$:** Apenas as ferramentas mais relevantes (Top-5 por padrão, configurável via `TOOL_FILTER_TOP_K`) que superam o limiar mínimo de relevância (`TOOL_FILTER_MIN_SIMILARITY=0.20`) são enviadas à LLM.
4. **Resiliência e Fallback:** Caso o serviço de embeddings esteja temporariamente inacessível, o sistema ativa um fallback automático enviando o catálogo completo de schemas sem interromper a conversa.

## 🧠 Memória Vetorial de Longo Prazo (ChromaDB + LM Studio Embeddings)

O bot utiliza uma arquitetura **Dual-Memory** que combina persistência relacional (SQLite) e busca semântica vetorial (ChromaDB):

1. **Geração Automática de Embeddings:**
   - Cada mensagem do usuário e resposta do assistente é automaticamente convertida em vetor denso através do servidor de embeddings local do LM Studio:
     - **Modelo:** `text-embedding-qwen3-embedding-4b`
     - **Endpoint:** `http://127.0.0.1:1234/v1/embeddings`
     - **Dimensão:** 2560 dimensões
2. **Coleções Isoladas por Usuário (`{user}_memory`):**
   - Cada usuário possui sua coleção dedicada no ChromaDB (ex: `rodrigomodel_memory`), garantindo que o contexto de um usuário nunca se misture com o de outro.
3. **RAG em Tempo Real nas Próximas Chamadas:**
   - Sempre que o usuário envia uma nova mensagem, o sistema busca os fragmentos mais similares no passado e os injeta contextualmente no prompt da LLM.
   - Mesmo que uma informação tenha sido discutida há semanas ou fora do limite de 10 mensagens do SQLite, a LLM recupera a lembrança!
4. **Comandos e Tools:**
   - Digite `!memoria <assunto>` para inspecionar o que o ChromaDB lembra sobre você.
   - Digite `!limpar_memoria` para reiniciar sua coleção vetorial.
   - A LLM também conta com a ferramenta nativa `consultar_memoria_passada` para pesquisas ativas.

---

## 📄 Gerenciamento de Arquivos PDF (`discord/pdf/{user}/`)

O bot possui um sistema completo de recebimento, armazenamento isolado e entrega de documentos PDF:

1. **Envio / Upload:**
   - Basta arrastar e soltar ou anexar qualquer arquivo `.pdf` no chat do Discord.
   - O bot salva automaticamente o arquivo na pasta pessoal do usuário: `discord/pdf/{seu_usuario}/`.
   - Um recibo com nome e tamanho do arquivo salvo é enviado imediatamente no canal.
2. **Listar PDFs Disponíveis:**
   - **Por comando:** Digite `!pdfs` (ou `!listar_pdfs`).
   - **Por conversa:** Pergunte à IA: *"Quais PDFs eu tenho disponíveis?"* ou *"O que tem na minha pasta de documentos?"*.
3. **Solicitar Envio / Download do Arquivo:**
   - **Por comando:** Digite `!enviar <nome>` (ex: `!enviar relatorio` ou `!enviar contrato.pdf`).
   - **Por conversa:** Diga à IA: *"Me envia o pdf de contrato"*, *"Disponibiliza o arquivo de relatório"*, *"Me manda o documento X"*.
   - A IA aciona a ferramenta correspondente e o bot anexa e devolve o arquivo PDF físico diretamente no chat!

---

## 📅 Integração com o Google Calendar (Passo a Passo de Configuração)

O bot permite interagir de forma bidirecional com a sua agenda do Google: consultar compromissos, agendar reuniões e cancelar eventos, tanto por comandos `!` quanto em linguagem natural com a IA!

### Passo a Passo para Configurar suas Credenciais Google:

1. **Acesse o Google Cloud Console:**
   - Entre em [https://console.cloud.google.com/](https://console.cloud.google.com/) com a sua conta Google.
   - Crie um novo projeto (ex: `Discord Bot Calendar`).
2. **Ative a Google Calendar API:**
   - No menu lateral, vá em **APIs e Serviços** -> **Biblioteca**.
   - Pesquise por `Google Calendar API` e clique em **Ativar**.
3. **Configure a Tela de Permissão OAuth (OAuth consent screen):**
   - Vá em **APIs e Serviços** -> **Tela de permissão OAuth**.
   - Selecione o tipo de usuário **Externo** e clique em **Criar**.
   - Preencha o nome do app (ex: `Discord Calendar Bot`) e seu e-mail de suporte.
   - Na etapa **Usuários de teste** (*Test Users*), **adicione o seu e-mail do Google**. Salve as alterações.
4. **Crie a Credencial OAuth 2.0:**
   - Vá em **APIs e Serviços** -> **Credenciais**.
   - Clique em **+ Criar Credenciais** -> **ID do cliente OAuth**.
   - Em *Tipo de aplicativo*, selecione **App para computador** (*Desktop App*).
   - Nomeie como `Discord Bot Desktop` e clique em **Criar**.
   - Na janela que aparecer, clique em **Fazer o download do JSON**.
5. **Coloque o arquivo no projeto:**
   - Renomeie o arquivo baixado para `credentials.json`.
   - Mova-o para a pasta do bot: `discord/credentials.json`.
6. **Execute o Assistente de Autenticação (Apenas 1 vez):**
   - No terminal, execute:
     ```bash
     python3 discord/auth_calendar.py
     ```
   - Uma aba do navegador se abrirá para você fazer login na sua conta Google e conceder acesso à agenda.
   - O token de acesso será salvo em `discord/token.json` e será renovado automaticamente para sempre!

### Como Usar no Discord:

| Ação | Via Comando | Via Conversa com a IA |
|---|---|---|
| **Ver compromissos** | `!agenda` ou `!agenda 15` | *"O que eu tenho agendado para hoje?"*, *"Mostre meus compromissos desta semana"* |
| **Marcar evento** | `!agendar Almoço \| 2026-10-22 12:30` | *"Agenda uma reunião com o João amanhã às 14h"*, *"Marca dentista dia 25/10 às 09:00"* |
| **Cancelar evento** | `!desmarcar Almoço` | *"Cancela minha reunião de amanhã"*, *"Desmarca o dentista"* |

---

## 🛒 Sistema de Listas (Mercado, Compras e Tarefas)

O bot conta com um gerenciador integrado de listas pessoais com persistência relacional no SQLite:

1. **Criação e Adição Automática:**
   - Cria listas sob demanda (ex: `mercado`, `compras`, `tarefas`, `filmes`).
   - `!lista add mercado 2L de leite integral`
   - Via IA: *"Coloque 1kg de arroz e café na minha lista de mercado"*
2. **Visualização Formatada:**
   - Exibe itens com status claro de pendente (`⬜`) ou concluído (`✅`), contadores e IDs:
   - `!lista ver mercado` ou `!lista mercado`
   - Via IA: *"O que tem na minha lista de mercado?"*
3. **Ticar / Concluir Itens:**
   - Marca itens como finalizados por ID numérico (`#1`) ou por busca de texto (`leite`):
   - `!lista ticar mercado 1` ou `!lista ticar mercado leite`
   - Via IA: *"Risque o leite da lista de mercado"*
4. **Limpar Concluídos (Excluir Itens Finalizados):**
   - Apaga permanentemente do banco todos os itens que já foram ticados/concluídos:
   - `!lista limpar mercado`
   - Via IA: *"Apague os itens concluídos da lista de compras"*
5. **Comandos Rápidos:**
   - `!listas`: Lista todas as listas existentes do usuário.
   - `!lista remover <nome> <id/texto>`: Exclui um item específico.
   - `!lista excluir <nome>`: Exclui uma lista inteira.

---

## ⏰ Sistema de Lembretes Agendados (Reminders)

O bot possui um agendador de avisos persistente no SQLite com um **worker assíncrono em segundo plano** que monitora o tempo e notifica ativamente o usuário no Discord quando o momento chega:

1. **Agendamento por Tempo Relativo:**
   - Aceita minutos, horas, dias ou segundos:
   - `!lembrete em 15m desligar o forno`
   - `!lembrete em 2h ligar para o cliente`
   - Via IA: *"Em 15 minutos me avise que preciso tirar o bolo do forno"*
2. **Agendamento por Data e Hora Absoluta:**
   - Aceita horários diretos ou datas completas:
   - `!lembrete 09:00 tomar remédio da manhã`
   - `!lembrete 19/10/2026 09:00 consulta médica`
   - Via IA: *"Às 09:00 do dia 19/10 me avise que devo tomar o remédio X"*
3. **Disparo Automático no Discord:**
   - Quando o horário é atingido, o bot envia uma mensagem citando o usuário (`<@user_id>`) no canal onde o lembrete foi solicitado (com fallback para Mensagem Direta se o canal não estiver acessível).
   - O status é atualizado para `disparado`, garantindo que nada se repita e que lembretes sobrevivam a reinicializações do bot!
4. **Controle de Lembretes:**
   - `!lembretes`: Exibe todos os lembretes pendentes com data/hora e ID.
   - `!cancelar_lembrete <id>`: Cancela um lembrete pendente.
   - Via IA: *"Quais são meus lembretes pendentes?"*, *"Cancele o lembrete #2"*.

---

## 🎙️ Mensagens de Áudio e Voz (faster-whisper em pt-br)

O bot conta com suporte nativo a mensagens de áudio e voz do Discord:

1. **Como Usar:**
   - Envie uma **mensagem de voz nativa** do Discord (botão de microfone no app mobile/desktop) ou anexe um arquivo de áudio (`.ogg`, `.mp3`, `.wav`, `.m4a`, etc.).
2. **Transcrição Não-Bloqueante com faster-whisper:**
   - O áudio é baixado em um arquivo temporário e transcrito em segundo plano utilizando o modelo `faster-whisper` calibrado para português (`pt-br`).
   - O loop do Discord nunca trava durante a inferência.
3. **Fluxo Conversacional Completo:**
   - O bot exibe o texto transcrito no chat: `🎙️ Áudio transcrito: "..."`
   - O texto resultante é alimentado diretamente no fluxo conversacional com memória (SQLite), busca vetorial (ChromaDB), filtragem semântica de ferramentas e raciocínio da LLM.
   - O bot responde normalmente por texto com todas as suas ferramentas ativas!
4. **Exclusão Garantida de Arquivos Temporários:**
   - Todos os arquivos de áudio temporários são **imediatamente excluídos do disco** em bloco `finally`, garantindo privacidade e zero acúmulo de arquivos residuais.

---

## 🔊 Modos de Resposta: Texto, Áudio e Ambos (edge-tts com Francisca pt-BR)

O bot oferece **3 modos de resposta** totalmente configuráveis pelo usuário:

| Modo | Descrição | Comportamento no Discord |
|---|---|---|
| `texto` *(Padrão)* | Apenas mensagens escritas | Envia as respostas normais divididas em texto |
| `audio` | Apenas mensagem de voz | Narra a resposta com a voz **Francisca Brasil** (`pt-BR-FranciscaNeural`) via `edge-tts` e anexa o áudio MP3 |
| `ambos` | Texto e Áudio simultâneos | Envia as mensagens escritas **e também** o arquivo de áudio narrado |

### Como Alterar a sua Preferência:
1. **Via Comando:**
   - `!voz`: Exibe o seu modo atual e as opções disponíveis.
   - `!voz texto`: Ativa respostas apenas em texto.
   - `!voz audio`: Ativa respostas apenas em áudio.
   - `!voz ambos`: Ativa respostas com texto e áudio juntos.
2. **Via Conversa / Linguagem Natural:**
   - Basta pedir naturalmente no chat:
     - *"A partir de agora me responda em áudio"*
     - *"Quero que responda com texto e áudio"*
     - *"Volte a me responder apenas por texto"*
   - O bot detecta a intenção imediatamente (ou através da tool `configurar_modo_resposta`) e confirma a alteração.
3. **Persistência Individual em SQLite:**
   - Cada usuário do Discord tem sua preferência gravada na tabela `user_settings`, que persiste mesmo se o bot for reiniciado.
4. **Exclusão Imediata de Arquivos Temporários:**
   - Todos os arquivos MP3 gerados para as respostas são apagados do disco imediatamente após o envio (`finally`), mantendo o servidor limpo e seguro.

---

## 🛠️ Guia de Expansão

### 1. Como Criar um Novo Comando `!`

Para criar um novo comando, basta adicionar uma função em `commands/builtins.py` (ou em um novo arquivo dentro de `commands/`) decorada com `@register_command`:

```python
from commands.registry import register_command, CommandContext

@register_command(
    name="dado",
    description="Rola um dado de N lados (padrão: 6)",
    usage="!dado [lados]",
    aliases=["roll", "rolar"]
)
async def cmd_dado(ctx: CommandContext):
    import random
    lados = int(ctx.args[0]) if ctx.args and ctx.args[0].isdigit() else 6
    sorteio = random.randint(1, lados)
    await ctx.reply(f"🎲 Você rolou um dado de {lados} lados e tirou: **{sorteio}**!")
```

O comando estará **imediatamente disponível** e aparecerá automaticamente na lista do `!ajuda`!

---

### 2. Como Criar uma Nova Tool para a LLM (Function Calling)

Para dar à LLM um novo superpoder (consultar API, ler arquivo, fazer pesquisa, etc.), registre uma função em `tools/` usando o decorador `@register_tool`:

```python
from tools.registry import register_tool

@register_tool(
    name="consultar_previsao_tempo",
    description="Retorna a previsão do tempo para uma cidade.",
    parameters={
        "type": "object",
        "properties": {
            "cidade": {
                "type": "string",
                "description": "Nome da cidade para consultar (ex: 'São Paulo', 'Curitiba')."
            }
        },
        "required": ["cidade"]
    }
)
def consultar_previsao_tempo(cidade: str) -> str:
    # Aqui você pode fazer uma requisição real de API
    return f"Previsão para {cidade}: 23°C, parcialmente nublado."
```

Pronto! A LLM receberá o schema automaticamente e decidirá sozinha quando chamar a função sempre que um usuário perguntar sobre o clima no Discord.

---

## 🩺 Resolução de Problemas Comuns

1. **Mensagem de erro: `Shard ID None heartbeat blocked for more than 10 seconds`:**
   - **Solução:** Este problema acontecia na versão legada quando chamadas de rede síncronas congelavam a thread principal. Na nova versão assíncrona com `AsyncOpenAI`, esse erro foi completamente eliminado.
2. **Bot não responde a mensagens:**
   - Verifique se a opção **Message Content Intent** está ativada no Discord Developer Portal.
   - Certifique-se de que o servidor do **LM Studio** está iniciado na porta 1234.
3. **Erro de conexão com o LM Studio:**
   - Verifique se a URL em `.env` (`LM_STUDIO_URL`) coincide com a porta ativa no LM Studio.
   - Teste acessando `http://localhost:1234/v1/models` no navegador.
