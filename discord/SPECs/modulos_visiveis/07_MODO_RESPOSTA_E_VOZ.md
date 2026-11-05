# Especificação do Módulo: Modo de Resposta & Voz (TTS)

**Código do Módulo:** `MOD-VIS-07`  
**Escopo:** Preferência de Resposta (Texto / Áudio / Ambos), Síntese Neural com Edge-TTS e Reconhecimento por Chat  
**Arquivos de Implementação:** [`tts_manager.py`](file:///Users/rodrigomodel/antigravity/discord/tts_manager.py), [`database.py`](file:///Users/rodrigomodel/antigravity/discord/database.py), [`tools/settings_tools.py`](file:///Users/rodrigomodel/antigravity/discord/tools/settings_tools.py)  

---

## 1. Descrição e Finalidade

O módulo de **Modo de Resposta & Voz** concede ao usuário o controle total sobre a forma como o bot deve se comunicar no Discord. O usuário pode alternar entre 3 modalidades operacionais:
1. **`texto` (Padrão):** Respostas escritas convencionais divididas em blocos de até 1900 caracteres.
2. **`audio`:** O bot responde exclusivamente enviando um arquivo de áudio MP3 narrado com a voz neural feminina **Francisca Brasil** (`pt-BR-FranciscaNeural`), suprimindo o texto no chat.
3. **`ambos`:** O bot envia tanto o texto completo quanto o arquivo de áudio narrado simultaneamente.

---

## 2. Métodos de Configuração pelo Usuário

O usuário pode alterar o modo de três formas intuitivas:

1. **Por Comando com Prefixo:**
   - `!voz texto`
   - `!voz audio`
   - `!voz ambos`
   - `!voz` (sem argumentos exibe o modo atual e opções).
2. **Por Conversa Natural no Chat:**
   O `message_handler` possui um analisador de intenções (`detectar_solicitacao_modo_resposta`) que identifica frases cotidianas sem necessidade de comando formal:
   - *"mude para áudio"*, *"responda em voz"*, *"quero apenas áudio"*.
   - *"responda em texto e áudio"*, *"mudar para ambos"*, *"nos dois formatos"*.
   - *"volte para texto"*, *"desativar voz"*, *"somente texto"*.
3. **Por Ferramenta da LLM (*Function Calling*):**
   Se o usuário formular um pedido sutil como *"a partir de agora me mande tudo narrado"*, a LLM aciona a tool `configurar_modo_resposta(modo="audio")`.

---

## 3. Comandos Disponíveis (`!`)

### 3.1 `!voz [modo]`
* **Descrição:** Consulta ou define o formato de saída do assistente.
* **Valores válidos para modo:** `texto`, `audio`, `ambos`.
* **Exemplo:** `!voz ambos`.

---

## 4. Ferramentas da LLM (*Function Calling*)

| Ferramenta | Parâmetros | Descrição |
|---|---|---|
| `configurar_modo_resposta` | `modo: str` | Define a preferência do usuário entre `texto`, `audio` ou `ambos`. |
| `consultar_modo_resposta` | *(sem parâmetros)* | Consulta o modo de resposta atualmente ativo no perfil do usuário. |

---

## 5. Persistência de Preferências

A preferência é gravada na tabela `user_settings` do SQLite (`user_id`, `response_mode`, `voice_name`, `updated_at`), garantindo que a escolha do usuário seja mantida mesmo após reinicializações do bot.
