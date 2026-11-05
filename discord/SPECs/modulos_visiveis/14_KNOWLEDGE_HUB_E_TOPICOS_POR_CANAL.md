# Especificação do Módulo: Knowledge Hub Temático e RAG Isolado por Canal

**Código do Módulo:** `MOD-VIS-14`  
**Escopo:** Gestão de Conhecimento, Anotações Estruturadas e Coleções RAG Multi-Tenant Isoladas por Canal  
**Arquivos de Implementação:** [`topic_manager.py`](file:///Users/rodrigomodel/antigravity/discord/topic_manager.py), [`database.py`](file:///Users/rodrigomodel/antigravity/discord/database.py), [`commands/builtins.py`](file:///Users/rodrigomodel/antigravity/discord/commands/builtins.py)  

---

## 1. Visão Geral e Propósito

O módulo **Knowledge Hub Temático** transforma canais e threads do Discord em silos de conhecimento estruturado e autônomo. Permite que um canal específico (ex: `#projeto-backend` ou `#reforma-tributaria`) concentre notas e contexto dedicados, sem misturar informações com as conversas cotidianas do usuário.

### Recursos Principais:
1. **Vinculação de Canais a Tópicos:**
   - O comando `!topico vincular <nome>` estabelece o escopo do canal.
   - O canal ganha uma coleção vetorial exclusiva no ChromaDB (`topic_notes_{channel_id}`).
   - O histórico de mensagens recentes no SQLite é isolado por `channel_id`.

2. **Auto-Captura Inteligente e Reações:**
   - Quando o `auto_capture_mode` está ativo, afirmações informativas com mais de 15 caracteres são salvas como notas e confirmadas com uma reação `📝`.
   - Adicionar o emoji `📝` manualmente em qualquer mensagem anterior do canal força a captura imediata daquele texto para o banco de notas.

3. **RAG Isolado vs Escape `--global`:**
   - Durante os diálogos no canal temático, o bot busca notas semanticamente relevantes na coleção ChromaDB exclusiva daquele canal.
   - Se o usuário incluir o sufixo `--global` na mensagem, o bot também consulta a memória semântica geral do usuário.

4. **Comandos Disponíveis:**
   - `!topico [vincular | status | desvincular | modo_livre]`
   - `!nota add <conteudo> [#tags]`
   - `!nota buscar <termo>`
   - `!nota ver <id>`
   - `!nota remover <id>`
   - `!nota limpar`
   - `!notas [#tag]`

5. **Ferramentas de Function Calling:**
   - `adicionar_nota_canal`: Salva uma nota estruturada com tags.
   - `buscar_notas_canal`: Executa busca semântica nas notas do canal.
   - `listar_notas_canal`: Lista notas recentes ou filtradas por tag.
