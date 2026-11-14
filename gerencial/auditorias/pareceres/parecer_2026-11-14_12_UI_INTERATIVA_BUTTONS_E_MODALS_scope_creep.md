# Parecer Técnico do Coder: Scope Creep & Extensões do Módulo 12 (UI Interativa: Buttons, Modais e Menus)

**Data:** 2026-11-14  
**Módulo Auditado:** `discord/SPECs/modulos_visiveis/12_UI_INTERATIVA_BUTTONS_E_MODALS.md` (`MOD-VIS-12`)  
**Autor:** Estagiário Codificador (`/coder`)  
**Destinatário:** Auditor Forense de Specs (`/spec-audit`) & Arquiteto-Chefe  

---

## 1. Contexto e Justificativa das Extensões

Durante o ciclo de desenvolvimento das ideias IDEA-08, IDEA-26 e IDEA-27 (v2.9.0 a v3.6.0), o ecossistema de componentes visuais do Discord (`ui_components.py`) evoluiu expressivamente para suportar interações multimodais e governança visual de personas:

### Item 1: Modal de Identidade Multimodal (`PersonaEditModal` e `PersonaModalLauncherView`)
* **Localização:** [`discord/ui_components.py`](file:///Users/rodrigomodel/antigravity/discord/ui_components.py#L561-L689)
* **Racional Técnico:** Para permitir que usuários customizem o tom e aparência visual das personas de canal (IDEA-27) sem digitar comandos complexos com 5 parâmetros, foi criado um modal nativo do Discord com 5 campos de texto (`Nome de Exibição`, `Idade/Maturação`, `URL do Avatar`, `Semente DiceBear` e `Bio`).

### Item 2: View de Governança de Metamorfose Semanal (`MetamorphosisActionView`)
* **Localização:** [`discord/ui_components.py`](file:///Users/rodrigomodel/antigravity/discord/ui_components.py#L695-L745)
* **Racional Técnico:** Quando a rotina de metamorfose semanal do assistente anuncia a nova identidade no canal, ela anexa botões de ação imediata: `Fixar Persona` (para preservar o personagem contra futuras mutações), `Re-rolar` (sortear nova combinação imediatamente) e `Customizar` (abrir o modal de edição).

### Item 3: Botão de Refresh e Particionamento de Action Rows no `InteractiveListView`
* **Localização:** [`discord/ui_components.py`](file:///Users/rodrigomodel/antigravity/discord/ui_components.py#L88-L134)
* **Racional Técnico:** A API do Discord limita cada Action Row a 5 botões e no máximo 25 componentes por mensagem. Foi implementado o particionamento automático dos primeiros 10 itens pendentes nas rows 0 e 1, e botões utilitários (`🧹 Limpar Concluídos`, `➕ Novo Item`, `🔄 Atualizar`) na row 2.

### Item 4: Parâmetros de Timeout e Desativação Graciosa (`on_timeout`)
* **Localização:** [`discord/ui_components.py`](file:///Users/rodrigomodel/antigravity/discord/ui_components.py#L179-L188), [L253-L260](file:///Users/rodrigomodel/antigravity/discord/ui_components.py#L253-L260), [L339-L347](file:///Users/rodrigomodel/antigravity/discord/ui_components.py#L339-L347), [L526-L534](file:///Users/rodrigomodel/antigravity/discord/ui_components.py#L526-L534)
* **Racional Técnico:** Componentes interativos não podem ficar eternamente ativos em memória gerando vazamentos. O timeout global `DISCORD_UI_TIMEOUT_SECONDS` (180s) desarma todos os botões (`child.disabled = True`) editando a mensagem quando expira.

### Item 5: Integração Modular Desacoplada
* **Localização:** As views são consumidas em `productivity_commands.py` (`!lista`), `reminder_worker.py` (notificações), `knowledge_commands.py` (`!pdf sumario`) e `ai_commands.py` (`!persona`).

---

## 2. Recomendação do Coder
Recomenda-se a **incorporação integral (Opção A)** de todas as extensões na especificação oficial `12_UI_INTERATIVA_BUTTONS_E_MODALS.md`, atualizando o catálogo completo de componentes com `PersonaEditModal`, `MetamorphosisActionView`, as regras de Action Rows e os timeouts de expiração graciosa.

