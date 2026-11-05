# 🚀 Ideias de Módulos Entregues e em Produção

Este diretório reúne as especificações de ideias geradas e validadas através da skill **`idea_generator`** que já foram **completamente desenvolvidas, testadas e colocadas em produção** no Discord AI Bot.

---

## 📋 Sumário de Ideias Implementadas

| Código | Nome da Ideia | Versão de Entrega | Resumo da Capacidade | Arquivo de Especificação |
|---|---|---|---|---|
| **`IDEA-01`** | **Pesquisa Web & Browsing em Tempo Real** | `v2.8.0` | Busca em tempo real na web (DuckDuckGo), leitura limpa de URLs e síntese executiva por IA. | [01_WEB_SEARCH_E_BROWSING.md](01_WEB_SEARCH_E_BROWSING.md) |
| **`IDEA-02`** | **Resumo Matinal Proativo (Morning Digest)** | `v2.5.0` | Briefing diário agendado (08:00) com agenda Google, clima Open-Meteo, lembretes e listas de tarefas em texto ou áudio. | [02_RESUMO_MATINAL_DIGEST.md](02_RESUMO_MATINAL_DIGEST.md) |
| **`IDEA-06`** | **Leitura Inteligente & RAG de Livros/PDFs** | `v2.6.0` | Ingestão leve, catálogo SQLite, sumários estruturados, resumos de capítulos e busca vetorial com citação de páginas. | [06_LEITURA_INTELIGENTE_E_RAG_PDFS.md](06_LEITURA_INTELIGENTE_E_RAG_PDFS.md) |
| **`IDEA-07`** | **Roteamento Híbrido & Provedores Cloud (Gemini)** | `v2.7.0` | Alternância fluida entre LM Studio Local e Google Gemini Cloud, auto-tiering por densidade e failover automático de alta disponibilidade. | [07_ROTEAMENTO_HIBRIDO_E_PROVEDORES_CLOUD_LLM.md](07_ROTEAMENTO_HIBRIDO_E_PROVEDORES_CLOUD_LLM.md) |
| **`IDEA-08`** | **Interface Interativa (Buttons, Modals, Menus)** | `v3.0.0` | Eliminação de comandos de texto repetitivos usando botões para listas de mercado, botões de ação em lembretes e dropdown de capítulos. | [08_UI_INTERATIVA_BUTTONS_E_MODALS.md](08_UI_INTERATIVA_BUTTONS_E_MODALS.md) |
| **`IDEA-20`** | **Central de Prompts & Templates Customizáveis** | `v3.5.0` | Repositório central de prompts reutilizáveis com 7 presets de fábrica (`padrao`, `dev`, `cfo`, `tributarista`, etc.), CRUD em SQLite e injeção em personas. | [20_CENTRAL_DE_PROMPTS_E_PERSONAS_CUSTOMIZAVEIS.md](20_CENTRAL_DE_PROMPTS_E_PERSONAS_CUSTOMIZAVEIS.md) |
| **`IDEA-24`** | **Barramento Central Outbox & Anti-Spam** | `v3.0.0` | Canal único de envio de mensagens com Fast-Path (<100ms), Leaky Bucket, deduplicação SHA-256 e Circuit Breaker contra flood. | [24_GATEWAY_UNIFICADO_OUTBOX_E_CONTROLE_ANTI_SPAM.md](24_GATEWAY_UNIFICADO_OUTBOX_E_CONTROLE_ANTI_SPAM.md) |
| **`IDEA-25`** | **Knowledge Hub Temático & RAG Isolado por Canal** | `v3.5.0` | Banco de notas temáticas por canal/thread com coleções ChromaDB estritamente isoladas, extração de hashtags e histórico SQLite separado. | [25_KNOWLEDGE_HUB_TEMATICO_E_RAG_ISOLADO_POR_CANAL.md](25_KNOWLEDGE_HUB_TEMATICO_E_RAG_ISOLADO_POR_CANAL.md) |
| **`IDEA-26`** | **Personas & Overrides Cognitivos por Canal** | `v3.5.0` | Injeção hierárquica de System Prompt, controle de temperatura e overrides de modelo (local/flash/pro) por canal, integrando presets do Hub. | [26_PERSONAS_E_OVERRIDES_COGNITIVOS_POR_CANAL.md](26_PERSONAS_E_OVERRIDES_COGNITIVOS_POR_CANAL.md) |

---

## 🏛️ Relação com Módulos do Sistema

As ideias entregues acima estão integradas ao código de produção do bot:
* `IDEA-01` -> [web_search_manager.py](../../web_search_manager.py) e comandos `!buscar`, `!ler`.
* `IDEA-02` -> [digest_manager.py](../../digest_manager.py) e comando `!digest`.
* `IDEA-06` -> [pdf_manager.py](../../pdf_manager.py) e comandos `!pdf`, `!pdfs`, `!enviar`.
* `IDEA-07` -> [llm_client.py](../../llm_client.py) e comando `!modelo`.
* `IDEA-08` -> [ui_components.py](../../ui_components.py) e comandos `!lista`, `!pdf`, notificações de lembrete.
* `IDEA-20` -> [prompt_hub.py](../../prompt_hub.py) e comandos `!prompts`, `!prompt`.
* `IDEA-24` -> [message_gateway.py](../../message_gateway.py) e comando `!gateway`.
* `IDEA-25` -> [topic_manager.py](../../topic_manager.py) e comandos `!topico`, `!nota`, `!notas`.
* `IDEA-26` -> [persona_manager.py](../../persona_manager.py) e comando `!persona`.
