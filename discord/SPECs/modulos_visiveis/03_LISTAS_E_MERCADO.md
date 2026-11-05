# Especificação do Módulo: Listas de Mercado & Tarefas

**Código do Módulo:** `MOD-VIS-03`  
**Escopo:** Gestão de Listas Nomeadas, Inclusão/Remoção de Itens, Checklists e Limpeza de Concluídos  
**Arquivos de Implementação:** [`list_manager.py`](file:///Users/rodrigomodel/antigravity/discord/list_manager.py), [`tools/list_tools.py`](file:///Users/rodrigomodel/antigravity/discord/tools/list_tools.py)  

---

## 1. Descrição e Finalidade

O módulo de **Listas & Mercado** implementa um sistema completo de checklists organizadas por usuário e nomeadas (ex: `mercado`, `compras`, `tarefas`, `viagem`). Ele atende à necessidade de registrar itens rapidamente, consultar o estado atual com indicadores visuais de pendente/concluído (`⬜` / `✅`), marcar itens como concluídos (ticar) e limpar os itens finalizados sem perder o histórico ou a estrutura da lista.

---

## 2. Modelo de Dados no SQLite

O módulo opera em cima de duas tabelas relacionais em SQLite com integridade referencial:

* **`user_lists`**: Armazena as listas criadas por usuário (`user_id`, `name`, `created_at`). Possui restrição `UNIQUE(user_id, name)`.
* **`list_items`**: Armazena os itens associados a uma lista (`id`, `list_id`, `item_text`, `concluido`, `created_at`), com chave estrangeira apontando para `user_lists(id)`.

---

## 3. Comandos Disponíveis (`!`)

### 3.1 `!lista ver [nome_lista]`
* **Descrição:** Exibe o conteúdo completo da lista, exibindo os itens pendentes e ticados com formatação especial.
* **Padrão:** Se `nome_lista` for omitido, assume a lista padrão `mercado`.
* **Exemplo:** `!lista ver feira` ou apenas `!lista`.

### 3.2 `!lista add [nome_lista] <item1>, <item2>, ...`
* **Descrição:** Adiciona um ou múltiplos itens (separados por vírgula) à lista informada.
* **Exemplo:** `!lista add mercado Maçã, Leite desnatado, Café, Pão integral`.

### 3.3 `!lista check [nome_lista] <id_ou_texto>` (alias: `!lista ticar`)
* **Descrição:** Marca um item específico como concluído (`concluido = 1`).
* **Exemplo:** `!lista check mercado Maçã` ou `!lista check mercado #3`.

### 3.4 `!lista uncheck [nome_lista] <id_ou_texto>`
* **Descrição:** Desmarca um item que havia sido concluído, retornando-o para pendente (`concluido = 0`).

### 3.5 `!lista del [nome_lista] <id_ou_texto>` (alias: `!lista remover`)
* **Descrição:** Remove permanentemente um único item da lista.

### 3.6 `!lista limpar [nome_lista]`
* **Descrição:** Remove em lote **todos os itens que já foram ticados/concluídos**, mantendo apenas os itens pendentes na lista.

### 3.7 `!lista excluir [nome_lista]`
* **Descrição:** Exclui a lista inteira e todos os seus itens associados.

### 3.8 `!listas`
* **Descrição:** Exibe todas as listas ativas do usuário e a contagem de itens em cada uma.

---

## 4. Ferramentas da LLM (*Function Calling*)

| Ferramenta | Parâmetros | Descrição |
|---|---|---|
| `adicionar_item_lista` | `nome_lista: str`, `item_ou_itens: str` | Adiciona um ou mais itens a uma lista nomeada. |
| `ver_itens_lista` | `nome_lista: str` (default: `"mercado"`) | Consulta e retorna a lista formatada com pendentes e concluídos. |
| `listar_minhas_listas` | *(sem parâmetros)* | Lista todas as listas de compras e tarefas criadas pelo usuário. |
| `ticar_item_lista` | `nome_lista: str`, `item_identificador: str` | Tica/marca um item como finalizado ou comprado. |
| `remover_item_lista` | `nome_lista: str`, `item_identificador: str` | Remove um item da lista. |
| `limpar_itens_concluidos_lista` | `nome_lista: str` | Exclui permanentemente os itens que já foram marcados como concluídos. |
| `excluir_lista` | `nome_lista: str` | Deleta completamente a lista e seus itens. |

---

## 5. Exemplo de Apresentação Visual no Discord

```markdown
📋 **Lista: MERCADO**
📊 *4 item(ns) | ⏳ 2 pendente(s) | ✅ 2 concluído(s)*
────────────────────────────────────────
⬜ `#1` **Café em pó**
⬜ `#2` **Leite desnatado**
✅ `#3` ~~Pão de forma~~
✅ `#4` ~~Maçã argentina~~
```
