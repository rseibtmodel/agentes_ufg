# Ordem de Serviço: OS-012 - Correção de Badges Duplicados e Deduplicação Anti-Spam em Embeds

- **ID:** `OS-012`
- **Data:** 09/11/2026
- **Alvo:** `@coder` (Estagiário Codificador)
- **Origem:** Incidentes reportados pelo Arquiteto-Chefe no canal de chat (Badges 3x e corte de mensagens longas)
- **Status:** Concluído (Entregue & Validado)

---

## 👑 Diretriz do Arquiteto-Chefe [Usuário]
1. Eliminar a duplicação e repetição do badge de modelo (`⚡ [Google Gemini...]`), garantindo que apareça rigorosamente uma única vez.
2. Garantir que respostas longas sejam divididas e entregues integralmente em 2 ou mais mensagens, sem que nenhuma parte seja descartada pelo bot.

---

## 📌 Diagnóstico & Causa Raiz
1. **Badges Repetidos:** O texto da resposta era gravado no SQLite e ChromaDB com o badge de UI concatenado. Ao carregar o histórico de conversas, a LLM imitava o padrão das mensagens anteriores do assistente e gerava o badge no próprio texto, além do badge injetado pelo `llm_client`.
2. **Corte de Mensagens Longas:** A divisão por `dividir_mensagem` funcionava, mas o despacho com fallback de persona usava `discord.Embed(description=chunk)` com `content=None`. A função `_generate_hash` do `message_gateway` gerava o hash usando apenas `channel_id` (pois `content` era nulo), produzindo o mesmo hash para todos os chunks. O Chunk 1 era descartado como mensagem duplicada pelo Anti-Spam.

---

## 🔧 Correções Exigidas
1. **[`discord/message_gateway.py`](file:///Users/rodrigomodel/antigravity/discord/message_gateway.py):**
   - Atualizar `_generate_hash` para extrair e hashear `embed.description`, `embed.title` e campos do `embed`.
   - Garantir que chunks de continuação usem `forcar_dedup=True`.
2. **[`discord/message_handler.py`](file:///Users/rodrigomodel/antigravity/discord/message_handler.py):**
   - Separar `resposta_texto` puro de `resposta_com_badge`.
   - Salvar no SQLite (`messages`) e ChromaDB estritamente o texto sem badge.
   - Sanitizar mensagens anteriores do histórico ao montar o payload para a LLM, removendo badges legados.
   - Adicionar rodapé visual nos Embeds fatiados (`📄 Parte X de Y`).
   - Passar `forcar_dedup=True` no despacho sequencial de chunks.
3. **[`discord/llm_client.py`](file:///Users/rodrigomodel/antigravity/discord/llm_client.py):**
   - Sanitizar preventivamente qualquer badge duplicado no início do texto gerado pela LLM antes de adicionar o badge oficial.
4. **Limpeza do Banco:**
   - Sanitizar mensagens no banco SQLite que continham badges gravados no corpo.

---

## 🛡️ Limites & Blast Radius
- Não quebrar suporte a áudio TTS nem views interativas associadas ao último chunk.
- Manter 100% de cobertura nos testes automatizados.
