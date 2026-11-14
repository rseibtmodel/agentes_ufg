# Especificação do Módulo: Geral & Diagnóstico

**Código do Módulo:** `MOD-VIS-01`  
**Escopo:** Comandos de Controle, Diagnóstico de Conexão, Sessão, Central de Ajuda em 2 Etapas com Ficha Individual e Telemetria Operacional  
**Arquivos de Implementação:** [`commands/system_commands.py`](file:///Users/rodrigomodel/antigravity/discord/commands/system_commands.py), [`commands/builtins.py`](file:///Users/rodrigomodel/antigravity/discord/commands/builtins.py), [`tools/datetime_tools.py`](file:///Users/rodrigomodel/antigravity/discord/tools/datetime_tools.py), [`utils.py`](file:///Users/rodrigomodel/antigravity/discord/utils.py)  

---

## 1. Descrição e Finalidade

O módulo **Geral & Diagnóstico** fornece ao usuário e ao administrador do bot ferramentas essenciais para verificação da saúde operacional do sistema, latência de rede com a API do Discord, conectividade com o LM Studio local e com os bancos de dados (SQLite e ChromaDB), além de prover uma **Central de Ajuda estruturada em duas etapas** (com suporte aos 14 blocos temáticos e fichas técnicas individuais por comando) para evitar estouro do limite de caracteres do Discord.

---

## 2. Comandos Disponíveis (`!`)

### 2.1 `!ajuda [modulo | comando]`
Central interativa de auxílio ao usuário:
* **Sem argumentos (`!ajuda`):** Apresenta o **Menu de 1ª Etapa**, listando os 14 grandes blocos temáticos disponíveis no bot (`geral`, `agenda`, `lista`, `lembrete`, `pdf`, `memoria`, `voz`, `digest`, `modelo`, `web`, `prompts`, `notas`, `persona`, `agy`) com um resumo executivo de cada um.
* **Com nome de módulo (`!ajuda <modulo>`):** Apresenta o **Menu de 2ª Etapa**, exibindo os comandos detalhados, sintaxes exatas, parâmetros aceitos e exemplos práticos para o módulo solicitado (ex: `!ajuda agenda`, `!ajuda lista`, `!ajuda web`).
* **Com nome de comando (`!ajuda <comando>`):** Apresenta a **Ficha Individual de Comando**, exibindo categoria, descrição, sintaxe, parâmetros, aliases e exemplos de uso direto (ex: `!ajuda ping`, `!ajuda agy`, `!ajuda gateway`).

### 2.2 `!ping`
* **Descrição:** Calcula e exibe a latência de comunicação WebSocket (heartbeat) entre a aplicação do bot e o Discord Gateway em milissegundos.
* **Saída esperada:** `🏓 Pong! Latência do Gateway: 42.0ms`

### 2.3 `!status`
* **Descrição:** Relatório abrangente sobre o estado de todos os componentes do sistema:
  * Versão e modelo ativo da LLM no LM Studio.
  * Quantidade de servidores conectados e latência do Gateway.
  * Total de mensagens salvas no SQLite para o usuário.
  * Hora atual do servidor com fuso horário.

### 2.4 `!hora [fuso_horario]`
* **Descrição:** Retorna a data e hora atual do servidor respeitando fusos horários IANA.
* **Padrão:** `America/Sao_Paulo`.
* **Exemplo de uso:** `!hora`, `!hora UTC`, `!hora America/New_York`.

### 2.5 `!modelo`
* **Descrição:** Especializado em [`commands/ai_commands.py`](file:///Users/rodrigomodel/antigravity/discord/commands/ai_commands.py) (Módulo Visível 10). Informa provedor ativo (LM Studio Local vs Google Gemini Cloud vs Auto), modelo, status da chave Gemini e failover.

### 2.6 `!historico`
* **Descrição:** Mostra quantas mensagens estão salvas no histórico SQLite do usuário e exibe as mensagens imediatas mais recentes formatadas em bloco seguro.

### 2.7 `!limpar`
* **Descrição:** Apaga o histórico imediato de mensagens do usuário no banco SQLite, iniciando uma nova sessão limpa de diálogo.

### 2.8 `!gateway [status|pausar|retomar|limpar]`
* **Descrição:** Telemetria e controle anti-spam do barramento de mensagens (IDEA-24). Exibe mensagens enviadas, mensagens duplicadas descartadas, estado dos circuit breakers por canal e permite pausar/retomar/limpar a fila Outbox.

### 2.9 `!agy [skills|info|status|consultar]`
* **Descrição:** Inspeção e consultas analíticas às 14 skills e agentes locais em modo Read-Only através do Antigravity Runner (IDEA-23).

---

## 3. Ferramentas da LLM (*Function Calling* em `tools/datetime_tools.py`)

| Ferramenta | Parâmetros | Descrição |
|---|---|---|
| `obter_hora_atual` | `fuso_horario: str` (default: `"America/Sao_Paulo"`) | Consulta a data e hora exatas no fuso horário informado para orientar a LLM em agendamentos ou respostas temporais. |
| `calcular_expressao` | `expressao: str` | Avalia expressões matemáticas básicas e avançadas de forma segura com `safe_dict` matemático, desativando builtins perigosos. |

---

## 4. Tratamento de Erros e Boas Práticas

1. **Permissão de Citação no Discord:** Caso o canal do Discord não possua a permissão `Read Message History`, o método `ctx.reply()` realiza fallback automático para menção simples (`@Usuario`) sem citação, prevenindo falhas HTTP 403 Forbidden.
2. **Divisão de Saída:** Todas as respostas dos comandos utilizam `dividir_mensagem(texto, limite=1900)`, garantindo que diagnósticos longos sejam divididos sem quebra de blocos Markdown ou palavras truncadas.

---

## 5. 📋 Matriz de Rastreabilidade & Aderência (Auditada em 2026-11-14)

Auditoria realizada via [`/spec-audit`](file:///Users/rodrigomodel/antigravity/.agents/skills/spec-audit/SKILL.md) com homologação do [`/review`](file:///Users/rodrigomodel/antigravity/gerencial/reviews/REV-010_auditoria_geral_e_diagnostico.md) e [`/doc_master`](file:///Users/rodrigomodel/antigravity/gerencial/auditorias/auditoria_2026-11-14_01_GERAL_E_DIAGNOSTICO.md):

| ID | Requisito da Especificação | Status | Implementação no Código | Notas de Auditoria |
| :---: | :--- | :---: | :--- | :--- |
| **REQ-01** | `!ajuda` estruturado em 2 etapas | 🟢 **Aderente** | [`system_commands.py:L40-L130`](file:///Users/rodrigomodel/antigravity/discord/commands/system_commands.py#L40-L130) | Menu de 14 blocos temáticos e navegação detalhada. |
| **REQ-02** | `!ping` (latência WebSocket do Gateway) | 🟢 **Aderente** | [`system_commands.py:L477-L487`](file:///Users/rodrigomodel/antigravity/discord/commands/system_commands.py#L477-L487) | Medição precisa em ms via `ctx.client.latency * 1000.0`. |
| **REQ-03** | `!status` (diagnóstico geral dos subsistemas) | 🟢 **Aderente** | [`system_commands.py:L542-L564`](file:///Users/rodrigomodel/antigravity/discord/commands/system_commands.py#L542-L564) | Reporta servidores, latência, total de mensagens e modelo LLM. |
| **REQ-04** | `!hora` (data e hora com fusos IANA) | 🟢 **Aderente** | [`system_commands.py:L529-L540`](file:///Users/rodrigomodel/antigravity/discord/commands/system_commands.py#L529-L540) | Consulta fuso com `obter_hora_formatada(fuso)` e padrão `America/Sao_Paulo`. |
| **REQ-05** | `!historico` e `!limpar` (gestão de sessão) | 🟢 **Aderente** | [`system_commands.py:L489-L527`](file:///Users/rodrigomodel/antigravity/discord/commands/system_commands.py#L489-L527) | `contar_mensagens`, `obter_historico` e `limpar_historico`. |
| **REQ-06** | Tool `obter_hora_atual` | 🟢 **Aderente** | [`datetime_tools.py:L15-L49`](file:///Users/rodrigomodel/antigravity/discord/tools/datetime_tools.py#L15-L49) | Function Calling tipada com `zoneinfo.ZoneInfo`. |
| **REQ-07** | Tool `calcular_expressao` | 🟢 **Aderente** | [`datetime_tools.py:L51-L97`](file:///Users/rodrigomodel/antigravity/discord/tools/datetime_tools.py#L51-L97) | Avaliação matemática segura sem builtins perigosos. |
| **REQ-08** | Divisão de mensagens e fallback de citação | 🟢 **Aderente** | [`utils.py:L70-L107`](file:///Users/rodrigomodel/antigravity/discord/utils.py#L70-L107) | `dividir_mensagem(texto, 1900)` e tratamento no `CommandContext.reply`. |
| **REQ-09** | Ficha Individual de Comando (`!ajuda <cmd>`) | 🟢 **Aderente** | [`system_commands.py:L91-L105`](file:///Users/rodrigomodel/antigravity/discord/commands/system_commands.py#L91-L105) | Manual detalhado por comando dinâmico (Código Excedente Homologado). |
| **REQ-10** | Comandos `!gateway` e `!agy` | 🟢 **Aderente** | [`system_commands.py:L687-L780`](file:///Users/rodrigomodel/antigravity/discord/commands/system_commands.py#L687-L780) | Controle do outbox e inspeção de skills locais (Código Excedente Homologado). |

