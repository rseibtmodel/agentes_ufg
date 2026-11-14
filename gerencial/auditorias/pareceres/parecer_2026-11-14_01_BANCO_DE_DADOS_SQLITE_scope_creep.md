# Parecer Técnico do Coder: Código Excedente em `database.py` (MOD-INT-01)

**Data:** 14 de Novembro de 2026  
**Módulo Auditado:** `discord/SPECs/modulos_internos/01_BANCO_DE_DADOS_SQLITE.md`  
**Autor:** Junior Coder (`/coder`)  
**Solicitante:** Spec Auditor (`/spec-audit`)  
**Status:** Submetido para Decisão do Arquiteto-Chefe  

---

## 1. Evidência Cirúrgica de Código Excedente

* **Item 1:** Tabela `user_model_preferences` e funções `normalizar_provedor_modelo`, `obter_preferencia_modelo`, `definir_preferencia_modelo`
  - **Localização:** [`discord/database.py:L79-L90`](file:///Users/rodrigomodel/antigravity/discord/database.py#L79-L90) e [`discord/database.py:L334-L434`](file:///Users/rodrigomodel/antigravity/discord/database.py#L334-L434).
* **Item 2:** Suporte a `channel_id` na tabela `messages` e índice `idx_messages_channel_id`
  - **Localização:** [`discord/database.py:L56-L65`](file:///Users/rodrigomodel/antigravity/discord/database.py#L56-L65) e [`discord/database.py:L130-L151, L194-L204`](file:///Users/rodrigomodel/antigravity/discord/database.py#L130-L151).
* **Item 3:** Função utilitária `contar_mensagens`
  - **Localização:** [`discord/database.py:L249-L258`](file:///Users/rodrigomodel/antigravity/discord/database.py#L249-L258).
* **Item 4:** Inicialização de subsistemas adicionais em `init_db()`
  - **Localização:** [`discord/database.py:L93-L107`](file:///Users/rodrigomodel/antigravity/discord/database.py#L93-L107).

---

## 2. Motivação Técnica e de Negócio

1. **`user_model_preferences`:** Foi implementada para atender à especificação [`discord/SPECs/SPECS_IDEIAS_IMPLEMENTADAS/07_ROTEAMENTO_HIBRIDO_E_PROVEDORES_CLOUD_LLM.md`](file:///Users/rodrigomodel/antigravity/discord/SPECs/SPECS_IDEIAS_IMPLEMENTADAS/07_ROTEAMENTO_HIBRIDO_E_PROVEDORES_CLOUD_LLM.md), permitindo que cada usuário configure dinamicamente se deseja usar LM Studio Local, Google Gemini Flash ou failover automático.
2. **`channel_id` em `messages`:** Foi implementado para viabilizar a especificação [`discord/SPECs/SPECS_IDEIAS_IMPLEMENTADAS/25_KNOWLEDGE_HUB_TEMATICO_E_RAG_ISOLADO_POR_CANAL.md`](file:///Users/rodrigomodel/antigravity/discord/SPECs/SPECS_IDEIAS_IMPLEMENTADAS/25_KNOWLEDGE_HUB_TEMATICO_E_RAG_ISOLADO_POR_CANAL.md) (IDEA-25), garantindo que mensagens enviadas dentro de canais temáticos dedicados fiquem isoladas e não vazem para conversas gerais.
3. **`contar_mensagens`:** Usada em diagnósticos (`!ajuda geral` / `!status`).
4. **Chamadas de `init_*_db` em `init_db()`:** Necessárias para que a inicialização central do bot configure o schema completo do SQLite de uma só vez na subida da aplicação.

---

## 3. Classificação do Excedente

* **Item 1 (`user_model_preferences`):** `[Feature Antecipada / Não-Documentada no Módulo Central]` — Possui lastro em spec de ideia implementada (IDEA-07), mas faltou sincronizar no spec base do SQLite.
* **Item 2 (`channel_id` em `messages`):** `[Feature Antecipada / Não-Documentada no Módulo Central]` — Possui lastro em spec de ideia implementada (IDEA-25), mas a spec base ainda lista o schema original sem a coluna.
* **Item 3 (`contar_mensagens`):** `[Otimização Não-Funcional / Helper Utilitário]` — Consulta simples de leitura sem quebra de contrato.
* **Item 4 (`init_*_db`):** `[Otimização de Infraestrutura]` — Orquestração de inicialização do banco.

---

## 4. Recomendação Técnica do Coder

* **Recomendação:** **INCORPORAR NA SPEC VIA `/doc_master`**.  
  Nenhum desses códigos deve ser removido. Todos estão em pleno funcionamento e são fundamentais para o roteamento híbrido (Gemini/Local) e para o isolamento de tópicos por canal. A ação correta é atualizar a documentação `01_BANCO_DE_DADOS_SQLITE.md` para incluir esses schemas e índices atualizados.

