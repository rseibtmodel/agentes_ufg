# Ordem de Serviço OS-018: Institucionalização da Comunicação Obrigatória Coder $\rightarrow$ DocMaster

**Status:** `concluido`  
**Data de Emissão:** 2026-11-14  
**Responsável pela Emissão:** [Agent Manager (`/gerente`)](file:///Users/rodrigomodel/antigravity/.agents/skills/agent_manager/SKILL.md)  
**Agentes Impactados:** [/coder](file:///Users/rodrigomodel/antigravity/.agents/skills/coder/SKILL.md), [/doc_master](file:///Users/rodrigomodel/antigravity/.agents/skills/doc_master/SKILL.md), [/review](file:///Users/rodrigomodel/antigravity/.agents/skills/review/SKILL.md)  
**Destinatário Soberano:** Arquiteto e Engenheiro-Chefe (Usuário)

---

## 1. Contexto & Diretriz Soberana

Por determinação imperativa e soberana do Arquiteto-Chefe:
> *"toda a alteração no código deve ser comunicada para o /doc_master para ele poder registrar caso tenha alguma alteração em algum módulo ou então incluir novos módulos."*

Para assegurar que essa diretriz não se perca nem dependa de memória contextual efêmera, o `agent_manager` formalizou a blindagem definitiva do ecossistema nos arquivos de regras (`.agents/rules/`), skills (`.agents/skills/`) e no catálogo central ([`AGENTS.md`](file:///Users/rodrigomodel/antigravity/AGENTS.md)).

---

## 2. Ações Implementadas & Blindagem nos Agentes

### 1. `/coder` (Estagiário Codificador)
* **Regra Adicionada em [`.agents/rules/coder.md`](file:///Users/rodrigomodel/antigravity/.agents/rules/coder.md):**
  * *Protocolo Compulsório de Comunicação ao `/doc_master` (DoD Inegociável):* Proibido de considerar qualquer tarefa concluída ou submeter código ao `/review` sem formalizar o handoff ao `/doc_master`.
* **Skill Atualizada em [`.agents/skills/coder/SKILL.md`](file:///Users/rodrigomodel/antigravity/.agents/skills/coder/SKILL.md):**
  * Fluxo Mermaid atualizado com etapa obrigatória: `Tests --> DocHandoff["Handoff Compulsório ao /doc_master"] --> ValidationMsg`.
  * Inclusão do 9º Princípio Inegociável de desenvolvimento.

### 2. `/review` (Tech Lead Reviewer)
* **Regra Adicionada em [`.agents/rules/code_review_rules.md`](file:///Users/rodrigomodel/antigravity/.agents/rules/code_review_rules.md):**
  * *Critério de Veto Crítico nº 9:* Veto compulsório em qualquer PR, refatoração ou entrega de código que altere lógica de módulos existentes ou crie novos módulos sem a formalização prévia do handoff/notificação ao `/doc_master`.

### 3. `/doc_master` (Guardião da Documentação & Specs)
* **Regra Adicionada em [`.agents/rules/doc_master.md`](file:///Users/rodrigomodel/antigravity/.agents/rules/doc_master.md):**
  * *Protocolo Compulsório de Recepção de Handoffs de Código:* Processamento imediato de toda notificação do `/coder` para atualizar especificações existentes em `modulos_visiveis/` e `modulos_internos/` ou criar nova especificação canônica numerada, sincronizando compulsoriamente os índices mestres.
* **Skill Atualizada em [`.agents/skills/doc_master/SKILL.md`](file:///Users/rodrigomodel/antigravity/.agents/skills/doc_master/SKILL.md):**
  * 4º Princípio de Governança Documental dedicado à recepção de alterações de código.

### 4. Roster Central ([`AGENTS.md`](file:///Users/rodrigomodel/antigravity/AGENTS.md))
* Atualização do diagrama Mermaid de topologia destacando o vínculo sólido compulsório: `Coder ==>|Compulsório: Notificação de Mudança de Código / Novo Módulo| DocMaster`.
* Matriz de inventário com Handoff do `/coder` apontando explicitamente `/doc_master (Compulsório)`.
* Responsabilidades e limites dos Agentes 1, 3 e 5 sincronizados com a diretriz.

---

## 3. Checklist de Verificação

- [x] Regra do Coder atualizada em `.agents/rules/coder.md`
- [x] Skill do Coder atualizada em `.agents/skills/coder/SKILL.md`
- [x] Regra do Reviewer atualizada com Critério 9 de Veto em `.agents/rules/code_review_rules.md`
- [x] Regra do DocMaster atualizada em `.agents/rules/doc_master.md`
- [x] Skill do DocMaster atualizada em `.agents/skills/doc_master/SKILL.md`
- [x] Topologia e descrições atualizadas em `AGENTS.md`
- [x] Ordem de Serviço registrada em `gerencial/ordem_servico/OS-018_institucionalizacao_comunicacao_obrigatoria_coder_doc_master.md`
