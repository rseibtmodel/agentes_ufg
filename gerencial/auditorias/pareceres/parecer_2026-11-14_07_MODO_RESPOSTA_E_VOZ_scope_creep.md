# Parecer Técnico do Coder: Scope Creep em Modo de Resposta & Voz (`MOD-VIS-07`)

**Data:** 2026-11-14  
**Módulo Auditado:** `discord/SPECs/modulos_visiveis/07_MODO_RESPOSTA_E_VOZ.md`  
**Autor:** Estagiário Codificador (Junior Coder)  
**Destinatário:** Auditor Forense de Specs (`/spec-audit`) & Arquiteto-Chefe  

---

## 1. Contexto das Funcionalidades Não Documentadas na Spec Original

O módulo `MOD-VIS-07` foi concebido originalmente como uma chave de alternância simples entre saída de texto e áudio MP3 narrado via Edge-TTS. No decorrer do desenvolvimento, a funcionalidade foi profundamente integrada com o Outbox Gateway, o sistema polimórfico de Personas e os módulos de conhecimento avançado (PDFs e RAG).

---

## 2. Detalhamento e Justificativas Técnicas

### 2.1 Despacho Seguro e Purga Automática via Outbox Gateway (`delete_after_send`)
- **Implementação:** [`message_handler.py`](file:///Users/rodrigomodel/antigravity/discord/message_handler.py#L639-L645) e [`L677-L682`](file:///Users/rodrigomodel/antigravity/discord/message_handler.py#L677-L682).
- **Racional Técnico:** A síntese via `edge-tts` gera arquivos `.mp3` temporários no sistema de arquivos. Para evitar acúmulo de lixo em `/tmp` ou concorrência na deleção imediata antes do upload pelo Discord, o arquivo é repassado ao Gateway com o parâmetro `delete_after_send`, garantindo que a purga do arquivo em disco só ocorra após a confirmação do envio bem-sucedido na rede.

### 2.2 Fallback Gracioso para Texto em Caso de Falha de Rede no TTS
- **Implementação:** [`message_handler.py`](file:///Users/rodrigomodel/antigravity/discord/message_handler.py#L646-L659).
- **Racional Técnico:** O Edge-TTS depende dos servidores da Microsoft. Se houver falha de rede ou timeout e o usuário estiver no modo exclusivo de áudio (`audio`), o bot não silencia: emite o texto formatado como salvaguarda operacional, avisando no log sobre a degradação momentânea.

### 2.3 Respeito à Identidade Polimórfica de Personas no Modo Texto/Ambos
- **Implementação:** [`message_handler.py`](file:///Users/rodrigomodel/antigravity/discord/message_handler.py#L624-L632).
- **Racional Técnico:** Quando a entrega envolve texto, o despacho passa por `_despachar_resposta_persona`, assegurando que o nome do webhook e o avatar reflitam a persona temática configurada para o canal (ex: Francisca, Arquimedes, etc.).

### 2.4 Extensão Multimodal para Leitura de PDFs e RAG
- **Implementação:** [`commands/knowledge_commands.py`](file:///Users/rodrigomodel/antigravity/discord/commands/knowledge_commands.py#L201-L215) e [`L254-L268`](file:///Users/rodrigomodel/antigravity/discord/commands/knowledge_commands.py#L254-L268).
- **Racional Técnico:** Comandos como `!pdf capitulo` e `!pdf perguntar` consultam a preferência do usuário em `obter_modo_resposta(user_id)`. Se estiver em `audio` ou `ambos`, a resposta analítica é narrada pela Francisca automaticamente, proporcionando uma experiência de audiolivro sob demanda.

---

## 3. Recomendação do Coder
Recomenda-se a **Opção A (Manter no código e incorporar à SPEC)**: as adições garantem limpeza de disco, tolerância a falhas na síntese externa e unificam a voz da Francisca em todo o ecossistema.

