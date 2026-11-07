---
agente: doc_master
data: 2026-11-07
versao: 2.0.0
status: implementado
branch: project/antigravity-discord-bot
projeto: Discord AI Bot (Antigravity)
---

# Evolução e Calibração de Conhecimento: Guardião da Documentação & Specs (`/doc_master`)

## 1. Contexto da Calibração
O agente herdado do repositório central (`modulo_agents`) estava estritamente calibrado para gerenciar diretórios inexistentes no projeto (`projeto_testes/specs/` e `projeto_testes/reviews/`), mediando desdobramentos burocráticos de ações de Django. Neste projeto, a documentação real e consolidada reside em [`discord/SPECs/`](file:///Users/rodrigomodel/antigravity/discord/SPECs/) (`ARQUITETURA.md`, `ROADMAP.md`, `modulos_visiveis/`, `modulos_internos/`, `SPECS_IDEIAS/`, `SPECS_IDEIAS_IMPLEMENTADAS/`) e os registros de governança em [`gerencial/`](file:///Users/rodrigomodel/antigravity/gerencial/).

A calibração foi conduzida pelo `/gerente` seguindo a **Rota 3 (Rito Formal de Entrevista)** em 2 dimensões essenciais, todas aprovadas pelo Arquiteto-Chefe.

---

## 2. Matriz Antes vs Depois

| Dimensão | Antes (Herdado do Central) | Depois (Calibrado para Discord Bot) |
| :--- | :--- | :--- |
| **Taxonomia Canônica & Ciclo de Ideias** | Diretórios inexistentes `projeto_testes/specs/` e `projeto_testes/reviews/`. | **Estrutura Canônica do Discord Bot:** Gestão de [`discord/SPECs/`](file:///Users/rodrigomodel/antigravity/discord/SPECs/) (`modulos_visiveis/`, `modulos_internos/`, `ARQUITETURA.md`, `ROADMAP.md`) e sincronização do [`README.md`](file:///Users/rodrigomodel/antigravity/README.md) raiz. Ciclo de vida: novas ideias entram em `SPECS_IDEIAS/`, vinculadas ao `ROADMAP.md` e, após entrega do `/coder`, movidas para `SPECS_IDEIAS_IMPLEMENTADAS/`. Veto a desvios arquiteturais não autorizados. |
| **Governança, Tools & Consulta Proativa** | Intermediação burocrática em `reviews/action/`. | **Integração Ágil & Inventário de Tools:** Monitora os laudos em `gerencial/reviews/` e as Ordens de Serviço do `/gerente`, sincronizando as specs sem pastas burocráticas redundantes. Mantém o inventário técnico de ferramentas de *Function Calling* (`discord/tools/`) em `discord/SPECs/modulos_internos/`. Consulta proativamente `/architect` e `/ux_designer`. Blast radius restrito à documentação. |

---

## 3. Checklist de Arquivos Atualizados
- [x] `gerencial/agentes/doc_master_20261107.md` (Registro histórico criado)
- [x] `.agents/rules/doc_master.md` (Regras operacionais atualizadas na branch `project/antigravity-discord-bot`)
- [x] `.agents/skills/doc_master/SKILL.md` (Definição da skill atualizada)
- [x] `.agents/AGENTS.md` (Catálogo consolidado atualizado na seção do Agente 5)
