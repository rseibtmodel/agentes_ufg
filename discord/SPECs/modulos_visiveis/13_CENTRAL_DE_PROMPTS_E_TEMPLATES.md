# Especificação do Módulo: Central de Prompts e Templates de IA (Prompt Hub)

**Código do Módulo:** `MOD-VIS-13`  
**Escopo:** Catálogo, Versionamento e Execução de System Prompts e Templates Customizados  
**Arquivos de Implementação:** [`prompt_hub.py`](file:///Users/rodrigomodel/antigravity/discord/prompt_hub.py), [`database.py`](file:///Users/rodrigomodel/antigravity/discord/database.py), [`commands/builtins.py`](file:///Users/rodrigomodel/antigravity/discord/commands/builtins.py)  

---

## 1. Visão Geral e Propósito

A **Central de Prompts** provê um repositório centralizado e persistente para catalogar, versionar e aplicar instruções de sistema e personas à inteligência artificial.

### Recursos Principais:
1. **Presets Oficiais de Fábrica:**
   - `padrao`: Assistente balanceado, prestativo e bem-humorado.
   - `dev`: Tech Lead sênior, com foco em código limpo, tipagem forte e testes.
   - `direto`: Ultra-conciso, eliminando saudações e enrolações.
   - `revisor`: Revisor crítico e rigoroso de textos, lógica e arquitetura.
   - `cfo`: Consultor financeiro corporativo com foco em ROI e redução de custos.
   - `socrates`: Instrutor maiêutico que responde com perguntas para estimular o raciocínio.
   - `tributarista`: Especialista em Reforma Tributária (CBS, IBS e IS).

2. **CRUD Completo de Prompts do Usuário:**
   - Criação de novos templates com suporte a variáveis interpoladas `{variavel}`.
   - Persistência em tabela SQLite `prompt_templates`.
   - Consulta e inspeção de versões ativas.

3. **Comandos Disponíveis:**
   - `!prompts`: Lista todos os templates disponíveis (fábrica e customizados).
   - `!prompt ver <nome>`: Exibe o conteúdo completo e metadados de um template.
   - `!prompt salvar <nome> <conteudo>`: Salva ou atualiza um template pessoal.
   - `!prompt remover <nome>`: Exclui um template customizado.

4. **Ferramentas de Function Calling Registradas:**
   - `listar_templates_prompt`: Permite à IA listar os templates existentes.
   - `obter_template_prompt`: Permite à IA consultar as instruções de um template específico.
   - `salvar_template_prompt`: Permite à IA criar ou atualizar templates a pedido do usuário.
