# Especificação do Módulo: Geral & Diagnóstico

**Código do Módulo:** `MOD-VIS-01`  
**Escopo:** Comandos de Controle, Diagnóstico de Conexão, Sessão e Central de Ajuda em 2 Etapas  
**Arquivos de Implementação:** [`commands/builtins.py`](file:///Users/rodrigomodel/antigravity/discord/commands/builtins.py), [`utils.py`](file:///Users/rodrigomodel/antigravity/discord/utils.py)  

---

## 1. Descrição e Finalidade

O módulo **Geral & Diagnóstico** fornece ao usuário e ao administrador do bot ferramentas essenciais para verificação da saúde operacional do sistema, latência de rede com a API do Discord, conectividade com o LM Studio local e com os bancos de dados (SQLite e ChromaDB), além de prover uma **Central de Ajuda estruturada em duas etapas** para evitar estouro do limite de caracteres do Discord.

---

## 2. Comandos Disponíveis (`!`)

### 2.1 `!ajuda [modulo]`
Central interativa de auxílio ao usuário:
* **Sem argumentos (`!ajuda`):** Apresenta o **Menu de 1ª Etapa**, listando os grandes blocos temáticos disponíveis no bot (`geral`, `agenda`, `lista`, `lembrete`, `pdf`, `memoria`, `voz`) com um resumo executivo de cada um.
* **Com argumento (`!ajuda <modulo>`):** Apresenta o **Menu de 2ª Etapa**, exibindo os comandos detalhados, sintaxes exatas, parâmetros aceitos e exemplos práticos para o módulo solicitado.
  * *Exemplos:* `!ajuda agenda`, `!ajuda lista`, `!ajuda lembrete`.

### 2.2 `!ping`
* **Descrição:** Calcula e exibe a latência de comunicação WebSocket (heartbeat) entre a aplicação do bot e o Discord Gateway em milissegundos.
* **Saída esperada:** `🏓 Pong! Latência do WebSocket: 42ms`

### 2.3 `!status`
* **Descrição:** Relatório abrangente sobre o estado de todos os componentes do sistema:
  * Versão e modelo ativo da LLM no LM Studio.
  * Modelo e URL do endpoint de embeddings.
  * Quantidade de mensagens salvas no SQLite para o usuário.
  * Quantidade de documentos indexados no ChromaDB do usuário.
  * Status da autenticação com o Google Calendar.
  * Modo de resposta configurado (`texto`, `audio`, `ambos`).
  * Total de ferramentas e comandos registrados em memória.

### 2.4 `!hora [fuso_horario]`
* **Descrição:** Retorna a data e hora atual do servidor respeitando fusos horários IANA.
* **Padrão:** `America/Sao_Paulo`.
* **Exemplo de uso:** `!hora`, `!hora UTC`, `!hora America/New_York`.

### 2.5 `!modelo`
* **Descrição:** Informa o nome do modelo de linguagem em uso, parâmetros de temperatura, timeout e endereço base do LM Studio.

### 2.6 `!historico`
* **Descrição:** Mostra quantas mensagens estão salvas no histórico SQLite do usuário e exibe as mensagens imediatas mais recentes formatadas em bloco seguro.

### 2.7 `!limpar`
* **Descrição:** Apaga o histórico imediato de mensagens do usuário no banco SQLite, iniciando uma nova sessão limpa de diálogo.

---

## 3. Ferramentas da LLM (*Function Calling*)

| Ferramenta | Parâmetros | Descrição |
|---|---|---|
| `obter_hora_atual` | `fuso_horario: str` (default: `"America/Sao_Paulo"`) | Consulta a data e hora exatas no fuso horário informado para orientar a LLM em agendamentos ou respostas temporais. |
| `calcular_expressao` | `expressao: str` | Avalia expressões matemáticas básicas de forma segura, sem uso de `eval()` inseguro. |

---

## 4. Tratamento de Erros e Boas Práticas

1. **Permissão de Citação no Discord:** Caso o canal do Discord não possua a permissão `Read Message History`, o método `ctx.reply()` realiza fallback automático para menção simples (`@Usuario`) sem citação, prevenindo falhas HTTP 403 Forbidden.
2. **Divisão de Saída:** Todas as respostas dos comandos utilizam `dividir_mensagem(texto, limite=1900)`, garantindo que diagnósticos longos sejam divididos sem quebra de blocos Markdown ou palavras truncadas.
