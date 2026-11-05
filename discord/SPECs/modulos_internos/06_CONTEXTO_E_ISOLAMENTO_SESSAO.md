# Especificação Técnica Interna: Contexto, Sessão e Concorrência de Processo

**Código do Módulo:** `MOD-INT-06`  
**Escopo:** Isolamento Assíncrono por Requisição via `ContextVar`, Singleton Lockfile de Processo e Fila de Anexos  
**Arquivos de Implementação:** [`context_manager.py`](file:///Users/rodrigomodel/antigravity/discord/context_manager.py), [`chat_discord.py`](file:///Users/rodrigomodel/antigravity/discord/chat_discord.py)  

---

## 1. Isolamento Assíncrono via `ContextVar`

Em uma aplicação orientada a eventos com `asyncio`, várias mensagens de usuários distintos podem ser recebidas e processadas simultaneamente no mesmo thread de execução do event loop. Variáveis globais convencionais causariam condições de corrida (*race conditions*), fazendo com que uma requisição sobrescrevesse os dados da outra.

Para garantir isolamento estrito, o módulo `context_manager.py` utiliza o recurso nativo de Python `contextvars.ContextVar`:

```python
_current_user_var: ContextVar[str] = ContextVar("current_user", default="default")
_current_user_id_var: ContextVar[str] = ContextVar("current_user_id", default="")
_current_channel_id_var: ContextVar[str] = ContextVar("current_channel_id", default="")
```

### Vantagens do `ContextVar`:
* **Escopo Automático:** Cada tarefa assíncrona (`asyncio.Task`) criada para tratar um evento de mensagem herda e mantém uma cópia isolada das variáveis de contexto.
* **Acesso Transparente por Tools:** Qualquer ferramenta da LLM em execução (mesmo em thread secundária via `asyncio.to_thread`) pode invocar `get_current_user()` ou `get_current_user_id()` sem que esses parâmetros precisem ser explicitados na assinatura pública da tool para a IA.

---

## 2. Fila Segura de Entrega de Arquivos Anexos

Quando uma ferramenta da LLM decide que um arquivo físico (como um PDF) deve ser entregue ao usuário, a função não deve tentar enviar a mensagem diretamente no Discord, pois isso quebraria a hierarquia de mensagens da LLM e poderia causar concorrência de digitação.

### 2.1 Ciclo de Vida dos Arquivos Pendentes
1. **Registro:** A tool chama `add_pending_file(caminho_pdf)`.
2. **Armazenamento:** O arquivo é adicionado a uma fila em memória particionada por usuário: `_pending_files_by_user[usuario].append(path)`.
3. **Entrega:** Após a conclusão da resposta da LLM, o `message_handler` recupera os caminhos via `get_pending_files()`, verifica a existência física e anexa os arquivos no Discord.
4. **Limpeza Garantida:** No bloco `finally:` de `processar_mensagem`, executa-se obrigatoriamente `clear_pending_files(user_name)`, garantindo que filas antigas não transbordem para interações futuras.

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
