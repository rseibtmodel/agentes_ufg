# Especificação do Módulo: Modo de Resposta & Voz (TTS)

**Código do Módulo:** `MOD-VIS-07`  
**Escopo:** Preferência de Resposta (Texto / Áudio / Ambos), Síntese Neural com Edge-TTS, Sanitização Textual, Detecção Natural por Chat e Entrega Multimodal  
**Arquivos de Implementação:** 
- [`tts_manager.py`](file:///Users/rodrigomodel/antigravity/discord/tts_manager.py)
- [`database.py`](file:///Users/rodrigomodel/antigravity/discord/database.py)
- [`tools/settings_tools.py`](file:///Users/rodrigomodel/antigravity/discord/tools/settings_tools.py)
- [`commands/system_commands.py`](file:///Users/rodrigomodel/antigravity/discord/commands/system_commands.py)
- [`message_handler.py`](file:///Users/rodrigomodel/antigravity/discord/message_handler.py)

---

## 1. Descrição e Finalidade

O módulo de **Modo de Resposta & Voz** concede ao usuário controle total sobre a forma como o bot se comunica no Discord. O usuário pode alternar fluidamente entre 3 modalidades operacionais:
1. **`texto` (Padrão):** Respostas escritas convencionais divididas em blocos de até 1900 caracteres, respeitando o webhook e identidade visual da persona ativa do canal.
2. **`audio`:** O bot responde exclusivamente enviando um arquivo de áudio MP3 narrado com a voz neural feminina **Francisca Brasil** (`pt-BR-FranciscaNeural`), suprimindo o texto no chat (com fallback para texto caso o serviço de síntese esteja instável).
3. **`ambos`:** O bot envia tanto o texto completo quanto o arquivo de áudio narrado simultaneamente.

---

## 2. Métodos de Configuração pelo Usuário

O usuário pode alterar o modo de três formas intuitivas e complementares:

1. **Por Comando com Prefixo (`!voz`):**
   - `!voz texto`
   - `!voz audio`
   - `!voz ambos`
   - `!voz` (sem argumentos exibe o modo atual, opções explicativas e dicas).
2. **Por Conversa Natural no Chat:**
   O `message_handler` possui um analisador de intenções (`detectar_solicitacao_modo_resposta`) que normaliza caracteres (removendo acentos via NFD) e captura frases cotidianas:
   - *"mude para áudio"*, *"responda em voz"*, *"quero apenas áudio"*, *"modo de voz"*.
   - *"responda em texto e áudio"*, *"mudar para ambos"*, *"nos dois formatos"*.
   - *"volte para texto"*, *"desativar voz"*, *"somente texto"*, *"sem áudio"*.
3. **Por Ferramenta da LLM (*Function Calling*):**
   Se o usuário formular um pedido sutil durante o diálogo, a LLM invoca autonomamente a ferramenta `configurar_modo_resposta(modo="audio")`.

---

## 3. Motor de Síntese Neural & Higienização Textual

A geração de fala opera através da biblioteca `edge-tts` com a voz `pt-BR-FranciscaNeural` ([`tts_manager.py`](file:///Users/rodrigomodel/antigravity/discord/tts_manager.py)):
1. **Higienização Textual (`limpar_texto_para_tts`):**
   - Substituição de blocos de código grandes por `(código omitido no áudio)`.
   - Conversão de links Markdown `[texto](url)` para apenas o texto descritivo.
   - Remoção de menções do Discord (`<@id>`, `<#id>`).
   - Supressão de formatação Markdown (`**`, `*`, `~~`, `` ` ``).
   - Remoção de marcadores de cabeçalho e listas (`#`, `##`, `•`, `-`, `>`).
   - Normalização de quebras de linha e espaçamentos.
   - Truncamento defensivo em ~2000 caracteres para garantir síntese rápida.
2. **Gestão Segura de Arquivos Temporários:**
   - O áudio é gravado em arquivo `.mp3` temporário gerado via `tempfile.NamedTemporaryFile`.
   - A purga do arquivo temporário é repassada ao Gateway de Mensagens via `delete_after_send=caminho_audio`, garantindo que o arquivo só seja deletado do disco após o envio completo pela rede.

---

## 4. Comandos Disponíveis (`!`)

Registrado em [`commands/system_commands.py`](file:///Users/rodrigomodel/antigravity/discord/commands/system_commands.py):

### 4.1 `!voz [modo]` (aliases: `modo`, `resposta`, `modo_resposta`, `audio`)
* **Sem Argumentos:** Exibe o modo atualmente configurado para o usuário, a voz ativa e as instruções para alteração.
* **Com Argumentos:** Altera a preferência para `texto`, `audio` ou `ambos`, gravando imediatamente no banco de dados.
* **Exemplo:** `!voz ambos`.

---

## 5. Ferramentas da LLM (*Function Calling*)

Registradas em [`tools/settings_tools.py`](file:///Users/rodrigomodel/antigravity/discord/tools/settings_tools.py):

| Ferramenta | Parâmetros | Descrição |
|---|---|---|
| `configurar_modo_resposta` | `modo: str` (`texto`, `audio`, `ambos`) | Define a preferência do usuário de forma persistente. |
| `consultar_modo_resposta` | *(sem parâmetros)* | Consulta o modo de resposta atualmente ativo no perfil do usuário. |

* Retorno canônico estruturado: `{"sucesso": bool, "dados": Any, "erro": Optional[str]}`.

---

## 6. Persistência de Preferências & Resiliência

1. **Persistência SQLite:** A preferência é armazenada na tabela `user_settings` (`user_id`, `response_mode`, `updated_at`), mantendo a escolha do usuário preservada entre reinicializações do bot.
2. **Fallback Gracioso para Texto:** Se o servidor externo do Edge-TTS retornar erro ou timeout e o usuário estiver no modo `audio`, o bot não falha silenciosamente: ele emite a resposta em texto como salvaguarda e registra o incidente nos logs.
3. **Identidade de Personas:** Em modos que envolvem texto (`texto` ou `ambos`), o envio utiliza `_despachar_resposta_persona`, assegurando que o nome do webhook e o avatar correspondam à persona temática configurada no canal.
4. **Integração com Leitura de PDFs:** Os comandos de leitura e consulta RAG de livros (`!pdf capitulo`, `!pdf perguntar`) respeitam a preferência do usuário e sintetizam a narração automaticamente se o modo for `audio` ou `ambos`.

---

## 7. 📋 Matriz de Rastreabilidade & Aderência (Auditada em 2026-11-14)

Auditoria realizada via [`/spec-audit`](file:///Users/rodrigomodel/antigravity/.agents/skills/spec-audit/SKILL.md) com homologação do [`/review`](file:///Users/rodrigomodel/antigravity/gerencial/reviews/REV-016_auditoria_modo_resposta_e_voz.md) e [`/doc_master`](file:///Users/rodrigomodel/antigravity/gerencial/auditorias/auditoria_2026-11-14_07_MODO_RESPOSTA_E_VOZ.md):

| ID | Requisito da Especificação | Status | Implementação no Código | Linhas & Símbolos Auditados |
| :--- | :--- | :---: | :--- | :--- |
| **REQ-01** | Suporte às 3 modalidades: `texto`, `audio`, `ambos` | 🟢 Aderente | [`database.py`](file:///Users/rodrigomodel/antigravity/discord/database.py#L267-L276) | `normalizar_modo_resposta()` |
| **REQ-02** | Síntese de voz neural Edge-TTS (`pt-BR-FranciscaNeural`) | 🟢 Aderente | [`tts_manager.py`](file:///Users/rodrigomodel/antigravity/discord/tts_manager.py#L64-L102) | `sintetizar_fala_edge()` |
| **REQ-03** | Sanitização de Markdown para fala fluida | 🟢 Aderente | [`tts_manager.py`](file:///Users/rodrigomodel/antigravity/discord/tts_manager.py#L21-L61) | `limpar_texto_para_tts()` |
| **REQ-04** | Detecção por linguagem natural no chat sem prefixo | 🟢 Aderente | [`message_handler.py`](file:///Users/rodrigomodel/antigravity/discord/message_handler.py#L198-L238) | `detectar_solicitacao_modo_resposta()` |
| **REQ-05** | Comando `!voz [modo]` com diagnósticos | 🟢 Aderente | [`system_commands.py`](file:///Users/rodrigomodel/antigravity/discord/commands/system_commands.py#L566-L605) | `cmd_voz` (L566-605) |
| **REQ-06** | Tool LLM `configurar_modo_resposta` | 🟢 Aderente | [`settings_tools.py`](file:///Users/rodrigomodel/antigravity/discord/tools/settings_tools.py#L17-L55) | `tool_configurar_modo_resposta` |
| **REQ-07** | Tool LLM `consultar_modo_resposta` | 🟢 Aderente | [`settings_tools.py`](file:///Users/rodrigomodel/antigravity/discord/tools/settings_tools.py#L57-L86) | `tool_consultar_modo_resposta` |
| **REQ-08** | Persistência na tabela SQLite `user_settings` | 🟢 Aderente | [`database.py`](file:///Users/rodrigomodel/antigravity/discord/database.py#L294-L329) | `definir_modo_resposta()` |
| **REQ-09** | Entrega de áudio MP3 no chat (isolado ou com texto) | 🟢 Aderente | [`message_handler.py`](file:///Users/rodrigomodel/antigravity/discord/message_handler.py#L610-L685) | Pipeline de entrega multimodal |
| **REQ-10** | Purga segura de áudio temporário via `delete_after_send` *(Scope Creep Incorporado)* | 🟢 Aderente | [`message_handler.py`](file:///Users/rodrigomodel/antigravity/discord/message_handler.py#L639-L645) | Integração com Outbox Gateway |
| **REQ-11** | Fallback gracioso para texto em falha do Edge-TTS *(Scope Creep Incorporado)* | 🟢 Aderente | [`message_handler.py`](file:///Users/rodrigomodel/antigravity/discord/message_handler.py#L646-L659) | Fallback operacional seguro |
| **REQ-12** | Respeito à identidade polimórfica de personas *(Scope Creep Incorporado)* | 🟢 Aderente | [`message_handler.py`](file:///Users/rodrigomodel/antigravity/discord/message_handler.py#L624-L632) | `_despachar_resposta_persona()` |
| **REQ-13** | Integração multimodal com leitura de PDFs e RAG *(Scope Creep Incorporado)* | 🟢 Aderente | [`knowledge_commands.py`](file:///Users/rodrigomodel/antigravity/discord/commands/knowledge_commands.py#L201-L215) | Narração automática em `!pdf` |
