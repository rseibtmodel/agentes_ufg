# Parecer Técnico do Coder: Scope Creep em Lembretes Agendados (`MOD-VIS-04`)

**Data:** 2026-11-14  
**Módulo Auditado:** `discord/SPECs/modulos_visiveis/04_LEMBRETES_AGENDADOS.md`  
**Autor:** Estagiário Codificador (Junior Coder)  
**Destinatário:** Auditor Forense de Specs (`/spec-audit`) & Arquiteto-Chefe  

---

## 1. Contexto das Funcionalidades Não Documentadas na Spec Original

Durante as Ondas 2 e 3 de implementação e estabilização do ecossistema, o módulo de Lembretes Agendados (`MOD-VIS-04`) evoluiu para além de um simples disparador de texto no Discord. Foram introduzidas melhorias críticas de usabilidade, prevenção de concorrência e integração com o barramento assíncrono.

---

## 2. Detalhamento e Justificativas Técnicas

### 2.1 Botões de Ação Imediata e Snooze no Discord UI (`ReminderActionView`)
- **Implementação:** [`ui_components.py`](file:///Users/rodrigomodel/antigravity/discord/ui_components.py#L194-L250) acoplado em [`reminder_manager.py`](file:///Users/rodrigomodel/antigravity/discord/reminder_manager.py#L488-L510).
- **Racional Técnico:** Quando um lembrete toca no Discord, o usuário frequentemente não pode executar a tarefa naquele segundo exato. Forçar o usuário a digitar novos comandos para adiar gera fricção extrema. A View anexa 4 botões de ação rápida:
  - `✅ Concluído`: finaliza o lembrete imediatamente.
  - `⏱️ +10 min`: adia o aviso em 10 minutos (*snooze* curto).
  - `🔁 +1 hora`: adia em 1 hora.
  - `📅 Amanhã`: adia em 24 horas (1440 minutos).
- **Segurança:** O callback valida `interaction_check(interaction)` com o `author_id`, impedindo que outros membros do canal apertem os botões alheios.

### 2.2 Funções de Ciclo de Vida: `concluir_lembrete` e `adiar_lembrete`
- **Implementação:** [`reminder_manager.py`](file:///Users/rodrigomodel/antigravity/discord/reminder_manager.py#L382-L452).
- **Racional Técnico:** Necessárias para dar suporte ao `ReminderActionView` e permitir a persistência relacional das transições de status (`pendente` $\rightarrow$ `concluido` ou recálculo do campo `remind_at` com retorno a `pendente`).

### 2.3 Roteamento Compulsório via Outbox Gateway (`message_gateway.dispatch`)
- **Implementação:** [`reminder_manager.py`](file:///Users/rodrigomodel/antigravity/discord/reminder_manager.py#L506-L527).
- **Racional Técnico:** Em conformidade com o módulo interno `MOD-INT-07`, todas as mensagens proativas emitidas em background pelo bot devem fluir pelo barramento central com `priority=MessagePriority.BACKGROUND`, usufruindo de anti-spam, debounce e reconexão transparente do Gateway.

### 2.4 Prevenção de Corridas com Estado Transitório `processando`
- **Implementação:** [`reminder_manager.py`](file:///Users/rodrigomodel/antigravity/discord/reminder_manager.py#L474-L476).
- **Racional Técnico:** Como o envio via Discord API pode sofrer latência de rede, o worker atualiza o status de `pendente` para `processando` antes de emitir a mensagem, prevenindo double-delivery em caso de timeouts ou iterações concorrentes do loop.

### 2.5 Sintaxe Fluida Natural no Comando `!lembrete` (sem obrigatoriedade de pipe `|`)
- **Implementação:** [`productivity_commands.py`](file:///Users/rodrigomodel/antigravity/discord/commands/productivity_commands.py#L198-L207).
- **Racional Técnico:** Usuários em smartphones têm dificuldade em localizar o caractere `|`. O interpretador tenta analisar as primeiras 1, 2 ou 3 palavras como timestamp natural (`em 15m`, `amanhã 09:00`), tornando o comando muito mais ergonômico.

---

## 3. Recomendação do Coder
Recomenda-se a **Opção A (Manter no código e atualizar a SPEC)**: as adições elevam o bot a um padrão moderno de assistente pessoal com snooze interativo, protegendo a concorrência e o barramento do Gateway.

