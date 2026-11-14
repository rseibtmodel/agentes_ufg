# Propostas e Especificações de Ideias (Backlog / Planejadas)

Este diretório contém exclusivamente especificações técnicas de ideias concebidas, refinadas e estruturadas para futuras versões do bot, que ainda **não** foram implementadas em código de produção.

---

## 🚨 Regra Canônica de Ciclo de Vida e Transição (INEGOCIÁVEL)

> ⚠️ **DETERMINAÇÃO DO ARQUITETO-CHEFE & DOC MASTER:**  
> Assim que uma ideia presente neste diretório for aprovada e passar pelo pipeline de engenharia (`/coder` $\rightarrow$ `/qa` $\rightarrow$ `/review`):
> 
> 1. **Movimentação Imediata:** O arquivo `.md` correspondente **DEVE ser compulsoriamente movido** para a pasta de histórico de entrega:
>    ```bash
>    git mv discord/SPECs/SPECS_IDEIAS/<NUMERO_SLUG>.md discord/SPECs/SPECS_IDEIAS_IMPLEMENTADAS/
>    ```
> 2. **Atualização de Status:** O frontmatter YAML da ideia deve ter seu campo `status` alterado de `planejado` para `implementado`.
> 3. **Vínculo com Módulo Oficial:** A ideia deve ser vinculada à especificação canônica correspondente em `discord/SPECs/modulos_visiveis/` ou `discord/SPECs/modulos_internos/`.
> 4. **Atualização do Índice:** Registrar a entrega na tabela oficial de [`discord/SPECs/SPECS_IDEIAS_IMPLEMENTADAS/README.md`](file:///Users/rodrigomodel/antigravity/discord/SPECs/SPECS_IDEIAS_IMPLEMENTADAS/README.md).
> 
> **Nenhuma ideia com código em produção pode permanecer em `discord/SPECs/SPECS_IDEIAS/`.**

---

## 📋 Backlog Atual de Propostas

| Arquivo de Spec | Título da Ideia | Versão Alvo | Resumo da Proposta |
| :--- | :--- | :---: | :--- |
| [`03_INTEGRACAO_NOTION_OBSIDIAN.md`](03_INTEGRACAO_NOTION_OBSIDIAN.md) | Integração com Notion & Obsidian | `v4.5.0` | Sincronização bidirecional de notas e listas de tarefas |
| [`04_SANDBOX_EXECUCAO_CODIGO.md`](04_SANDBOX_EXECUCAO_CODIGO.md) | Sandbox de Execução de Código | `v4.0.0` | Execução controlada de scripts Python para cálculos e gráficos |
| [`05_VISAO_COMPUTACIONAL_MULTIMODAL.md`](05_VISAO_COMPUTACIONAL_MULTIMODAL.md) | Visão Computacional Multimodal | `v4.0.0` | OCR e análise cognitiva de imagens enviadas no Discord |
| [`09_GESTAO_FINANCEIRA_E_CONTROLE_DE_GASTOS.md`](09_GESTAO_FINANCEIRA_E_CONTROLE_DE_GASTOS.md) | Gestão Financeira Pessoal | `v4.0.0` | Registro de despesas por chat/voz e relatórios mensais |
| [`10_PODCAST_MULTI_VOZ_E_AUDIO_DEBATE.md`](10_PODCAST_MULTI_VOZ_E_AUDIO_DEBATE.md) | Podcast Multi-Voz & Debate | `v5.0.0` | Mini-podcasts com vozes neurais brasileiras complementares |
| [`11_HUB_WEBHOOKS_E_AUTOMACAO_EXTERNA.md`](11_HUB_WEBHOOKS_E_AUTOMACAO_EXTERNA.md) | Hub de Webhooks & Automação | `v4.5.0` | Receptor assíncrono de eventos do GitHub, Stripe e CI/CD |
| [`12_RESUMO_E_RAG_DE_VIDEOS_YOUTUBE.md`](12_RESUMO_E_RAG_DE_VIDEOS_YOUTUBE.md) | RAG de Vídeos do YouTube | `v4.0.0` | Download de transcrições e conversação com minutagem |
| [`13_MEMORIA_GRAFO_DE_CONHECIMENTO_GRAPH_RAG.md`](13_MEMORIA_GRAFO_DE_CONHECIMENTO_GRAPH_RAG.md) | Grafo de Conhecimento (Graph RAG) | `v5.5.0` | Grafo de entidades para raciocínio relacional complexo |
| [`14_SAUDE_HABITOS_E_RASTREAMENTO_DE_ROTINA.md`](14_SAUDE_HABITOS_E_RASTREAMENTO_DE_ROTINA.md) | Rastreamento de Hábitos & Rotina | `v5.5.0` | Check-in diário e métricas de consistência pessoal |
| [`15_SISTEMA_DE_FLASHCARDS_E_REPETICAO_ESPACADA_ANKI.md`](15_SISTEMA_DE_FLASHCARDS_E_REPETICAO_ESPACADA_ANKI.md) | Flashcards & Repetição Espaçada | `v5.5.0` | Criação de cards a partir de leituras e quizzes no chat |
| [`16_MONITOR_DE_PRECOS_E_ALERTAS_DE_COMPRA.md`](16_MONITOR_DE_PRECOS_E_ALERTAS_DE_COMPRA.md) | Monitor de Preços (Price Tracker) | `v4.0.0` | Raspagem periódica de e-commerces com alertas de desconto |
| [`18_DISCORD_VOICE_CHANNEL_ASSISTANT.md`](18_DISCORD_VOICE_CHANNEL_ASSISTANT.md) | Assistente no Canal de Voz | `v5.0.0` | Participação ao vivo em chamadas com VAD e barge-in |
| [`19_GESTAO_DE_EMAILS_E_INBOX_ZERO.md`](19_GESTAO_DE_EMAILS_E_INBOX_ZERO.md) | Gestão de E-mails & Inbox Zero | `v4.5.0` | Classificação de prioridades e minutas de resposta |
| [`21_AUTOMACAO_DE_BACKUP_E_SINCRONIZACAO_CLOUD.md`](21_AUTOMACAO_DE_BACKUP_E_SINCRONIZACAO_CLOUD.md) | Backup & Sincronização Cloud | `v4.0.0` | Snapshots periódicos criptografados de SQLite e ChromaDB |
| [`22_ANALISE_DE_DADOS_E_GRAFICOS_CSV_EXCEL.md`](22_ANALISE_DE_DADOS_E_GRAFICOS_CSV_EXCEL.md) | Análise de Planilhas CSV/Excel | `v4.0.0` | Análise exploratória de dados e plotagem de gráficos |
| [`24_AGY_CODE_SANDBOX_WORKTREE.md`](24_AGY_CODE_SANDBOX_WORKTREE.md) | Sandbox via Git Worktree | `v4.0.0` | Ambientes efêmeros isolados para tarefas do Antigravity |
| [`30_ARENA_DIALETICA_MULTIAGENTE_EM_THREADS.md`](30_ARENA_DIALETICA_MULTIAGENTE_EM_THREADS.md) | Arena Dialética em Threads | `v4.5.0` | Debates turn-by-turn orquestrados por botões interativos |
