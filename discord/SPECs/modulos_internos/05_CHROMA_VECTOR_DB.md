# Especificação Técnica Interna: Banco de Dados Vetorial (ChromaDB)

**Código do Módulo:** `MOD-INT-05`  
**Escopo:** Armazenamento Vetorial Persistente, Multi-inquilino Seguro, Geração de Embeddings e RAG Semântico  
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

Para garantir privacidade estrita e evitar contaminação cruzada de memórias entre diferentes usuários do Discord:
1. **Coleção Exclusiva:** Cada usuário possui sua própria coleção vetorial nomeada com o sufixo `_memory` (ex: `rsmodel_memory`, `joao_silva_memory`).
2. **Sanitização de Nomes de Coleção (`sanitizar_nome_colecao`):**
   - O ChromaDB exige nomes com tamanho entre 3 e 63 caracteres contendo apenas letras, números, traços e sublinhados.
   - Qualquer caractere fora dessa especificação é convertido para sublinhado.
   - O prefixo do nome de usuário é truncado em 55 caracteres para garantir que com a adição de `_memory` (7 caracteres) o total não exceda 62 caracteres.

```python
def sanitizar_nome_colecao(usuario: str) -> str:
    user_str = getattr(usuario, "name", str(usuario)).strip()
    limpo = re.sub(r"[^a-zA-Z0-9_\-]", "_", user_str).strip("_")
    if not limpo:
        limpo = "usuario"
    return f"{limpo[:55]}_memory"
```

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
2. **Execução no ChromaDB:**
   ```python
   resultados = colecao.query(
       query_embeddings=[vetor_query],
       n_results=min(top_k, colecao.count()),
       include=["documents", "metadatas", "distances"]
   )
   ```
3. **Métrica de Distância:** O ChromaDB calcula a distância de cosseno entre o vetor da mensagem e os documentos armazenados. Valores próximos a 0.0 representam máxima similaridade semântica.
4. **Desduplicação com Histórico Imediato:**
   No `message_handler.py`, antes de injetar as memórias recuperadas do ChromaDB no prompt do sistema, o código compara os textos com o histórico imediato do SQLite. Fragmentos que já estejam presentes nas mensagens recentes são descartados para evitar redundância de tokens.
