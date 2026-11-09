# Ordem de Serviço: OS-010 - Identidade Multimodal de Personas (Onda 1 - IDEA-27)

- **ID:** `OS-010`
- **Data:** 09/11/2026
- **Alvo:** `@coder` (Estagiário Codificador)
- **Origem:** Rota 1 aprovada pelo Arquiteto-Chefe sobre a [`IDEA-27`](file:///Users/rodrigomodel/antigravity/discord/SPECs/SPECS_IDEIAS/27_IDENTIDADE_MULTIMODAL_E_METAMORFOSE_SEMANAL.md)
- **Status:** Em Execução

---

## 👑 Diretriz do Arquiteto-Chefe [Usuário]
Implementar a **Onda 1** da IDEA-27: estruturar o suporte completo a avatares, nomes, idades, biografias e sementes visuais por persona de canal no SQLite WAL, com despacho polimórfico (Webhook Masquerade por canal e fallback para Embed com Author Header), injeção cognitiva no System Prompt e novos comandos de gerenciamento (`!persona avatar`, `!persona identidade`, `!persona fixar`, `!persona destravar`, `!persona editar`).

---

## 📌 Objetivo Imediato
1. **Migration Segura no SQLite WAL ([`persona_manager.py`](file:///Users/rodrigomodel/antigravity/discord/persona_manager.py)):**
   - Adicionar colunas `display_name`, `avatar_url`, `avatar_seed`, `age`, `bio`, `is_adaptive`, `is_locked`, `last_evolved_at`, `evolution_history_json`.
   - Atualizar funções de consulta e cadastro para serializar e desserializar esses campos.
2. **Injeção Cognitiva Identitária ([`message_handler.py`](file:///Users/rodrigomodel/antigravity/discord/message_handler.py)):**
   - Injetar no prompt de sistema do canal as instruções de identidade da persona (Nome, Idade, Bio) para que a LLM assuma o personagem de forma coerente.
3. **Despacho Polimórfico ([`message_gateway.py`](file:///Users/rodrigomodel/antigravity/discord/message_gateway.py) & [`message_handler.py`](file:///Users/rodrigomodel/antigravity/discord/message_handler.py)):**
   - Envio de resposta pelo webhook gerenciado do canal (`username` e `avatar_url` da persona) se o bot tiver permissão; caso contrário, envio com Embed e Author Header estruturado.
4. **Comandos de Gerenciamento & Modal UI ([`ai_commands.py`](file:///Users/rodrigomodel/antigravity/discord/commands/ai_commands.py) & [`ui_components.py`](file:///Users/rodrigomodel/antigravity/discord/ui_components.py)):**
   - `!persona avatar <url>`
   - `!persona identidade <nome> | <idade> | <bio>`
   - `!persona fixar` / `!persona travar`
   - `!persona destravar`
   - `!persona editar` (Modal nativo do Discord)
5. **Cobertura de Testes Automatizados:**
   - Testes unitários atualizados em `tests/` cobrindo as novas funções e comandos.

---

## 🛡️ Limites & Blast Radius
- Proibido quebrar comandos existentes de `!persona canal` ou `!persona preset`.
- Proibido introduzir dependências externas (usar DiceBear API / Avatars locais como fallback).
- Não alterar operações síncronas no loop principal (todas as operações de banco e webhook devem ser não-bloqueantes).
- 100% Type Hints (PEP 484).

---

## 📦 Artefatos Esperados
- Código atualizado em `discord/persona_manager.py`, `discord/commands/ai_commands.py`, `discord/ui_components.py`, `discord/message_handler.py`.
- Testes em `tests/` passando 100%.
