# 💻 Parecer Técnico do Coder — Código Excedente em `MOD-INT-07`

**Data:** 14 de Novembro de 2026  
**Autor:** Estagiário Codificador (`/coder`)  
**Solicitante:** Spec Auditor (`/spec-audit`)  
**Módulo Referência:** [`discord/SPECs/modulos_internos/07_MESSAGE_GATEWAY_OUTBOX.md`](file:///Users/rodrigomodel/antigravity/discord/SPECs/modulos_internos/07_MESSAGE_GATEWAY_OUTBOX.md) (`MOD-INT-07`)  
**Arquivos Inspecionados:** [`discord/message_gateway.py`](file:///Users/rodrigomodel/antigravity/discord/message_gateway.py)  

---

## 1. Contexto e Motivação Técnica

Durante a auditoria forense do módulo `MOD-INT-07` (Barramento Central de Mensagens / Message Gateway & Outbox), o `/spec-audit` confirmou que o Leaky Bucket, a fila prioritária Dual-Tier (Fast-Path e Background), a deduplicação SHA-256 e o Circuit Breaker estão 100% implementados e aderentes.

Foram identificados 3 componentes de código em [`discord/message_gateway.py`](file:///Users/rodrigomodel/antigravity/discord/message_gateway.py) que transcendem a especificação original.

Abaixo apresento a justificativa técnica para esses componentes:

---

## 2. Análise Detalhada dos Componentes Excedentes

### Componente 1: Custódia e Destruição Segura Pós-Envio (`delete_after_send`)
- **Localização:** [`discord/message_gateway.py:L60, L232, L263-L272, L284, L328-L335, L422-L428`](file:///Users/rodrigomodel/antigravity/discord/message_gateway.py#L60)
- **O que faz:**  
  Permite que chamadores do `dispatch()` passem caminhos de arquivos temporários (`delete_after_send=path`). O Gateway assume a responsabilidade de exclusão física dos arquivos no disco apenas no bloco `finally:` após a chamada `target.send(**kwargs)` ou em caso de descarte por duplicata/circuit breaker.
- **Justificativa Técnica:**  
  Desenvolvido para eliminar *race conditions* no pipeline de áudio TTS (`02_PIPELINE_AUDIO_E_VOZ.md`) e em relatórios PDF (`pdf_tools.py`). Se o chamador apagasse o arquivo imediatamente após o `dispatch()`, o stream de upload HTTP da biblioteca `aiohttp` falhava porque o arquivo sumia do disco antes do envio ser concluído pelo Discord.
- **Recomendação do Coder:** **Incorporar na especificação**, como garantia de ciclo de vida de arquivos temporários.

---

### Componente 2: Fallback Defensivo de Mensagem de Referência (`reply` fallback)
- **Localização:** [`discord/message_gateway.py:L253-L258`](file:///Users/rodrigomodel/antigravity/discord/message_gateway.py#L253-L258)
- **O que faz:**  
  Caso o Discord rejeite o envio com erros de mensagem referenciada inexistente ou expirada (códigos `160002`, `50035` ou `10008`), o Gateway remove o parâmetro `reference` do payload e reenvia a mensagem como uma mensagem normal no canal.
- **Justificativa Técnica:**  
  Se o usuário apagar a mensagem original enquanto a LLM estiver gerando a resposta (ou em servidores onde mensagens antigas expiram rapidamente), o bot travaria com erro HTTP se tentasse responder à mensagem deletada. O fallback garante que a resposta chegue ao canal independentemente da existência da mensagem original.
- **Recomendação do Coder:** **Incorporar na especificação**, sob a seção de resiliência.

---

### Componente 3: Hashing Profundo de Embeds na Deduplicação SHA-256
- **Localização:** [`discord/message_gateway.py:L158-L173`](file:///Users/rodrigomodel/antigravity/discord/message_gateway.py#L158-L173)
- **O que faz:**  
  A função `_generate_hash` inspeciona campos estruturados de `discord.Embed` (título, descrição, nomes e valores dos campos) e nomes de arquivos anexos para compor a assinatura SHA-256.
- **Justificativa Técnica:**  
  Muitas mensagens visuais do bot possuem texto `content` vazio ou genérico e transmitem toda a informação útil através de Embeds ricos (ex: `!ajuda`, `!digest`, `!modelo status`). Se o hash considerasse apenas `content`, mensagens com embeds diferentes seriam descartadas incorretamente como duplicatas.
- **Recomendação do Coder:** **Incorporar na especificação**, na seção de deduplicação anti-spam.

---

## 3. Conclusão do Coder
Todos os três componentes agregam robustez crítica ao tráfego do bot e previnem falhas em produção. Recomenda-se sua aprovação e incorporação na especificação oficial.

