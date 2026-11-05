# Especificação Técnica Interna: Barramento Central de Mensagens (Message Gateway & Outbox)

**Código do Módulo:** `MOD-INT-07`  
**Escopo:** Barramento Centralizado de Saída, Fila Outbox Dual-Tier, Deduplicação Anti-Spam SHA-256 e Circuit Breaker  
**Arquivos de Implementação:** [`message_gateway.py`](file:///Users/rodrigomodel/antigravity/discord/message_gateway.py), [`database.py`](file:///Users/rodrigomodel/antigravity/discord/database.py), [`message_handler.py`](file:///Users/rodrigomodel/antigravity/discord/message_handler.py), [`chat_discord.py`](file:///Users/rodrigomodel/antigravity/discord/chat_discord.py)  

---

## 1. Propósito e Motivação

O **Message Gateway** centraliza 100% do tráfego de saída do Discord AI Bot (mensagens de chat, respostas a comandos, notificações de lembretes, resumos matinais e alertas do sistema).

### Problemas Resolvidos:
1. **Eliminação de Chamadas Dispersas:** Módulos de negócio e workers não invocam `channel.send()` diretamente, evitando concorrência caótica e desrespeito a rate limits.
2. **Mitigação de Banimento por Rate Limit (HTTP 429):** O gateway implementa cadência controlada por Leaky Bucket para tráfego em background e Fast-Path para respostas interativas.
3. **Deduplicação Anti-Spam:** Payloads com o mesmo hash SHA-256 enviados em uma janela de 60 segundos são descartados silenciosamente.
4. **Proteção por Circuit Breaker:** Se um canal receber mais de 8 mensagens em 10 segundos, o circuito desarma temporariamente, represando as mensagens no banco de dados e evitando tempestades de pacotes.

---

## 2. Arquitetura e Estrutura de Classes

### 2.1 Enumeração de Prioridade (`MessagePriority`)
* `HIGH = 1`: Mensagens interativas diretas (chat do usuário e comandos com prefixo). Recebem Fast-Path prioritário (< 100ms).
* `NORMAL = 2`: Mensagens padrão e notificações pontuais.
* `LOW = 3`: Workers em background (Resumo Matinal, Lembretes, backups e relatórios). Passam obrigatoriamente pela fila com Leaky Bucket (intervalo mínimo de 1.5s entre disparos).

### 2.2 Estrutura do Payload (`OutboxMessage`)
Contém:
- `id`: Identificador único UUID da mensagem.
- `target`: Objeto de destino (canal, thread ou usuário do Discord).
- `content`: Texto formatado da mensagem (respeitando limites <= 1900 caracteres).
- `embed`: Objeto `discord.Embed` opcional.
- `files`: Lista de arquivos anexos (`discord.File`).
- `view`: Objeto `discord.ui.View` interativo (botões, modais ou menus suspensos).
- `priority`: Nível de prioridade (`MessagePriority`).
- `channel_id` e `user_id`: Identificadores para rastreamento e auditoria.
- `created_at` e `attempts`: Controle de expiração e retentativas com backoff exponencial.

---

## 3. Mecanismos de Proteção e Resiliência

### 3.1 Fast-Path Prioritário vs Fila Background
```python
if priority == MessagePriority.HIGH and not self._is_circuit_open(channel_id):
    # Envio imediato síncrono com o event loop
    return await self._enviar_direto(msg)
else:
    # Enfileiramento assíncrono para o worker do Outbox
    await self._fila_background.put(msg)
```

### 3.2 Deduplicação com Hash SHA-256
Antes de qualquer despacho, calcula-se o hash do conteúdo combinado:
$$\text{Hash} = \text{SHA256}(\text{target\_id} + \text{content} + \text{view\_id})$$
Se o hash constar na janela deslizante dos últimos 60 segundos com o mesmo canal de destino, a mensagem é descartada e um aviso de log é emitido.

### 3.3 Persistência no SQLite (`outbox_queue`)
Para garantir resiliência a crashes do processo, mensagens que não puderem ser entregues de imediato são registradas no SQLite com status `PENDING`. O worker em segundo plano reprocessa mensagens pendentes com retentativas e backoff exponencial (até 3 tentativas).

---

## 4. Auditoria e Telemetria

O comando built-in `!gateway` expõe métricas em tempo real:
* `!gateway status`: Exibe quantidade de mensagens enviadas, mensagens descartadas por deduplicação, estado dos disjuntores por canal e tamanho da fila pendente.
* `!gateway pausar`: Pausa temporariamente o despacho de mensagens em background.
* `!gateway retomar`: Retoma o processamento das filas.
* `!gateway limpar`: Limpa filas pendentes represadas.
