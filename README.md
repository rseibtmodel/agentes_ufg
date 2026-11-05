# Antigravity Workspace

Bem-vindo ao repositório **Antigravity**. Este workspace abriga dois subsistemas autônomos de Inteligência Artificial:

---

## 📁 Estrutura de Projetos

```text
antigravity/
├── processo_interno/        # Tribunal Antifraude B2B (CPI-TJA)
│   ├── executar_pipeline.py # Script mestre do rito processual adversarial
│   ├── orquestrador_*.py    # Orquestradores dos agentes (Acusação, Defesa, Juiz, Perito)
│   ├── dataset_*.csv        # Base de dados de pedidos de compra
│   ├── json/                # Registros estruturados de julgamento por execução
│   ├── prompts/             # Prompts enviados aos modelos por execução
│   ├── README.md            # Documentação completa do Tribunal Antifraude
│   └── SPECS.md             # Especificações técnicas e limiares do CPI
│
├── discord/                 # Discord AI Bot & Google Calendar Integration
│   ├── chat_discord.py      # Ponto de entrada do Bot no Discord Gateway
│   ├── config.py            # Configuração centralizada e variáveis de ambiente
│   ├── google_calendar.py   # Integração OAuth 2.0 com a agenda do Google
│   ├── list_manager.py      # Gestor de listas pessoais (mercado, tarefas)
│   ├── reminder_manager.py  # Agendador de lembretes ativos em background
│   ├── vector_db.py         # Memória semântica de longo prazo com ChromaDB
│   ├── tools/               # Catálogo de ferramentas da LLM (Function Calling)
│   ├── commands/            # Comandos de chat com prefixo (!)
│   ├── README.md            # Documentação completa do Bot Discord
│   └── SPECs/               # Especificações formais e arquitetura do Bot
│
├── .venv/                   # Ambiente virtual Python compartilhado
├── gemini-key.txt           # Chave de API da Google GenAI (processo interno)
└── README.md                # Este documento de visão geral
```

---

## 1. ⚖️ Processo Interno: Tribunal Antifraude B2B (`processo_interno/`)

Pipeline multiagente adversarial para auditoria, saneamento e julgamento de pedidos comerciais de alto valor:

* **Agentes:** Acusação (Risco), Defesa (Comercial), Perito da Realidade (Fact-Checker) e Juiz (Instrução e Sentença).
* **Diretriz de Decisão:** Priorização de decisão binária conclusiva (*Fraude: 53%-100%* vs. *Não Fraude: 0%-47%*). Intervenção humana apenas em empate crítico (47%-53%).
* **Como Executar:**
  ```bash
  # A partir da raiz do repositório:
  python3 processo_interno/executar_pipeline.py --linha random

  # Ou entrando na pasta:
  cd processo_interno
  python3 executar_pipeline.py --linha 0
  ```
* 📖 Consulte a documentação completa em [processo_interno/README.md](file:///Users/rodrigomodel/antigravity/processo_interno/README.md) e as especificações em [processo_interno/SPECS.md](file:///Users/rodrigomodel/antigravity/processo_interno/SPECS.md).

---

## 2. 🤖 Discord AI Bot & Google Calendar (`discord/`)

Assistente pessoal inteligente para o Discord integrado ao LM Studio (OpenAI API local) e serviços em nuvem:

* **Dual-Memory:** Memória imediata relacional (SQLite) + Memória semântica de longo prazo isolada por usuário (ChromaDB + Embeddings).
* **Gestão Documental:** Recebimento, armazenamento em `discord/pdf/{user}/` e entrega de arquivos PDF físicos sob demanda.
* **Google Calendar:** Consulta, criação e cancelamento de compromissos oficiais via OAuth 2.0.
* **Listas Pessoais:** Gestão de listas de mercado e tarefas com marcação/ticar e limpeza de concluídos.
* **Lembretes Agendados:** Avisos por tempo relativo (`em 15m`) ou absoluto (`09:00`) com notificação ativa no Discord via worker assíncrono.
* **Como Executar:**
  ```bash
  python3 discord/chat_discord.py
  ```
* 📖 Consulte a documentação completa em [discord/README.md](file:///Users/rodrigomodel/antigravity/discord/README.md) e as especificações em [discord/SPECs/discord-specs.md](file:///Users/rodrigomodel/antigravity/discord/SPECs/discord-specs.md).

---

## 🚀 Ambiente e Dependências

O workspace utiliza um único ambiente virtual Python (`.venv`):
```bash
# Ativar o ambiente virtual no terminal macOS/Linux:
source .venv/bin/activate
```
