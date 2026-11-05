# Especificação do Módulo: Lembretes Agendados

**Código do Módulo:** `MOD-VIS-04`  
**Escopo:** Agendamento de Avisos por Tempo Relativo ou Absoluto, Worker Assíncrono e Notificação Ativa  
**Arquivos de Implementação:** [`reminder_manager.py`](file:///Users/rodrigomodel/antigravity/discord/reminder_manager.py), [`tools/reminder_tools.py`](file:///Users/rodrigomodel/antigravity/discord/tools/reminder_tools.py)  

---

## 1. Descrição e Finalidade

O módulo de **Lembretes Agendados** permite ao usuário instruir o bot a emitir avisos futuros em momentos específicos. O sistema suporta interpretação em linguagem natural de expressões de tempo relativas (ex: `"em 15 minutos"`, `"daqui a 2 horas"`) e datas/horários absolutos (ex: `"às 09:00 do dia 19/10"`). Um worker em segundo plano monitora continuamente o banco de dados e notifica ativamente o usuário no canal de origem (com fallback para mensagem direta/DM).

---

## 2. Expressões de Tempo Suportadas (`interpretar_expressao_tempo`)

O interpretador de tempo utiliza expressões regulares robustas para normalizar e extrair a data/hora alvo:

1. **Prazos Relativos:**
   - Minutos: `15m`, `15 min`, `15 minutos`, `em 15 minutos`, `daqui a 10 min`.
   - Horas: `1h`, `2 horas`, `daqui a 2h`.
   - Segundos: `30s`, `45 segundos`.
   - Dias: `1d`, `2 dias`, `daqui a 1 dia`.
2. **Horários Absolutos (Dia Atual ou Seguinte):**
   - `09:00`, `14:30`, `às 21:00`.
   - *Regra:* Se o horário informado já passou no dia de hoje, o agendamento é automaticamente transferido para o mesmo horário do dia seguinte.
3. **Datas e Horários Completos:**
   - `19/10 09:00`, `19/10/2026 14:00`, `2026-10-19 16:30`.

---

## 3. Comandos Disponíveis (`!`)

### 3.1 `!lembrete <quando> | <mensagem>`
* **Descrição:** Cria um novo lembrete agendado.
* **Exemplos:**
  - `!lembrete em 15 minutos | Tirar o bolo do forno`
  - `!lembrete às 09:00 do dia 20/10 | Tomar remédio para pressão`
  - `!lembrete 2h | Entrar na call com o cliente`

### 3.2 `!lembretes`
* **Descrição:** Lista todos os lembretes do usuário que estão atualmente com status `pendente`.

### 3.3 `!cancelar_lembrete <id>`
* **Descrição:** Cancela um lembrete pendente através do seu ID numérico.

---

## 4. Ferramentas da LLM (*Function Calling*)

| Ferramenta | Parâmetros | Descrição |
|---|---|---|
| `criar_lembrete` | `quando: str`, `mensagem: str` | Interpreta a expressão temporal e cadastra o lembrete ativo no banco de dados. |
| `listar_meus_lembretes` | *(sem parâmetros)* | Retorna os lembretes pendentes agendados para o usuário. |
| `cancelar_lembrete` | `lembrete_id: int` | Cancela um lembrete agendado específico do usuário. |

---

## 5. Arquitetura do Worker Assíncrono (`iniciar_worker_lembretes`)

O worker de disparo opera como uma tarefa perpétua em segundo plano no `asyncio`:
1. **Loop com Intervalo de 10s:** Executa a query `SELECT * FROM reminders WHERE status = 'pendente' AND remind_at <= CURRENT_TIMESTAMP`.
2. **Despacho no Canal:** Localiza o canal original (`channel_id`) e envia a mensagem com menção ao usuário (`<@user_id>`).
3. **Fallback para DM:** Se o canal não estiver acessível ou as permissões de envio no servidor tiverem sido revogadas, busca o usuário via `client.fetch_user(user_id)` e entrega o lembrete via Mensagem Direta privada.
4. **Atualização de Status:** Marca o registro como `disparado` (ou `falha_envio`).
