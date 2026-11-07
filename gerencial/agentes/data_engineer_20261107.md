---
agente: data_engineer
data: 2026-11-07
versao: 2.0.0
status: implementado
branch: project/antigravity-discord-bot
projeto: Discord AI Bot (Antigravity)
---

# Evolução e Calibração de Conhecimento: Engenheiro de Dados & Parser Forense (`/data_engineer`)

## 1. Contexto da Calibração
O agente herdado do repositório central (`modulo_agents`) estava estritamente calibrado para engenharia reversa de faturas bancárias em PDF, conciliação de extratos OFX/CSV, IOF e câmbio financeiro. Neste projeto, a realidade é um **Bot Conversacional Inteligente para Discord** com foco em **Ingestão Multimodal (PDFs/Livros e Áudio)**, **Chunking Semântico para ChromaDB**, extração de sumários estruturados (TOC) via PyMuPDF e transcrição em tempo real com faster-whisper.

A calibração foi conduzida pelo `/gerente` seguindo a **Rota 3 (Rito Formal de Entrevista)** em 2 dimensões essenciais, todas aprovadas pelo Arquiteto-Chefe.

---

## 2. Matriz Antes vs Depois

| Dimensão | Antes (Herdado do Central) | Depois (Calibrado para Discord Bot) |
| :--- | :--- | :--- |
| **Escopo de Pipelines & Modelagem** | Faturas bancárias em PDF, arquivos CSV/OFX de bancos, IOF e câmbio. | **Ingestão Multimodal & Book RAG:** Extração de metadados e sumários TOC de PDFs com PyMuPDF, chunking hierárquico com citação de páginas para ChromaDB, transcrição de voz com faster-whisper e VAD, dataclasses imutáveis tipadas (`@dataclass(frozen=True)`) e isolamento seguro de arquivos por usuário (`discord/pdf/{user}/`). |
| **Resiliência Forense & Fallbacks** | Conciliação de centavos e detecção de CNPJ. | **Defesas Contra Falhas & Idempotência:** Fallback de TOC em PDFs sem sumário, detecção de PDFs escaneados (`sem_camada_texto: bool`), descarte de silêncios com VAD contra alucinações do Whisper (`sem_fala: True`), cache idempotente por hash SHA-256 em SQLite e telemetria rica de extração. |

---

## 3. Checklist de Arquivos Atualizados
- [x] `gerencial/agentes/data_engineer_20261107.md` (Registro histórico criado)
- [x] `.agents/rules/data_engineer.md` (Regras operacionais atualizadas na branch `project/antigravity-discord-bot`)
- [x] `.agents/skills/data_engineer/SKILL.md` (Definição da skill atualizada)
- [x] `.agents/AGENTS.md` (Catálogo consolidado atualizado na seção do Agente 11)

