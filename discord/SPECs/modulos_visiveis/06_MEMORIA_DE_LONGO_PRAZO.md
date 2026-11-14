# Especificação do Módulo: Memória de Longo Prazo (RAG Vetorial & ChromaDB)

**Código do Módulo:** `MOD-VIS-06`  
**Escopo:** Memória Semântica Persistente, ChromaDB Multi-Tenant, Knowledge Hub Vetorial por Canal e Injeção Contextual RAG  
**Arquivos de Implementação:** 
- [`vector_db.py`](file:///Users/rodrigomodel/antigravity/discord/vector_db.py)
- [`commands/knowledge_commands.py`](file:///Users/rodrigomodel/antigravity/discord/commands/knowledge_commands.py)
- [`tools/memory_tools.py`](file:///Users/rodrigomodel/antigravity/discord/tools/memory_tools.py)
- [`message_handler.py`](file:///Users/rodrigomodel/antigravity/discord/message_handler.py)

---

## 1. Descrição e Finalidade

Diferente do histórico imediato (que armazena as últimas ~10 mensagens no SQLite e é truncado conforme o diálogo avança), o módulo de **Memória de Longo Prazo** utiliza o banco vetorial **ChromaDB** para criar um índice semântico duradouro de todas as interações. Sempre que o usuário envia uma nova mensagem, o sistema recupera fatos, preferências e discussões passadas relevantes e os injeta contextualmente no início do prompt da LLM. Adicionalmente, provê a infraestrutura vetorial para o Knowledge Hub temático de notas isoladas por canal.

---

## 2. Fluxo RAG de Ingestão e Recuperação

1. **Ingestão Vetorial Automática:**
   - A cada mensagem do usuário e resposta do assistente no fluxo conversacional (`message_handler.py`), gera-se um embedding denso via LM Studio (`text-embedding-qwen3-embedding-4b`).
   - O documento, o vetor e os metadados (`role`, `timestamp`, `usuario`) são gravados na coleção exclusiva do usuário: `{user}_memory`.
2. **Recuperação Semântica por Similaridade:**
   - Antes de enviar o turno atual para a LLM, o texto da mensagem do usuário é vetorizado.
   - O ChromaDB executa uma busca de Top-K vizinhos mais próximos utilizando distância de cosseno.
   - As mensagens recuperadas são agregadas ao prompt inicial do sistema:
     ```markdown
     [MEMÓRIA SEMÂNTICA DE LONGO PRAZO DO USUÁRIO - CHROMADB]:
     • (Usuário): Meu aniversário é no dia 15 de maio e eu sou vegetariano.
     • (Assistente): Anotado! Vou lembrar disso para recomendações futuras.
     ```

---

## 3. Sanitização de Nomes e Particionamento no ChromaDB

O ChromaDB impõe restrições para nomes de coleção (comprimento entre 3 e 63 caracteres, apenas letras, números, sublinhados e hifens):
1. **Memória de Usuário:** A função `sanitizar_nome_colecao(usuario)` trunca o nome base em até 55 caracteres e anexa o sufixo `_memory`, garantindo conformidade com o limite de 63 caracteres.
2. **Knowledge Hub por Canal (IDEA-25):** A função `sanitizar_nome_colecao_topico(channel_id)` particiona coleções vetoriais independentes sob o padrão `topic_notes_{channel_id}`.

---

## 4. Knowledge Hub Vetorial por Canal Temático

Além da memória semântica individual, o motor em [`vector_db.py`](file:///Users/rodrigomodel/antigravity/discord/vector_db.py) provê suporte nativo a bases de conhecimento compartilhadas por canal:
* **`salvar_nota_vetorial(channel_id, note_id, content, metadata_extra)`:** Vetoriza notas de tópicos e persiste no ChromaDB com metadados de tags, autor e timestamp.
* **`buscar_notas_canal_vetorial(channel_id, consulta_texto, top_k=4)`:** Realiza busca semântica RAG restrita estritamente ao canal ativo.
* **`remover_nota_vetorial(channel_id, note_id)`:** Purga fragmentos específicos na exclusão de notas.
* **`limpar_colecao_topico(channel_id)`:** Reinicia a coleção vetorial do canal temático.

---

## 5. Comandos Disponíveis (`!`)

Todos os comandos de memória são registrados em [`commands/knowledge_commands.py`](file:///Users/rodrigomodel/antigravity/discord/commands/knowledge_commands.py):

### 5.1 `!memoria [termo_ou_pergunta]` (aliases: `lembrar`, `busca_vetorial`, `rag`)
* **Sem Argumentos:** Exibe o diagnóstico de integridade da coleção vetorial do usuário (`{user}_memory`) e a contagem total de fragmentos armazenados via `contar_memorias()`.
* **Com Argumentos:** Executa busca semântica direta, retornando os fragmentos mais relevantes com indicação do papel (`Usuário` / `Assistente`), data/hora e distância de cosseno.
* **Exemplo:** `!memoria framework favorito`.

### 5.2 `!limpar_memoria` (aliases: `reset_memoria`, `clear_memory`)
* **Descrição:** Exclui permanentemente a coleção vetorial `{user}_memory` do ChromaDB e recria uma nova coleção vazia para o usuário.
* **Exemplo:** `!limpar_memoria`.

---

## 6. Ferramentas da LLM (*Function Calling*)

O módulo disponibiliza a ferramenta de busca vetorial em [`tools/memory_tools.py`](file:///Users/rodrigomodel/antigravity/discord/tools/memory_tools.py):

| Ferramenta | Parâmetros | Descrição |
|---|---|---|
| `consultar_memoria_passada` | `termo_ou_pergunta: str` | Permite à LLM consultar o acervo de memórias do usuário durante o raciocínio para resgatar detalhes pessoais, histórico ou conversas passadas. |

* Retorno canônico estruturado: `{"sucesso": bool, "dados": {"usuario": str, "total": int, "memorias": list, "texto_formatado": str}, "erro": None}`.

---

## 7. Resiliência e Degradação Graciosa

1. **Zero Bloqueio do Event Loop:** Todas as operações síncronas do ChromaDB são delegadas obrigatoriamente a thread workers dedicados através de `await asyncio.to_thread(...)`.
2. **Tolerância a Falhas de Embeddings:** Se o endpoint local do LM Studio estiver indisponível ou retornar timeout, `salvar_memoria_vetorial` descarta silenciosamente a persistência vetorial daquele turno sem propagar erros fatais ao usuário, assegurando que o atendimento conversacional nunca seja interrompido.
3. **Modificador `--global`:** Em canais temáticos de tópicos, o sistema foca nas notas locais, mas permite mesclar memórias globais do usuário caso a mensagem contenha o modificador `--global`.

---

## 8. 📋 Matriz de Rastreabilidade & Aderência (Auditada em 2026-11-14)

Auditoria realizada via [`/spec-audit`](file:///Users/rodrigomodel/antigravity/.agents/skills/spec-audit/SKILL.md) com homologação do [`/review`](file:///Users/rodrigomodel/antigravity/gerencial/reviews/REV-015_auditoria_memoria_longo_prazo.md) e [`/doc_master`](file:///Users/rodrigomodel/antigravity/gerencial/auditorias/auditoria_2026-11-14_06_MEMORIA_DE_LONGO_PRAZO.md):

| ID | Requisito da Especificação | Status | Implementação no Código | Linhas & Símbolos Auditados |
| :--- | :--- | :---: | :--- | :--- |
| **REQ-01** | Coleção vetorial isolada por usuário (`{user}_memory`) | 🟢 Aderente | [`vector_db.py`](file:///Users/rodrigomodel/antigravity/discord/vector_db.py#L44-L68) | `obter_colecao_usuario()` (L61-68) |
| **REQ-02** | Geração de embeddings via LM Studio (`qwen3-embedding-4b`) | 🟢 Aderente | [`vector_db.py`](file:///Users/rodrigomodel/antigravity/discord/vector_db.py#L70-L89) | `gerar_embedding()` (L70-89) |
| **REQ-03** | Ingestão e persistência vetorial com metadados | 🟢 Aderente | [`vector_db.py`](file:///Users/rodrigomodel/antigravity/discord/vector_db.py#L91-L141) | `salvar_memoria_vetorial()` (L91-141) |
| **REQ-04** | Busca por similaridade semântica (Top-K) por cosseno | 🟢 Aderente | [`vector_db.py`](file:///Users/rodrigomodel/antigravity/discord/vector_db.py#L143-L191) | `buscar_memorias_relevantes()` |
| **REQ-05** | Injeção contextual das memórias no prompt da LLM | 🟢 Aderente | [`message_handler.py`](file:///Users/rodrigomodel/antigravity/discord/message_handler.py#L440-L459) | Bloco de injeção RAG em `processar_mensagem` |
| **REQ-06** | Comando `!memoria <termo>` com distância de cosseno | 🟢 Aderente | [`knowledge_commands.py`](file:///Users/rodrigomodel/antigravity/discord/commands/knowledge_commands.py#L283-L318) | `cmd_memoria` (L283-318) |
| **REQ-07** | Comando `!limpar_memoria` para purge da coleção | 🟢 Aderente | [`knowledge_commands.py`](file:///Users/rodrigomodel/antigravity/discord/commands/knowledge_commands.py#L320-L335) | `cmd_limpar_memoria` (L320-335) |
| **REQ-08** | Tool LLM `consultar_memoria_passada` | 🟢 Aderente | [`memory_tools.py`](file:///Users/rodrigomodel/antigravity/discord/tools/memory_tools.py#L14-L72) | `tool_consultar_memoria_passada` |
| **REQ-09** | Sanitização de nomes de coleção (3 a 63 chars) | 🟢 Aderente | [`vector_db.py`](file:///Users/rodrigomodel/antigravity/discord/vector_db.py#L44-L59) | `sanitizar_nome_colecao()` (L44-59) |
| **REQ-10** | Coleções temáticas por canal (`topic_notes_{channel_id}`) *(Scope Creep Incorporado)* | 🟢 Aderente | [`vector_db.py`](file:///Users/rodrigomodel/antigravity/discord/vector_db.py#L216-L362) | CRUD vetorial de tópicos |
| **REQ-11** | Diagnóstico rápido de integridade e contagem em `!memoria` *(Scope Creep Incorporado)* | 🟢 Aderente | [`knowledge_commands.py`](file:///Users/rodrigomodel/antigravity/discord/commands/knowledge_commands.py#L293-L300) | `cmd_memoria` |
| **REQ-12** | Degradação graciosa em indisponibilidade de embeddings *(Scope Creep Incorporado)* | 🟢 Aderente | [`vector_db.py`](file:///Users/rodrigomodel/antigravity/discord/vector_db.py#L102-L106) | `salvar_memoria_vetorial()` |
| **REQ-13** | Hibridismo de memória com a flag `--global` no handler *(Scope Creep Incorporado)* | 🟢 Aderente | [`message_handler.py`](file:///Users/rodrigomodel/antigravity/discord/message_handler.py#L440-L459) | Injeção condicional no `message_handler` |
