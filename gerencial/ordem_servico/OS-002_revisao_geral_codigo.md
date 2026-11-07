---
id: OS-002
data: 2026-11-07
agente_alvo: review
supervisor: architect
fase_roadmap: auditoria_codigo
status: concluido
rota: 1_fatiada_por_dominios
---

# 🎯 ORDEM DE SERVIÇO: @review (Supervisão: @architect)

=====================================================  
👑 **Diretriz do Arquiteto-Chefe [Usuário]:** Rota 1 — Revisão Total do Código Fatiada por 3 Domínios Lógicos.  
📌 **Objetivo Imediato:** Conduzir auditoria técnica e arquitetural dos 40 arquivos de código-fonte em `discord/`, identificando problemáticas de concorrência, bloqueios de event loop, vazamentos de contexto, inconsistências de contrato de Function Calling e pontos de reestruturação para convergência com as decisões da v3.6.0.  
🛡️ **Limites & Blast Radius:** Escrita estritamente restrita a laudos gerenciais (`gerencial/reviews/REV-001_revisao_geral_codigo.md`). Proibido alterar código de produção (`discord/*.py`) nesta fase pericial. Toda e qualquer alteração de código será posteriormente delegada ao `/coder` sob aprovação soberana do Arquiteto-Chefe.  
📦 **Artefato Esperado:** Laudo Pericial unificado em `gerencial/reviews/REV-001_revisao_geral_codigo.md` contendo:
1. Diagnóstico Geral do Código.
2. Análise dos 3 Domínios (Bloco 1: Core/Gateway, Bloco 2: Cognição/RAG/Tools, Bloco 3: Mídia/Workers/UI).
3. Matriz de Débitos Técnicos por Severidade (🔴 Crítico, 🟡 Médio, 🟢 Baixo).
4. Recomendações Cirúrgicas e Plano de Refatoração para o `/coder`.  
=====================================================

## Checklist de Execução
- [x] Emissão e persistência da OS-002 em `gerencial/ordem_servico/`
- [x] Auditoria do Bloco 1: Core, Concorrência & Gateway (`chat_discord.py`, `message_handler.py`, `message_gateway.py`, `context_manager.py`, `database.py`, `config.py`, `utils.py`)
- [x] Auditoria do Bloco 2: Cognição, RAG & Function Calling (`llm_client.py`, `vector_db.py`, `pdf_manager.py`, `topic_manager.py`, `persona_manager.py`, `prompt_hub.py`, `tools/*`)
- [x] Auditoria do Bloco 3: Mídia, Workers & Interface (`audio_manager.py`, `tts_manager.py`, `reminder_manager.py`, `digest_manager.py`, `list_manager.py`, `google_calendar.py`, `auth_calendar.py`, `ui_components.py`, `commands/*`)
- [x] Consolidação do Laudo Pericial `REV-001_revisao_geral_codigo.md` com Matriz de Débitos Técnicos
- [x] Apresentação Executiva ao Arquiteto-Chefe com Proposta de Priorização de Refatoração
