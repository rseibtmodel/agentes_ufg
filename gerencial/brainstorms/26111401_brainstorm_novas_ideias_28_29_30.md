# Dossiê de Brainstorm: Novas Ideias para o Ecossistema (IDEA-28, IDEA-29, IDEA-30)

**Data da Sessão:** 2026-11-14  
**Orquestrador:** Meta-Skill [`/brainstorm`](file:///Users/rodrigomodel/antigravity/.agents/skills/brainstorm/SKILL.md)  
**Agentes Participantes:** [/oraculo](file:///Users/rodrigomodel/antigravity/.agents/skills/oraculo/SKILL.md), [/hacker](file:///Users/rodrigomodel/antigravity/.agents/skills/hacker/SKILL.md), [/critic](file:///Users/rodrigomodel/antigravity/.agents/skills/critic/SKILL.md), [/impact](file:///Users/rodrigomodel/antigravity/.agents/skills/impact/SKILL.md), [/ux_designer](file:///Users/rodrigomodel/antigravity/.agents/skills/ux_designer/SKILL.md), [/architect](file:///Users/rodrigomodel/antigravity/.agents/skills/architect/SKILL.md) e [/alquimista](file:///Users/rodrigomodel/antigravity/.agents/skills/alquimista/SKILL.md)  
**Diretriz Soberana:** Foco em três novas ideias estruturantes processadas uma por vez, descarte das propostas secundárias e condução com calibração humana contínua.

---

## 1. Resumo Executivo das Entregas

Três novas especificações formais de ideias de módulos foram lapidadas, aprovadas e persistidas em [`discord/SPECs/SPECS_IDEIAS/`](file:///Users/rodrigomodel/antigravity/discord/SPECs/SPECS_IDEIAS/):

| Código | Título da Proposta | Arquivo da Spec | Score Alquimista | Classificação |
| :---: | :--- | :--- | :---: | :---: |
| **`IDEA-28`** | FinOps, Telemetria de Tokens & Observabilidade LLM | [`28_FINOPS_TELEMETRIA_DE_TOKENS_E_CUSTOS_LLM.md`](file:///Users/rodrigomodel/antigravity/discord/SPECs/SPECS_IDEIAS/28_FINOPS_TELEMETRIA_DE_TOKENS_E_CUSTOS_LLM.md) | **9.4** | 🥇 Ouro |
| **`IDEA-29`** | Radar Autônomo de RSS, ArXiv & Curadoria de Feeds | [`29_RADAR_AUTONOMO_RSS_E_CURADORIA_DE_FEEDS.md`](file:///Users/rodrigomodel/antigravity/discord/SPECs/SPECS_IDEIAS/29_RADAR_AUTONOMO_RSS_E_CURADORIA_DE_FEEDS.md) | **9.3** | 🥇 Ouro |
| **`IDEA-30`** | Arena Dialética Multiagente em Threads do Discord | [`30_ARENA_DIALETICA_MULTIAGENTE_EM_THREADS.md`](file:///Users/rodrigomodel/antigravity/discord/SPECs/SPECS_IDEIAS/30_ARENA_DIALETICA_MULTIAGENTE_EM_THREADS.md) | **9.5** | 🥇 Ouro |

---

## 2. Dossiê Sintético de Cada Ideia

### 📊 IDEA-28: FinOps & Telemetria de Tokens
* **Convergência Técnica:** Buffer assíncrono em lote com `executemany` a cada 30 segundos no SQLite WAL (`llm_token_logs`).
* **Regra de Fallback Gracioso:** Ao atingir a cota diária de nuvem, o bot não aborta a requisição; chaveia transparentemente para o LM Studio local gratuito exibindo um badge semântico.
* **Isolamento de Background:** Chamadas do sistema (Digest e Deep Research) possuem cota dedicada (`user_id='SYSTEM_BACKGROUND'`), impedindo canibalização das cotas de usuários.
* **Artefato Alquimista:** [`26111401_alquimia_94_finops_telemetria_tokens_llm.json`](file:///Users/rodrigomodel/antigravity/alquimista_ideias/ouro/26111401_alquimia_94_finops_telemetria_tokens_llm.json).

### 📡 IDEA-29: Radar Autônomo de RSS, ArXiv & GitHub
* **Convergência Técnica:** Poller assíncrono com loop único e agendamento granular no SQLite WAL (`next_run_at`).
* **Cache Inteligente:** Uso de ETag / Last-Modified com retorno `304 Not Modified` para evitar consumo de banda e rate limits.
* **Filtragem em Duas Fases:** Regex local preliminar de keywords (custo zero de tokens) $\rightarrow$ Síntese via LLM somente para os artigos aprovados.
* **Frequência Dinâmica:** Modo duplo configurável por feed/usuário: **Tempo Real** para alertas críticos e **Boletins Consolidados** para leituras diárias.
* **Artefato Alquimista:** [`26111402_alquimia_93_radar_autonomo_rss_feeds.json`](file:///Users/rodrigomodel/antigravity/alquimista_ideias/ouro/26111402_alquimia_93_radar_autonomo_rss_feeds.json).

### ⚔️ IDEA-30: Arena Dialética Multiagente em Threads
* **Convergência Técnica:** Reuso de um único Webhook (`Antigravity-Theater`) no canal pai com override dinâmico de `username` e `avatar_url` para postar falas na Thread como especialistas distintos.
* **Controle Humano Passo a Passo:** Views persistentes (`timeout=None`) no SQLite WAL com botões `[▶️ Próxima Rodada]`, `[✍️ Injetar Opinião]` (modal) e `[🛑 Encerrar & Sintetizar]`.
* **Personas Nativas:** Dois avatares iniciais padrão (🏛️ Arquiteto Sênior e 💻 Hacker Pragmático), com suporte completo a qualquer persona customizada do ecossistema.
* **Artefato Alquimista:** [`26111403_alquimia_95_arena_dialetica_threads.json`](file:///Users/rodrigomodel/antigravity/alquimista_ideias/ouro/26111403_alquimia_95_arena_dialetica_threads.json).

---

## 3. Próximos Passos Recomendados

1. **Revisão pelo Arquiteto-Chefe:** Validar os três documentos criados em `discord/SPECs/SPECS_IDEIAS/`.
2. **Atualização do Roadmap:** Incorporar os três módulos no backlog do [`discord/SPECs/ROADMAP.md`](file:///Users/rodrigomodel/antigravity/discord/SPECs/ROADMAP.md) vinculando aos arquivos criados.
3. **Commit & Push:** Salvar os novos artefatos no repositório remoto.
