# Especificação do Módulo: Listas de Mercado & Tarefas

**Código do Módulo:** `MOD-VIS-03`  
**Escopo:** Gestão de Listas Nomeadas, Inclusão/Remoção de Itens, Checklists Interativos e Limpeza de Concluídos  
**Arquivos de Implementação:** 
- [`list_manager.py`](file:///Users/rodrigomodel/antigravity/discord/list_manager.py)
- [`commands/productivity_commands.py`](file:///Users/rodrigomodel/antigravity/discord/commands/productivity_commands.py)
- [`tools/list_tools.py`](file:///Users/rodrigomodel/antigravity/discord/tools/list_tools.py)
- [`ui_components.py`](file:///Users/rodrigomodel/antigravity/discord/ui_components.py)

---

## 1. Descrição e Finalidade

O módulo de **Listas & Mercado** implementa um sistema completo de checklists organizadas por usuário e nomeadas (ex: `mercado`, `compras`, `tarefas`, `viagem`). Ele atende à necessidade de registrar itens rapidamente, consultar o estado atual com indicadores visuais de pendente/concluído (`⬜` / `✅`), marcar itens como concluídos (ticar), reabrir itens (*toggle* bidirecional) e limpar itens finalizados sem perder o histórico ou a estrutura da lista. Além de comandos textuais e invocação autônoma pela LLM, oferece suporte a componentes visuais interativos do Discord UI (botões e modais).

---

## 2. Modelo de Dados no SQLite

O módulo opera em cima de duas tabelas relacionais em SQLite local-first (modo WAL) com integridade referencial estrita e índices de performance:

* **`user_lists`**: Armazena as listas criadas por usuário (`id`, `user_id`, `name`, `created_at`). Possui restrição `UNIQUE(user_id, name)`.
* **`list_items`**: Armazena os itens associados a uma lista (`id`, `list_id`, `item_text`, `concluido`, `created_at`), com chave estrangeira apontando para `user_lists(id) ON DELETE CASCADE`.
* **Índices de Performance:**
  * `idx_user_lists_user_name` em `user_lists (user_id, name)`.
  * `idx_list_items_list_id` em `list_items (list_id, concluido)`.

---

## 3. Comandos Disponíveis (`!`)

Todos os comandos de lista são registrados em [`commands/productivity_commands.py`](file:///Users/rodrigomodel/antigravity/discord/commands/productivity_commands.py) e operam de maneira desacoplada:

### 3.1 `!lista ver [nome_lista]`
* **Descrição:** Exibe o conteúdo completo da lista, exibindo os itens pendentes e ticados com formatação especial e view interativa.
* **Padrão:** Se `nome_lista` for omitido, assume a lista padrão `mercado`.
* **Exemplo:** `!lista ver feira` ou apenas `!lista`.

### 3.2 `!lista add <nome_lista> <item>`
* **Descrição:** Adiciona um item à lista indicada (criando a lista automaticamente se ela não existir).
* **Exemplo:** `!lista add mercado 2L de leite desnatado`.

### 3.3 `!lista ticar <nome_lista> <id_ou_texto>` (aliases: `check`, `concluir`, `marcar`)
* **Descrição:** Marca um item específico como concluído ou inverte seu estado (*toggle* inteligente). Aceita ID numérico, índice ordinal ou texto aproximado.
* **Exemplo:** `!lista ticar mercado 1` ou `!lista ticar mercado Café`.

### 3.4 `!lista remover <nome_lista> <id_ou_texto>` (aliases: `del`, `apagar`)
* **Descrição:** Remove permanentemente um único item da lista.
* **Exemplo:** `!lista remover mercado 2`.

### 3.5 `!lista limpar [nome_lista]` (aliases: `clean`, `limpar_concluidos`)
* **Descrição:** Remove em lote **todos os itens que já foram ticados/concluídos**, mantendo apenas os itens pendentes.
* **Exemplo:** `!lista limpar mercado`.

### 3.6 `!lista excluir <nome_lista>` (aliases: `delete`, `deletar`)
* **Descrição:** Exclui a lista inteira e todos os seus itens associados de forma segura e atômica.
* **Exemplo:** `!lista excluir compras_antigas`.

### 3.7 Atalho Direto: `!lista <nome_lista>`
* **Descrição:** Se o argumento fornecido não coincidir com palavras reservadas, abre diretamente a lista do usuário.
* **Exemplo:** `!lista feira`.

### 3.8 `!listas` (alias: `minhas_listas`)
* **Descrição:** Exibe todas as listas ativas do usuário e a contagem de itens em cada uma (total, pendentes e concluídos).
* **Exemplo:** `!listas`.

---

## 4. Componentes Visuais Interativos do Discord UI

Quando `DISCORD_UI_COMPONENTS_ENABLED = True` em [`config.py`](file:///Users/rodrigomodel/antigravity/discord/config.py), o módulo anexa a [`InteractiveListView`](file:///Users/rodrigomodel/antigravity/discord/ui_components.py#L61-L150) às respostas do bot:
1. **Botões de Checklist Rápido:** Até 10 botões dinâmicos correspondentes aos itens pendentes da lista para marcação imediata com 1 clique.
2. **Botão Limpar Concluídos (`🧹`):** Exclui itens ticados diretamente pela interface.
3. **Botão Novo Item (`➕`):** Abre um modal nativo [`AddItemModal`](file:///Users/rodrigomodel/antigravity/discord/ui_components.py#L25-L56) permitindo cadastrar novo item sem novo comando de texto.
4. **Botão Atualizar (`🔄`):** Recarrega o estado atual da lista em tempo real.
5. **Segurança de Ação:** O listener valida `interaction.user.id == self.author_id`, impedindo que usuários não autorizados modifiquem listas de terceiros.

---

## 5. Ferramentas da LLM (*Function Calling*)

Todas as ferramentas operam de forma isolada via `ContextVars` com o usuário autenticado (`get_current_user()`) e retornam o dicionário canônico `{"sucesso": bool, "dados": Any, "erro": Optional[str]}`:

| Ferramenta | Parâmetros | Descrição |
|---|---|---|
| `adicionar_item_lista` | `nome_lista: str`, `item: str` | Adiciona um novo item à lista nomeada (cria automaticamente se não existir). |
| `ver_itens_lista` | `nome_lista: str` | Consulta e retorna a lista formatada com pendentes, concluídos e resumo. |
| `listar_minhas_listas` | *(sem parâmetros)* | Retorna todas as listas criadas pelo usuário com estatísticas de conclusão. |
| `ticar_item_lista` | `nome_lista: str`, `item_ou_id: str`, `concluido: bool = True` | Tica/marca um item como finalizado ou reabre como pendente. |
| `remover_item_lista` | `nome_lista: str`, `item_ou_id: str` | Remove um item individual da lista por ID, ordinal ou texto. |
| `limpar_itens_concluidos_lista` | `nome_lista: str` | Exclui permanentemente todos os itens ticados/concluídos da lista. |
| `excluir_lista` | `nome_lista: str` | Deleta completamente a lista e seus itens. |

---

## 6. Exemplo de Apresentação Visual no Discord

```markdown
📋 **Lista: MERCADO**
📊 *4 item(ns) | ⏳ 2 pendente(s) | ✅ 2 concluído(s)*
────────────────────────────────────────
⬜ `#1` **Café em pó**
⬜ `#2` **Leite desnatado**
✅ `#3` ~~Pão de forma~~
✅ `#4` ~~Maçã argentina~~
────────────────────────────────────────
💡 *Dicas: !lista ticar mercado <id/nome> | !lista limpar mercado*
```

---

## 7. 📋 Matriz de Rastreabilidade & Aderência (Auditada em 2026-11-14)

Auditoria realizada via [`/spec-audit`](file:///Users/rodrigomodel/antigravity/.agents/skills/spec-audit/SKILL.md) com homologação do [`/review`](file:///Users/rodrigomodel/antigravity/gerencial/reviews/REV-012_auditoria_listas_e_mercado.md) e [`/doc_master`](file:///Users/rodrigomodel/antigravity/gerencial/auditorias/auditoria_2026-11-14_03_LISTAS_E_MERCADO.md):

| ID | Requisito da Especificação | Status | Implementação no Código | Linhas & Símbolos Auditados |
| :--- | :--- | :---: | :--- | :--- |
| **REQ-01** | Tabela SQLite `user_lists` (`UNIQUE(user_id, name)`) | 🟢 Aderente | [`list_manager.py`](file:///Users/rodrigomodel/antigravity/discord/list_manager.py#L30-L41) | `init_list_db()` (L30-41) |
| **REQ-02** | Tabela SQLite `list_items` com FK Cascade | 🟢 Aderente | [`list_manager.py`](file:///Users/rodrigomodel/antigravity/discord/list_manager.py#L43-L54) | `init_list_db()` (L43-54) |
| **REQ-03** | Índices compostos `idx_user_lists_user_name` e `idx_list_items_list_id` | 🟢 Aderente | [`list_manager.py`](file:///Users/rodrigomodel/antigravity/discord/list_manager.py#L57-L68) | `init_list_db()` (L57-68) |
| **REQ-04** | Subcomando `!lista ver [nome]` (default: `mercado`) | 🟢 Aderente | [`productivity_commands.py`](file:///Users/rodrigomodel/antigravity/discord/commands/productivity_commands.py#L61-L67) | `cmd_lista` (L61-67) |
| **REQ-05** | Subcomando `!lista add <nome> <item>` | 🟢 Aderente | [`productivity_commands.py`](file:///Users/rodrigomodel/antigravity/discord/commands/productivity_commands.py#L69-L82) | `cmd_lista` (L69-82) |
| **REQ-06** | Subcomando `!lista ticar [nome] <id/texto>` | 🟢 Aderente | [`productivity_commands.py`](file:///Users/rodrigomodel/antigravity/discord/commands/productivity_commands.py#L84-L95) | `cmd_lista` (L84-95) |
| **REQ-07** | Subcomando `!lista remover [nome] <id/texto>` | 🟢 Aderente | [`productivity_commands.py`](file:///Users/rodrigomodel/antigravity/discord/commands/productivity_commands.py#L98-L109) | `cmd_lista` (L98-109) |
| **REQ-08** | Subcomando `!lista limpar [nome]` | 🟢 Aderente | [`productivity_commands.py`](file:///Users/rodrigomodel/antigravity/discord/commands/productivity_commands.py#L111-L119) | `cmd_lista` (L111-119) |
| **REQ-09** | Subcomando `!lista excluir <nome>` | 🟢 Aderente | [`productivity_commands.py`](file:///Users/rodrigomodel/antigravity/discord/commands/productivity_commands.py#L121-L132) | `cmd_lista` (L121-132) |
| **REQ-10** | Comando Geral `!listas` | 🟢 Aderente | [`productivity_commands.py`](file:///Users/rodrigomodel/antigravity/discord/commands/productivity_commands.py#L146-L172) | `cmd_listas` (L146-172) |
| **REQ-11** | Tool LLM `adicionar_item_lista` | 🟢 Aderente | [`list_tools.py`](file:///Users/rodrigomodel/antigravity/discord/tools/list_tools.py#L23-L48) | `tool_adicionar_item_lista` (L23-48) |
| **REQ-12** | Tool LLM `ver_itens_lista` | 🟢 Aderente | [`list_tools.py`](file:///Users/rodrigomodel/antigravity/discord/tools/list_tools.py#L50-L76) | `tool_ver_itens_lista` (L50-76) |
| **REQ-13** | Tool LLM `listar_minhas_listas` | 🟢 Aderente | [`list_tools.py`](file:///Users/rodrigomodel/antigravity/discord/tools/list_tools.py#L78-L99) | `tool_listar_minhas_listas` (L78-99) |
| **REQ-14** | Tool LLM `ticar_item_lista` | 🟢 Aderente | [`list_tools.py`](file:///Users/rodrigomodel/antigravity/discord/tools/list_tools.py#L101-L131) | `tool_ticar_item_lista` (L101-131) |
| **REQ-15** | Tool LLM `remover_item_lista` | 🟢 Aderente | [`list_tools.py`](file:///Users/rodrigomodel/antigravity/discord/tools/list_tools.py#L133-L158) | `tool_remover_item_lista` (L133-158) |
| **REQ-16** | Tool LLM `limpar_itens_concluidos_lista` | 🟢 Aderente | [`list_tools.py`](file:///Users/rodrigomodel/antigravity/discord/tools/list_tools.py#L160-L181) | `tool_limpar_itens_concluidos_lista` (L160-181) |
| **REQ-17** | Tool LLM `excluir_lista` | 🟢 Aderente | [`list_tools.py`](file:///Users/rodrigomodel/antigravity/discord/tools/list_tools.py#L183-L203) | `tool_excluir_lista` (L183-203) |
| **REQ-18** | Formatação Visual em Markdown | 🟢 Aderente | [`list_manager.py`](file:///Users/rodrigomodel/antigravity/discord/list_manager.py#L453-L486) | `formatar_lista_para_exibicao` (L453-486) |
| **REQ-19** | Discord UI: `InteractiveListView` & `AddItemModal` *(Scope Creep Incorporado)* | 🟢 Aderente | [`ui_components.py`](file:///Users/rodrigomodel/antigravity/discord/ui_components.py#L25-L150) | `AddItemModal` e `InteractiveListView` |
| **REQ-20** | Resolução Tripla de Identificadores *(Scope Creep Incorporado)* | 🟢 Aderente | [`list_manager.py`](file:///Users/rodrigomodel/antigravity/discord/list_manager.py#L239-L282) | `_localizar_item_id` (L239-282) |
| **REQ-21** | Toggle Bidirecional de Conclusão *(Scope Creep Incorporado)* | 🟢 Aderente | [`list_manager.py`](file:///Users/rodrigomodel/antigravity/discord/list_manager.py#L314-L322) | `ticar_item_lista` (L314-322) |
