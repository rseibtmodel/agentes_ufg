# Parecer Técnico do Coder: Scope Creep & Extensões do Módulo 13 (Central de Prompts & Templates de IA)

**Data:** 2026-11-14  
**Módulo Auditado:** `discord/SPECs/modulos_visiveis/13_CENTRAL_DE_PROMPTS_E_TEMPLATES.md` (`MOD-VIS-13`)  
**Autor:** Estagiário Codificador (`/coder`)  
**Destinatário:** Auditor Forense de Specs (`/spec-audit`) & Arquiteto-Chefe  

---

## 1. Contexto e Justificativa das Extensões

Durante o ciclo de desenvolvimento das ideias IDEA-20 e IDEA-26 (v3.0.0 a v3.6.0), a Central de Prompts (`prompt_hub.py`) foi estabilizada como a biblioteca base de conhecimento cognitivo do bot:

### Item 1: Calibração de Temperatura Sugerida por Preset
* **Localização:** [`discord/prompt_hub.py`](file:///Users/rodrigomodel/antigravity/discord/prompt_hub.py#L23), [L35](file:///Users/rodrigomodel/antigravity/discord/prompt_hub.py#L35), [L47](file:///Users/rodrigomodel/antigravity/discord/prompt_hub.py#L47), [L123](file:///Users/rodrigomodel/antigravity/discord/prompt_hub.py#L123)
* **Racional Técnico:** Modelos de linguagem exigem calibrações térmicas distintas dependendo do domínio. Para código e tributos, criatividade causa alucinações (temperatura `0.2` a `0.3`). Para filosofia ou conversação padrão, maior amplitude é desejada (`0.7`). O campo `temperatura_sugerida` foi adicionado à tabela `prompt_templates` para transmitir esse hiperparâmetro diretamente à inferência da LLM.

### Item 2: Integração com o Subsistema de Personas de Canal (IDEA-26)
* **Localização:** [`discord/commands/ai_commands.py`](file:///Users/rodrigomodel/antigravity/discord/commands/ai_commands.py#L184), [L243](file:///Users/rodrigomodel/antigravity/discord/commands/ai_commands.py#L243) e [`discord/tools/persona_tools.py`](file:///Users/rodrigomodel/antigravity/discord/tools/persona_tools.py#L122)
* **Racional Técnico:** Os templates do Prompt Hub servem como a fonte da verdade para aplicar personas a canais temáticos (`!persona canal aplicar <slug>`). O usuário pode criar um template pessoal via `!prompt salvar` e aplicá-lo instantaneamente ao canal do Discord.

### Item 3: Modularização em `ai_commands.py` e `prompt_tools.py`
* **Localização:** [`discord/commands/ai_commands.py`](file:///Users/rodrigomodel/antigravity/discord/commands/ai_commands.py#L164-L261) e [`discord/tools/prompt_tools.py`](file:///Users/rodrigomodel/antigravity/discord/tools/prompt_tools.py#L1-L125)
* **Racional Técnico:** A especificação original apontava `commands/builtins.py`. Em conformidade com o desacoplamento arquitetural, os comandos `!prompts` e `!prompt` residem em `ai_commands.py`, e as 3 ferramentas de Function Calling (`listar_templates_prompt`, `obter_template_prompt`, `salvar_template_prompt`) foram isoladas em `prompt_tools.py`.

### Item 4: Proteção Inviolável contra Modificação de Built-ins
* **Localização:** [`discord/prompt_hub.py`](file:///Users/rodrigomodel/antigravity/discord/prompt_hub.py#L245-L251), [L302-L303](file:///Users/rodrigomodel/antigravity/discord/prompt_hub.py#L302-L303)
* **Racional Técnico:** Presets de fábrica oficiais (`padrao`, `dev`, `cfo`, `direto`, `revisor`, `socrates`, `tributarista`) são blindados contra sobrescrita ou deleção acidental, garantindo a integridade dos presets nativos do assistente.

---

## 2. Recomendação do Coder
Recomenda-se a **incorporação integral (Opção A)** de todas as extensões na especificação oficial `13_CENTRAL_DE_PROMPTS_E_TEMPLATES.md`, expandindo o documento para sua versão canônica completa com os 7 presets de fábrica, o esquema da tabela SQLite, as ferramentas de Function Calling e a matriz de rastreabilidade reversa.

