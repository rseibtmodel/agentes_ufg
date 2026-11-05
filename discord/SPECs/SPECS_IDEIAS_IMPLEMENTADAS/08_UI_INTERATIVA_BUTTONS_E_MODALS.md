# Especificação de Ideia de Módulo: Interface Interativa com Botões, Menus e Modais (Discord UI)

**Código da Proposta:** `IDEA-08`  
**Status:** ✅ **ENTREGUE / EM PRODUÇÃO (v3.0.0)**  
**Impacto:** Substitui digitação repetitiva de comandos de texto por botões clicáveis, menus de seleção (dropdowns) e modais nativos do Discord.

---

## 1. Origem e Validação no Pipeline `idea_generator`

Esta especificação foi submetida e processada pelo pipeline multi-agente da skill **`idea_generator`**:

1. **💡 Geração Criativa (`Ideator`):**
   Como IDEATOR, proponho transformar a experiência do Discord AI Bot em uma verdadeira aplicação rica com o IDEA-08. O conceito central é eliminar a fricção da digitação de comandos slash ou textuais complexos através do uso massivo de Message Components nativos: Action Rows com botões de A/B, Select Menus dinâmicos para paginação de PDFs longos ou navegação em listas, e Modals para coleta estruturada de dados sem poluir os canais de texto públicos. A proposta de valor é aumentar o engajamento e a retenção do usuário ao trazer uma interface fluida, visual e tátil diretamente para dentro do chat do Discord.

2. **😈 Análise Crítica (`Devil's Advocate`):**
   Como DEVIL'S ADVOCATE, aponto falhas críticas nesta proposta. Primeiramente, state management: o Discord exige que componentes de interface interativos expirem ou lidem com interações expiradas após 15 minutos, gerando erros frustrantes 'A interação falhou' se a aplicação reiniciar ou se o usuário demorar a responder. Segundo, concorrência e race conditions: se múltiplos usuários clicarem em botões de uma lista compartilhada, haverá dessincronização do estado se não houver locks robustos no banco de dados. Terceiro, custos de API e latência: o uso excessivo de modais pode mascarar a necessidade de validações complexas que a LLM faria melhor. Quarto, acessibilidade e rate limits da API do Discord.

3. **🏆 Defesa Estratégica (`Champion`):**
   Como CHAMPION, defendo que o IDEA-08 é o divisor de águas entre um bot utilitário comum e um produto de nível corporativo. A redução de atrito no UX aumenta a retenção em mais de 300% em bots de produtividade. Menus de seleção para navegação de PDFs resolvem o problema clássico de limite de caracteres do Discord. O uso de modals para agendamentos traz uma UX familiar, limpa e imune à poluição de chat. As barreiras técnicas de timeout de interações são facilmente resolvidas com cache em Redis e tratamento de exceções amigáveis (ex: 'Esta sessão expirou, gere uma nova lista').

4. **⚖️ Veredito do Gatekeeper & Mitigação:**
   * **Status:** `[APROVADA]`
   * **Diretrizes e Condicionantes:** O módulo é formalmente APROVADO com base no alto valor de usabilidade. Condicionantes obrigatórias de segurança e viabilidade técnica: 1. Implementar tratamento de timeout (15 minutos) em todas as Views (`discord.ui.View`) com mensagens de fallback informativas. 2. Utilizar persistência de estado atômica (Redis/PostgreSQL) para evitar race conditions em cliques simultâneos em botões de listas compartilhadas. 3. Limitar o escopo de Modals estritamente a entradas de texto estruturadas (títulos, descrições), mantendo a lógica de processamento desacoplada em filas de background.

5. **✍️ Síntese do Editor (`Editor/Enricher`):**
   Síntese executiva do Editor: O IDEA-08 (UI Interativa com Botões, Menus e Modais) foi validado e aprovado pelo Gatekeeper. Plano de mitigação de riscos integrará: a) Gerenciamento de estado efêmero e persistente via Redis para contornar o timeout de 15 minutos da API do Discord; b) Uso de `interaction.response.defer()` para evitar falhas de timeout de 3 segundos do Discord durante chamadas assíncronas à LLM; c) Padronização de componentes em classes reutilizáveis no codebase do bot. Próximos passos imediatos: criar o framework base de `discord.ui.View` customizadas para listas e disparar a implementação do piloto no módulo de agendamento.

---

## 2. Justificativa e Motivação

Atualmente, todas as interações com o bot (com exceção de anexos de arquivo e áudio) ocorrem através de digitação no chat. Para gerenciar listas de compras, navegar entre capítulos de um livro, confirmar presença em lembretes ou aprovar eventos da agenda, a necessidade de digitar comandos como `!lista ticar mercado 2` ou `!lembrete adiar 15m` gera atrito cognitivo.

O Discord oferece suporte nativo a componentes de interface (*Message Components*):
- **Botões (`Button`):** Ações imediatas de um clique (concluir tarefa, adiar lembrete, acionar voz).
- **Menus de Seleção (`SelectMenu`):** Dropdowns para escolher capítulos de PDFs ou listas ativas.
- **Formulários Modais (`Modal`):** Janelas pop-up nativas para cadastrar compromissos ou lembretes sem poluir o chat.

---

## 3. Arquitetura Proposta

```mermaid
flowchart TD
    UserTrigger[Usuário solicita: 'Ver minha lista de mercado'] --> LLM[LLM / Comando !lista]
    LLM --> InteractiveView[Gera discord.ui.View com Itens e Botões]
    InteractiveView --> DiscordMessage[Mensagem no Discord com Botões de Checkbox]
    
    DiscordMessage --> UserClick[Usuário clica em: 'Ticar Tomate']
    UserClick --> DiscordInteraction[Interaction Event: button.callback]
    DiscordInteraction --> DBUpdate[Atualiza SQLite: item_marcado=1]
    DBUpdate --> ViewRefresh[Atualiza a View no Discord com tachado: ~Tomate~]
```

---

## 4. Casos de Uso e Telas Interativas

### 3.1 Listas de Mercado e Tarefas Interativas
Ao listar uma lista (`!lista ver mercado` ou por conversa natural):
- Cada item não-concluído é renderizado com um botão verde correspondente ou uma lista de seleção multi-select.
- Ao clicar no botão, o item é ticado instantaneamente no SQLite e a mensagem é editada no Discord com visual tachado (`~Item~`).
- Botão inferior vermelho: **"Limpar Concluídos"** e botão cinza: **"Adicionar Novo Item"** (que abre um Modal pop-up de texto).

### 3.2 Lembretes com Ações Rápidas
Quando o worker disparar uma notificação de lembrete:
- **Botão 1 (Verde):** `✅ Concluído` (finaliza o lembrete).
- **Botão 2 (Amarelo):** `⏱️ Adiar 10 min` (remarca automaticamente).
- **Botão 3 (Azul):** `🔁 Adiar para amanhã`.

### 3.3 Navegador de Capítulos de Livros / PDFs
Ao consultar o sumário de um livro (`!pdf sumario <arquivo>`):
- Um menu suspenso (`SelectMenu`) exibe todos os capítulos indexados com seus títulos e páginas.
- Ao selecionar um capítulo no menu, o bot envia imediatamente o resumo consolidado daquele capítulo com opção de ouvir em áudio.

---

## 5. Especificação Técnica

### 4.1 Tecnologias
- `discord.ui.View`, `discord.ui.Button`, `discord.ui.Select`, `discord.ui.Modal`.
- Persistência de estado de views para views persistentes (sobrevivência ao reinício do bot).

### 4.2 Configuração em `.env`
```ini
# Ativa componentes visuais interativos
DISCORD_UI_COMPONENTS_ENABLED=true
DISCORD_UI_TIMEOUT_SECONDS=180
```
