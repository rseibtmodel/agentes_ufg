# Especificação do Módulo: Google Calendar

**Código do Módulo:** `MOD-VIS-02`  
**Escopo:** Gestão de Compromissos, Agendamento e Integração OAuth2 com a API Google Calendar v3  
**Arquivos de Implementação:** [`commands/calendar_commands.py`](file:///Users/rodrigomodel/antigravity/discord/commands/calendar_commands.py), [`google_calendar.py`](file:///Users/rodrigomodel/antigravity/discord/google_calendar.py), [`auth_calendar.py`](file:///Users/rodrigomodel/antigravity/discord/auth_calendar.py), [`tools/calendar_tools.py`](file:///Users/rodrigomodel/antigravity/discord/tools/calendar_tools.py)  

---

## 1. Descrição e Finalidade

O módulo **Google Calendar** possibilita ao usuário gerenciar sua agenda pessoal diretamente pelo Discord, seja através de comandos de texto prefixados com `!` ou em linguagem natural intermediada pela LLM. O bot consegue ler os próximos compromissos, criar novos eventos (com título, data/hora de início, fim e descrição) e cancelar reuniões por ID ou busca de texto.

---

## 2. Fluxo de Autenticação OAuth 2.0

A autenticação é baseada no padrão OAuth 2.0 do Google Cloud Platform (GCP) com o escopo `https://www.googleapis.com/auth/calendar`:

1. **Credenciais da Aplicação:** O arquivo `credentials.json` (baixado do GCP Console pelo usuário) deve ser colocado na pasta `discord/`.
2. **Autorização Local (`auth_calendar.py`):**
   - O usuário executa `python3 discord/auth_calendar.py`.
   - Um servidor local temporário é aberto e a URL de consentimento do Google é exibida no terminal.
   - Após a autorização no navegador, o token de acesso e o *refresh token* são gravados em `discord/token.json`.
3. **Renovação Transparente:** Durante a execução do bot, o método `obter_servico_calendar()` verifica automaticamente se o token expirou. Se expirado, utiliza o `refresh_token` para renová-lo em segundo plano e regrava o `token.json` atualizado.

---

## 3. Comandos Disponíveis (`!`)

Todos os comandos de calendário são executados de forma assíncrona não-bloqueante via `await asyncio.to_thread(...)`, protegendo o heartbeat do Discord Gateway:

### 3.1 `!agenda [dias]`
* **Descrição:** Lista os próximos compromissos agendados no calendário principal do usuário.
* **Argumentos:** Número de dias futuros a consultar (padrão: 7 dias).
* **Exemplo:** `!agenda` ou `!agenda 15`.

### 3.2 `!agendar <titulo> | <inicio> | [fim_ou_duracao] | [descricao]`
* **Descrição:** Cria um novo evento no Google Calendar.
* **Formatos de data/hora aceitos:** `YYYY-MM-DD HH:MM`, `DD/MM/YYYY HH:MM` ou apenas `HH:MM` (para o dia atual). Se o término for omitido, assume duração padrão de 1 hora.
* **Exemplo:** `!agendar Reunião de Alinhamento | 19/10/2026 15:00 | 1h | Discutir roadmap do bot`

### 3.3 `!desmarcar <id_ou_termo>`
* **Descrição:** Localiza e exclui um evento pelo seu identificador único do Google Calendar ou pelo termo presente no título do evento.
* **Exemplo:** `!desmarcar Reunião de Alinhamento`.

---

## 4. Ferramentas da LLM (*Function Calling*)

| Ferramenta | Parâmetros | Descrição |
|---|---|---|
| `listar_agenda_google` | `dias_a_frente: int` (default: 7), `data_inicio: str` (default: `""`) | Consulta os próximos compromissos (a partir de hoje ou de uma data futura arbitrária). |
| `adicionar_evento_google` | `titulo: str`, `data_hora_inicio: str`, `data_hora_fim: str`, `descricao: str`, `localizacao: str` | Registra um novo evento com data/hora em formato ISO ou texto no fuso local. |
| `remover_evento_google` | `termo_ou_id: str` | Cancela ou apaga um compromisso da agenda do Google por nome ou ID. |

---

## 5. Resiliência e Tratamento de Erros

1. **Credenciais Ausentes:** Se o arquivo `credentials.json` ou `token.json` não existirem, os comandos e tools retornam um alerta amigável com o passo a passo para execução do script `auth_calendar.py`.
2. **Fuso Horário:** Por padrão, todos os cálculos e conversões utilizam o fuso horário configurado na variável de ambiente `CALENDAR_DEFAULT_TIMEZONE` (default: `America/Sao_Paulo`).
3. **Bloqueio Zero do Event Loop:** Como a biblioteca `google-api-python-client` realiza I/O de rede síncrono, as chamadas são delegadas obrigatoriamente a thread workers dedicados via `asyncio.to_thread`.

---

## 6. 📋 Matriz de Rastreabilidade & Aderência (Auditada em 2026-11-14)

Auditoria realizada via [`/spec-audit`](file:///Users/rodrigomodel/antigravity/.agents/skills/spec-audit/SKILL.md) com homologação do [`/review`](file:///Users/rodrigomodel/antigravity/gerencial/reviews/REV-011_auditoria_google_calendar.md) e [`/doc_master`](file:///Users/rodrigomodel/antigravity/gerencial/auditorias/auditoria_2026-11-14_02_GOOGLE_CALENDAR.md):

| ID | Requisito da Especificação | Status | Implementação no Código | Notas de Auditoria |
| :---: | :--- | :---: | :--- | :--- |
| **REQ-01** | Autenticação OAuth 2.0 e renovação de token | 🟢 **Aderente** | [`google_calendar.py:L29-L101`](file:///Users/rodrigomodel/antigravity/discord/google_calendar.py#L29-L101) | Escopo `auth/calendar`, credenciais GCP e refresh transparente. |
| **REQ-02** | Parsing flexível de datas com fuso horário | 🟢 **Aderente** | [`google_calendar.py:L103-L139`](file:///Users/rodrigomodel/antigravity/discord/google_calendar.py#L103-L139) | `_parse_data_hora` com múltiplos formatos e `zoneinfo.ZoneInfo`. |
| **REQ-03** | Comando `!agenda` | 🟢 **Aderente** | [`calendar_commands.py:L14-L46`](file:///Users/rodrigomodel/antigravity/discord/commands/calendar_commands.py#L14-L46)<br>[`google_calendar.py:L141-L211`](file:///Users/rodrigomodel/antigravity/discord/google_calendar.py#L141-L211) | Consulta `dias_a_frente` com links diretos ao Google Calendar. |
| **REQ-04** | Comando `!agendar` com validação de término | 🟢 **Aderente** | [`calendar_commands.py:L48-L82`](file:///Users/rodrigomodel/antigravity/discord/commands/calendar_commands.py#L48-L82)<br>[`google_calendar.py:L213-L280`](file:///Users/rodrigomodel/antigravity/discord/google_calendar.py#L213-L280) | Sintaxe com `\|`, duração padrão de 1h e validação `fim > inicio`. |
| **REQ-05** | Comando `!desmarcar` (por termo ou ID) | 🟢 **Aderente** | [`calendar_commands.py:L84-L105`](file:///Users/rodrigomodel/antigravity/discord/commands/calendar_commands.py#L84-L105)<br>[`google_calendar.py:L283-L359`](file:///Users/rodrigomodel/antigravity/discord/google_calendar.py#L283-L359) | Localização e cancelamento por ID ou correspondência de título. |
| **REQ-06** | Tools tipadas de Function Calling | 🟢 **Aderente** | [`calendar_tools.py:L18-L150`](file:///Users/rodrigomodel/antigravity/discord/tools/calendar_tools.py#L18-L150) | `listar_agenda_google`, `adicionar_evento_google`, `remover_evento_google`. |
| **REQ-07** | Diagnóstico amigável de credenciais | 🟢 **Aderente** | [`google_calendar.py:L33-L80`](file:///Users/rodrigomodel/antigravity/discord/google_calendar.py#L33-L80) | `verificar_status_autenticacao()` instrui uso de `auth_calendar.py`. |
| **REQ-08** | Thread offloading nos comandos assíncronos | 🟢 **Aderente** | [`calendar_commands.py:L25,L70,L99`](file:///Users/rodrigomodel/antigravity/discord/commands/calendar_commands.py#L25) | `asyncio.to_thread` em todas as chamadas de rede à API do Google. |
| **REQ-09** | Parâmetro `data_inicio` em consultas de agenda | 🟢 **Aderente** | [`google_calendar.py:L143,L156-L163`](file:///Users/rodrigomodel/antigravity/discord/google_calendar.py#L143)<br>[`calendar_tools.py:L28-L39`](file:///Users/rodrigomodel/antigravity/discord/tools/calendar_tools.py#L28) | Suporte a consultas futuras a partir de data arbitrária (Código Homologado). |

