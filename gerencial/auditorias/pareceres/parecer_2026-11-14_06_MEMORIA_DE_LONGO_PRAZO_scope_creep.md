# Parecer Técnico do Coder: Scope Creep em Memória de Longo Prazo (`MOD-VIS-06`)

**Data:** 2026-11-14  
**Módulo Auditado:** `discord/SPECs/modulos_visiveis/06_MEMORIA_DE_LONGO_PRAZO.md`  
**Autor:** Estagiário Codificador (Junior Coder)  
**Destinatário:** Auditor Forense de Specs (`/spec-audit`) & Arquiteto-Chefe  

---

## 1. Contexto das Funcionalidades Não Documentadas na Spec Original

A especificação `MOD-VIS-06` delimitou originalmente o RAG vetorial de memória semântica pessoal `{user}_memory`. Durante o avanço da arquitetura de IA local e o desacoplamento de canais de tópicos (IDEA-25), o motor em [`discord/vector_db.py`](file:///Users/rodrigomodel/antigravity/discord/vector_db.py) expandiu para suportar particionamento multi-tenant por canal e resiliência offline.

---

## 2. Detalhamento e Justificativas Técnicas

### 2.1 Suporte a Coleções Vetoriais de Canais Temáticos (`topic_notes_{channel_id}`)
- **Implementação:** [`vector_db.py`](file:///Users/rodrigomodel/antigravity/discord/vector_db.py#L216-L362).
- **Racional Técnico:** Permitir que o ChromaDB sirva não apenas para a memória individual do usuário, mas também como o Knowledge Hub vetorial isolado de cada canal de tópico (`topic_notes_{channel_id}`). Foram implementadas funções dedicadas de CRUD vetorial: `salvar_nota_vetorial`, `buscar_notas_canal_vetorial`, `remover_nota_vetorial` e `limpar_colecao_topico`.

### 2.2 Diagnóstico e Status Rápido no Comando `!memoria`
- **Implementação:** [`knowledge_commands.py`](file:///Users/rodrigomodel/antigravity/discord/commands/knowledge_commands.py#L293-L300).
- **Racional Técnico:** Quando invocado sem argumentos (`!memoria`), em vez de retornar erro de sintaxe, o comando executa `contar_memorias(ctx.author.name)` e exibe o status de saúde da coleção vetorial do usuário e a contagem total de fragmentos indexados.

### 2.3 Resiliência e Degradação Graciosa sem Queda do Event Loop
- **Implementação:** [`vector_db.py`](file:///Users/rodrigomodel/antigravity/discord/vector_db.py#L70-L89) e [`L102-L106`](file:///Users/rodrigomodel/antigravity/discord/vector_db.py#L102-L106).
- **Racional Técnico:** Caso o modelo de embeddings no LM Studio sofra lentidão ou timeout, a função `gerar_embedding` captura a exceção e retorna `None`. O `salvar_memoria_vetorial` ignora a gravação vetorial daquele turno sem propagar erro fatal, permitindo que o diálogo do usuário continue ininterrupto.

### 2.4 Hibridismo de Memória com a Flag `--global` no Message Handler
- **Implementação:** [`message_handler.py`](file:///Users/rodrigomodel/antigravity/discord/message_handler.py#L440-L459).
- **Racional Técnico:** Em canais de tópicos, o bot foca nas notas locais do canal para evitar poluição de contexto. No entanto, se o usuário incluir o modificador `--global`, o handler mescla a busca no ChromaDB pessoal do usuário, viabilizando cross-pollination de memórias.

---

## 3. Recomendação do Coder
Recomenda-se a **Opção A (Manter no código e incorporar à SPEC)**: as adições consolidam o ChromaDB como o pilar vetorial unificado tanto para memórias individuais quanto para hubs temáticos de canal, mantendo isolamento absoluto e alta tolerância a falhas.

