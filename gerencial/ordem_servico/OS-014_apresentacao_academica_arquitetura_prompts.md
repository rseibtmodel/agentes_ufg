# OS-014: Apresentação Acadêmica da Arquitetura v3.6.0 & Engenharia de Prompt

**Data:** 11 de Novembro de 2026  
**Status:** Em Execução  
**Autor:** Agent Manager (`/gerente`)  
**Especialista Convocado:** Deck Master (`/deck_master`)  
**Destinatário:** Apresentação para Professor Especialista em IA / Trabalho de Prompt  

---

## 👑 Diretriz do Arquiteto-Chefe [Usuário]
Construir uma apresentação aprofundada com o `/deck_master` baseada na arquitetura v3.6.0 (`discord/SPECs/arquitetura/visao_geral_arquitetura_v36.jpg`) e no laudo de auditoria (`gerencial/reviews/REV-002_auditoria_visao_geral_arquitetura_v36.md`). A apresentação deve conter de 1 a 3 slides por camada do sistema (8 camadas), com nível técnico rigoroso voltado para um professor com conhecimentos profundos de IA, enfatizando a esteira de Engenharia de Prompt, RAG hierárquico, Tool RAG e mitigação de alucinação.

---

## 📌 Escopo e Roteiro Técnico dos Slides
1. **Contexto & Tese:** Orquestração de prompts em escala no Discord sem estourar janelas de contexto.
2. **Layer 1 (Gateway):** Ingestão WebSocket assíncrona e lockfile atômico.
3. **Layer 2 (Percepção Multimodal):** Whisper int8 VAD e PyMuPDF TOC — saneamento pré-prompt.
4. **Layer 3 (Roteamento & Contexto):** Fast-Path determinístico (<50ms) vs Slow-Path neural; `ContextVars`.
5. **Layer 4 (Memória Híbrida & RAG):** SQLite WAL (curto prazo) + ChromaDB (longo prazo) com filtro anti-redundância.
6. **Layer 5 (Motor Cognitivo & Prompts):**
   - Montagem hierárquica do System Prompt Único (Núcleo $\rightarrow$ Persona $\rightarrow$ Tópico $\rightarrow$ Memória).
   - Sanitização para compatibilidade Jinja (índice 0) e sanitização anti-vazamento de badges.
   - Dynamic Tool RAG por similaridade de cosseno (Top-K tools para poupar 80% do contexto).
   - Roteamento híbrido (LM Studio local vs Gemini Cloud) e ciclo de Function Calling.
7. **Layer 6 (UI Engine):** Respostas de IA acopladas a componentes interativos (`discord.ui`).
8. **Layer 7 (Outbox Gateway):** Fila Leaky Bucket, SHA-256 deduplication e circuit breaker.
9. **Layer 8 (Entrega Multimodal):** Edge-TTS, chunking semântico (<= 1900 chars) e Rich Embeds.
10. **Conclusão Acadêmica:** Balanço de trade-offs, soberania de dados e lições de Prompt Engineering.

---

## 📦 Artefatos Esperados
- Deck canônico Marp: `gerencial/apresentacoes/20261111_arquitetura_e_engenharia_de_prompt.md`.
- Apresentação HTML interativa standalone: `gerencial/apresentacoes/apresentacao_academica_prompts.html`.

