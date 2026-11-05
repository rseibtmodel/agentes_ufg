# 🤖 Discord AI Bot — Antigravity

Assistente conversacional inteligente e multiagente para o Discord, construído com arquitetura 100% assíncrona, suporte a roteamento híbrido de LLMs (LM Studio local e Google Gemini com failover automático), memória dual persistente (SQLite e ChromaDB isolado por usuário), catálogo extensível de ferramentas (Function Calling) e sistema de comandos interativos.

---

## 📁 Estrutura do Repositório

```text
antigravity/
├── .agents/                 # Catálogo de Skills e Agentes especializados
├── discord/                 # Código-fonte principal do bot Discord
│   ├── chat_discord.py      # Ponto de entrada do Bot no Discord Gateway
│   ├── config.py            # Configuração centralizada e variáveis de ambiente
│   ├── message_handler.py   # Orquestrador do fluxo e ciclo de mensagens
│   ├── message_gateway.py   # Gateway outbox e controle de rate-limit
│   ├── database.py          # Camada SQLite (memória conversacional e estado)
│   ├── vector_db.py         # Memória semântica isolada com ChromaDB
│   ├── llm_client.py        # Cliente assíncrono para LM Studio e Google Gemini
│   ├── pdf_manager.py       # Gestão, RAG e indexação de documentos PDF
│   ├── google_calendar.py   # Integração OAuth 2.0 com a agenda do Google
│   ├── reminder_manager.py  # Worker de lembretes agendados em background
│   ├── digest_manager.py    # Resumo matinal e síntese diária de atividades
│   ├── list_manager.py      # Gestor de listas pessoais (mercado, tarefas)
│   ├── audio_manager.py     # Transcrição de áudio e voz via faster-whisper
│   ├── ui_components.py     # Componentes interativos do Discord (Botões e Modals)
│   ├── commands/            # Subsistema de Comandos de Prefixo (!)
│   │   ├── registry.py      # Despachante e decorador @register_command
│   │   └── builtins.py      # Catálogo de comandos nativos (!ajuda, !status, etc.)
│   ├── tools/               # Catálogo de Ferramentas da LLM (Function Calling)
│   │   ├── registry.py      # Despachante de tools e conversor de schemas
│   │   └── *_tools.py       # Implementações (calendário, listas, web, etc.)
│   ├── SPECs/               # Especificações Técnicas Formais e Arquitetura
│   └── README.md            # Guia técnico detalhado do módulo Discord
├── .gitignore               # Regras de exclusão do Git
├── .venv/                   # Ambiente virtual Python
└── README.md                # Este documento de visão geral
```

---

## 🌟 Principais Recursos

- **🚀 100% Assíncrono e Não-Bloqueante:** Utiliza `discord.py` assíncrono com `AsyncOpenAI` e workers em background, evitando bloqueios de heartbeat no loop de eventos.
- **🔄 Roteamento Híbrido de Modelos:** Suporte nativo ao **LM Studio** local com failover automático ou chaveamento para a **API do Google Gemini**.
- **🧠 Memória Híbrida Inteligente:**
  - **Relacional (SQLite):** Histórico de conversas, sanitização de contexto, lembretes e listas.
  - **Semântica (ChromaDB):** Embeddings e busca de conhecimento persistente com coleções isoladas por usuário e canal.
- **🔧 Function Calling (Tools):** A LLM pode consultar e executar ferramentas locais autonomamente (data/hora, pesquisa web, manipulação de PDFs, lembretes, agenda Google e listas).
- **🎙️ Áudio e Mensagens de Voz:** Transcrição automática de áudios (.ogg, .mp3, etc.) com `faster-whisper` em português.
- **📄 RAG e Gestão Documental:** Upload, leitura, indexação vetorial e envio sob demanda de arquivos PDF diretamente pelo Discord.
- **📅 Google Calendar:** Consulta, adição e cancelamento de compromissos sincronizados via OAuth 2.0.
- **⏰ Lembretes e Resumo Matinal:** Agendamento de alertas por tempo relativo ou absoluto e geração de relatórios diários (Digest).
- **⚡ Comandos com Prefixo (`!`):** Suporte nativo a dezenas de comandos utilitários (`!ajuda`, `!ping`, `!status`, `!limpar`, `!historico`, `!modelo`, etc.).

---

## 🚀 Como Executar

### 1. Pré-requisitos
- **Python 3.10+** (utilize o ambiente virtual `.venv`)
- **LM Studio** ativo localmente (`http://localhost:1234/v1`) ou chave configurada da **Gemini API**
- Intent **Message Content Intent** ativada no [Discord Developer Portal](https://discord.com/developers/applications)

### 2. Configuração do Ambiente
Copie o modelo de variáveis de ambiente e preencha suas credenciais:
```bash
cp discord/.env.example discord/.env
```
Edite `discord/.env` informando seu `DISCORD_TOKEN`, endpoint da LLM e demais integrações desejadas.

### 3. Inicialização do Bot
A partir da raiz do repositório:

```bash
# Ativar o ambiente virtual
source .venv/bin/activate

# Executar o bot
python discord/chat_discord.py
```

---

## 📚 Documentação & Especificações

Para detalhes aprofundados sobre arquitetura, contratos e novos módulos:
- 📖 [Documentação Técnica do Módulo Discord](file:///Users/rodrigomodel/antigravity/discord/README.md)
- 🏛️ [Arquitetura Geral & Fluxos](file:///Users/rodrigomodel/antigravity/discord/SPECs/ARQUITETURA.md)
- 🗺️ [Roadmap de Desenvolvimento](file:///Users/rodrigomodel/antigravity/discord/SPECs/ROADMAP.md)
- 💡 [Especificações Técnicas de Módulos e Ideias](file:///Users/rodrigomodel/antigravity/discord/SPECs/README.md)
