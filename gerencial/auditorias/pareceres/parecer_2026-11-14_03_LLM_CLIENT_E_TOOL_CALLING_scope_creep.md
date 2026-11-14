# 💻 Parecer Técnico do Coder — Código Excedente em `MOD-INT-03`

**Data:** 14 de Novembro de 2026  
**Autor:** Estagiário Codificador (`/coder`)  
**Solicitante:** Spec Auditor (`/spec-audit`)  
**Módulo Referência:** [`discord/SPECs/modulos_internos/03_LLM_CLIENT_E_TOOL_CALLING.md`](file:///Users/rodrigomodel/antigravity/discord/SPECs/modulos_internos/03_LLM_CLIENT_E_TOOL_CALLING.md) (`MOD-INT-03`)  
**Arquivos Inspecionados:** [`discord/llm_client.py`](file:///Users/rodrigomodel/antigravity/discord/llm_client.py), [`discord/tools/registry.py`](file:///Users/rodrigomodel/antigravity/discord/tools/registry.py)  

---

## 1. Contexto e Motivação Técnica

Durante a auditoria forense do módulo interno `MOD-INT-03` (Motor LLM & Function Calling), o `/spec-audit` identificou que o código de produção em [`llm_client.py`](file:///Users/rodrigomodel/antigravity/discord/llm_client.py) e [`discord/tools/registry.py`](file:///Users/rodrigomodel/antigravity/discord/tools/registry.py) implementa recursos avançados que transcendem a especificação original (que cobria apenas a integração monoprovedor com LM Studio).

Abaixo apresento a justificativa técnica para cada um dos 3 componentes identificados:

---

## 2. Análise Detalhada dos Componentes Excedentes

### Componente 1: Roteamento Híbrido e Auto-Failover para Google Gemini
- **Localização:** [`discord/llm_client.py:L77-L112, L129-L174, L228-L355`](file:///Users/rodrigomodel/antigravity/discord/llm_client.py#L77-L112)
- **O que faz:** 
  1. Suporta dinamicamente provedores locais (`LM Studio`) e em nuvem (`Google Gemini API`) via cliente unificado OpenAI-compatible.
  2. Implementa heurística de classificação de complexidade de demanda (`classificar_complexidade_demanda`) para roteamento no modo `auto` (tarefas pesadas/RAG/código para Gemini Flash/Pro; rotina diária para o nó local).
  3. Ativa o **Auto-Failover transparente**: se o LM Studio local não responder no timeout de failover (`LOCAL_TIMEOUT_FAILOVER_SECONDS`), transborda a requisição para a nuvem sem interrupção de serviço.
- **Justificativa Técnica:**  
  Este código foi implementado para viabilizar a proposta **`IDEA-07`** (formalizada em [`discord/SPECs/SPECS_IDEIAS_IMPLEMENTADAS/07_ROTEAMENTO_HIBRIDO_E_PROVEDORES_CLOUD_LLM.md`](file:///Users/rodrigomodel/antigravity/discord/SPECs/SPECS_IDEIAS_IMPLEMENTADAS/07_ROTEAMENTO_HIBRIDO_E_PROVEDORES_CLOUD_LLM.md) e [`discord/SPECs/modulos_visiveis/10_ROTEAMENTO_HIBRIDO_E_GOOGLE_GEMINI.md`](file:///Users/rodrigomodel/antigravity/discord/SPECs/modulos_visiveis/10_ROTEAMENTO_HIBRIDO_E_GOOGLE_GEMINI.md)). Sem isso na classe central `LLMClient`, o bot não conseguiria realizar failover automático nem roteamento cognitivo inteligente.
- **Recomendação do Coder:** **Incorporar na especificação interna `03_LLM_CLIENT_E_TOOL_CALLING.md`**, conectando-a formalmente com o Módulo Visível 10.

---

### Componente 2: Sanitização de Badges Visuais Repetidos (`sanitizar_badges_repetidos`)
- **Localização:** [`discord/llm_client.py:L34-L40, L287, L317, L345`](file:///Users/rodrigomodel/antigravity/discord/llm_client.py#L34-L40)
- **O que faz:**  
  Remove expressões regulares que detectem badges repetidos (`🏠 [LM Studio: ...]`, `⚡ [Google Gemini: ...]`, `🧠 [Google Gemini: ...]`) do corpo da resposta gerada.
- **Justificativa Técnica:**  
  Modelos autorregressivos treinados em conversas com histórico às vezes "alucinam" ou imitam o badge de identificador visual que o bot injeta no início da mensagem. Se não forem higienizados, o usuário veria múltiplos cabeçalhos poluindo a interface do Discord.
- **Recomendação do Coder:** **Incorporar na especificação interna**, sob a seção de sanitização de saídas.

---

### Componente 3: Introspecção do Catálogo de Tools (`get_registered_names`)
- **Localização:** [`discord/tools/registry.py:L216-L219`](file:///Users/rodrigomodel/antigravity/discord/tools/registry.py#L216-L219)
- **O que faz:**  
  Retorna a lista ordenada dos nomes de todas as ferramentas registradas no catálogo em tempo de execução (`list(self._tools.keys())`).
- **Justificativa Técnica:**  
  Utilizado pelo Tool RAG semântico, comandos de diagnóstico (`!tools` ou depuração interna) e testes automatizados para verificar a integridade do carregamento dinâmico de ferramentas.
- **Recomendação do Coder:** **Incorporar na especificação interna**, sob a seção de API pública do `ToolRegistry`.

---

## 3. Conclusão do Coder
Todos os componentes foram desenvolvidos seguindo Clean Code, PEP 484 (100% Type Hints) e arquitetura assíncrona não-bloqueante. Recomenda-se a aprovação de todos para incorporação definitiva na documentação.

