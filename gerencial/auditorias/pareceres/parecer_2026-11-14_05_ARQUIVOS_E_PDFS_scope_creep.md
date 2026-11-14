# Parecer Técnico do Coder: Scope Creep em Gestão de Arquivos & PDFs (`MOD-VIS-05`)

**Data:** 2026-11-14  
**Módulo Auditado:** `discord/SPECs/modulos_visiveis/05_ARQUIVOS_E_PDFS.md`  
**Autor:** Estagiário Codificador (Junior Coder)  
**Destinatário:** Auditor Forense de Specs (`/spec-audit`) & Arquiteto-Chefe  

---

## 1. Contexto das Funcionalidades Não Documentadas na Spec Original

A especificação original `MOD-VIS-05` contemplava apenas um serviço básico de upload/download de PDFs em disco (`!pdfs` e `!enviar`). Durante a execução das Ondas 1 e 2 do Roadmap, o módulo foi promovido a um subsistema inteligente de **Leitura Aprofundada, Análise Estrutural e RAG Semântico de Documentos e Livros**, alinhando-se aos princípios da arquitetura de IA local-first.

---

## 2. Detalhamento e Justificativas Técnicas

### 2.1 Catálogo Relacional no SQLite (`user_pdf_documents` e `user_pdf_chapters`)
- **Implementação:** [`pdf_manager.py`](file:///Users/rodrigomodel/antigravity/discord/pdf_manager.py#L67-L120).
- **Racional Técnico:** Apenas salvar o PDF no disco impedia consultas estruturadas. Foram criadas tabelas relacionais com chaves estrangeiras e cascata para persistir metadados (título, autor, contagem de páginas, tamanho, sinopse) e a árvore de capítulos/seções do documento.

### 2.2 Extração Estrutural com PyMuPDF e Pré-processamento na Ingestão
- **Implementação:** [`pdf_manager.py`](file:///Users/rodrigomodel/antigravity/discord/pdf_manager.py#L273-L379).
- **Racional Técnico:** Na ingestão do arquivo pelo Discord, o bot extrai síncronamente (via `asyncio.to_thread`) o Table of Contents (TOC/Bookmarks) do PDF. Se ausente, aplica heurísticas por regex para detectar títulos de capítulos e divisões lógicas, eliminando processamento repetitivo.

### 2.3 RAG Vetorial Particionado no ChromaDB (`indexar_documento_rag`)
- **Implementação:** [`pdf_manager.py`](file:///Users/rodrigomodel/antigravity/discord/pdf_manager.py#L838-L960).
- **Racional Técnico:** Permite perguntas livres sobre livros densos. O texto é fatiado em chunks de 900 caracteres com overlap de 150 caracteres, mantendo metadados de página e capítulo. Vetorizado em lotes via modelo de embedding do LM Studio e gravado em coleções isoladas `pdf_{user}_{doc_id}` no ChromaDB.

### 2.4 Q&A Semântico com Citação Factual de Páginas (`consultar_documento_rag`)
- **Implementação:** [`pdf_manager.py`](file:///Users/rodrigomodel/antigravity/discord/pdf_manager.py#L963-L1118).
- **Racional Técnico:** O sistema recupera os top fragmentos mais aderentes, monta o contexto e instrui a LLM a citar explicitamente `[Página X]`, mitigando alucinações e garantindo rastreabilidade acadêmica. Integra-se ao TTS (Francisca) caso o usuário tenha preferência por áudio.

### 2.5 Componente Interativo no Discord UI (`PDFChapterSelectView` & `PDFChapterSelect`)
- **Implementação:** [`ui_components.py`](file:///Users/rodrigomodel/antigravity/discord/ui_components.py#L267-L347).
- **Racional Técnico:** O comando `!pdf sumario` anexa um Dropdown Select Menu nativo do Discord com os primeiros 25 capítulos. O usuário seleciona o capítulo desejado com 1 clique e recebe o resumo sem precisar digitar comandos.

### 2.6 Suíte Expandida de Function Calling (5 Novas Ferramentas)
- **Implementação:** [`tools/pdf_tools.py`](file:///Users/rodrigomodel/antigravity/discord/tools/pdf_tools.py#L109-L254).
- **Racional Técnico:** Foram adicionadas as tools `consultar_metadados_pdf`, `obter_sumario_pdf`, `resumir_capitulo_pdf`, `indexar_pdf_rag` e `consultar_conteudo_pdf_rag`. Quando acionadas pela LLM, o backend injeta diretamente os trechos documentais evitando chamadas LLM aninhadas (recursivas), prevenindo timeouts no LM Studio.

---

## 3. Recomendação do Coder
Recomenda-se enfaticamente a **Opção A (Manter no código e incorporar à SPEC)**: esta evolução transforma o bot de um simples repositório passivo de arquivos em um poderoso tutor literário e acadêmico interativo.

