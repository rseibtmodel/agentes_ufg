# Parecer Técnico do Coder: Código Excedente no Pipeline de Áudio & Voz (MOD-INT-02)

**Data:** 14 de Novembro de 2026  
**Módulo Auditado:** [`discord/SPECs/modulos_internos/02_PIPELINE_AUDIO_E_VOZ.md`](file:///Users/rodrigomodel/antigravity/discord/SPECs/modulos_internos/02_PIPELINE_AUDIO_E_VOZ.md)  
**Autor:** Junior Coder (`/coder`)  
**Solicitante:** Spec Auditor (`/spec-audit`)  
**Status:** Submetido para Decisão do Arquiteto-Chefe  

---

## 1. Evidência Cirúrgica de Código Excedente

* **Item 1:** Reconhecimento de intenção conversacional para alternância de modo de voz
  - **Localização:** [`discord/message_handler.py:L196-L238`](file:///Users/rodrigomodel/antigravity/discord/message_handler.py#L196-L238) e [`discord/message_handler.py:L365-L381`](file:///Users/rodrigomodel/antigravity/discord/message_handler.py#L365-L381).
* **Item 2:** Feedback visual interativo durante transcrição com edição de mensagem
  - **Localização:** [`discord/message_handler.py:L305-L315`](file:///Users/rodrigomodel/antigravity/discord/message_handler.py#L305-L315).
* **Item 3:** Concatenação de múltiplos anexos de áudio ou texto + áudio
  - **Localização:** [`discord/message_handler.py:L320-L325`](file:///Users/rodrigomodel/antigravity/discord/message_handler.py#L320-L325).
* **Item 4:** Delegação de exclusão de temporários via `MessageGateway.dispatch(delete_after_send=...)`
  - **Localização:** [`discord/message_handler.py:L644, L681`](file:///Users/rodrigomodel/antigravity/discord/message_handler.py#L644) e [`discord/message_gateway.py:L264-L270`](file:///Users/rodrigomodel/antigravity/discord/message_gateway.py#L264-L270).

---

## 2. Motivação Técnica e de Negócio

1. **Reconhecimento Conversacional de Voz:** Permite que o usuário diga *"responda em áudio"* ou *"quero apenas texto"* sem precisar digitar comandos com prefixo (`!voz`).
2. **Feedback Visual:** Ao receber um áudio longo, o usuário no Discord recebe um placeholder *"🎙️ Ouvindo e transcrevendo áudio..."*, que é editado após a transcrição, reduzindo a sensação de atraso (UX de feedback contínuo).
3. **Múltiplos Áudios:** Suporta situações em que o usuário envia duas notas de voz seguidas ou um texto com áudio explicativo.
4. **Delegação via Gateway:** Previne que o arquivo de áudio temporário seja destruído pelo `finally` antes de o cliente HTTP do Discord concluir o upload dos bytes na rede, eliminando falhas de *file not found* sob conexões lentas.

---

## 3. Classificação do Excedente

* **Item 1 (Intenção Conversacional):** `[Feature Antecipada / UX]` — Excelente para a usabilidade do bot.
* **Item 2 (Feedback Visual):** `[Otimização Não-Funcional / Heurística de UX]` — Mantém o usuário informado do status.
* **Item 3 (Múltiplos Áudios):** `[Robustez de Entrada / Edge-case]`.
* **Item 4 (Gateway `delete_after_send`):** `[Evolução Arquitetural]` — Substituição do envio direto pelo barramento outbox com controle anti-spam (IDEA-24).

---

## 4. Recomendação Técnica do Coder

* **Recomendação:** **INCORPORAR NA SPEC VIA `/doc_master`**.  
  Essas funcionalidades aumentam a robustez do pipeline de áudio. A recomendação é atualizar a Seção 1 (diagrama de sequência) e Seção 4 de `02_PIPELINE_AUDIO_E_VOZ.md` para documentar a deleção assíncrona segura via `delete_after_send` do `MessageGateway` e os reconhecimentos de intenção de fala.

