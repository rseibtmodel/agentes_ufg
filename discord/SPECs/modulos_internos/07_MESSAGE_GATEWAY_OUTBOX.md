# Especificação Técnica Interna: Barramento Central de Mensagens (Message Gateway & Outbox)

**Código do Módulo:** `MOD-INT-07`  
**Escopo:** Barramento Centralizado de Saída, Fila Outbox Dual-Tier, Deduplicação Anti-Spam SHA-256 com Hashing Profundo de Embeds, Custódia `delete_after_send` e Circuit Breaker  
**Arquivos de Implementação:** [`message_gateway.py`](file:///Users/rodrigomodel/antigravity/discord/message_gateway.py), [`database.py`](file:///Users/rodrigomodel/antigravity/discord/database.py), [`message_handler.py`](file:///Users/rodrigomodel/antigravity/discord/message_handler.py), [`chat_discord.py`](file:///Users/rodrigomodel/antigravity/discord/chat_discord.py)  

---

## 1. Propósito e Motivação

O **Message Gateway** centraliza 100% do tráfego de saída do Discord AI Bot (mensagens de chat, respostas a comandos, notificações de lembretes, resumos matinais e alertas do sistema).

### Problemas Resolvidos:
1. **Eliminação de Chamadas Dispersas:** Módulos de negócio e workers não invocam `channel.send()` diretamente, evitando concorrência caótica e desrespeito a rate limits.
2. **Mitigação de Banimento por Rate Limit (HTTP 429):** O gateway implementa cadência controlada por Leaky Bucket para tráfego em background e Fast-Path para respostas interativas.
3. **Deduplicação Anti-Spam:** Payloads com o mesmo hash SHA-256 enviados em uma janela de 60 segundos são descartados silenciosamente.
4. **Proteção por Circuit Breaker:** Se um canal receber mais de 8 mensagens em 10 segundos, o circuito desarma temporariamente, represando as mensagens no banco de dados e evitando tempestades de pacotes.
5. **Custódia Segura de Arquivos Temporários:** Eliminação de race conditions no envio de áudios TTS e relatórios PDF via `delete_after_send`.

---

## 2. Arquitetura e Estrutura de Classes

### 2.1 Enumeração de Prioridade (`MessagePriority`)
* `HIGH = 1`: Mensagens interativas diretas (chat do usuário e comandos com prefixo). Recebem Fast-Path prioritário (< 100ms) quando o canal estiver calmo.
* `BACKGROUND = 2`: Workers em background (Resumo Matinal, Lembretes, backups e relatórios). Passam obrigatoriamente pela fila com Leaky Bucket (intervalo mínimo de 1.5s entre disparos por canal).

### 2.2 Estrutura do Payload (`OutboxItem`)
Dataclass prioritária ordenada por `(priority, timestamp)`:
- `msg_id`: Identificador único UUID da mensagem.
- `target`: Objeto de destino (canal, thread ou usuário do Discord).
- `channel_id`: Identificador textual do canal de destino.
- `content`: Texto formatado da mensagem.
- `embed`: Objeto `discord.Embed` opcional.
- `file` / `files`: Arquivos anexos (`discord.File`).
- `view`: Objeto `discord.ui.View` interativo (botões ou menus suspensos).
- `reference`: Mensagem de referência para resposta direta (*reply*).
- `delete_after_send`: Lista de caminhos `Path` a serem destruídos apenas após conclusão do envio físico.
- `content_hash`: Hash SHA-256 para deduplicação.

---

## 3. Mecanismos de Proteção e Resiliência

### 3.1 Fast-Path Prioritário vs Fila Background
```python
if priority == MessagePriority.HIGH and not is_breaker_open and time_since_last >= 0.2:
    # Fast-Path imediato síncrono com o event loop
    return await self._send_raw(target, content=content, embed=embed, ...)
else:
    # Enfileiramento na fila prioritária do Outbox (Leaky Bucket)
    await self._queue.put(item)
```

### 3.2 Deduplicação com Hashing Profundo de Embeds
Antes de qualquer despacho, calcula-se o hash SHA-256 incorporando canal, texto, títulos, descrições e campos de Embeds, além de filenames de anexos:
$$\text{Hash} = \text{SHA256}(\text{channel\_id} + \text{content} + \text{embed\_fields} + \text{filenames})$$
Se o hash constar na janela deslizante dos últimos 60 segundos (`GATEWAY_DEBOUNCE_WINDOW_SEC`) com o mesmo canal de destino, a mensagem é descartada, o contador `duplicates_dropped` é incrementado e eventuais arquivos em `delete_after_send` são expurgados com segurança.

### 3.3 Custódia Segura de Arquivos Temporários (`delete_after_send`)
Para prevenir falhas de upload causadas por exclusão prematura de arquivos no sistema operacional:
```python
try:
    return await target.send(**kwargs)
finally:
    if delete_after_send:
        for p in delete_after_send:
            if p and p.exists():
                p.unlink()  # Destruição segura garantida pós-envio
```

### 3.4 Fallback Defensivo de Mensagem de Referência
Se o Discord rejeitar o envio por erro de mensagem referenciada deletada ou expirada (códigos HTTP `160002`, `50035` ou `10008`), o Gateway remove o parâmetro `reference` e reenvia a mensagem normalmente no canal, garantindo que o usuário nunca fique sem resposta.

### 3.5 Persistência e Auditoria no SQLite (`outbox_queue`)
Para fins de rastreabilidade e auditoria, as mensagens processadas pelo gateway têm seu status persistido na tabela `outbox_queue` com status tipados (`sent_fastpath`, `enqueued`, `sent_queued`, `discarded_duplicate`, `circuit_breaker_drop`).

---

## 4. Auditoria e Telemetria

O comando built-in `!gateway` expõe métricas em tempo real consumindo `get_status()`:
* `!gateway status`: Exibe quantidade de mensagens enviadas, mensagens descartadas por deduplicação, estado dos disjuntores por canal e tamanho da fila pendente.
* `!gateway pausar`: Pausa temporariamente o despacho de mensagens em background (`pause()`).
* `!gateway retomar`: Retoma o processamento das filas (`resume()`).
* `!gateway limpar`: Limpa filas pendentes represadas (`clear()`).

---

## 5. 📋 Matriz de Rastreabilidade & Aderência (Auditada em 2026-11-14)

Auditoria realizada via [`/spec-audit`](file:///Users/rodrigomodel/antigravity/.agents/skills/spec-audit/SKILL.md) com homologação do [`/review`](file:///Users/rodrigomodel/antigravity/gerencial/reviews/REV-009_auditoria_message_gateway_outbox.md) e [`/doc_master`](file:///Users/rodrigomodel/antigravity/gerencial/auditorias/auditoria_2026-11-14_07_MESSAGE_GATEWAY_OUTBOX.md):

| ID | Requisito da Especificação | Status | Implementação no Código | Notas de Auditoria |
| :---: | :--- | :---: | :--- | :--- |
| **REQ-01** | Prioridades e fila Dual-Tier (Fast-Path / Background) | 🟢 **Aderente** | [`message_gateway.py:L39-L43,L340-L395`](file:///Users/rodrigomodel/antigravity/discord/message_gateway.py#L39-L43) | `MessagePriority.HIGH` (Fast-Path < 100ms) e `BACKGROUND` (Leaky Bucket). |
| **REQ-02** | Dataclass do Payload Outbox (`OutboxItem`) | 🟢 **Aderente** | [`message_gateway.py:L45-L61`](file:///Users/rodrigomodel/antigravity/discord/message_gateway.py#L45-L61) | Dataclass ordenada por prioridade/timestamp com alvos, views, files e hashes. |
| **REQ-03** | Deduplicação anti-spam com hash SHA-256 | 🟢 **Aderente** | [`message_gateway.py:L145-L190,L319-L336`](file:///Users/rodrigomodel/antigravity/discord/message_gateway.py#L145-L190) | Hash SHA-256 e janela deslizante `GATEWAY_DEBOUNCE_WINDOW_SEC` (60s). |
| **REQ-04** | Circuit Breaker por canal contra rajadas | 🟢 **Aderente** | [`message_gateway.py:L192-L221`](file:///Users/rodrigomodel/antigravity/discord/message_gateway.py#L192-L221) | Bloqueia canais com > 8 msgs em 10s com cooldown de 30s. |
| **REQ-05** | Cadência Leaky Bucket para tráfego background | 🟢 **Aderente** | [`message_gateway.py:L411-L417`](file:///Users/rodrigomodel/antigravity/discord/message_gateway.py#L411-L417) | Intervalo mínimo de 1.5s entre envios no mesmo canal via worker. |
| **REQ-06** | Tabela SQLite `outbox_queue` e auditoria | 🟢 **Aderente** | [`message_gateway.py:L104-L144`](file:///Users/rodrigomodel/antigravity/discord/message_gateway.py#L104-L144) | Persistência de telemetria com status tipados no SQLite. |
| **REQ-07** | Métodos de telemetria e controle `!gateway` | 🟢 **Aderente** | [`message_gateway.py:L490-L527`](file:///Users/rodrigomodel/antigravity/discord/message_gateway.py#L490-L527) | `get_status()`, `pause()`, `resume()`, `clear()`. |
| **REQ-08** | Custódia e destruição segura `delete_after_send` | 🟢 **Aderente** | [`message_gateway.py:L60,L263-L272,L284`](file:///Users/rodrigomodel/antigravity/discord/message_gateway.py#L60) | Limpeza em bloco `finally:` pós-upload (Código Excedente Homologado). |
| **REQ-09** | Fallback defensivo de mensagem de referência | 🟢 **Aderente** | [`message_gateway.py:L253-L258`](file:///Users/rodrigomodel/antigravity/discord/message_gateway.py#L253-L258) | Trata erros 160002/50035/10008 reenviando sem reply (Código Excedente Homologado). |

