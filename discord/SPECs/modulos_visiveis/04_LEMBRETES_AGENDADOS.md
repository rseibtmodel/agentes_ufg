# Especificação do Módulo: Lembretes Agendados

**Código do Módulo:** `MOD-VIS-04`  
**Escopo:** Agendamento de Avisos Temporais, Worker Assíncrono Perpétuo, Despacho via Outbox Gateway e Ações Interativas no Discord UI  
**Arquivos de Implementação:** 
- [`reminder_manager.py`](file:///Users/rodrigomodel/antigravity/discord/reminder_manager.py)
- [`commands/productivity_commands.py`](file:///Users/rodrigomodel/antigravity/discord/commands/productivity_commands.py)
- [`tools/reminder_tools.py`](file:///Users/rodrigomodel/antigravity/discord/tools/reminder_tools.py)
- [`ui_components.py`](file:///Users/rodrigomodel/antigravity/discord/ui_components.py)
- [`message_gateway.py`](file:///Users/rodrigomodel/antigravity/discord/message_gateway.py)

---

## 1. Descrição e Finalidade

O módulo de **Lembretes Agendados** permite ao usuário instruir o bot a emitir avisos futuros em momentos específicos. O sistema suporta interpretação em linguagem natural de expressões de tempo relativas (ex: `"em 15 minutos"`, `"daqui a 2 horas"`) e datas/horários absolutos (ex: `"às 09:00"`, `"19/10 às 14:00"`). Um worker em segundo plano monitora continuamente o banco de dados e notifica ativamente o usuário no canal de origem através do Outbox Gateway com botões de ação e snooze (com fallback para mensagem direta/DM).

---

## 2. Modelo de Dados no SQLite

O módulo opera em cima da tabela `reminders` em SQLite local-first (modo WAL) com índices para pesquisa temporal rápida:

* **Tabela `reminders`:**
  * `id`: Chave primária autoincrement.
  * `user_id`: ID numérico ou textual do usuário solicitante.
  * `channel_id`: ID do canal do Discord onde o lembrete deve ser enviado.
  * `message`: Texto da mensagem de aviso.
  * `remind_at`: Timestamp de disparo em formato ISO 8601 (`YYYY-MM-DDTHH:MM:SS`).
  * `status`: Estado atual do ciclo de vida (`'pendente'`, `'processando'`, `'disparado'`, `'cancelado'`, `'concluido'`, `'falha_envio'`).
  * `created_at`: Data e hora de criação do registro no banco.
* **Índices de Performance:**
  * `idx_reminders_status_time` em `reminders (status, remind_at)`.
  * `idx_reminders_user` em `reminders (user_id, status)`.

---

## 3. Expressões de Tempo Suportadas (`interpretar_expressao_tempo`)

O interpretador de tempo normaliza e converte expressões de linguagem natural para `datetime` ancorado no fuso horário configurado (`America/Sao_Paulo` via `zoneinfo.ZoneInfo`):

1. **Prazos Relativos Simples:**
   - Minutos: `15m`, `15 min`, `15 minutos`, `em 15 minutos`, `daqui a 10 min`.
   - Horas: `1h`, `2 horas`, `daqui a 2h`.
   - Segundos: `30s`, `45 segundos`.
   - Dias: `1d`, `2 dias`, `daqui a 1 dia`.
2. **Prazos Combinados:**
   - `"1h 30m"`, `"1 hora e 20 minutos"`, `"2h 15min"`.
3. **Horários Absolutos (Dia Atual ou Seguinte):**
   - `09:00`, `14:30`, `às 21:00`, `amanhã às 10:00`.
   - *Regra:* Se o horário informado já passou no dia de hoje, o agendamento é automaticamente transferido para o mesmo horário do dia seguinte.
4. **Datas e Horários Completos:**
   - `19/10 09:00`, `19/10/2026 14:00`, `2026-10-19 16:30`.

---

## 4. Comandos Disponíveis (`!`)

Todos os comandos de lembretes são registrados em [`commands/productivity_commands.py`](file:///Users/rodrigomodel/antigravity/discord/commands/productivity_commands.py):

### 4.1 `!lembrete <quando> <mensagem>` (aliases: `lembrar`, `aviso`, `avisar`)
* **Descrição:** Cria um novo lembrete agendado. O interpretador de tokens analisa inteligentemente as primeiras 1 a 3 palavras para determinar o tempo sem exigir delimitadores rígidos (pipe `|`).
* **Exemplos:**
  - `!lembrete em 15m desligar o forno`
  - `!lembrete 09:00 tomar remédio da pressão`
  - `!lembrete 19/10/2026 14:00 consulta médica`

### 4.2 `!lembretes` (aliases: `meus_lembretes`, `avisos`)
* **Descrição:** Lista todos os lembretes pendentes agendados para o usuário.
* **Exemplo:** `!lembretes`.

### 4.3 `!cancelar_lembrete <id>` (aliases: `remover_lembrete`, `desmarcar_lembrete`)
* **Descrição:** Cancela um lembrete pendente através do seu ID numérico.
* **Exemplo:** `!cancelar_lembrete 3`.

---

## 5. Componentes Visuais Interativos do Discord UI (`ReminderActionView`)

Ao disparar a notificação no Discord, a mensagem anexa a [`ReminderActionView`](file:///Users/rodrigomodel/antigravity/discord/ui_components.py#L191-L250) com botões de ação imediata:
1. **`✅ Concluído`:** Marca o lembrete como finalizado (`status = 'concluido'`).
2. **`⏱️ +10 min`:** Adia o disparo em 10 minutos (*snooze* curto).
3. **`🔁 +1 hora`:** Adia o disparo em 60 minutos.
4. **`📅 Amanhã`:** Adia o disparo para o dia seguinte no mesmo horário (+1440 minutos).
5. **Segurança de Ação:** O método `interaction_check` valida `interaction.user.id == self.author_id`, garantindo que terceiros no canal não possam interferir no lembrete alheio.

---

## 6. Ferramentas da LLM (*Function Calling*)

Todas as ferramentas operam de forma isolada via `ContextVars` com o usuário (`get_current_user_id()`) e canal (`get_current_channel_id()`), retornando o formato canônico `{"sucesso": bool, "dados": Any, "erro": Optional[str]}`:

| Ferramenta | Parâmetros | Descrição |
|---|---|---|
| `criar_lembrete` | `quando: str`, `mensagem: str` | Interpreta a expressão temporal e cadastra o lembrete ativo no banco de dados. |
| `listar_meus_lembretes` | *(sem parâmetros)* | Retorna os lembretes pendentes agendados para o usuário atual. |
| `cancelar_lembrete` | `lembrete_id: int` | Cancela um lembrete agendado específico do usuário. |

---

## 7. Arquitetura do Worker Assíncrono (`iniciar_worker_lembretes`)

O worker de disparo opera como uma tarefa perpétua em segundo plano no `asyncio` (`reminder_manager.py`):
1. **Loop Perpétuo com Intervalo de 10s:** Executa a query `SELECT ... FROM reminders WHERE status = 'pendente' AND remind_at <= ?`.
2. **Bloqueio de Corrida (Anti-Double Delivery):** Imediatamente antes de qualquer operação de rede, altera o status do lembrete para `'processando'`.
3. **Roteamento Centralizado via Outbox Gateway:** Despacha através de `message_gateway.dispatch(canal, content=..., view=view_lembrete, priority=MessagePriority.BACKGROUND)`.
4. **Fallback para DM Privada:** Se o canal não estiver acessível ou as permissões tiverem sido revogadas, busca o usuário via `client.fetch_user(user_id)` e entrega o lembrete via mensagem privada.
5. **Atualização Final de Status:** Marca o registro como `'disparado'` (ou `'falha_envio'`).

---

## 8. 📋 Matriz de Rastreabilidade & Aderência (Auditada em 2026-11-14)

Auditoria realizada via [`/spec-audit`](file:///Users/rodrigomodel/antigravity/.agents/skills/spec-audit/SKILL.md) com homologação do [`/review`](file:///Users/rodrigomodel/antigravity/gerencial/reviews/REV-013_auditoria_lembretes_agendados.md) e [`/doc_master`](file:///Users/rodrigomodel/antigravity/gerencial/auditorias/auditoria_2026-11-14_04_LEMBRETES_AGENDADOS.md):

| ID | Requisito da Especificação | Status | Implementação no Código | Linhas & Símbolos Auditados |
| :--- | :--- | :---: | :--- | :--- |
| **REQ-01** | Tabela SQLite `reminders` e integridade de colunas | 🟢 Aderente | [`reminder_manager.py`](file:///Users/rodrigomodel/antigravity/discord/reminder_manager.py#L58-L69) | `init_reminder_db()` (L58-69) |
| **REQ-02** | Índices SQLite `idx_reminders_status_time` e `idx_reminders_user` | 🟢 Aderente | [`reminder_manager.py`](file:///Users/rodrigomodel/antigravity/discord/reminder_manager.py#L70-L81) | `init_reminder_db()` (L70-81) |
| **REQ-03** | Prazos relativos em `interpretar_expressao_tempo` | 🟢 Aderente | [`reminder_manager.py`](file:///Users/rodrigomodel/antigravity/discord/reminder_manager.py#L108-L139) | `interpretar_expressao_tempo()` |
| **REQ-04** | Horários simples com rolagem para o dia seguinte | 🟢 Aderente | [`reminder_manager.py`](file:///Users/rodrigomodel/antigravity/discord/reminder_manager.py#L149-L158) | `interpretar_expressao_tempo()` |
| **REQ-05** | Datas e horários completos (DD/MM, ISO) e fuso | 🟢 Aderente | [`reminder_manager.py`](file:///Users/rodrigomodel/antigravity/discord/reminder_manager.py#L160-L187) | `interpretar_expressao_tempo()` |
| **REQ-06** | Comando `!lembrete <quando> <mensagem>` | 🟢 Aderente | [`productivity_commands.py`](file:///Users/rodrigomodel/antigravity/discord/commands/productivity_commands.py#L174-L228) | `cmd_lembrete` (L174-228) |
| **REQ-07** | Comando `!lembretes` para listagem de pendências | 🟢 Aderente | [`productivity_commands.py`](file:///Users/rodrigomodel/antigravity/discord/commands/productivity_commands.py#L230-L252) | `cmd_lembretes` (L230-252) |
| **REQ-08** | Comando `!cancelar_lembrete <id>` | 🟢 Aderente | [`productivity_commands.py`](file:///Users/rodrigomodel/antigravity/discord/commands/productivity_commands.py#L254-L273) | `cmd_cancelar_lembrete` (L254-273) |
| **REQ-09** | Tool LLM `criar_lembrete` integrada com contexto | 🟢 Aderente | [`reminder_tools.py`](file:///Users/rodrigomodel/antigravity/discord/tools/reminder_tools.py#L25-L82) | `tool_criar_lembrete` (L25-82) |
| **REQ-10** | Tool LLM `listar_meus_lembretes` | 🟢 Aderente | [`reminder_tools.py`](file:///Users/rodrigomodel/antigravity/discord/tools/reminder_tools.py#L84-L101) | `tool_listar_meus_lembretes` (L84-101) |
| **REQ-11** | Tool LLM `cancelar_lembrete` | 🟢 Aderente | [`reminder_tools.py`](file:///Users/rodrigomodel/antigravity/discord/tools/reminder_tools.py#L103-L131) | `tool_cancelar_lembrete` (L103-131) |
| **REQ-12** | Worker assíncrono perpétuo (`intervalo=10s`) | 🟢 Aderente | [`reminder_manager.py`](file:///Users/rodrigomodel/antigravity/discord/reminder_manager.py#L458-L539) | `iniciar_worker_lembretes()` |
| **REQ-13** | Menção ao usuário (`<@user_id>`) no canal | 🟢 Aderente | [`reminder_manager.py`](file:///Users/rodrigomodel/antigravity/discord/reminder_manager.py#L500-L513) | `iniciar_worker_lembretes()` |
| **REQ-14** | Fallback para mensagem privada (DM) via `fetch_user` | 🟢 Aderente | [`reminder_manager.py`](file:///Users/rodrigomodel/antigravity/discord/reminder_manager.py#L516-L530) | `iniciar_worker_lembretes()` |
| **REQ-15** | Atualização de status relacional final | 🟢 Aderente | [`reminder_manager.py`](file:///Users/rodrigomodel/antigravity/discord/reminder_manager.py#L532-L534) | `atualizar_status_lembrete()` |
| **REQ-16** | Discord UI: `ReminderActionView` *(Scope Creep Incorporado)* | 🟢 Aderente | [`ui_components.py`](file:///Users/rodrigomodel/antigravity/discord/ui_components.py#L191-L250) | `ReminderActionView` (L191-250) |
| **REQ-17** | Funções de Snooze e Ciclo de Vida *(Scope Creep Incorporado)* | 🟢 Aderente | [`reminder_manager.py`](file:///Users/rodrigomodel/antigravity/discord/reminder_manager.py#L382-L452) | `concluir_lembrete` e `adiar_lembrete` |
| **REQ-18** | Roteamento Outbox Gateway *(Scope Creep Incorporado)* | 🟢 Aderente | [`reminder_manager.py`](file:///Users/rodrigomodel/antigravity/discord/reminder_manager.py#L506-L527) | `message_gateway.dispatch()` |
| **REQ-19** | Prevenção de Corrida com Status `processando` *(Scope Creep Incorporado)* | 🟢 Aderente | [`reminder_manager.py`](file:///Users/rodrigomodel/antigravity/discord/reminder_manager.py#L474-L476) | `iniciar_worker_lembretes()` |
| **REQ-20** | Sintaxe Natural Fluida sem Pipe Obrigatório *(Scope Creep Incorporado)* | 🟢 Aderente | [`productivity_commands.py`](file:///Users/rodrigomodel/antigravity/discord/commands/productivity_commands.py#L198-L207) | `cmd_lembrete` (L198-207) |
