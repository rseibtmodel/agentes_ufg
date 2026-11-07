---
id: OS-004
data: 2026-11-07
agente_alvo: coder
supervisor: review
fase_roadmap: refatoracao_onda_2
status: concluido
---

# 🎯 ORDEM DE SERVIÇO: @coder (Supervisão: @review)

=====================================================  
👑 **Diretriz do Arquiteto-Chefe [Usuário]:** Implementação da Onda 2 de Refatoração — Blindagem do Event Loop e Adequação ao Contrato Canônico de Function Calling.  
📌 **Objetivo Imediato:** Sanar os débitos técnicos de event loop e Function Calling mapeados no laudo `REV-001`:
1. `BUG-01`: Migrar todas as operações síncronas de SQLite no fluxo de mensagens (`message_handler.py`) para `await asyncio.to_thread()`, blindando o loop contra bloqueios.
2. `BUG-03`: Padronizar 100% das ferramentas do catálogo (`discord/tools/*`) e o despachante (`tools/registry.py`) para retornarem compulsoriamente a estrutura canônica:
   `{"sucesso": bool, "dados": Any, "erro": Optional[str]}`.
3. `BUG-09`: Serializar o `content` da role `tool` em `llm_client.py` estritamente como JSON válido (`json.dumps(resultado, ensure_ascii=False)`).
4. `BUG-10`: Garantir que chamadas síncronas ao ChromaDB em `vector_db.py`, `topic_manager.py` e `pdf_manager.py` executem em `asyncio.to_thread()`.  
🛡️ **Limites & Blast Radius:** Modificações nos arquivos:
- `discord/message_handler.py`
- `discord/tools/registry.py`
- `discord/tools/*_tools.py`
- `discord/llm_client.py`
- `discord/vector_db.py`
- `discord/topic_manager.py`
- `discord/pdf_manager.py`  
Não quebrar comandos de chat existentes nem assinaturas declaradas das tools. Preservar 100% de tipagem estática (PEP 484).  
📦 **Artefato Esperado:** Código refatorado, testado em bancada e validado sem erros de importação ou tipagem.  
=====================================================

## Checklist de Execução
- [x] Emissão e persistência da OS-004 em `gerencial/ordem_servico/`
- [x] Blindagem de I/O de SQLite em `discord/message_handler.py` com `await asyncio.to_thread()`
- [x] Adequação do despachante `discord/tools/registry.py` com contrato canônico JSON estrito
- [x] Refatoração das ferramentas em `discord/tools/*` para retornarem `{"sucesso", "dados", "erro"}`
- [x] Ajuste da serialização de retorno de tools em `discord/llm_client.py`
- [x] Blindagem de operações de ChromaDB em `discord/vector_db.py`, `discord/topic_manager.py` e `discord/pdf_manager.py`
- [x] Teste de bancada (validação de contratos das 42 tools e ciclo assíncrono)
- [x] Atualização do status da OS-004 para `concluido` e commit das alterações
