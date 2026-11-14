---
id: MOD-VIS-10
modulo: Roteamento Híbrido de LLMs & Provedor Google Gemini Cloud
versao: 1.1.0
status: ATIVO EM PRODUÇÃO
camada: Cognitiva & Roteamento de Modelos
autores:
  - Software Architect
  - Tech Lead Reviewer
  - Junior Coder
  - Doc Master
ultima_atualizacao: 2026-11-14
---

# Módulo 10: Roteamento Híbrido de LLMs & Provedor Google Gemini Cloud

**Versão do Módulo:** 1.1.0 (Auditado e Estabilizado no Bot v3.6.0)  
**Status Operacional:** ✅ **ATIVO EM PRODUÇÃO (100% Cobertura de Testes)**  
**Camada Arquitetural:** Cognitiva & Roteamento de Modelos (`llm_client.py`, `database.py`, `message_handler.py`, `commands/ai_commands.py`, `tools/settings_tools.py`)

---

## 1. Visão Geral e Justificativa

O **Módulo de Roteamento Híbrido** resolve o dilema entre privacidade/custo zero do hardware local e poder cognitivo/janela de contexto massiva da nuvem.

Historicamente, o bot operava 100% ancorado no **LM Studio local** (`http://localhost:1234/v1`). Embora excelente para tarefas cotidianas, modelos locais enfrentam limitações em tarefas pesadas (leitura de livros longos, raciocínio em múltiplas etapas, concorrência de chamadas de ferramentas).

A introdução do **Google Gemini API** (`gemini-2.5-flash`, `gemini-3.5-flash` e `gemini-2.5-pro`) com fallback automático de alta disponibilidade e seleção dinâmica (via comando, linguagem natural ou personas) viabiliza:
1. **Janela de Contexto Gigante (1M+ tokens):** Análise holística de livros, relatórios e manuais completos.
2. **Alta Velocidade e Zero Fila Local:** Requisições assíncronas paralelas sem sobrecarregar a GPU/CPU da máquina local.
3. **Resiliência Crítica (Failover Automático):** Se o LM Studio estiver fechado, sem memória ou com timeout > 15s (`LOCAL_TIMEOUT_FAILOVER_SECONDS`), a requisição transborda suavemente para a nuvem sem interrupção para o usuário.
4. **Fallback Suave Inverso:** Se a API remota do Gemini falhar ou a chave não estiver configurada, o sistema retorna com segurança para o nó local LM Studio.

---

## 2. Comandos Disponíveis para o Usuário (`!modelo`)

Comando principal registrado em [`discord/commands/ai_commands.py`](file:///Users/rodrigomodel/antigravity/discord/commands/ai_commands.py#L41-L162) com aliases: `!modelo`, `!llm`, `!ia`, `!provedor`.

| Comando | Descrição | Exemplo |
| :--- | :--- | :--- |
| `!modelo` / `!modelo status` | Exibe o provedor ativo, modelo atual, status da chave Gemini e failover. | `!modelo` |
| `!modelo local` | Força a utilização do nó local LM Studio (`qwen/qwen3.5-9b`). | `!modelo local` |
| `!modelo google` / `!modelo gemini` | Ativa o Google Gemini Flash em nuvem (respostas ultrarrápidas). | `!modelo google` |
| `!modelo gemini-pro` | Ativa o Google Gemini Pro para raciocínio denso e código complexo. | `!modelo gemini-pro` |
| `!modelo auto` | Ativa o modo inteligente automático (Local para rotina, Gemini para tarefas pesadas). | `!modelo auto` |
| `!modelo key <chave>` | Cadastra a chave da Google Gemini API (apaga a mensagem do chat por proteção e persiste no `.env`). | `!modelo key AIzaSy...` |

> 🔒 **Segurança Operacional:** Ao receber o comando `!modelo key`, o bot invoca `await ctx.message.delete()` imediatamente para evitar vazamento da credencial no histórico do Discord. Em seguida, atualiza o cliente em memória e grava a variável `GEMINI_API_KEY` diretamente no `.env` do projeto para persistência contínua.

---

## 3. Alternância por Linguagem Natural

O processador de mensagens ([`discord/message_handler.py`](file:///Users/rodrigomodel/antigravity/discord/message_handler.py#L164-L194) e [L387-L401](file:///Users/rodrigomodel/antigravity/discord/message_handler.py#L387-L401)) detecta intenções em linguagem natural via `detectar_solicitacao_modelo`, permitindo que o usuário alterne sem comandos formais:
* *"Troque para o modelo do Google"* ➔ Ativa Gemini Flash.
* *"Mude para o Gemini Pro"* ➔ Ativa Gemini Pro.
* *"Volte para o modelo local"* ➔ Ativa LM Studio Local.
* *"Ative o modo automático de modelo"* ➔ Ativa o Roteamento Inteligente Auto-Tiering.

---

## 4. Indicadores Visuais de Provedor (Badges) & Sanitização

Cada resposta gerada inclui um identificador transparente no topo da mensagem:
- 🏠 `[LM Studio: qwen/qwen3.5-9b]` — Processado pelo servidor local.
- ⚡ `[Google Gemini: gemini-3.5-flash]` — Processado pelo Google Gemini Flash.
- 🧠 `[Google Gemini: gemini-3.5-flash]` (ou Pro) — Processado pelo Google Gemini Pro.
- ⚡ `[Google Gemini: gemini-3.5-flash | Auto-Failover]` — Fallback ativado devido à indisponibilidade do nó local.

> 🛡️ **Sanitização de Badges (`sanitizar_badges_repetidos`):** Para evitar que a LLM aprenda a imitar os badges e acumule cabeçalhos repetidos nas mensagens seguintes, o texto é sanitizado via regex antes de ser enviado e antes de ser persistido na memória SQLite e vetorial ChromaDB.

---

## 5. Roteamento Inteligente Automático (Modo `auto`)

Quando configurado em `!modelo auto`, a mensagem passa por `classificar_complexidade_demanda` ([`discord/llm_client.py`](file:///Users/rodrigomodel/antigravity/discord/llm_client.py#L77-L112)):
* **Rotina / Cotidiano ➔ LM Studio Local:** Saudações, hora, previsão do tempo, gerenciamento de listas (`!lista`), lembretes (`!lembrete`), eventos do Google Calendar.
* **Tarefas Pesadas ➔ Google Gemini:**
  - *Gemini Pro:* Raciocínio avançado, teses, dissertações, refatoração de código complexo e provas matemáticas.
  - *Gemini Flash:* Leitura de livros e PDFs (`!pdf`), RAG, sínteses de capítulos, scripts longos, tradução, links/web browsing e qualquer mensagem com mais de 350 caracteres.

---

## 6. Defesas de Arquitetura & Integração com Personas

1. **Compatibilidade com Templates Jinja (`sanitizar_mensagens_jinja`):**
   Modelos no LM Studio frequentemente impõem regras rígidas que exigem blocos de sistema estritamente no índice zero. A função normaliza a lista de mensagens aglutinando instruções de sistema no cabeçalho antes do envio.
2. **Precedência de Personas de Canal (`persona_manager.py`):**
   Quando um canal possui uma persona vinculada com `model_override` (ex: canal focado em raciocínio exigindo `gemini-pro`), essa diretriz sobrepõe a preferência individual de `user_model_preferences`, garantindo a integridade do propósito do canal.

---

## 7. Persistência de Preferências no SQLite

Tabela criada em `chat_memory.db` via [`discord/database.py`](file:///Users/rodrigomodel/antigravity/discord/database.py#L81-L90):

```sql
CREATE TABLE IF NOT EXISTS user_model_preferences (
    user_id TEXT PRIMARY KEY,
    user_name TEXT NOT NULL,
    provider TEXT NOT NULL DEFAULT 'local',       -- 'local', 'google', 'auto'
    model_name TEXT NOT NULL DEFAULT 'qwen/qwen3.5-9b',
    auto_failover INTEGER DEFAULT 1,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

Funções de suporte:
* `obter_preferencia_modelo(user_id)`: Retorna dicionário com `provider`, `model_name`, `auto_failover` e `updated_at`.
* `definir_preferencia_modelo(user_id, user_name, provedor, nome_modelo, auto_failover)`: Insere ou atualiza via `ON CONFLICT(user_id) DO UPDATE`.
* `normalizar_provedor_modelo(termo)`: Mapeia sinônimos (`lmstudio`, `nuvem`, `hibrido`, etc.) para chaves canônicas.

---

## 8. Ferramentas da LLM Integradas (Function Calling)

Disponíveis em [`discord/tools/settings_tools.py`](file:///Users/rodrigomodel/antigravity/discord/tools/settings_tools.py#L88-L170):

* `configurar_provedor_modelo(provedor: str)`: Permite à própria IA mudar o provedor se o usuário solicitar durante a conversa.
* `consultar_provedor_modelo()`: Retorna o modelo e provedor ativo com status de conectividade do Gemini.

---

## 9. 📋 Matriz de Rastreabilidade & Aderência (Auditada em 2026-11-14)

| Requisito / Componente | Arquivo de Implementação | Símbolos / Classes / Funções | Linhas Auditadas | Status |
| :--- | :--- | :--- | :--- | :---: |
| **Cliente Híbrido Assíncrono** | [`discord/llm_client.py`](file:///Users/rodrigomodel/antigravity/discord/llm_client.py) | `LLMClient`, `_inicializar_google_client`, `tem_gemini_disponivel` | [L114-L174](file:///Users/rodrigomodel/antigravity/discord/llm_client.py#L114-L174) | 🟢 Aderente |
| **Roteamento & Failover Automático** | [`discord/llm_client.py`](file:///Users/rodrigomodel/antigravity/discord/llm_client.py) | `gerar_resposta`, `_executar_loop_completions` | [L228-L355](file:///Users/rodrigomodel/antigravity/discord/llm_client.py#L228-L355) | 🟢 Aderente |
| **Classificador Heurístico Auto** | [`discord/llm_client.py`](file:///Users/rodrigomodel/antigravity/discord/llm_client.py) | `classificar_complexidade_demanda` | [L77-L112](file:///Users/rodrigomodel/antigravity/discord/llm_client.py#L77-L112) | 🟢 Aderente |
| **Sanitização Jinja & Badges** | [`discord/llm_client.py`](file:///Users/rodrigomodel/antigravity/discord/llm_client.py) | `sanitizar_mensagens_jinja`, `sanitizar_badges_repetidos` | [L34-L74](file:///Users/rodrigomodel/antigravity/discord/llm_client.py#L34-L74) | 🟢 Aderente |
| **Comando CLI `!modelo`** | [`discord/commands/ai_commands.py`](file:///Users/rodrigomodel/antigravity/discord/commands/ai_commands.py) | `cmd_modelo` (status, local, google, gemini-pro, auto, key) | [L41-L162](file:///Users/rodrigomodel/antigravity/discord/commands/ai_commands.py#L41-L162) | 🟢 Aderente |
| **Persistência Segura de Chave (.env)** | [`discord/commands/ai_commands.py`](file:///Users/rodrigomodel/antigravity/discord/commands/ai_commands.py) | `ctx.message.delete()`, regex substitution `.env` | [L87-L118](file:///Users/rodrigomodel/antigravity/discord/commands/ai_commands.py#L87-L118) | 🟢 Aderente |
| **Detecção em Linguagem Natural** | [`discord/message_handler.py`](file:///Users/rodrigomodel/antigravity/discord/message_handler.py) | `detectar_solicitacao_modelo` | [L164-L194](file:///Users/rodrigomodel/antigravity/discord/message_handler.py#L164-L194), [L387-L401](file:///Users/rodrigomodel/antigravity/discord/message_handler.py#L387-L401) | 🟢 Aderente |
| **Precedência de Persona de Canal** | [`discord/message_handler.py`](file:///Users/rodrigomodel/antigravity/discord/message_handler.py) | `persona_canal.get("model_override")` | [L558-L577](file:///Users/rodrigomodel/antigravity/discord/message_handler.py#L558-L577) | 🟢 Aderente |
| **Tabela SQLite & Preferências** | [`discord/database.py`](file:///Users/rodrigomodel/antigravity/discord/database.py) | `user_model_preferences`, `obter_preferencia_modelo`, `definir_preferencia_modelo` | [L81-L90](file:///Users/rodrigomodel/antigravity/discord/database.py#L81-L90), [L357-L434](file:///Users/rodrigomodel/antigravity/discord/database.py#L357-L434) | 🟢 Aderente |
| **Tools de IA de Configuração** | [`discord/tools/settings_tools.py`](file:///Users/rodrigomodel/antigravity/discord/tools/settings_tools.py) | `tool_configurar_provedor_modelo`, `tool_consultar_provedor_modelo` | [L88-L170](file:///Users/rodrigomodel/antigravity/discord/tools/settings_tools.py#L88-L170) | 🟢 Aderente |
| **Parâmetros e Defaults no Config** | [`discord/config.py`](file:///Users/rodrigomodel/antigravity/discord/config.py) | `DEFAULT_LLM_PROVIDER`, `GEMINI_API_KEY`, `LOCAL_TIMEOUT_FAILOVER_SECONDS` | [L32-L40](file:///Users/rodrigomodel/antigravity/discord/config.py#L32-L40) | 🟢 Aderente |
