# Módulo 10: Roteamento Híbrido de LLMs & Provedor Google Gemini Cloud

**Versão do Módulo:** 1.0.0 (Entregue no Bot v2.7.0)  
**Status Operacional:** ✅ **ATIVO EM PRODUÇÃO**  
**Camada Arquitetural:** Cognitiva & Roteamento de Modelos (`llm_client.py`, `database.py`, `message_handler.py`, `commands/builtins.py`)

---

## 1. Visão Geral e Justificativa

O **Módulo de Roteamento Híbrido** resolve o dilema entre privacidade/custo zero do hardware local e poder cognitivo/janela de contexto massiva da nuvem.

Historicamente, o bot operava 100% ancorado no **LM Studio local** (`http://localhost:1234/v1`). Embora excelente para tarefas cotidianas, modelos locais enfrentam limitações em tarefas pesadas (leitura de livros longos, raciocínio em múltiplas etapas, concorrência de chamadas de ferramentas).

A introdução do **Google Gemini API** (`gemini-2.5-flash` e `gemini-2.5-pro`) com fallback automático de alta disponibilidade e seleção dinâmica (via comando ou linguagem natural) viabiliza:
1. **Janela de Contexto Gigante (1M+ tokens):** Análise holística de livros, relatórios e manuais completos.
2. **Alta Velocidade e Zero Fila Local:** Requisições assíncronas paralelas sem sobrecarregar a GPU/CPU da máquina local.
3. **Resiliência Crítica (Failover Automático):** Se o LM Studio estiver fechado, sem memória ou com timeout > 15s, a requisição transborda suavemente para a nuvem sem interrupção para o usuário.

---

## 2. Comandos Disponíveis para o Usuário

| Comando | Descrição | Exemplo |
| :--- | :--- | :--- |
| `!modelo` / `!modelo status` | Exibe o provedor ativo, modelo atual, status da chave Gemini e failover. | `!modelo` |
| `!modelo local` | Força a utilização do nó local LM Studio (`qwen/qwen3.5-9b`). | `!modelo local` |
| `!modelo google` / `!modelo gemini` | Ativa o Google Gemini 2.5 Flash em nuvem (respostas ultrarrápidas). | `!modelo google` |
| `!modelo gemini-pro` | Ativa o Google Gemini 2.5 Pro para raciocínio denso e código complexo. | `!modelo gemini-pro` |
| `!modelo auto` | Ativa o modo inteligente automático (Local para rotina, Gemini para tarefas pesadas). | `!modelo auto` |
| `!modelo key <chave>` | Cadastra a chave da Google Gemini API (apaga a mensagem do chat por proteção). | `!modelo key AIzaSy...` |

---

## 3. Alternância por Linguagem Natural

O processador de mensagens (`message_handler.py`) detecta intenções em linguagem natural, permitindo que o usuário alterne sem comandos formais:
* *"Troque para o modelo do Google"* ➔ Ativa Gemini 2.5 Flash.
* *"Mude para o Gemini Pro"* ➔ Ativa Gemini 2.5 Pro.
* *"Volte para o modelo local"* ➔ Ativa LM Studio Local.
* *"Ative o modo automático de modelo"* ➔ Ativa o Roteamento Inteligente Auto-Tiering.

---

## 4. Indicadores Visuais de Provedor (Badges)

Cada resposta gerada inclui um identificador transparente no topo da mensagem:
- 🏠 `[LM Studio: qwen/qwen3.5-9b]` — Processado pelo servidor local.
- ⚡ `[Google Gemini: gemini-2.5-flash]` — Processado pelo Google Gemini Flash.
- 🧠 `[Google Gemini: gemini-2.5-pro]` — Processado pelo Google Gemini Pro.
- ⚡ `[Google Gemini: gemini-2.5-flash | Auto-Failover]` — Fallback ativado devido à indisponibilidade do nó local.

---

## 5. Roteamento Inteligente Automático (Modo `auto`)

Quando configurado em `!modelo auto`, a mensagem passa por um classificador de intenção ultrarrápido:
* **Rotina / Cotidiano ➔ LM Studio Local:** Saudações, hora, previsão do tempo, gerenciamento de listas (`!lista`), lembretes (`!lembrete`), eventos do Google Calendar.
* **Tarefas Pesadas ➔ Google Gemini:** Dúvidas sobre livros (`!pdf perguntar`), resumos analíticos densos de capítulos, geração/depuração de código longo, análises comparativas e textos com mais de 350 caracteres.

---

## 6. Persistência de Preferências no SQLite

Tabela criada em `chat_memory.db`:

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

---

## 7. Ferramentas da LLM Integradas

* `configurar_provedor_modelo(provedor: str)`: Permite à própria IA mudar o provedor se o usuário solicitar durante a conversa.
* `consultar_provedor_modelo()`: Retorna o modelo e provedor ativo com status de conectividade do Gemini.
