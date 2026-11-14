# Parecer Técnico do Coder: Scope Creep em Listas de Mercado & Tarefas (`MOD-VIS-03`)

**Data:** 2026-11-14  
**Módulo Auditado:** `discord/SPECs/modulos_visiveis/03_LISTAS_E_MERCADO.md`  
**Autor:** Estagiário Codificador (Junior Coder)  
**Destinatário:** Auditor Forense de Specs (`/spec-audit`) & Arquiteto-Chefe  

---

## 1. Contexto das Funcionalidades Não Documentadas na Spec Original

Durante o ciclo de engenharia e aprimoramento da experiência do usuário no Discord (Ondas 2 e 3 do Roadmap), a implementação de listas em [`discord/list_manager.py`](file:///Users/rodrigomodel/antigravity/discord/list_manager.py), [`discord/commands/productivity_commands.py`](file:///Users/rodrigomodel/antigravity/discord/commands/productivity_commands.py) e [`discord/ui_components.py`](file:///Users/rodrigomodel/antigravity/discord/ui_components.py) recebeu melhorias ergonômicas substanciais que excederam a especificação original `MOD-VIS-03`.

---

## 2. Detalhamento e Justificativas Técnicas

### 2.1 Componentes Visuais Interativos do Discord UI (`InteractiveListView` & `AddItemModal`)
- **Implementação:** [`ui_components.py`](file:///Users/rodrigomodel/antigravity/discord/ui_components.py#L61-L150) acoplado condicionalmente em [`productivity_commands.py`](file:///Users/rodrigomodel/antigravity/discord/commands/productivity_commands.py#L43-L66).
- **Racional Técnico:** Em interfaces de chat como o Discord mobile/desktop, digitar comandos como `!lista ticar mercado 3` enquanto se está fisicamente no supermercado causa alto atrito cognitivo e motor. A introdução de botões interativos dinâmicos (`Button` com custom_id `list_toggle_{id}`) permite marcar itens com 1 clique direto no chat.
- **Segurança & Concorrência:** O callback valida compulsoriamente a posse da lista (`interaction.user.id == self.author_id`), impedindo que terceiros alterem a lista alheia. Adicionalmente, o botão `➕ Novo Item` abre um `discord.ui.Modal` nativo, dispensando novo comando de texto.

### 2.2 Resolução Tripla de Identificadores de Itens (`_localizar_item_id`)
- **Implementação:** [`list_manager.py`](file:///Users/rodrigomodel/antigravity/discord/list_manager.py#L239-L282).
- **Racional Técnico:** Na spec original, previa-se busca por ID primário ou texto. O Coder adicionou resolução por índice ordinal (1º item da lista, 2º item...), ID real do SQLite e busca parcial insensível a maiúsculas (`LIKE %texto%`). Isso garante resiliência máxima tanto para o usuário humano quanto para a LLM chamando Function Calling com pequenas variações ortográficas.

### 2.3 Suporte a *Toggle* Bidirecional Automático em `ticar_item_lista`
- **Implementação:** [`list_manager.py`](file:///Users/rodrigomodel/antigravity/discord/list_manager.py#L314-L322).
- **Racional Técnico:** Caso o usuário não especifique explicitamente `concluido=True` ou `False`, a função inverte o estado atual do item (`1 -> 0` ou `0 -> 1`), permitindo reabrir itens marcados por engano sem necessitar de um subcomando dedicado `!lista uncheck`.

### 2.4 Atalho de Acesso Direto (`!lista <nome>`)
- **Implementação:** [`productivity_commands.py`](file:///Users/rodrigomodel/antigravity/discord/commands/productivity_commands.py#L134-L144).
- **Racional Técnico:** Digitar `!lista mercado` é mais natural e rápido do que `!lista ver mercado`. Se o primeiro argumento não coincidir com subcomandos reservados (`ver`, `add`, `ticar`, `remover`, `limpar`, `excluir`), o despachante verifica diretamente se é o nome de uma lista existente do usuário.

---

## 3. Recomendação do Coder
Recomenda-se veementemente a **Opção A (Manter e incorporar à SPEC)**: todas as adições aumentam substancialmente a robustez, diminuem a fricção em dispositivos móveis e mantêm 100% de retrocompatibilidade com o modelo relacional SQLite projetado.

