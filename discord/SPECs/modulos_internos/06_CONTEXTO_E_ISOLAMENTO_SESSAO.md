# Especificação Técnica Interna: Contexto, Sessão e Concorrência de Processo

**Código do Módulo:** `MOD-INT-06`  
**Escopo:** Isolamento Assíncrono por Requisição via `ContextVar`, Singleton Lockfile de Processo e Filas Desacopladas de Anexos/Views UI  
**Arquivos de Implementação:** [`context_manager.py`](file:///Users/rodrigomodel/antigravity/discord/context_manager.py), [`chat_discord.py`](file:///Users/rodrigomodel/antigravity/discord/chat_discord.py)  

---

## 1. Isolamento Assíncrono via `ContextVar`

Em uma aplicação orientada a eventos com `asyncio`, várias mensagens de usuários distintos podem ser recebidas e processadas simultaneamente no mesmo thread de execução do event loop. Variáveis globais convencionais causariam condições de corrida (*race conditions*), fazendo com que uma requisição sobrescrevesse os dados da outra.

Para garantir isolamento estrito, o módulo `context_manager.py` utiliza o recurso nativo de Python `contextvars.ContextVar`, rastreando 5 dimensões por mensagem:

```python
_current_user_var: ContextVar[str] = ContextVar("current_user", default="default")
_current_user_id_var: ContextVar[str] = ContextVar("current_user_id", default="")
_current_channel_id_var: ContextVar[str] = ContextVar("current_channel_id", default="")
_current_guild_id_var: ContextVar[str] = ContextVar("current_guild_id", default="")
_current_channel_name_var: ContextVar[str] = ContextVar("current_channel_name", default="")
```

### 1.1 Injeção Atômica de Contexto (`set_contexto_requisicao`)
No início do pipeline (`message_handler.py`), todo o contexto da requisição é inicializado atomicamente:
```python
def set_contexto_requisicao(
    user_name: str,
    user_id: str | int,
    channel_id: str | int,
    guild_id: Optional[str | int] = None,
    channel_name: Optional[str] = None,
) -> None:
    set_current_user(user_name)
    set_current_user_id(user_id)
    set_current_channel_id(channel_id)
    set_current_guild_id(guild_id)
    set_current_channel_name(channel_name)
```

### 1.2 Vantagens do `ContextVar`:
* **Escopo Automático:** Cada tarefa assíncrona (`asyncio.Task`) criada para tratar um evento de mensagem herda e mantém uma cópia isolada das variáveis de contexto.
* **Acesso Transparente por Tools:** Qualquer ferramenta da LLM em execução (mesmo em thread secundária via `asyncio.to_thread`) pode invocar `get_current_user()`, `get_current_user_id()`, `get_current_channel_id()` ou `get_current_guild_id()` sem que esses parâmetros precisem ser explicitados na assinatura pública da tool para a IA.

---

## 2. Filas Seguras de Entrega: Anexos e Componentes UI Interativos

Quando uma ferramenta da LLM decide que um arquivo físico (como um PDF) ou um componente interativo do Discord (botões/menus `discord.ui.View`) deve ser entregue ao usuário, a função não deve tentar enviar a mensagem diretamente no Discord, pois isso quebraria a hierarquia de mensagens da LLM e causaria desordem visual.

### 2.1 Resolução Canônica de Chave de Usuário (`_resolve_user_key`)
Para evitar descompasso caso uma tool registre itens pelo nome do usuário e o handler os resgate pelo ID numérico, todas as filas utilizam resolução unificada:
```python
def _resolve_user_key(user: Optional[str | int] = None) -> str:
    if user is not None and str(user).strip():
        return str(user).strip()
    user_id = get_current_user_id()
    if user_id:
        return user_id
    return get_current_user() or "default"
```

### 2.2 Fila de Arquivos Anexos Pendentes
1. **Registro:** A tool chama `add_pending_file(caminho_pdf)`.
2. **Armazenamento:** O arquivo é adicionado a `_pending_files_by_user[chave].append(path)`.
3. **Entrega:** Após a conclusão da resposta da LLM, o `message_handler` recupera os caminhos via `get_pending_files()`, verifica a existência física e anexa os arquivos no Discord.
4. **Limpeza Garantida:** No bloco `finally:` de `processar_mensagem`, executa-se compulsoriamente `clear_pending_files(user)`.

### 2.3 Fila de Views Interativas (`discord.ui.View`) — IDEA-08
Permite o agendamento de botões de confirmação, selects ou modais dinâmicos:
1. **Registro:** A tool ou comando chama `add_pending_view(view)`.
2. **Armazenamento:** Registrado em `_pending_views_by_user[chave].append(view)`.
3. **Entrega & Limpeza:** O Gateway despacha a mensagem com `view=views_pendentes[0]` e limpa a fila com `clear_pending_views(user)` no bloco `finally:`.

---

## 3. Prevenção de Instâncias Concorrentes (Singleton Lockfile)

### 3.1 O Problema da Duplicação de Mensagens no Discord
Quando dois processos Python iniciam o bot utilizando o mesmo `DISCORD_TOKEN`, o Discord Gateway aceita ambas as conexões WebSocket e envia cada evento de mensagem recebida para as duas instâncias. Ambas as instâncias processam a mensagem, invocam a LLM e respondem no canal, resultando em **respostas duplicadas para o usuário**.

### 3.2 A Solução: Lock Atômico no Kernel com `fcntl.flock`
Em `chat_discord.py`, a função `adquirir_lock_instancia_unica()` cria e trava o arquivo `discord/.bot.lock` antes de iniciar a conexão do Discord:

```python
LOCK_FILE_PATH = Path(__file__).resolve().parent / ".bot.lock"
_lock_file_handle = None

def adquirir_lock_instancia_unica() -> bool:
    global _lock_file_handle
    try:
        _lock_file_handle = open(LOCK_FILE_PATH, "a+")
        # Tenta obter lock exclusivo não-bloqueante no arquivo
        fcntl.flock(_lock_file_handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        _lock_file_handle.seek(0)
        _lock_file_handle.truncate()
        _lock_file_handle.write(f"{os.getpid()}\n")
        _lock_file_handle.flush()
        return True
    except (BlockingIOError, IOError):
        # Outro processo já possui o lock ativo
        return False
```

* **Comportamento da 2ª Instância:** Se outra instância tentar rodar (seja no terminal ou em segundo plano), a chamada `fcntl.flock` levanta imediatamente `BlockingIOError`. O bot exibe um aviso claro no console com o PID do processo em execução e finaliza a execução com código 0, **impedindo qualquer duplicidade de mensagens**.
* **Liberação Automática:** Caso o processo primário sofra encerramento forçado (ex: SIGTERM, SIGKILL ou queda de energia), o kernel do sistema operacional fecha o descritor de arquivo e **remove a trava automaticamente**, eliminando arquivos de lock órfãos (*stale locks*).

---

## 4. 📋 Matriz de Rastreabilidade & Aderência (Auditada em 2026-11-14)

Auditoria realizada via [`/spec-audit`](file:///Users/rodrigomodel/antigravity/.agents/skills/spec-audit/SKILL.md) com homologação do [`/review`](file:///Users/rodrigomodel/antigravity/gerencial/reviews/REV-008_auditoria_contexto_sessao_lock.md) e [`/doc_master`](file:///Users/rodrigomodel/antigravity/gerencial/auditorias/auditoria_2026-11-14_06_CONTEXTO_E_ISOLAMENTO_SESSAO.md):

| ID | Requisito da Especificação | Status | Implementação no Código | Notas de Auditoria |
| :---: | :--- | :---: | :--- | :--- |
| **REQ-01** | Isolamento assíncrono via `ContextVar` | 🟢 **Aderente** | [`context_manager.py:L16-L19`](file:///Users/rodrigomodel/antigravity/discord/context_manager.py#L16-L19) | Rastreia `user`, `user_id` e `channel_id` com escopo isolado por Task. |
| **REQ-02** | Acesso transparente por tools em threads | 🟢 **Aderente** | [`context_manager.py:L43-L56`](file:///Users/rodrigomodel/antigravity/discord/context_manager.py#L43-L56) | Getters funcionam dentro de `asyncio.to_thread` sem poluir schemas da IA. |
| **REQ-03** | Fila segura de entrega de arquivos anexos | 🟢 **Aderente** | [`context_manager.py:L103-L120`](file:///Users/rodrigomodel/antigravity/discord/context_manager.py#L103-L120) | `add_pending_file`, `get_pending_files` e limpeza no `finally:` do gateway. |
| **REQ-04** | Lock atômico de processo singleton no kernel | 🟢 **Aderente** | [`chat_discord.py:L49-L65`](file:///Users/rodrigomodel/antigravity/discord/chat_discord.py#L49-L65) | `fcntl.flock(LOCK_EX \| LOCK_NB)` em `.bot.lock` impede instâncias concorrentes. |
| **REQ-05** | Prevenção de duplicação e liberação de lock | 🟢 **Aderente** | [`chat_discord.py:L66-L78`](file:///Users/rodrigomodel/antigravity/discord/chat_discord.py#L66-L78) | Encerra 2ª instância com log defensivo; kernel libera trava em crash. |
| **REQ-06** | Injeção atômica de contexto (`guild` e `channel`) | 🟢 **Aderente** | [`context_manager.py:L20-L21,L68-L101`](file:///Users/rodrigomodel/antigravity/discord/context_manager.py#L20-L21) | `set_contexto_requisicao` unifica entrada (Código Excedente Homologado). |
| **REQ-07** | Fila de views interativas (`discord.ui.View`) | 🟢 **Aderente** | [`context_manager.py:L25,L122-L138`](file:///Users/rodrigomodel/antigravity/discord/context_manager.py#L25) | Desacopla botões/modais de tools para despacho no Gateway (IDEA-08). |
| **REQ-08** | Resolução canônica de chave de isolamento | 🟢 **Aderente** | [`context_manager.py:L28-L36`](file:///Users/rodrigomodel/antigravity/discord/context_manager.py#L28-L36) | `_resolve_user_key` prioriza `user_id` numérico (Código Excedente Homologado). |

