# Especificação do Módulo: Interface Interativa com Botões, Modais e Menus (UI Components)

**Código do Módulo:** `MOD-VIS-12`  
**Escopo:** Componentes Visuais do Discord (`discord.ui.View`, `Button`, `Modal`, `Select`) para Interações sem Digitação  
**Arquivos de Implementação:** [`ui_components.py`](file:///Users/rodrigomodel/antigravity/discord/ui_components.py), [`commands/builtins.py`](file:///Users/rodrigomodel/antigravity/discord/commands/builtins.py), [`message_handler.py`](file:///Users/rodrigomodel/antigravity/discord/message_handler.py)  

---

## 1. Visão Geral e Propósito

O módulo de **UI Interativa** substitui a necessidade de digitação contínua de comandos por uma experiência visual moderna e intuitiva no Discord através do uso dos componentes nativos da API do Discord.

### Principais Componentes Implementados:

1. **`InteractiveListView` (Gestão de Listas):**
   - Renderiza listas de compras e tarefas com botões individuais para marcar/desmarcar itens (`☐` / `☑`).
   - Botão `➕ Adicionar Item`: Abre instantaneamente um pop-up nativo do Discord (`AddItemModal`) para inclusão de novos itens sem comandos de texto.
   - Botão `🧹 Limpar Concluídos`: Remove todos os itens riscados da lista com um único clique.
   - Atualização in-place da mensagem original (`interaction.response.edit_message`), evitando poluição de novas mensagens no chat.
   - Controle estrito de permissões: apenas o autor da lista pode acionar os botões; tentativas de outros membros disparam respostas efêmeras (`ephemeral=True`).

2. **`ReminderActionView` (Ações em Lembretes):**
   - Anexada às notificações ativas disparadas pelo worker de lembretes.
   - Botões com 1 clique: `✅ Concluído`, `⏱️ +10 min`, `🔁 +1 hora`, `📅 Amanhã`.
   - Adia ou encerra lembretes diretamente no SQLite sem intervenção manual no chat.

3. **`PDFChapterSelectView` (Navegação de Livros):**
   - Menu suspenso dropdown (`discord.ui.Select`) anexado ao comando `!pdf sumario <livro>`.
   - Lista até 25 capítulos com numeração de páginas; a seleção do usuário dispara automaticamente a síntese do capítulo escolhido.

4. **`criar_view_selecao_persona` (Seleção de Personas):**
   - Dropdown interativo para escolher e aplicar personas ao canal com preview de diretrizes cognitivas.
