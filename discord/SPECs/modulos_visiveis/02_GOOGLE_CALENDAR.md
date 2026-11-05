# Especificação do Módulo: Google Calendar

**Código do Módulo:** `MOD-VIS-02`  
**Escopo:** Gestão de Compromissos, Agendamento e Integração OAuth2 com a API Google Calendar v3  
**Arquivos de Implementação:** [`google_calendar.py`](file:///Users/rodrigomodel/antigravity/discord/google_calendar.py), [`auth_calendar.py`](file:///Users/rodrigomodel/antigravity/discord/auth_calendar.py), [`tools/calendar_tools.py`](file:///Users/rodrigomodel/antigravity/discord/tools/calendar_tools.py)  

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

### 3.1 `!agenda [dias]`
* **Descrição:** Lista os próximos compromissos agendados no calendário principal do usuário.
* **Argumentos:** Número de dias futuros a consultar (padrão: 7 dias).
* **Exemplo:** `!agenda` ou `!agenda 15`.

### 3.2 `!agendar <titulo> | <inicio> | [fim_ou_duracao] | [descricao]`
* **Descrição:** Cria um novo evento no Google Calendar.
* **Formatos de data/hora aceitos:** `YYYY-MM-DD HH:MM`, `DD/MM/YYYY HH:MM` ou apenas `HH:MM` (para o dia atual).
* **Exemplo:** `!agendar Reunião de Alinhamento | 19/10/2026 15:00 | 1h | Discutir roadmap do bot`

### 3.3 `!desmarcar <id_ou_termo>`
* **Descrição:** Localiza e exclui um evento pelo seu identificador único do Google Calendar ou pelo termo presente no título do evento.
* **Exemplo:** `!desmarcar Reunião de Alinhamento`.

---

## 4. Ferramentas da LLM (*Function Calling*)

| Ferramenta | Parâmetros | Descrição |
|---|---|---|
| `listar_agenda_google` | `dias_a_frente: int` (default: 7), `max_resultados: int` (default: 10) | Consulta os próximos compromissos para a LLM informar a agenda ao usuário. |
| `adicionar_evento_google` | `titulo: str`, `inicio_iso: str`, `fim_iso: str`, `descricao: str`, `local: str` | Registra um novo evento com data/hora em formato ISO 8601 no fuso local. |
| `remover_evento_google` | `evento_id_ou_titulo: str` | Cancela ou apaga um compromisso da agenda do Google. |

---

## 5. Resiliência e Tratamento de Erros

* **Credenciais Ausentes:** Se o arquivo `credentials.json` ou `token.json` não existirem, os comandos e tools retornam um alerta amigável com o passo a passo para execução do script `auth_calendar.py`.
* **Fuso Horário:** Por padrão, todos os cálculos e conversões utilizam o fuso horário configurado na variável de ambiente `CALENDAR_DEFAULT_TIMEZONE` (default: `America/Sao_Paulo`).
