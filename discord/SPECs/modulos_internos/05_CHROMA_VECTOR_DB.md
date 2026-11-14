# Especificação Técnica Interna: Banco de Dados Vetorial (ChromaDB)

**Código do Módulo:** `MOD-INT-05`  
**Escopo:** Armazenamento Vetorial Persistente, Multi-inquilino de Usuários (`_memory`), Knowledge Hub Temático por Canal (`topic_notes_`), Geração de Embeddings e RAG Semântico  
**Arquivos de Implementação:** [`vector_db.py`](file:///Users/rodrigomodel/antigravity/discord/vector_db.py)  

---

## 1. Arquitetura do Armazenamento Vetorial

O subsistema de memória semântica baseia-se no **ChromaDB**, executando como um cliente embutido persistente em disco (`chromadb.PersistentClient`) no diretório `discord/chroma_db/`.

### 1.1 Modelo de Embeddings Local
* **Modelo:** `text-embedding-qwen3-embedding-4b` (ou modelo configurado em `LM_STUDIO_EMBEDDING_MODEL`).
* **Endpoint:** API compatível com OpenAI em `http://localhost:1234/v1/embeddings`.
* **Dimensão Vetorial:** Adequada ao modelo carregado no LM Studio (ex: 1536 ou 2560 dimensões dependendo da arquitetura Qwen/Nomic).
* **Cliente:** `AsyncOpenAI` assíncrono com timeout de 30s.

---

## 2. Multi-inquilino e Particionamento por Coleção

Para garantir privacidade estrita e evitar contaminação cruzada de memórias entre diferentes usuários e canais temáticos do Discord, o ChromaDB é particionado em dois tipos de coleções:

### 2.1 Coleções Pessoais de Usuário (`{user}_memory`)
Cada usuário possui sua própria coleção vetorial para armazenamento de conversas e preferências pessoais:
* **Sanitização (`sanitizar_nome_colecao`):** Converte caracteres especiais em `_`, trunca o nome base em 55 caracteres e adiciona o sufixo `_memory` (máximo 62 caracteres, respeitando o teto de 63 caracteres do ChromaDB).

```python
def sanitizar_nome_colecao(usuario: str) -> str:
    user_str = getattr(usuario, "name", str(usuario)).strip()
    limpo = re.sub(r"[^a-zA-Z0-9_\-]", "_", user_str).strip("_")
    if not limpo:
        limpo = "usuario"
    return f"{limpo[:55]}_memory"
```

### 2.2 Coleções Temáticas de Canal (`topic_notes_{channel_id}`) — IDEA-25
Para canais dedicados a temas específicos (ex: `#dev`, `#estudos`, `#financas`), o módulo mantém coleções vetoriais isoladas por canal:
* **Sanitização (`sanitizar_nome_colecao_topico`):** Normaliza o ID do canal para o prefixo `topic_notes_{channel_id}` truncado em 63 caracteres.
* **Isolamento Cognitivo:** Garante que notas e conhecimentos especializados de um canal nunca vazem para a memória pessoal de outros usuários ou canais distintos.

---

## 3. Ingestão e Estrutura dos Documentos Vetoriais

Ao persistir uma mensagem via `salvar_memoria_vetorial(usuario, role, content)`:
* **`id`:** UUID v4 único gerado em tempo de execução (`str(uuid.uuid4())`).
* **`document`:** O texto literal da mensagem.
* **`embedding`:** O vetor de floats obtido do servidor do LM Studio.
* **`metadata`:**
  - `role`: `"user"` ou `"assistant"`.
  - `usuario`: Nome/identificador do autor.
  - `timestamp`: Data/hora em formato ISO 8601.

---

## 4. Consulta Semântica e Filtro de Relevância (`buscar_memorias_relevantes`)

1. **Vetorização da Query:** O texto da mensagem atual é convertido no vetor correspondente.
2. **Execução no ChromaDB com Thread Offloading:**
   ```python
   def _buscar_sync() -> List[Dict[str, Any]]:
       colecao = obter_colecao_usuario(usuario)
       if colecao.count() == 0:
           return []
       limite = min(top_k, colecao.count())
       resultados = colecao.query(
           query_embeddings=[vetor_query],
           n_results=limite,
           include=["documents", "metadatas", "distances"],
       )
       # ... formatação com distâncias ...
   
   return await asyncio.to_thread(_buscar_sync)
   ```
3. **Métrica de Distância:** O ChromaDB calcula a distância de cosseno entre o vetor da mensagem e os documentos armazenados. Valores próximos a 0.0 representam máxima similaridade semântica.
4. **Desduplicação com Histórico Imediato:**
   No `message_handler.py`, antes de injetar as memórias recuperadas do ChromaDB no prompt do sistema, o código compara os textos com o histórico imediato do SQLite. Fragmentos que já estejam presentes nas mensagens recentes são descartados para evitar redundância de tokens.

---

## 5. Knowledge Hub Temático & RAG Isolado por Canal (IDEA-25)

Para canais ou threads associados a tópicos específicos (`#bot-discord`, `#financas`, `#dev`), o módulo disponibiliza a suíte completa de persistência e recuperação vetorial:

1. **`salvar_nota_vetorial(channel_id, note_id, content, metadata_extra)`:**  
   Vetoriza o conteúdo da nota e executa `upsert()` assíncrono em `topic_notes_{channel_id}` com metadados estruturados (`note_id`, `tags`, `user_id`, `timestamp`).
2. **`buscar_notas_canal_vetorial(channel_id, consulta_texto, top_k=4)`:**  
   Executa busca semântica RAG restrita à coleção do canal temático, retornando documentos, tags e distâncias arredondadas sem misturar com notas de outros canais ou memória de usuário.
3. **`remover_nota_vetorial(channel_id, note_id)`:**  
   Remove cirurgicamente o vetor da nota do ChromaDB via `colecao.delete(ids=[str(note_id)])`.
4. **`limpar_colecao_topico(channel_id)`:**  
   Exclui e recria a coleção do canal para expurgo completo de tópicos redefinidos.

---

## 6. 📋 Matriz de Rastreabilidade & Aderência (Auditada em 2026-11-14)

Auditoria realizada via [`/spec-audit`](file:///Users/rodrigomodel/antigravity/.agents/skills/spec-audit/SKILL.md) com homologação do [`/review`](file:///Users/rodrigomodel/antigravity/gerencial/reviews/REV-007_auditoria_chroma_vector_db.md) e [`/doc_master`](file:///Users/rodrigomodel/antigravity/gerencial/auditorias/auditoria_2026-11-14_05_CHROMA_VECTOR_DB.md):

| ID | Requisito da Especificação | Status | Implementação no Código | Notas de Auditoria |
| :---: | :--- | :---: | :--- | :--- |
| **REQ-01** | Armazenamento persistente e cliente embeddings | 🟢 **Aderente** | [`vector_db.py:L31-L42`](file:///Users/rodrigomodel/antigravity/discord/vector_db.py#L31-L42) | `chromadb.PersistentClient` em `CHROMA_DIR` e `AsyncOpenAI(timeout=30.0)`. |
| **REQ-02** | Sanitização de coleção pessoal `{user}_memory` | 🟢 **Aderente** | [`vector_db.py:L44-L68`](file:///Users/rodrigomodel/antigravity/discord/vector_db.py#L44-L68) (`sanitizar_nome_colecao`) | Regex `[^a-zA-Z0-9_\-]`, corte em 55 chars e sufixo `_memory` (máx 62 chars). |
| **REQ-03** | Geração assíncrona de embeddings com fallback | 🟢 **Aderente** | [`vector_db.py:L70-L89`](file:///Users/rodrigomodel/antigravity/discord/vector_db.py#L70-L89) (`gerar_embedding`) | Trata indisponibilidade do LM Studio retornando `None` sem quebrar o bot. |
| **REQ-04** | Persistência vetorial com metadados e offload | 🟢 **Aderente** | [`vector_db.py:L91-L141`](file:///Users/rodrigomodel/antigravity/discord/vector_db.py#L91-L141) (`salvar_memoria_vetorial`) | UUID v4, timestamp ISO e inserção via `asyncio.to_thread(_adicionar_sync)`. |
| **REQ-05** | Busca semântica por similaridade & RAG | 🟢 **Aderente** | [`vector_db.py:L143-L191`](file:///Users/rodrigomodel/antigravity/discord/vector_db.py#L143-L191) (`buscar_memorias_relevantes`) | Consulta vetorial por cosseno com `asyncio.to_thread(_buscar_sync)`. |
| **REQ-06** | Ciclo de vida de memórias (contagem e limpeza) | 🟢 **Aderente** | [`vector_db.py:L193-L213`](file:///Users/rodrigomodel/antigravity/discord/vector_db.py#L193-L213) | `contar_memorias()` e `limpar_memoria_vetorial()` com recriação segura. |
| **REQ-07** | Coleções temáticas de canal (`topic_notes_`) | 🟢 **Aderente** | [`vector_db.py:L219-L237`](file:///Users/rodrigomodel/antigravity/discord/vector_db.py#L219-L237) (`sanitizar_nome_colecao_topico`) | Normalização `topic_notes_{channel_id}` <= 63 chars (Código Excedente Homologado - IDEA-25). |
| **REQ-08** | Suíte de operações RAG do Knowledge Hub | 🟢 **Aderente** | [`vector_db.py:L239-L362`](file:///Users/rodrigomodel/antigravity/discord/vector_db.py#L239-L362) | `salvar_nota_vetorial`, `buscar_notas_canal_vetorial`, `remover_nota_vetorial`, `limpar_colecao_topico` (Código Excedente Homologado - IDEA-25). |

