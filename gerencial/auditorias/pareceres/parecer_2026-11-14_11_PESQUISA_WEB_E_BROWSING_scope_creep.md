# Parecer Técnico do Coder: Scope Creep & Extensões do Módulo 11 (Pesquisa na Web & Browsing)

**Data:** 2026-11-14  
**Módulo Auditado:** `discord/SPECs/modulos_visiveis/11_PESQUISA_WEB_E_BROWSING.md` (`MOD-VIS-11`)  
**Autor:** Estagiário Codificador (`/coder`)  
**Destinatário:** Auditor Forense de Specs (`/spec-audit`) & Arquiteto-Chefe  

---

## 1. Contexto e Justificativa das Extensões

Durante o ciclo de produção e evolução do bot (v2.8.0 a v3.6.0), foram implementadas melhorias de resiliência e usabilidade no motor de busca e navegação web:

### Item 1: Migração dos Comandos para `commands/web_commands.py`
* **Localização:** [`discord/commands/web_commands.py`](file:///Users/rodrigomodel/antigravity/discord/commands/web_commands.py#L12-L137)
* **Racional Técnico:** Originalmente, a spec mencionava `commands/builtins.py`. Em conformidade com a convenção modular dos 6 pilares temáticos de comandos (`calendar`, `productivity`, `ai`, `knowledge`, `web`, `system`), os comandos `!buscar` e `!ler` foram centralizados em `web_commands.py`.

### Item 2: Calibração de Timeout para 18.0s e Fallback de Backends DDGS
* **Localização:** [`discord/config.py`](file:///Users/rodrigomodel/antigravity/discord/config.py#L93) e [`discord/web_search_manager.py`](file:///Users/rodrigomodel/antigravity/discord/web_search_manager.py#L110-L134)
* **Racional Técnico:** 
  1. O timeout padrão de 12.0s provocava cancelamentos indevidos em portais de notícias pesados ou em conexões com latência variável. A elevação para 18.0s estabilizou o scraping.
  2. Adicionou-se o loop de backends no DuckDuckGo (`backends = ["yahoo", "auto"]`). Quando o endpoint padrão sofre rate limit temporário de IP, o backend alternativo responde instantaneamente sem gerar falha para o usuário.

### Item 3: Expansão de Aliases e UX Aprimorada nos Comandos
* **Localização:** [`discord/commands/web_commands.py`](file:///Users/rodrigomodel/antigravity/discord/commands/web_commands.py#L18-L19), [L60-L61](file:///Users/rodrigomodel/antigravity/discord/commands/web_commands.py#L60-L61)
* **Racional Técnico:** Foram adicionados aliases intuitivos como `!search`, `!web`, `!pesquisar` e `!resumir_link`, além de tratamento de feedback visual em tempo real com mensagens editáveis (`msg_status.edit`).

### Item 4: Coexistência com Comandos de Deep Research (`!pesquisa_profunda`, `!pesquisas`)
* **Localização:** [`discord/commands/web_commands.py`](file:///Users/rodrigomodel/antigravity/discord/commands/web_commands.py#L139-L276)
* **Racional Técnico:** O módulo `web_commands.py` passou a acolher os comandos do Agente de Pesquisa Profunda (IDEA-17), que consome `web_search_manager.py` para varredura multi-eixo.

---

## 2. Recomendação do Coder
Recomenda-se a **incorporação integral (Opção A)** de todas as extensões na especificação oficial `11_PESQUISA_WEB_E_BROWSING.md`, atualizando o caminho do arquivo de comandos, o timeout calibrado de 18s e a robustez dos backends DDGS.

