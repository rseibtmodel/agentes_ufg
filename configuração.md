# 🛠️ Guia Completo de Configuração: Discord Bot & Google Gemini

Este guia orienta passo a passo como criar e autorizar o seu **Bot no Discord**, como gerar a chave da API do **Google Gemini** e como configurar tudo no arquivo `.env` para colocar o assistente em execução.

---

## 📑 Sumário

1. [Parte 1: Criando e Configurando o Bot no Discord](#parte-1-criando-e-configurando-o-bot-no-discord)
2. [Parte 2: Gerando a Chave de API do Google Gemini](#parte-2-gerando-a-chave-de-api-do-google-gemini)
3. [Parte 3: Configuração do Arquivo `.env`](#parte-3-configuração-do-arquivo-env)
4. [Parte 4: Gerenciamento do Gemini pelo Próprio Discord](#parte-4-gerenciamento-do-gemini-pelo-próprio-discord)
5. [Parte 5: Executando e Testando o Bot](#parte-5-executando-e-testando-o-bot)

---

## Parte 1: Criando e Configurando o Bot no Discord

### 1.1 Criar a Aplicação no Portal de Desenvolvedores
1. Acesse o [Discord Developer Portal](https://discord.com/developers/applications).
2. Faça login com a sua conta do Discord.
3. No canto superior direito, clique no botão **"New Application"**.
4. Dê um nome para a aplicação (por exemplo: `Antigravity Bot`) e confirme clicando em **Create**.

---

### 1.2 Configurar o Bot e Obter o Token
1. No menu lateral esquerdo, clique na aba **"Bot"**.
2. Personalize o nome de exibição e o avatar do seu bot, se desejar.
3. Na seção **Token**, clique no botão **"Reset Token"** (confirme se solicitado).
4. Clique em **"Copy"** para copiar o token gerado.
   > ⚠️ **ATENÇÃO:** Guarde este token em um local seguro. Ele nunca deve ser compartilhado ou enviado para repositórios públicos. Ele será usado na variável `DISCORD_TOKEN`.

---

### 1.3 Habilitar as Privileged Gateway Intents (Obrigatório)
O bot precisa de permissão explícita para ler as mensagens e comandos nos canais:
1. Ainda na aba **"Bot"**, role para baixo até a seção **"Privileged Gateway Intents"**.
2. **Ative obrigatoriamente:**
   - ✅ **Message Content Intent** (essencial para o bot ler comandos e mensagens).
   - ✅ **Server Members Intent** (recomendado para identificar membros e permissões).
3. Clique em **"Save Changes"** no rodapé da página.

---

### 1.4 Gerar o Link de Convite e Adicionar o Bot ao seu Servidor
1. No menu lateral esquerdo, clique em **OAuth2** ➔ **URL Generator**.
2. Na caixa **Scopes**, selecione:
   - ✅ `bot`
   - ✅ `applications.commands`
3. Na caixa **Bot Permissions** que se abrirá abaixo, selecione as seguintes permissões:
   - ✅ **Send Messages** (Enviar mensagens)
   - ✅ **Read Messages/View Channels** (Ver canais)
   - ✅ **Read Message History** (Ler histórico de mensagens)
   - ✅ **Embed Links** (Inserir links/cards)
   - ✅ **Attach Files** (Anexar arquivos e PDFs)
   - ✅ **Add Reactions** (Adicionar reações com emojis)
   - ✅ **Use External Emojis** (Usar emojis externos)
   - ✅ **Manage Messages** *(opcional, recomendado para que o bot possa apagar mensagens sensíveis contendo chaves de API enviadas via comando)*.
4. No rodapé, copie a URL gerada no campo **"Generated URL"**.
5. Cole a URL no seu navegador, selecione o servidor Discord onde deseja adicionar o bot e confirme a autorização.

---

## Parte 2: Gerando a Chave de API do Google Gemini

O bot possui integração nativa com o Google Gemini para respostas rápidas, raciocínio avançado e failover automático caso a LLM local esteja indisponível.

1. Acesse o portal [Google AI Studio](https://aistudio.google.com/).
2. Faça login com a sua conta Google.
3. No menu lateral ou no topo, clique no botão **"Get API key"**.
4. Clique em **"Create API key"** (você pode associar a um projeto Google Cloud novo ou existente).
5. Copie a chave de API gerada (ela normalmente começa com o prefixo `AIza...`).
   > 💡 **Nota:** O Google AI Studio oferece cotas gratuitas generosas para os modelos Gemini Flash e Pro.

---

## Parte 3: Configuração do Arquivo `.env`

O bot carrega suas variáveis a partir do arquivo `discord/.env`.

### 3.1 Criando o arquivo `.env`
Na raiz do projeto (`antigravity`), execute no terminal:

```bash
# Copia o modelo de exemplo para o arquivo definitivo
cp discord/.env.example discord/.env
```

---

### 3.2 Preenchendo as Variáveis

Abra o arquivo `discord/.env` em seu editor e preencha as configurações abaixo:

```env
# ==============================================================================
# 1. CREDENCIAIS DO DISCORD
# ==============================================================================
# Cole o Token obtido no passo 1.2
DISCORD_TOKEN=seu_token_do_discord_aqui

# (Opcional) ID de usuário Discord para restringir quem pode usar o bot
# Deixe vazio para permitir que qualquer membro use
DISCORD_USER=

# ==============================================================================
# 2. CONFIGURAÇÃO DO GOOGLE GEMINI
# ==============================================================================
# Cole a chave de API gerada no Google AI Studio (passo 2)
GEMINI_API_KEY=AIzaSyD...sua_chave_aqui...

# Define o Google Gemini como provedor inicial padrão (opções: google, local, auto)
DEFAULT_LLM_PROVIDER=google

# Modelos do Gemini a utilizar
GEMINI_FLASH_MODEL=gemini-2.5-flash
GEMINI_PRO_MODEL=gemini-2.5-pro

# Endpoint da API do Gemini (deixe o padrão compatível com OpenAI)
GEMINI_API_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/

# ==============================================================================
# 3. LM STUDIO (PROVEDOR LOCAL - OPCIONAL)
# ==============================================================================
# Se você também usa LM Studio localmente:
LM_STUDIO_URL=http://localhost:1234/v1
LM_STUDIO_API_KEY=lm-studio
MODELO_LLM=qwen/qwen3.5-9b

# Failover Automático: se o LM Studio falhar ou demorar mais de 15s,
# o bot redireciona a requisição automaticamente para o Gemini na nuvem!
ENABLE_AUTO_FAILOVER=true
LOCAL_TIMEOUT_FAILOVER_SECONDS=15.0

# ==============================================================================
# 4. CONFIGURAÇÕES GERAIS
# ==============================================================================
COMMAND_PREFIX=!
DB_FILE=discord/chat_memory.db
```

---

## Parte 4: Gerenciamento do Gemini pelo Próprio Discord

Você não precisa reiniciar o bot para alternar provedores ou cadastrar sua chave. O bot possui comandos integrados via chat:

### 4.1 Cadastrar ou atualizar a chave do Gemini
No canal do Discord onde o bot está presente:
```text
!modelo key AIzaSyD...sua_chave_aqui...
```
> 🔒 **Segurança:** O bot apaga imediatamente a mensagem enviada pelo usuário no canal para evitar que sua chave fique exposta no histórico do Discord, atualiza a memória e grava no `discord/.env` automaticamente.

---

### 4.2 Alternar entre modelos e provedores
| Comando | Descrição |
|---|---|
| `!modelo` | Exibe o painel de status do provedor ativo, modelo e conexão do Gemini |
| `!modelo google` | Chaveia para o **Google Gemini Flash** (rápido e econômico) |
| `!modelo gemini-pro` | Chaveia para o **Google Gemini Pro** (alta capacidade analítica) |
| `!modelo local` | Chaveia para o modelo local do **LM Studio** |
| `!modelo auto` | Ativa o modo de roteamento dinâmico |

---

## Parte 5: Executando e Testando o Bot

### 5.1 Iniciar o Bot
Com o ambiente virtual ativado na raiz do projeto:

```bash
# Ativa o ambiente virtual Python
source .venv/bin/activate

# Inicia o bot
python discord/chat_discord.py
```

### 5.2 Saída esperada no terminal
```text
[INFO] discord_bot: ============================================================
[INFO] discord_bot: 🤖 Bot conectado com sucesso como: Antigravity Bot#1234
[INFO] discord_bot: 🧠 Modelo LLM: gemini-2.5-flash (Provedor: GOOGLE)
[INFO] discord_bot: 🌐 Provedor Cloud Ativo: Google Gemini API
[INFO] discord_bot: ⚙️  Prefixo de Comandos: !
[INFO] discord_bot: 🔧 Tools ativas: ['obter_hora_atual', 'calcular_expressao', ...]
[INFO] discord_bot: ⚡ Comandos ativos: ['ajuda', 'modelo', 'status', 'ping', ...]
[INFO] discord_bot: ============================================================
```

### 5.3 Testando no Discord
1. Digite no canal: `!status` ou `!ping`.
2. Digite: `!modelo` para confirmar que o Gemini está ativo.
3. Envie qualquer pergunta em linguagem natural para começar a conversar!

