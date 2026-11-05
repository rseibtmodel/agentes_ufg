# Especificação do Módulo: Personas e Overrides Cognitivos por Canal

**Código do Módulo:** `MOD-VIS-15`  
**Escopo:** Especialização Cognitiva de Canais, Overrides de Temperatura e Modelo LLM  
**Arquivos de Implementação:** [`persona_manager.py`](file:///Users/rodrigomodel/antigravity/discord/persona_manager.py), [`database.py`](file:///Users/rodrigomodel/antigravity/discord/database.py), [`commands/builtins.py`](file:///Users/rodrigomodel/antigravity/discord/commands/builtins.py), [`message_handler.py`](file:///Users/rodrigomodel/antigravity/discord/message_handler.py)  

---

## 1. Visão Geral e Propósito

O módulo de **Personas por Canal** permite transformar cada canal do servidor em um agente especialista com personalidade, diretrizes operacionais, temperatura e modelo de IA próprios.

### Recursos Principais:

1. **Injeção Hierárquica em Duas Camadas:**
   - **Camada 1 (Regras Nucleares):** O `SYSTEM_PROMPT` padrão do bot garante concisão, formatação adequada para Discord e bom senso.
   - **Camada 2 (Diretrizes da Persona):** Injeta instruções comportamentais e conhecimentos específicos do papel definido para aquele canal.

2. **Overrides Cognitivos por Canal:**
   - **Temperatura:** Ajuste fino de 0.0 (totalmente determinístico para código ou finanças) a 1.0 (máxima criatividade).
   - **Modelo/Provedor:** Força a execução naquele canal para `local` (LM Studio), `gemini-flash` (Google Gemini Flash) ou `gemini-pro` (Google Gemini Pro), independentemente da preferência pessoal do usuário.

3. **Integração com a Central de Prompts (Prompt Hub):**
   - Aplicação instantânea de qualquer preset de prompt com um único comando: `!persona canal aplicar cfo` ou `!persona canal aplicar dev`.

4. **Comandos Disponíveis:**
   - `!persona canal ver`: Exibe a persona ativa, prompt, temperatura e modelo do canal atual.
   - `!persona canal aplicar <preset>`: Aplica um preset ou template ao canal.
   - `!persona canal temp <0.0-1.0>`: Ajusta a temperatura da LLM no canal.
   - `!persona canal modelo <local|gemini-flash|gemini-pro>`: Define o modelo do canal.
   - `!persona canal reset`: Restaura as configurações padrão globais para o canal.

5. **Ferramentas de Function Calling:**
   - `consultar_persona_canal`: Permite à IA consultar as regras ativas no canal.
   - `configurar_persona_canal`: Permite à IA customizar o prompt, temperatura e modelo do canal.
   - `aplicar_preset_persona_canal`: Permite à IA vincular um preset existente ao canal.
