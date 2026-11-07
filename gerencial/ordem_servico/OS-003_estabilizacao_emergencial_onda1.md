---
id: OS-003
data: 2026-11-07
agente_alvo: coder
supervisor: review
fase_roadmap: refatoracao_onda_1
status: concluido
---

# 🎯 ORDEM DE SERVIÇO: @coder (Supervisão: @review)

=====================================================  
👑 **Diretriz do Arquiteto-Chefe [Usuário]:** Implementação da Onda 1 de Refatoração — Estabilização Emergencial de Concorrência, Gateway e Contexto.  
📌 **Objetivo Imediato:** Sanar os 5 débitos técnicos prioritários mapeados no laudo `REV-001`:
1. `BUG-02`: Eliminar a race condition de exclusão prematura de arquivos temporários de áudio no Message Gateway.
2. `BUG-07` & `BUG-08`: Corrigir import de `Any`, adicionar `from __future__ import annotations` e isolar pendências por `user_id` em `context_manager.py`.
3. `BUG-06`: Garantir que 100% dos despachos em `CommandContext.reply()` passem pelo `message_gateway` com suporte a `reference`.
4. `BUG-04`: Envolver chamadas síncronas de rede do Google Calendar em `asyncio.to_thread()` em `commands/builtins.py`.
5. `BUG-11`: Unificar conexões SQLite em `reminder_manager.py` utilizando `_get_connection()` com timeout de 30s e WAL.  
🛡️ **Limites & Blast Radius:** Modificação cirúrgica restrita aos arquivos:
- `discord/context_manager.py`
- `discord/message_gateway.py`
- `discord/message_handler.py`
- `discord/commands/registry.py`
- `discord/commands/builtins.py`
- `discord/reminder_manager.py`  
Não quebrar contratos de chamadas existentes. Preservar 100% de tipagem estática (PEP 484).  
📦 **Artefato Esperado:** Código refatorado, testado em bancada e validado sem erros de sintaxe ou importação.  
=====================================================

## Checklist de Execução
- [x] Emissão e persistência da OS-003 em `gerencial/ordem_servico/`
- [x] Refatoração de `discord/context_manager.py` (correção de `Any`, `__future__` e chaveamento por `user_id`)
- [x] Refatoração de `discord/message_gateway.py` e `discord/message_handler.py` (suporte a `delete_after_send` e `reference` de mensagem)
- [x] Refatoração de `discord/commands/registry.py` (canalização integral de `reply()` via `message_gateway`)
- [x] Refatoração de `discord/commands/builtins.py` (chamadas Google Calendar não-bloqueantes com `asyncio.to_thread`)
- [x] Refatoração de `discord/reminder_manager.py` (conexões seguras com `_get_connection` e timeout de 30s)
- [x] Teste de bancada (validação de imports, tipos e integridade do bot)
- [x] Atualização do status da OS-003 para `concluido` e commit das alterações
