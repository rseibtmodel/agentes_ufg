# Parecer Técnico do Coder: Scope Creep & Extensões do Módulo 10 (Roteamento Híbrido & Google Gemini)

**Data:** 2026-11-14  
**Módulo Auditado:** `discord/SPECs/modulos_visiveis/10_ROTEAMENTO_HIBRIDO_E_GOOGLE_GEMINI.md` (`MOD-VIS-10`)  
**Autor:** Estagiário Codificador (`/coder`)  
**Destinatário:** Auditor Forense de Specs (`/spec-audit`) & Arquiteto-Chefe  

---

## 1. Contexto e Justificativa das Extensões

Durante o ciclo de desenvolvimento e estabilização do Módulo 10 (v2.7.0 a v3.6.0), foram implementadas extensões operacionais críticas para viabilizar resiliência contínua, segurança de segredos e integração com a governança de personas:

### Item 1: Persistência Automática da Chave API no `.env` via `!modelo key`
* **Localização:** [`discord/commands/ai_commands.py`](file:///Users/rodrigomodel/antigravity/discord/commands/ai_commands.py#L101-L112)
* **Racional Técnico:** Originalmente a spec previa salvar a chave apenas em memória. Caso o bot reiniciasse ou o container fosse reiniciado, o usuário perdia o acesso à Google Gemini API e precisava reinserir a chave. A persistência via regex no `.env` (combinada com a deleção imediata da mensagem do chat `await ctx.message.delete()`) garante durabilidade de produção sem expor a credencial no histórico do Discord.

### Item 2: Sanitização Defensiva de Templates Jinja e Badges Repetidos
* **Localização:** [`discord/llm_client.py`](file:///Users/rodrigomodel/antigravity/discord/llm_client.py#L34-L74)
* **Racional Técnico:** 
  1. *Jinja strict templates:* Modelos locais (como Qwen 2.5 / 3.5) falham com erro `System message must be at the beginning` quando há múltiplos blocos de sistema intercalados com chamadas de tool. `sanitizar_mensagens_jinja` unifica e normaliza a estrutura.
  2. *Badges repetidos:* A LLM, ao receber o histórico de mensagens contendo badges anteriores (ex: `🏠 [LM Studio: ...]`), passava a alucinar e gerar múltiplos badges no corpo do texto. `sanitizar_badges_repetidos` aniquila esse ruído visual.

### Item 3: Precedência de `model_override` da Persona de Canal
* **Localização:** [`discord/message_handler.py`](file:///Users/rodrigomodel/antigravity/discord/message_handler.py#L558-L569)
* **Racional Técnico:** Com a introdução do sistema de Personas por Canal (IDEA-26), canais especializados (ex: `#raciocinio-profundo` ou `#debug-codigo`) podem exigir compulsoriamente o `gemini-pro`, enquanto `#bate-papo` pode forçar `local`. Se houver override na persona do canal, ele prevalece sobre a preferência individual do usuário.

### Item 4: Evolução de Nomenclatura dos Modelos Gemini (`3.5-flash`) e Aliases de Comando
* **Localização:** [`discord/config.py`](file:///Users/rodrigomodel/antigravity/discord/config.py#L35-L36), [`discord/database.py`](file:///Users/rodrigomodel/antigravity/discord/database.py#L348-L351), [`discord/commands/ai_commands.py`](file:///Users/rodrigomodel/antigravity/discord/commands/ai_commands.py#L47)
* **Racional Técnico:** Os modelos padrão foram atualizados para versões mais recentes (`gemini-3.5-flash`), mantendo retrocompatibilidade transparente. Foram adicionados os aliases `!llm`, `!ia` e `!provedor` para melhorar a experiência do usuário.

---

## 2. Recomendação do Coder
Recomenda-se a **incorporação integral (Opção A)** de todas as extensões na especificação oficial `10_ROTEAMENTO_HIBRIDO_E_GOOGLE_GEMINI.md`, visto que aumentam a robustez do bot, a segurança de segredos e o alinhamento com a arquitetura moderna de personas.

