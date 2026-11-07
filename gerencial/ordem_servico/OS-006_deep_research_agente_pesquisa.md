---
id: OS-006
data: 2026-11-07
agente_alvo: coder
supervisor: architect
fase_roadmap: implementacao_idea_17
status: concluido
---

# 🎯 ORDEM DE SERVIÇO: @coder (Supervisão: @architect & @qa)

=====================================================  
👑 **Diretriz do Arquiteto-Chefe [Usuário]:** Implementação da Rota 1 — Agente de Pesquisa Profunda (Deep Research / `IDEA-17`).  
📌 **Objetivo Imediato:**
1. Criar o motor `discord/deep_research_manager.py` com:
   - Loop de decomposição do tema em sub-perguntas analíticas com LLM.
   - Varredura paralela de 8 a 15 fontes web via `web_search_manager` com controle de concorrência (`asyncio.Semaphore`).
   - Extração de dados, cruzamento de fontes e síntese de Dossiê Executivo detalhado.
   - Persistência dos relatórios em SQLite WAL e geração de arquivo Markdown (`.md`) para anexo no Discord.
2. Criar a ferramenta de Function Calling em `discord/tools/research_tools.py` aderente ao contrato canônico `{"sucesso": bool, "dados": Any, "erro": Optional[str]}`.
3. Registrar os comandos `!pesquisa_profunda` (aliases: `!pesquisa`, `!deepresearch`, `!investigar`) e `!pesquisas` em `discord/commands/web_commands.py`.
4. Criar testes automatizados em `tests/test_deep_research.py` para homologar o pipeline.  
🛡️ **Limites & Blast Radius:**  
- Preservar a não-bloqueância do loop assíncrono (I/O via `asyncio.to_thread` ou `httpx.AsyncClient`).
- Canalizar o envio e progresso pelo `message_gateway` com `priority=HIGH`.
- 100% Type Hints (PEP 484).  
📦 **Artefato Esperado:** Módulo `deep_research_manager.py`, tool `research_tools.py`, comandos registrados e testes automatizados passando.  
=====================================================

## Checklist de Execução
- [x] Emissão e persistência da OS-006 em `gerencial/ordem_servico/`
- [x] Implementação de `discord/deep_research_manager.py`
- [x] Implementação de `discord/tools/research_tools.py`
- [x] Integração dos comandos `!pesquisa_profunda` e `!pesquisas` em `discord/commands/web_commands.py`
- [x] Atualização do catálogo de comandos e registro de tools em `discord/tools/__init__.py`
- [x] Implementação e homologação dos testes em `tests/test_deep_research.py` (19 testes passando)
- [x] Atualização do status da OS-006 para `concluido` e commit da funcionalidade
