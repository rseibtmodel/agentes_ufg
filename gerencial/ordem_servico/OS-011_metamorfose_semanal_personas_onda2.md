# Ordem de Serviço: OS-011 - Motor de Metamorfose Semanal & Bag-of-Words Local (Onda 2 - IDEA-27)

- **ID:** `OS-011`
- **Data:** 09/11/2026
- **Alvo:** `@coder` (Estagiário Codificador)
- **Origem:** Rota 1 aprovada pelo Arquiteto-Chefe sobre a [`IDEA-27`](file:///Users/rodrigomodel/antigravity/discord/SPECs/SPECS_IDEIAS_IMPLEMENTADAS/27_IDENTIDADE_MULTIMODAL_E_METAMORFOSE_SEMANAL.md)
- **Status:** Concluído (Entregue & Validado)

---

## 👑 Diretriz do Arquiteto-Chefe [Usuário]
Implementar a **Onda 2** da IDEA-27: desenvolver o extrator local em Python puro de Bag-of-Words (zero-token e sem custos de nuvem), o motor de metamorfose semanal adaptativa, os componentes visuais interativos pós-mutação (`MetamorphosisActionView`), a tarefa em segundo plano (`iniciar_worker_metamorfose`) rodando a cada 30 minutos e os subcomandos `!persona metamorfose` (forçar evolução imediata) e `!persona historico` (álbum genealógico de encarnações).

---

## 📌 Entregas Realizadas
1. **Extrator Local Bag-of-Words ([`discord/text_frequency.py`](file:///Users/rodrigomodel/antigravity/discord/text_frequency.py)):**
   - Lista defensiva de Stopwords em PT-BR e EN (`STOPWORDS_PT_EN`).
   - Funções `sanitizar_texto_mensagem`, `extrair_top_palavras_canal` e `formatar_bag_of_words_prompt`.
2. **Gerenciador de Metamorfose ([`discord/persona_evolution_manager.py`](file:///Users/rodrigomodel/antigravity/discord/persona_evolution_manager.py)):**
   - Métodos `verificar_canais_para_metamorfose`, `coletar_mensagens_canal`, `sintetizar_metamorfose_llm`, `executar_metamorfose_canal` e `obter_historico_metamorfoses`.
   - Preservação atômica das últimas 5 encarnações passadas em `evolution_history_json`.
3. **Componentes Visuais Interativos ([`discord/ui_components.py`](file:///Users/rodrigomodel/antigravity/discord/ui_components.py)):**
   - Classe `MetamorphosisActionView` com botões:
     - `[ 🔒 Fixar Persona ]`: Trava imediatamente contra mutações futuras.
     - `[ 🎲 Re-rolar ]`: Dispara re-cálculo forçado da identidade.
     - `[ ⚙️ Customizar ]`: Abre `PersonaEditModal`.
4. **Worker Assíncrono Contínuo ([`discord/chat_discord.py`](file:///Users/rodrigomodel/antigravity/discord/chat_discord.py)):**
   - `iniciar_worker_metamorfose` integrado ao ciclo perpétuo do bot executando checagem a cada 30 minutos.
5. **Comandos de Usuário ([`discord/commands/ai_commands.py`](file:///Users/rodrigomodel/antigravity/discord/commands/ai_commands.py)):**
   - `!persona metamorfose` / `!persona evoluir`: Execução manual sob demanda.
   - `!persona historico` / `!persona album`: Exibição visual do histórico genealógico.
6. **Suíte de Testes Automatizados ([`tests/test_persona_evolution.py`](file:///Users/rodrigomodel/antigravity/tests/test_persona_evolution.py)):**
   - 6 novos testes unitários adicionados (totalizando 39 testes no ecossistema, todos passando em 0.065s).
7. **Governança:**
   - Movido `27_IDENTIDADE_MULTIMODAL_E_METAMORFOSE_SEMANAL.md` para `SPECS_IDEIAS_IMPLEMENTADAS/` com status `Implementada`.

---

## 🛡️ Validação & Blindagem
- Zero vazamentos de tokens: leitura 100% local com Python standard library (`Counter`, `re`).
- Zero bloqueios no Event Loop: chamadas SQLite executadas com `asyncio.to_thread`.
- Respeito soberano ao `is_locked`: personas fixadas pelo usuário jamais são sobrescritas.
