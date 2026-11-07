---
agente: architect
data: 2026-11-07
versao: 2.0.0
status: implementado
branch: project/antigravity-discord-bot
projeto: Discord AI Bot (Antigravity)
---

# Evolução e Calibração de Conhecimento: Arquiteto de Software (`/architect`)

## 1. Contexto da Calibração
O agente herdado do repositório central (`modulo_agents`) estava estritamente calibrado para o ecossistema Django monólito/microsserviços, Celery/Redis, pgvector e frameworks de IA pesados (LangChain, LlamaIndex). Neste projeto, a realidade é um **Bot Conversacional Inteligente para Discord** baseado em arquitetura assíncrona orientada a eventos (`discord.py`, `asyncio`), inferência local-first (LM Studio, faster-whisper, ChromaDB, SQLite WAL) com failover transparente para nuvem (Google Gemini API), Tool RAG semântico próprio e Outbox Gateway com rate-limiting.

A calibração foi conduzida pelo `/gerente` seguindo a **Rota 3 (Rito Formal de Entrevista)** em 2 dimensões essenciais, todas aprovadas pelo Arquiteto-Chefe.

---

## 2. Matriz Antes vs Depois

| Dimensão | Antes (Herdado do Central) | Depois (Calibrado para Discord Bot) |
| :--- | :--- | :--- |
| **Filosofia de IA & Stack Central** | Django monólito/microsserviços, Celery/Redis, pgvector, LangChain, LlamaIndex. | **Local-First, Leve e Assíncrono:** Prioridade absoluta para inferência local com LM Studio, faster-whisper e ChromaDB local, com failover para Gemini Cloud. Zero frameworks opacos de IA (LangChain/LlamaIndex); SDKs diretos (`AsyncOpenAI`, `google-genai`). Resiliência do Gateway via `message_gateway.py` (Outbox leaky bucket) e `ContextVars`. |
| **Dinâmica de Debate, Tags & Formalização** | Apontava ADRs para diretórios Django inexistentes. | **Parceria Socrática Implacável & Diagramas:** Ataque prioritário a premissas frágeis (latência, inchaço de memória, condições de corrida assíncronas). Roteamento por tags `[abstrata]` e `[concreta]`. Diagramas Mermaid proativos de concorrência e fluxo de dados. Minutas arquiteturais entregues ao `/doc_master` para atualizar `discord/SPECs/ARQUITETURA.md` ou criar specs em `SPECS_IDEIAS/`, com rascunhos mínimos no chat para o `/coder`. Modo estritamente consultivo. |

---

## 3. Checklist de Arquivos Atualizados
- [x] `gerencial/agentes/architect_20261107.md` (Registro histórico criado)
- [x] `.agents/rules/architect.md` (Regras operacionais atualizadas na branch `project/antigravity-discord-bot`)
- [x] `.agents/skills/architect/SKILL.md` (Definição da skill atualizada)
- [x] `.agents/AGENTS.md` (Catálogo consolidado atualizado na seção do Agente 2)
