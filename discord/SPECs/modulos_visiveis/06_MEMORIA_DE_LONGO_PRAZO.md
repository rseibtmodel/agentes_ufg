# Especificação do Módulo: Memória de Longo Prazo (RAG Vetorial)

**Código do Módulo:** `MOD-VIS-06`  
**Escopo:** Memória Semântica Persistente, ChromaDB e Recuperação Aumentada por Geração (RAG)  
**Arquivos de Implementação:** [`vector_db.py`](file:///Users/rodrigomodel/antigravity/discord/vector_db.py), [`tools/memory_tools.py`](file:///Users/rodrigomodel/antigravity/discord/tools/memory_tools.py)  

---

## 1. Descrição e Finalidade

Diferente do histórico imediato (que armazena apenas as últimas ~10 mensagens no SQLite e é descartado ou truncado quando o diálogo avança), o módulo de **Memória de Longo Prazo** utiliza o banco vetorial **ChromaDB** para criar um índice semântico duradouro de todas as mensagens trocadas. Sempre que o usuário faz uma nova pergunta, o sistema recupera fatos, preferências e discussões passadas relevantes e os injeta contextualmente no início do prompt da LLM.

---

## 2. Fluxo RAG de Ingestão e Recuperação

1. **Ingestão Vetorial:**
   - A cada mensagem do usuário e resposta do assistente, gera-se um vetor denso (*embedding*) via endpoint do LM Studio (`text-embedding-qwen3-embedding-4b`).
   - O documento, o vetor e os metadados (`role`, `timestamp`, `usuario`) são gravados na coleção exclusiva do usuário: `{user}_memory`.
2. **Recuperação por Similaridade:**
   - Antes de enviar a consulta atual para a LLM, o texto do usuário é vetorizado.
   - O ChromaDB realiza uma busca de Top-K vizinhos mais próximos utilizando similaridade de cosseno.
   - As mensagens recuperadas são agregadas ao prompt inicial do sistema no bloco:
     ```
     [MEMÓRIA SEMÂNTICA DE LONGO PRAZO DO USUÁRIO - CHROMADB]:
     • (Usuário): Meu aniversário é no dia 15 de maio e eu sou vegetariano.
     • (Assistente): Anotado! Vou lembrar disso para recomendações futuras.
     ```

---

## 3. Comandos Disponíveis (`!`)

### 3.1 `!memoria <termo_ou_pergunta>`
* **Descrição:** Executa uma consulta semântica direta na coleção vetorial do usuário e exibe os fragmentos recuperados, com respectiva distância de cosseno e data de gravação.
* **Exemplo:** `!memoria comida favorita`.

### 3.2 `!limpar_memoria`
* **Descrição:** Exclui permanentemente a coleção vetorial `{user}_memory` do ChromaDB e recria uma nova coleção vazia para o usuário.

---

## 4. Ferramentas da LLM (*Function Calling*)

| Ferramenta | Parâmetros | Descrição |
|---|---|---|
| `consultar_memoria_passada` | `query: str`, `top_k: int` (default: 3) | Permite à LLM realizar buscas direcionadas na memória vetorial durante o raciocínio para recuperar informações específicas mencionadas em dias anteriores. |

---

## 5. Sanitização de Nomes de Coleção no ChromaDB

O ChromaDB impõe restrições rígidas para nomes de coleção (comprimento entre 3 e 63 caracteres, apenas letras, números, sublinhados e hifens). A função `sanitizar_nome_colecao()` garante conformidade total truncando nomes excessivos e substituindo espaços ou caracteres especiais por sublinhados antes de anexar o sufixo `_memory`.
