---
id: OS-009
data: 2026-11-07
agente_alvo: doc_master
supervisor: agent_manager
fase_roadmap: sincronizacao_governanca_ecossistema
status: concluido
---

# 🎯 ORDEM DE SERVIÇO: @doc_master (Supervisão: @agent_manager)

=====================================================  
👑 **Diretriz do Arquiteto-Chefe [Usuário]:** Execução da Rota A — Sincronização Completa de Governança e Aderência dos Agentes.  
📌 **Objetivo Imediato:**
1. Higienizar os links absolutos no `AGENTS.md`, substituindo `/agentes_inteligentes/` pelo caminho oficial `/antigravity/`.
2. Sincronizar as regras do `@coder` e `@review` (`.agents/rules/` e `.agents/skills/`) com:
   - Taxonomia canônica dos 6 submódulos temáticos de comandos em `discord/commands/`.
   - Uso obrigatório do `message_gateway.dispatch(...)` para envios assíncronos em background.
3. Atualizar o `discord/SPECs/ROADMAP.md` registrando a entrega de `IDEA-17` e `IDEA-23` em `SPECS_IDEIAS_IMPLEMENTADAS/` e cadastrando `IDEA-24` no backlog.
4. Expandir o escopo do `@data_engineer` (`.agents/skills/data_engineer/` e `AGENTS.md`) para parsing forense de faturas de cartão e extratos bancários (PDF/OFX/CSV) em preparação para a IDEA-09.  
🛡️ **Limites & Blast Radius:**  
- Escrita restrita a documentações, regras de agentes e specs (`AGENTS.md`, `ROADMAP.md`, `.agents/`). Zero alteração destrutiva em código de produção.  
📦 **Artefato Esperado:** `AGENTS.md` higienizado, `ROADMAP.md` sincronizado, regras dos agentes atualizadas e testes passando.  
=====================================================

## Checklist de Execução
- [x] Emissão e persistência da OS-009 em `gerencial/ordem_servico/`
- [x] Higienização dos links no `AGENTS.md`
- [x] Atualização do `ROADMAP.md` com status de `IDEA-17`, `IDEA-23` e inclusão de `IDEA-24`
- [x] Atualização das regras do `@coder` e `@review` (Módulos de comandos e Outbox Gateway)
- [x] Atualização do `@data_engineer` para parsing de faturas e finanças (IDEA-09)
- [x] Atualização da seção de inventário do `AGENTS.md`
- [x] Execução da suíte completa de testes (27 testes passando em 0.047s)
- [x] Atualização do status da OS-009 para `concluido` e commit
