---
id: OS-005
data: 2026-11-07
agente_alvo: coder
supervisor: qa
fase_roadmap: refatoracao_onda_3
status: concluido
---

# 🎯 ORDEM DE SERVIÇO: @coder (Supervisão: @qa & @review)

=====================================================  
👑 **Diretriz do Arquiteto-Chefe [Usuário]:** Implementação da Onda 3 de Refatoração via Rota 3 (Modularização Primeiro + Suíte Formal de Testes).  
📌 **Objetivo Imediato:**
1. `BUG-13`: Modularizar `discord/commands/builtins.py` (~1.080 linhas) dividindo os comandos em submódulos temáticos especializados dentro de `discord/commands/`:
   - `system_commands.py` (ajuda, ping, status, modo de resposta)
   - `calendar_commands.py` (agenda, compromissos Google Calendar)
   - `ai_commands.py` (modelo, persona, prompt hub)
   - Manter `builtins.py` importando todos os submódulos para retrocompatibilidade total.
2. `BUG-12`: Criar a suíte formal de testes assíncronos no diretório `tests/` cobrindo os módulos críticos do sistema:
   - `test_gateway.py` (MessageGateway, fila, timeout, chunking)
   - `test_context_manager.py` (ContextVars, isolamento de views/arquivos por user_id)
   - `test_tool_registry.py` (despachante de tools, normalização de schema canônico `{"sucesso", "dados", "erro"}`)
   - `test_commands.py` (registro e execução de comandos)  
🛡️ **Limites & Blast Radius:**  
- Criar novos arquivos em `discord/commands/` e `tests/`.
- Não quebrar prefixos de comandos existentes (`!ajuda`, `!agenda`, `!modelo`, etc.).
- Preservar 100% de tipagem estática (PEP 484) e não introduzir operações bloqueantes.  
📦 **Artefato Esperado:** Comandos modularizados, `tests/` configurado e 100% dos testes passando via pytest/unittest.  
=====================================================

## Checklist de Execução
- [x] Emissão e persistência da OS-005 em `gerencial/ordem_servico/`
- [x] Inspeção e mapeamento dos comandos em `discord/commands/builtins.py`
- [x] Criação dos submódulos especializados em `discord/commands/`
- [x] Adequação de `discord/commands/builtins.py` como agregador transparente
- [x] Validação do registro dos comandos em bancada (31 comandos e 75 aliases)
- [x] Implementação da suíte de testes em `tests/` (Gateway, Context, Tools, Commands)
- [x] Execução e homologação de 100% dos testes automatizados (15/15 OK)
- [x] Atualização do status da OS-005 para `concluido` e commit da Onda 3

