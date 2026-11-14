# Parecer Técnico do Coder: Scope Creep & Extensões do Módulo 14 (Knowledge Hub Temático & RAG Isolado por Canal)

**Data:** 2026-11-14  
**Módulo Auditado:** `discord/SPECs/modulos_visiveis/14_KNOWLEDGE_HUB_E_TOPICOS_POR_CANAL.md` (`MOD-VIS-14`)  
**Autor:** Estagiário Codificador (`/coder`)  
**Destinatário:** Auditor Forense de Specs (`/spec-audit`) & Arquiteto-Chefe  

---

## 1. Contexto e Justificativa das Extensões

Durante o ciclo de desenvolvimento da ideia IDEA-25 (v3.1.0 a v3.6.0), o subsistema de tópicos e anotações temáticas (`topic_manager.py`) evoluiu expressivamente para garantir isolamento de contexto (*multi-tenant context isolation*), auto-captura reativa e busca RAG de alta fidelidade:

### Item 1: RAG Isolado com Injeção Estruturada no System Prompt
* **Localização:** [`discord/message_handler.py`](file:///Users/rodrigomodel/antigravity/discord/message_handler.py#L440-L449), [L494-L506](file:///Users/rodrigomodel/antigravity/discord/message_handler.py#L494-L506)
* **Racional Técnico:** Para garantir que a LLM não misture conhecimentos de diferentes canais, as notas temáticas recuperadas por proximidade vetorial no ChromaDB (`topic_notes_{channel_id}`) são injetadas em um bloco explícito `[BASE DE CONHECIMENTO TEMÁTICA DO CANAL (...) - RAG ISOLADO]`. Isso orienta a inferência a priorizar fatos locais do canal, a menos que o usuário solicite explicitamente o escape `--global`.

### Item 2: Captura Reativa via Listener `on_raw_reaction_add`
* **Localização:** [`discord/chat_discord.py`](file:///Users/rodrigomodel/antigravity/discord/chat_discord.py#L140-L180)
* **Racional Técnico:** Permitir que o usuário transforme qualquer mensagem do histórico em nota permanente simplesmente adicionando a reação `📝`. O listener busca a mensagem de forma assíncrona, extrai o texto e cadastra a nota com a tag rastreável `reaction_save`.

### Item 3: Purga Segura com Confirmação Mandatória (`!nota limpar confirmar`)
* **Localização:** [`discord/commands/knowledge_commands.py`](file:///Users/rodrigomodel/antigravity/discord/commands/knowledge_commands.py#L501-L507)
* **Racional Técnico:** Para evitar que o usuário apague acidentalmente dezenas de notas e destrua a coleção vetorial no ChromaDB com um comando mal digitado, foi adicionada a exigência do segundo argumento `confirmar`.

### Item 4: Modularização em `knowledge_commands.py` e `topic_tools.py`
* **Localização:** [`discord/commands/knowledge_commands.py`](file:///Users/rodrigomodel/antigravity/discord/commands/knowledge_commands.py#L340-L546) e [`discord/tools/topic_tools.py`](file:///Users/rodrigomodel/antigravity/discord/tools/topic_tools.py#L1-L157)
* **Racional Técnico:** Em conformidade com o desacoplamento arquitetural, os comandos `!topico`, `!nota` e `!notas` residem no pilar de conhecimento, e as 3 ferramentas de Function Calling (`adicionar_nota_canal`, `buscar_notas_canal`, `listar_notas_canal`) foram alocadas em arquivo dedicado com schemas JSON tipados.

---

## 2. Recomendação do Coder
Recomenda-se a **incorporação integral (Opção A)** de todas as extensões na especificação oficial `14_KNOWLEDGE_HUB_E_TOPICOS_POR_CANAL.md`, expandindo o documento para a versão canônica completa com o esquema relacional, o ciclo de vida vetorial do ChromaDB, a captura por reações e a matriz de rastreabilidade reversa.

