# Especificações Gerais do Sistema — Discord AI Bot (Antigravity)

**Versão do Sistema:** 3.5.0  
**Data da Revisão:** 20 de Outubro de 2026  
**Status do Projeto:** Ativo / Produção Estável  
**Stack Principal:** Python 3.10+, Discord.py 2.3+, AsyncOpenAI, LM Studio (LLM + Embeddings), SQLite3 (WAL), ChromaDB, Faster-Whisper, Edge-TTS, Open-Meteo API, PyMuPDF (fitz).

---

## 1. Visão Geral e Grande Escopo do Projeto

O **Discord AI Bot (Antigravity)** é um assistente conversacional autônomo e multimodal de alta performance projetado para operar na plataforma Discord. O sistema conecta usuários a modelos locais de linguagem (LLMs) executados no **LM Studio** através de uma API compatível com OpenAI, provendo raciocínio contínuo, persistência de contexto em múltiplos níveis, execução autônoma de ferramentas (*Function Calling*), comunicação bilateral por texto e voz natural, assistência proativa diária (Resumo Matinal) e análise inteligente de livros e documentos com RAG vetorial sob demanda.

### 1.1 Pilares Fundamentais da Arquitetura
1. **Desacoplamento e Modularidade Extrema:**
   Cada funcionalidade é organizada em módulos independentes com responsabilidades bem delimitadas. A adição de novas capacidades ocorre via padrões declarativos de registro (`@register_tool` e `@register_command`), sem necessidade de modificar o fluxo central do bot.
2. **Resiliência e Execução Não-Bloqueante:**
   O loop de eventos do Discord Gateway nunca é bloqueado. Inferências de LLMs, síntese de voz, transcrição de áudio e operações de I/O em disco rodam em tarefas assíncronas dedicadas ou em thread pools gerenciadas (`asyncio.to_thread`), eliminando quedas de conexão por *heartbeat blocked*.
3. **Instância Única e Integridade Concorrente:**
   Uso de travas a nível de sistema operacional (`fcntl.flock` no arquivo `.bot.lock`) para impedir a execução simultânea de múltiplas instâncias no mesmo token, erradicando duplicidade de respostas.
4. **Memória em Dois Níveis:**
   - **Curto Prazo / Sessão:** SQLite configurado em modo WAL para acesso imediato às últimas mensagens do diálogo.
   - **Longo Prazo / Semântica:** ChromaDB particionado por usuário (`{user}_memory`) para recuperação de fatos e contextos passados via embeddings vetoriais (RAG).
5. **Comunicação Multimodal Bilateral:**
   - **Entrada:** Texto convencional, comandos com prefixo (`!`), documentos PDF e arquivos/mensagens de voz transcrevidos localmente via `faster-whisper`.
   - **Saída:** Mensagens de texto divididas dentro dos limites do Discord (2000 caracteres) e áudios narrados em português brasileiro natural (`pt-BR-FranciscaNeural` via `edge-tts`), com preferência customizável por usuário (`texto`, `audio`, `ambos`).
6. **Tool RAG (Dynamic Tool Selection):**
   Seleção semântica em tempo de execução das ferramentas mais pertinentes à consulta do usuário, diminuindo a sobrecarga de tokens no modelo e otimizando a latência de inferência.
7. **Assistência Proativa Diária (Morning Digest):**
   Agendamento assíncrono em segundo plano capaz de consolidar previsão meteorológica em tempo real, Google Calendar, lembretes e listas pendentes em um briefing matinal entregue pontualmente em texto e áudio narrado.
8. **Ecossistema de Livros e Leitura Inteligente (Book RAG):**
   Ingestão leve de PDFs no upload (autor, páginas, sumário TOC), geração de resumos hierárquicos por capítulo sob demanda e indexação vetorial dedicada no ChromaDB para conversa interativa e respostas fundamentadas com citação exata de páginas.

---

## 2. Mapa Geral da Documentação de Especificações

Assim como o comando `!ajuda` organiza a experiência do usuário em módulos temáticos, as especificações técnicas foram estruturadas em documentos dedicados divididos entre **Módulos Visíveis** (funcionalidades com interação direta no chat), **Módulos Internos** (camadas de infraestrutura e pipelines não visíveis ao usuário final), **Arquitetura & Roadmap** e **Ideias Futuras**.

```
discord/
├── SPECs/
│   ├── README.md                      # [Este documento] Visão geral e índice mestre
│   ├── ARQUITETURA.md                 # Diagramas, fluxo de dados ponta a ponta e segurança
│   ├── ROADMAP.md                     # Histórico de versões entregues e planos futuros
│   │
│   ├── arquitetura/                   # Diagramas visuais e ilustrações da arquitetura
│   │
│   ├── modulos_visiveis/              # Especificações das funcionalidades com interface de chat
│   │   ├── 01_GERAL_E_DIAGNOSTICO.md  # !ping, !status, !hora, !historico, !limpar, !ajuda
│   │   ├── 02_GOOGLE_CALENDAR.md      # !agenda, !agendar, !desmarcar e tools da agenda Google
│   │   ├── 03_LISTAS_E_MERCADO.md     # !lista, !listas e tools de compras, tarefas e itens
│   │   ├── 04_LEMBRETES_AGENDADOS.md  # !lembrete, !lembretes, !cancelar_lembrete e worker ativo
│   │   ├── 05_ARQUIVOS_E_PDFS.md      # !pdfs, !enviar, upload de PDFs e entrega sob demanda
│   │   ├── 06_MEMORIA_DE_LONGO_PRAZO.md # !memoria, !limpar_memoria e RAG vetorial no ChromaDB
│   │   ├── 07_MODO_RESPOSTA_E_VOZ.md  # !voz, alternância texto/áudio/ambos e preferências
│   │   ├── 08_RESUMO_MATINAL_DIGEST.md # !digest, briefing diário proativo, clima e agenda
│   │   ├── 09_LEITURA_INTELIGENTE_E_RAG_PDFS.md # !pdf, metadados, sumários, capítulos e RAG de livros
│   │   ├── 10_ROTEAMENTO_HIBRIDO_E_GOOGLE_GEMINI.md # !modelo, Gemini Flash/Pro e failover
│   │   ├── 11_PESQUISA_WEB_E_BROWSING.md # !buscar, !ler, DuckDuckGo e extração de artigos
│   │   ├── 12_UI_INTERATIVA_BUTTONS_E_MODALS.md # Views interativas, modais e botões
│   │   ├── 13_CENTRAL_DE_PROMPTS_E_TEMPLATES.md # !prompts, !prompt, templates e presets
│   │   ├── 14_KNOWLEDGE_HUB_E_TOPICOS_POR_CANAL.md # !topico, !nota, canais temáticos e RAG isolado
│   │   └── 15_PERSONAS_E_OVERRIDES_POR_CANAL.md # !persona canal, temperaturas e overrides de modelo
│   │
│   ├── modulos_internos/              # Especificações dos subsistemas e infraestrutura interna
│   │   ├── 01_BANCO_DE_DADOS_SQLITE.md # Schemas, índices, modo WAL, concorrência e integridade
│   │   ├── 02_PIPELINE_AUDIO_E_VOZ.md # Faster-Whisper (STT) + Edge-TTS (TTS) e ciclo de tempfiles
│   │   ├── 03_LLM_CLIENT_E_TOOL_CALLING.md # AsyncOpenAI, iterações de tools, sanitização Jinja
│   │   ├── 04_TOOL_FILTERING_RAG.md   # Seleção dinâmica de ferramentas via embeddings e cosseno
│   │   ├── 05_CHROMA_VECTOR_DB.md     # Multi-tenancy vetorial, persistência e busca semântica
│   │   ├── 06_CONTEXTO_E_ISOLAMENTO_SESSAO.md # ContextVars, lockfile singleton e fila de anexos
│   │   └── 07_MESSAGE_GATEWAY_OUTBOX.md # Barramento Outbox, anti-spam SHA-256 e circuit breaker
│   │
│   ├── SPECS_IDEIAS/                  # Especificações de ideias propostas para expansão futura (17 módulos)
│   │   ├── 03_INTEGRACAO_NOTION_OBSIDIAN.md # Sincronização com Notion API e cofres Obsidian
│   │   ├── 04_SANDBOX_EXECUCAO_CODIGO.md    # Execução isolada de scripts Python e gráficos
│   │   ├── 05_VISAO_COMPUTACIONAL_MULTIMODAL.md # OCR e compreensão de imagens com Vision LLMs
│   │   ├── 09_GESTAO_FINANCEIRA_E_CONTROLE_DE_GASTOS.md # Gestão de finanças pessoais por chat
│   │   ├── 10_PODCAST_MULTI_VOZ_E_AUDIO_DEBATE.md # Podcasts multi-voz e debates
│   │   ├── 11_HUB_WEBHOOKS_E_AUTOMACAO_EXTERNA.md # Webhooks e alertas externos
│   │   ├── 12_RESUMO_E_RAG_DE_VIDEOS_YOUTUBE.md # Transcrição e RAG de YouTube
│   │   ├── 13_MEMORIA_GRAFO_DE_CONHECIMENTO_GRAPH_RAG.md # Graph RAG e grafos relacionais
│   │   ├── 14_SAUDE_HABITOS_E_RASTREAMENTO_DE_ROTINA.md # Rastreador de hábitos
│   │   ├── 15_SISTEMA_DE_FLASHCARDS_E_REPETICAO_ESPACADA_ANKI.md # Flashcards SM-2 / Anki
│   │   ├── 16_MONITOR_DE_PRECOS_E_ALERTAS_DE_COMPRA.md # Monitor de preços e compras
│   │   ├── 17_AGENTE_DE_PESQUISA_PROFUNDA_DEEP_RESEARCH.md # Pesquisa profunda iterativa
│   │   ├── 18_DISCORD_VOICE_CHANNEL_ASSISTANT.md # Assistente em canal de voz ao vivo
│   │   ├── 19_GESTAO_DE_EMAILS_E_INBOX_ZERO.md # E-mails inteligentes e Inbox Zero
│   │   ├── 21_AUTOMACAO_DE_BACKUP_E_SINCRONIZACAO_CLOUD.md # Backups automáticos AES-256
│   │   ├── 22_ANALISE_DE_DADOS_E_GRAFICOS_CSV_EXCEL.md # Análise de dados e planilhas
│   │   └── 23_EXECUCAO_LOCAL_DE_AGENTES_E_SKILLS_VIA_AGY.md # Execução local de skills via AGY
│   │
│   └── SPECS_IDEIAS_IMPLEMENTADAS/    # Ideias concebidas no pipeline e já entregues em produção
│       ├── 01_WEB_SEARCH_E_BROWSING.md      # [Entregue v2.8.0] Pesquisa Web DuckDuckGo
│       ├── 02_RESUMO_MATINAL_DIGEST.md      # [Entregue v2.5.0] Morning Digest proativo
│       ├── 06_LEITURA_INTELIGENTE_E_RAG_PDFS.md # [Entregue v2.6.0] Leitura e RAG de PDFs
│       ├── 07_ROTEAMENTO_HIBRIDO_E_PROVEDORES_CLOUD_LLM.md # [Entregue v2.7.0] Gemini Cloud
│       ├── 08_UI_INTERATIVA_BUTTONS_E_MODALS.md # [Entregue v3.0.0] Botões, Menus e Modais
│       ├── 20_CENTRAL_DE_PROMPTS_E_PERSONAS_CUSTOMIZAVEIS.md # [Entregue v3.5.0] Central de Prompts & Templates
│       ├── 24_GATEWAY_UNIFICADO_OUTBOX_E_CONTROLE_ANTI_SPAM.md # [Entregue v3.0.0] Message Gateway
│       ├── 25_KNOWLEDGE_HUB_TEMATICO_E_RAG_ISOLADO_POR_CANAL.md # [Entregue v3.5.0] Knowledge Hub & RAG Isolado
│       └── 26_PERSONAS_E_OVERRIDES_COGNITIVOS_POR_CANAL.md # [Entregue v3.5.0] Personas por Canal e Overrides
```

---

## 3. Matriz de Módulos e Componentes do Sistema

| Módulo | Tipo | Arquivos Principais | Comandos (`!`) | Tools da LLM |
|---|---|---|---|---|
| **Geral & Diagnóstico** | Visível | `commands/builtins.py`, `utils.py` | `!ping`, `!status`, `!hora`, `!historico`, `!limpar`, `!ajuda` | `obter_hora_atual`, `calcular_expressao` |
| **Google Calendar** | Visível | `google_calendar.py`, `auth_calendar.py` | `!agenda`, `!agendar`, `!desmarcar` | `listar_agenda_google`, `adicionar_evento_google`, `remover_evento_google` |
| **Listas & Mercado** | Visível | `list_manager.py`, `ui_components.py` | `!lista`, `!listas` | `adicionar_item_lista`, `ver_itens_lista`, `listar_minhas_listas`, `ticar_item_lista`, `remover_item_lista`, `limpar_itens_concluidos_lista`, `excluir_lista` |
| **Lembretes Agendados** | Visível | `reminder_manager.py`, `ui_components.py` | `!lembrete`, `!lembretes`, `!cancelar_lembrete` | `criar_lembrete`, `listar_meus_lembretes`, `cancelar_lembrete` |
| **Arquivos & PDFs** | Visível | `pdf_manager.py` | `!pdfs`, `!enviar` | `listar_meus_pdfs`, `disponibilizar_pdf_usuario` |
| **Leitura & RAG de PDFs** | Visível | `pdf_manager.py`, `ui_components.py` | `!pdf` (`info`, `sumario`, `capitulo`, `indexar`, `perguntar`) | `consultar_metadados_pdf`, `obter_sumario_pdf`, `resumir_capitulo_pdf`, `indexar_pdf_rag`, `consultar_conteudo_pdf_rag` |
| **Memória Vetorial** | Visível | `vector_db.py` | `!memoria`, `!limpar_memoria` | `consultar_memoria_passada` |
| **Modo de Resposta / Voz** | Visível | `tts_manager.py`, `audio_manager.py` | `!voz` | `configurar_modo_resposta`, `consultar_modo_resposta` |
| **Resumo Matinal (Digest)** | Visível | `digest_manager.py` | `!digest`, `!resumo`, `!matinal`, `!dia` | `gerar_resumo_matinal`, `configurar_resumo_matinal` |
| **Roteamento Híbrido & Gemini** | Visível | `llm_client.py` | `!modelo` (`local`, `google`, `gemini-pro`, `auto`, `key`) | Suporte multi-provedor com failover |
| **Pesquisa Web & Browsing** | Visível | `web_search_manager.py` | `!buscar`, `!ler` | `buscar_na_web`, `ler_pagina_web` |
| **UI Interativa (Buttons/Modals)** | Visível | `ui_components.py` | Interações visuais via botões, modais e dropdowns | N/A (Componentes gráficos) |
| **Central de Prompts (Hub)** | Visível | `prompt_hub.py` | `!prompts`, `!prompt` | `listar_templates_prompt`, `obter_template_prompt`, `salvar_template_prompt` |
| **Knowledge Hub (Tópicos)** | Visível | `topic_manager.py` | `!topico`, `!nota`, `!notas` | `adicionar_nota_canal`, `buscar_notas_canal`, `listar_notas_canal` |
| **Personas por Canal** | Visível | `persona_manager.py` | `!persona` | `consultar_persona_canal`, `configurar_persona_canal`, `aplicar_preset_persona_canal` |
| **Barramento Outbox (Gateway)** | Interno | `message_gateway.py` | `!gateway` | Gerenciamento de envio anti-spam e circuit breaker |
| **Banco de Dados (SQLite)** | Interno | `database.py`, `chat_memory.db` | *N/A (Persistência)* | *N/A (Suporte às demais tools)* |
| **Pipeline de Áudio (STT/TTS)** | Interno | `audio_manager.py`, `tts_manager.py` | *N/A (Processamento de voz)* | *N/A (Entrada/Saída de mídia)* |
| **Motor LLM & Function Calling** | Interno | `llm_client.py`, `tools/registry.py` | *N/A (Inferência)* | Gerenciamento de execução |
| **Filtro Semântico de Tools** | Interno | `tools/tool_filter.py` | *N/A (Otimização RAG)* | Seleção prévia de esquemas |
| **ChromaDB Vector Store** | Interno | `vector_db.py`, `chroma_db/` | *N/A (Embeddings)* | Armazenamento de vetores |
| **Contexto & Concorrência** | Interno | `context_manager.py`, `chat_discord.py` | *N/A (Estado seguro)* | Isolamento assíncrono e Lockfile |

---

## 4. Diretrizes de Desenvolvimento e Manutenção

1. **Garantia de Não-Bloqueio do Loop:**
   Funções síncronas que realizem I/O pesado (operações de disco, chamadas de rede externas ou processamento de CPU como Whisper) nunca devem ser chamadas diretamente em métodos `async def`. Devem utilizar `await asyncio.to_thread(funcao_sincrona, *args)`.
2. **Ciclo de Vida de Arquivos Temporários:**
   Arquivos temporários (tanto os criados durante o recebimento de mensagens de voz quanto os gerados pela síntese TTS) devem obrigatoriamente ser destruídos dentro de cláusulas `finally:`.
3. **Compatibilidade com Modelos Locais no LM Studio:**
   Mensagens enviadas para o endpoint de chat completions devem obedecer estritamente à regra de conter **no máximo uma única mensagem com `role: "system"`**, localizada no índice 0 da lista. Qualquer dado contextual (como RAG ou orientações temporais) deve ser incorporado via concatenação textual no corpo dessa mensagem de sistema única.
4. **Isolamento de Dados por Usuário:**
   Cada usuário possui coleções exclusivas de arquivos em `pdf/{sanitizar_nome_usuario(user)}/`, coleção isolada no ChromaDB `{sanitizar_nome_colecao(user)}_memory` e filtragem rígida por `user_id` em todas as tabelas SQLite.
