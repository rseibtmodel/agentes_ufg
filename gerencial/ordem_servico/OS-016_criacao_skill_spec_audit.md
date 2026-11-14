# OS-016: Criação da Skill `/spec-audit` & Adaptação do Ecossistema

**Data:** 14 de Novembro de 2026  
**Status:** Concluída  
**Autor:** Agent Manager (`/gerente`)  
**Especialista Convocado:** Spec Auditor (`/spec-audit`), Doc Master (`/doc_master`), Reviewer (`/review`), Coder (`/coder`)  
**Alvo:** `.agents/skills/`, `.agents/rules/`, `AGENTS.md`, `gerencial/`  

---

## 👑 1. Diretriz do Arquiteto-Chefe [Usuário]
Criar uma nova skill oficial para o Antigravity IDE chamada `spec-audit` (acionada via `/spec-audit`), com papel de auditoria forense de conformidade entre especificações em Markdown (`.md`) e código real (Python e SQL), mapeamento cirúrgico de rastreabilidade reversa (`arquivo:símbolo:linhas`), gestão de código excedente (*scope creep*) e orquestração sequencial dos agentes (`/review` $\rightarrow$ `/doc_master`). Adaptar os agentes `/doc_master`, `/review` e `/coder` para os novos contratos operacionais, cumprindo o rito interativo de entrevista do `/gerente`.

---

## ⚙️ 2. Decisões de Calibração da Entrevista

1. **Mapeamento Canônico de Especificações (Pergunta 1 - Opção A):**  
   O `/spec-audit` aceita o caminho explícito de qualquer `.md` informado na linha de comando (`/spec-audit <caminho.md>`), mas adota como fonte canônica de padrões do sistema os diretórios [`discord/SPECs/`](file:///Users/rodrigomodel/antigravity/discord/SPECs/) e [`README.md`](file:///Users/rodrigomodel/antigravity/README.md), mantendo compatibilidade com `/docs`.
2. **Protocolo de Código Excedente (Pergunta 2 - Opção A + Aditivo):**  
   Ao detectar código sem lastro na spec, o `/spec-audit` consulta o `/coder`, que emite um mini-relatório estruturado em 4 blocos (Evidência, Motivação, Classificação e Recomendação) e **salva compulsoriamente em disco** em `gerencial/auditorias/pareceres/`.
3. **Taxonomia de Persistência & Atualização da Spec (Pergunta 3 - Opção A):**  
   - Relatórios consolidados gravados em `gerencial/auditorias/auditoria_{YYYY-MM-DD}_{modulo}.md`;
   - Conflitos adiados gravados em `gerencial/conflitos/conflito_{YYYY-MM-DD}_{modulo}_{slug}.md`;
   - Atualização da spec original via `/doc_master` anexando a seção `## 📋 Matriz de Rastreabilidade & Aderência (Auditada em YYYY-MM-DD)` com links clicáveis `[arquivo.py:L10-L45](file:///...)`.

---

## 📦 3. Artefatos Criados & Atualizados

| Artefato | Caminho do Arquivo | Descrição |
| :--- | :--- | :--- |
| **Nova Skill** | [`.agents/skills/spec-audit/SKILL.md`](file:///Users/rodrigomodel/antigravity/.agents/skills/spec-audit/SKILL.md) | Definição da skill com 6 etapas, contratos e regra absoluta de não-escrita. |
| **Novas Regras** | [`.agents/rules/spec_audit.md`](file:///Users/rodrigomodel/antigravity/.agents/rules/spec_audit.md) | Diretrizes operacionais e invariantes analíticas da auditoria. |
| **Doc Master (Skill)** | [`.agents/skills/doc_master/SKILL.md`](file:///Users/rodrigomodel/antigravity/.agents/skills/doc_master/SKILL.md) | Incorpora busca de contexto (Etapa 1) e persistência de rastreabilidade/relatórios (Etapa 5). |
| **Doc Master (Regras)** | [`.agents/rules/doc_master.md`](file:///Users/rodrigomodel/antigravity/.agents/rules/doc_master.md) | Regras para injeção da tabela de rastreabilidade no `.md` e gravação de conflitos. |
| **Reviewer (Skill)** | [`.agents/skills/review/SKILL.md`](file:///Users/rodrigomodel/antigravity/.agents/skills/review/SKILL.md) | Consumo da Matriz Completa de Auditoria para emissão de laudo `REV-{NNN}`. |
| **Reviewer (Regras)** | [`.agents/rules/code_review_rules.md`](file:///Users/rodrigomodel/antigravity/.agents/rules/code_review_rules.md) | Critérios de veto e validação técnica de divergências e código excedente. |
| **Coder (Skill)** | [`.agents/skills/coder/SKILL.md`](file:///Users/rodrigomodel/antigravity/.agents/skills/coder/SKILL.md) | Protocolo de mini-relatório em 4 blocos e persistência compulsória em disco. |
| **Coder (Regras)** | [`.agents/rules/coder.md`](file:///Users/rodrigomodel/antigravity/.agents/rules/coder.md) | Regras para não apagar código passivamente antes da decisão humana. |
| **Governança & Roster** | [`AGENTS.md`](file:///Users/rodrigomodel/antigravity/AGENTS.md) | Registro do 16º agente, tabela de permissões, blast radius e diagrama Mermaid. |
| **Diretórios de Suporte** | `gerencial/conflitos/`<br>`gerencial/auditorias/pareceres/` | Pastas versionadas com `.gitkeep` para persistência de conflitos e pareceres. |

