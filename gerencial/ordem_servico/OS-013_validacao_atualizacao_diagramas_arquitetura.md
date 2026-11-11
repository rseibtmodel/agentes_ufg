# OS-013: Validação e Atualização dos Diagramas de Arquitetura

**Data:** 11 de Novembro de 2026  
**Status:** Em Execução / Concluída  
**Autor:** Agent Manager (`/gerente`) com validação do Software Architect (`/architect`)  
**Alvo:** `discord/SPECs/arquitetura/`  

---

## 👑 Diretriz do Arquiteto-Chefe [Usuário]
Auditar as imagens `fluxo_processamento_mensagem.jpg` e `visao_geral_arquitetura.jpg` em `discord/SPECs/arquitetura/`, verificar a aderência com a arquitetura atual (v3.6.0), identificar novos módulos e gerar uma nova imagem atualizada caso necessário indicando a evolução do sistema.

---

## 🏛️ Parecer Técnico do Arquiteto de Software (`/architect`)

### 1. Diagnóstico de Aderência da Imagem Legada: `fluxo_processamento_mensagem.jpg`
- **O que permanece válido:**
  - Ingestão multimodal (Faster-Whisper para áudio, PyMuPDF para estrutura TOC de PDFs).
  - Isolamento de memória multinível (Notas de Tópico do Canal, Memória Semântica do Usuário no ChromaDB, Histórico Recente no SQLite WAL).
  - Montagem de System Prompt único e Roteamento Híbrido (LM Studio local vs Google Gemini Cloud).
  - Outbox Gateway com deduplicação SHA-256 e entrega particionada em blocos <= 1900 caracteres.
- **O que evoluiu no código atual (v3.6.0):**
  - **Fast-Path Desacoplado (<50ms):** Comandos com prefixo (`!`) são interceptados imediatamente pelo `CommandRegistry` e executados diretamente, contornando completamente o overhead de LLM e montagem de prompt de sistema.
  - **Pesquisa Web & Deep Research:** Inclusão de DuckDuckGo / Yahoo failover e sumarizador recursivo de páginas web integrados ao ferramental (`web_search_manager.py`).
  - **Sanitização de Badges e Chunking Anti-Spam (OS-012):** Hash SHA-256 aprimorado cobrindo títulos e descrições de embeds, com deduplicação forçada para chunks subsequentes (`idx > 0`).

---

### 2. Diagnóstico de Aderência da Imagem Legada: `visao_geral_arquitetura.jpg`
- **O que evoluiu no código atual (v3.6.0):**
  - **De 7 para 9 Camadas Arquiteturais:** A versão v3.6.0 formalizou duas novas camadas cruciais:
    1. **Camada de UI Interativa (`ui_components.py`):** Modais, Botões de Ação e Menus Seletores dinâmicos (`discord.ui.View`).
    2. **Camada de Governança Multiagente & Controle Versionado:** 15 agentes especializados (`AGENTS.md`) e controle de qualidade contínuo (`gerencial/`).
  - **Correção de Anomalias do Diagrama v3.5.0:**
    - O diagrama antigo possuía nós duplicados na Layer 4 (`SQLite WAL` e `ChromaDB Vector DB` desenhados duas vezes).
    - Erro tipográfico na Layer 5 (*"nechanism"* em vez de *"mechanism"*).
    - Ausência do Singleton Lock (`.bot.lock`).

---

## 📦 Artefatos Produzidos
1. Parecer técnico analítico no chat comparando ponto a ponto o sistema legado vs v3.6.0.
2. Nova imagem arquitetural gerada: `discord/SPECs/arquitetura/visao_geral_arquitetura_v36.jpg`.
3. Atualização do `discord/SPECs/arquitetura/README.md` documentando o histórico de versões e as novidades arquiteturais.

