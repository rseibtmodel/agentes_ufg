---
id: MOD-VIS-13
modulo: Central de Prompts e Templates de IA (Prompt Hub)
versao: 1.1.0
status: ATIVO EM PRODUÇÃO
camada: Cognitiva & Engenharia de Prompts
autores:
  - Software Architect
  - Tech Lead Reviewer
  - Junior Coder
  - Doc Master
ultima_atualizacao: 2026-11-14
---

# Módulo 13: Central de Prompts e Templates de IA (Prompt Hub)

**Versão do Módulo:** 1.1.0 (Auditado e Estabilizado no Bot v3.6.0)  
**Status Operacional:** ✅ **ATIVO EM PRODUÇÃO (100% Cobertura de Testes)**  
**Escopo:** Catálogo, Versionamento, Persistência e Execução de System Prompts e Templates Customizados (IDEA-20)  
**Arquivos de Implementação:** [`prompt_hub.py`](file:///Users/rodrigomodel/antigravity/discord/prompt_hub.py), [`commands/ai_commands.py`](file:///Users/rodrigomodel/antigravity/discord/commands/ai_commands.py), [`tools/prompt_tools.py`](file:///Users/rodrigomodel/antigravity/discord/tools/prompt_tools.py), [`persona_manager.py`](file:///Users/rodrigomodel/antigravity/discord/persona_manager.py)  

---

## 1. Visão Geral e Propósito

A **Central de Prompts (Prompt Hub)** provê um repositório centralizado, tipado e persistente para catalogar, versionar e aplicar instruções de sistema (*system prompts*), estilos cognitivos e diretrizes reutilizáveis ao assistente de inteligência artificial.

O módulo atua em três frentes complementares:
1. **Presets Oficiais de Fábrica:** 7 perfis cognitivos calibrados por domínio técnico com temperaturas específicas.
2. **Biblioteca de Templates do Usuário:** CRUD completo para criação, listagem, inspeção e exclusão de prompts pessoais.
3. **Alimentador de Personas por Canal (IDEA-26):** Fornece os templates que podem ser vinculados diretamente aos canais do Discord através de comandos ou componentes de UI.

---

## 2. Catálogo dos 7 Presets Oficiais de Fábrica

Constantes embutidas em [`discord/prompt_hub.py`](file:///Users/rodrigomodel/antigravity/discord/prompt_hub.py#L17-L102):

| Slug (`id`) | Nome do Preset | Categoria | Temp. Sugerida | Diretriz Comportamental Principal |
| :--- | :--- | :---: | :---: | :--- |
| **`padrao`** | Assistente Pessoal Padrão | `geral` | `0.7` | Equilibrado, educado, bem-humorado, prestativo e com respostas naturais e detalhadas. |
| **`dev`** | Tech Lead & Arquiteto | `programacao` | `0.3` | Focado em código limpo, tipado, assíncrono, testes e sem introduções ou saudações óbvias. |
| **`direto`** | Modo Ultra-Conciso | `produtividade` | `0.2` | Respostas telegráficas em bullet points ou no máximo 3 frases, eliminando qualquer cortesia. |
| **`revisor`** | Editor Textual Rígido | `escrita` | `0.4` | Análise estrita de gramática, coesão e estilo persuasivo com versão revisada recomendada. |
| **`cfo`** | Consultor Financeiro | `negocios` | `0.3` | Foco absoluto em ROI, custos, sustentabilidade de longo prazo, liquidez e mitigação de riscos. |
| **`socrates`** | Filósofo Maiêutico | `filosofia` | `0.7` | Não entrega respostas prontas; desafia premissas e conduz o usuário via perguntas reflexivas. |
| **`tributarista`**| Consultor CBS/IBS | `tributario` | `0.2` | Especialista em Reforma Tributária brasileira, precisão técnica contábil e impactos em alíquotas. |

> 🔒 **Blindagem de Fábrica:** Todos os presets possuem a flag `is_builtin = 1` no banco de dados. Qualquer tentativa de remoção (`remover_template`) ou sobrescrita (`salvar_template`) é bloqueada programaticamente.

---

## 3. Persistência de Dados no SQLite

Gerenciada por `init_prompt_hub_db` em `chat_memory.db`:

```sql
CREATE TABLE IF NOT EXISTS prompt_templates (
    id TEXT PRIMARY KEY,
    user_id TEXT,
    nome TEXT NOT NULL,
    descricao TEXT,
    template_text TEXT NOT NULL,
    categoria TEXT DEFAULT 'geral',
    temperatura_sugerida REAL DEFAULT 0.7,
    is_builtin INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_prompt_templates_cat ON prompt_templates(categoria);
```

### Operações do Banco
* **`init_prompt_hub_db()`**: Cria a tabela e insere/atualiza os 7 presets embutidos via `ON CONFLICT(id) DO UPDATE`.
* **`listar_templates(categoria, incluir_presets)`**: Consulta filtrada ordenada por presets oficiais primeiro, depois categoria e ID.
* **`obter_template(slug_ou_id)`**: Recupera os metadados e o texto integral do prompt.
* **`salvar_template(...)`**: Salva novo template ou atualiza existente com timestamp e temperatura validada entre `[0.0, 1.0]`.
* **`remover_template(slug)`**: Exclui template do usuário (presets oficiais protegidos).

---

## 4. Comandos de Usuário (`ai_commands.py`)

Registrados em [`discord/commands/ai_commands.py`](file:///Users/rodrigomodel/antigravity/discord/commands/ai_commands.py#L164-L261):

### 4.1 `!prompts [categoria]`
* **Aliases:** `!templates`, `!presets`
* **Descrição:** Lista todos os templates disponíveis no catálogo com distinção visual entre `🔒 Oficial` e `👤 Custom`.
* **Exemplo:** `!prompts programacao` ou `!prompts`

### 4.2 `!prompt [ver|salvar|remover]`
* **Aliases:** `!template`
* **Subcomandos:**
  - `!prompt ver <slug>` (aliases: `show`, `info`): Exibe o texto completo, categoria e temperatura do template.
  - `!prompt salvar <slug> <texto completo>` (aliases: `save`, `criar`, `add`): Cria um novo template pessoal.
  - `!prompt remover <slug>` (aliases: `del`, `delete`, `rm`): Exclui um template customizado.

---

## 5. Ferramentas da LLM (Function Calling)

Registradas em [`discord/tools/prompt_tools.py`](file:///Users/rodrigomodel/antigravity/discord/tools/prompt_tools.py#L1-L125):

1. **`listar_templates_prompt(categoria: Optional[str] = None)`**:  
   Permite à LLM inspecionar o catálogo de templates existentes com filtro de domínio.
2. **`obter_template_prompt(slug_template: str)`**:  
   Permite à LLM ler as diretrizes completas de um template específico para auto-aplicação ou consulta.
3. **`salvar_template_prompt(slug: str, nome: str, texto_prompt: str, descricao: Optional[str], categoria: str)`**:  
   Permite à IA criar ou atualizar templates a pedido do usuário em linguagem natural.

---

## 6. Integração com Personas de Canal (IDEA-26)

Os templates criados ou disponíveis na Central de Prompts atuam como predefinições que podem ser aplicadas instantaneamente a canais temáticos:
* Comando de Aplicação: `!persona canal aplicar <slug>`
* Dropdown Visual: Menu interativo `PersonaSelect` em [`ui_components.py`](file:///Users/rodrigomodel/antigravity/discord/ui_components.py#L353-L555).
* A temperatura configurada no template (`temperatura_sugerida`) é herdada automaticamente pela persona do canal durante a inferência.

---

## 7. 📋 Matriz de Rastreabilidade & Aderência (Auditada em 2026-11-14)

| Requisito / Componente | Arquivo de Implementação | Símbolos / Classes / Métodos | Linhas Auditadas | Status |
| :--- | :--- | :--- | :--- | :---: |
| **Presets Oficiais de Fábrica** | [`discord/prompt_hub.py`](file:///Users/rodrigomodel/antigravity/discord/prompt_hub.py) | `BUILTIN_PRESETS` (7 perfis) | [L16-L102](file:///Users/rodrigomodel/antigravity/discord/prompt_hub.py#L16-L102) | 🟢 Aderente |
| **DDL da Tabela SQLite & Índices** | [`discord/prompt_hub.py`](file:///Users/rodrigomodel/antigravity/discord/prompt_hub.py) | `init_prompt_hub_db`, `prompt_templates` | [L110-L157](file:///Users/rodrigomodel/antigravity/discord/prompt_hub.py#L110-L157) | 🟢 Aderente |
| **Listagem Filtrada de Templates** | [`discord/prompt_hub.py`](file:///Users/rodrigomodel/antigravity/discord/prompt_hub.py) | `listar_templates` | [L159-L193](file:///Users/rodrigomodel/antigravity/discord/prompt_hub.py#L159-L193) | 🟢 Aderente |
| **Recuperação de Template por Slug** | [`discord/prompt_hub.py`](file:///Users/rodrigomodel/antigravity/discord/prompt_hub.py) | `obter_template` | [L195-L223](file:///Users/rodrigomodel/antigravity/discord/prompt_hub.py#L195-L223) | 🟢 Aderente |
| **Criação / Atualização de Template** | [`discord/prompt_hub.py`](file:///Users/rodrigomodel/antigravity/discord/prompt_hub.py) | `salvar_template` (com proteção de built-ins) | [L225-L284](file:///Users/rodrigomodel/antigravity/discord/prompt_hub.py#L225-L284) | 🟢 Aderente |
| **Exclusão Segura de Template** | [`discord/prompt_hub.py`](file:///Users/rodrigomodel/antigravity/discord/prompt_hub.py) | `remover_template` (bloqueio para built-ins) | [L286-L310](file:///Users/rodrigomodel/antigravity/discord/prompt_hub.py#L286-L310) | 🟢 Aderente |
| **Comando CLI `!prompts`** | [`discord/commands/ai_commands.py`](file:///Users/rodrigomodel/antigravity/discord/commands/ai_commands.py) | `cmd_prompts` (aliases: `templates`, `presets`) | [L164-L191](file:///Users/rodrigomodel/antigravity/discord/commands/ai_commands.py#L164-L191) | 🟢 Aderente |
| **Comando CLI `!prompt` (ver/salvar/remover)** | [`discord/commands/ai_commands.py`](file:///Users/rodrigomodel/antigravity/discord/commands/ai_commands.py) | `cmd_prompt` | [L193-L261](file:///Users/rodrigomodel/antigravity/discord/commands/ai_commands.py#L193-L261) | 🟢 Aderente |
| **Tool Function Calling: `listar_templates_prompt`** | [`discord/tools/prompt_tools.py`](file:///Users/rodrigomodel/antigravity/discord/tools/prompt_tools.py) | `tool_listar_templates_prompt` | [L11-L35](file:///Users/rodrigomodel/antigravity/discord/tools/prompt_tools.py#L11-L35) | 🟢 Aderente |
| **Tool Function Calling: `obter_template_prompt`** | [`discord/tools/prompt_tools.py`](file:///Users/rodrigomodel/antigravity/discord/tools/prompt_tools.py) | `tool_obter_template_prompt` | [L37-L66](file:///Users/rodrigomodel/antigravity/discord/tools/prompt_tools.py#L37-L66) | 🟢 Aderente |
| **Tool Function Calling: `salvar_template_prompt`** | [`discord/tools/prompt_tools.py`](file:///Users/rodrigomodel/antigravity/discord/tools/prompt_tools.py) | `tool_salvar_template_prompt` | [L68-L125](file:///Users/rodrigomodel/antigravity/discord/tools/prompt_tools.py#L68-L125) | 🟢 Aderente |
| **Integração com Personas de Canal** | [`discord/commands/ai_commands.py`](file:///Users/rodrigomodel/antigravity/discord/commands/ai_commands.py) | Integração com `persona canal aplicar` | [L243](file:///Users/rodrigomodel/antigravity/discord/commands/ai_commands.py#L243) | 🟢 Aderente |
