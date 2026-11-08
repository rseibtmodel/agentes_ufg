---
id: OS-008
data: 2026-11-07
agente_alvo: coder
supervisor: agent_manager
fase_roadmap: governanca_ajuda_dinamico
status: concluido
---

# 🎯 ORDEM DE SERVIÇO: @coder (Supervisão: @agent_manager & @ux_designer)

=====================================================  
👑 **Diretriz do Arquiteto-Chefe [Usuário]:** Implementação da Rota 1 — Help Dinâmico via CommandRegistry & Atualização das Regras de Governança para Coder, Reviewer e UX Designer.  
📌 **Objetivo Imediato:**
1. Evoluir o `CommandDefinition` e `CommandRegistry` em `discord/commands/registry.py` com:
   - Campos `category: str = "Geral"` e `example: Optional[str] = None`.
   - Métodos `get_categories()` e `get_commands_by_category(cat)`.
2. Refatorar o comando `!ajuda` em `discord/commands/system_commands.py` para gerar menus e detalhes dinamicamente a partir do registro de comandos, sem risco de omissão de novas features.
3. Atualizar as anotações `@register_command` dos comandos existentes em `calendar_commands.py`, `productivity_commands.py`, `ai_commands.py`, `knowledge_commands.py`, `web_commands.py` e `system_commands.py` com categorias e exemplos explícitos.
4. Atualizar as skills e regras dos agentes em `.agents/`:
   - `.agents/skills/coder/SKILL.md` e `.agents/rules/coder.md`: Invariante inegociável de categorização e obrigatoriedade de suporte no `!ajuda`.
   - `.agents/skills/review/SKILL.md` e `.agents/rules/code_review_rules.md`: Veto para comandos sem categoria ou ausentes na documentação de ajuda.
   - `.agents/skills/ux_designer/SKILL.md`: Responsabilidade pela arquitetura de informação e redação de exemplos no `!ajuda`.
5. Validar suíte de testes com testes específicos para o Help dinâmico em `tests/test_commands.py`.  
🛡️ **Limites & Blast Radius:**  
- Preservar compatibilidade total de chamada e aliases dos comandos existentes.
- Garantir não-bloqueância e 100% Type Hints.  
📦 **Artefato Esperado:** Registry e Help dinâmicos, comandos anotados, regras sincronizadas e testes passando.  
=====================================================

## Checklist de Execução
- [x] Emissão e persistência da OS-008 em `gerencial/ordem_servico/`
- [x] Atualização de `discord/commands/registry.py` com `category` e `example`
- [x] Enriquecimento com categorias em todos os módulos de comandos (`web_commands.py`, `system_commands.py`, etc.)
- [x] Refatoração do `cmd_ajuda` em `discord/commands/system_commands.py` para geração dinâmica
- [x] Atualização das regras e skills do `@coder`, `@review` e `@ux_designer`
- [x] Atualização dos testes em `tests/test_commands.py` e homologação da suíte completa (27 testes passando)
- [x] Reinicialização do bot no Discord para carregar as alterações
- [x] Atualização do status da OS-008 para `concluido` e commit
