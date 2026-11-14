# Especificação do Módulo: Gestão de Arquivos, Livros & RAG de PDFs

**Código do Módulo:** `MOD-VIS-05`  
**Escopo:** Armazenamento Isolado por Usuário, Extração Estrutural de Livros com PyMuPDF, Indexação Vetorial RAG no ChromaDB, Q&A com Citação de Páginas e Navegação Interativa no Discord UI  
**Arquivos de Implementação:** 
- [`pdf_manager.py`](file:///Users/rodrigomodel/antigravity/discord/pdf_manager.py)
- [`commands/knowledge_commands.py`](file:///Users/rodrigomodel/antigravity/discord/commands/knowledge_commands.py)
- [`tools/pdf_tools.py`](file:///Users/rodrigomodel/antigravity/discord/tools/pdf_tools.py)
- [`ui_components.py`](file:///Users/rodrigomodel/antigravity/discord/ui_components.py)

---

## 1. Descrição e Finalidade

O módulo de **Arquivos & PDFs** provê um diretório seguro de armazenamento pessoal para cada usuário no Discord (`discord/pdf/{user}/`) e atua como um subsistema inteligente de leitura técnica, síntese de capítulos e RAG vetorial de alta precisão. Quando um documento PDF é enviado, o bot realiza o download, cataloga os metadados no SQLite, mapeia a estrutura de capítulos via PyMuPDF e permite fatiamento semântico com vetorização no ChromaDB, viabilizando conversações interativas com citação obrigatória de páginas.

---

## 2. Modelo de Dados no SQLite

O catálogo documental opera em cima de duas tabelas relacionais em SQLite local-first (modo WAL) com cascata:

* **Tabela `user_pdf_documents`:**
  * `id`: Chave primária autoincrement.
  * `user_id`: ID ou identificador do usuário proprietário.
  * `user_name`: Nome de exibição do usuário.
  * `filename`: Nome original do arquivo PDF (com restrição `UNIQUE(user_id, filename)`).
  * `filepath`: Caminho absoluto no disco local.
  * `title`, `author`: Metadados bibliográficos extraídos da obra.
  * `total_pages`: Contagem total de páginas.
  * `file_size_bytes`: Tamanho físico em bytes.
  * `short_summary`: Sinopse preliminar extraída das primeiras páginas.
  * `is_indexed`: Flag booleana indicando se a obra já foi vetorizada no ChromaDB.
* **Tabela `user_pdf_chapters`:**
  * `id`: Chave primária.
  * `doc_id`: Chave estrangeira referenciando `user_pdf_documents(id) ON DELETE CASCADE`.
  * `chapter_index`, `level`, `title`: Número, profundidade e título da seção.
  * `start_page`, `end_page`: Intervalo de páginas do capítulo.
  * `summary`: Cache da síntese do capítulo gerada pela LLM.

---

## 3. Isolamento de Diretórios & Defesa Anti-Traversal

1. **Sanitização de Usuário:** O diretório pessoal é normalizado via `re.sub(r"[^\w\-\.]", "_", nome).strip(" ._")`, garantindo nomes seguros em `discord/pdf/{sanitized_user}/`.
2. **Defesa Anti-Path Traversal:** Todas as buscas e aberturas de arquivos validam compulsoriamente se o caminho resolvido pertence à pasta do usuário via `candidato.resolve().is_relative_to(pasta)`.
3. **Prevenção de Conflitos:** Ingestão atômica de anexos via `attachment.save(caminho_destino)`.

---

## 4. Pipeline de Extração com PyMuPDF & RAG no ChromaDB

1. **Ingestão Estrutural:** Durante o salvamento, `_extrair_estrutura_pdf_sync` extrai o Table of Contents (TOC/Bookmarks). Caso o PDF não contenha bookmarks, aplica heurísticas regex (`Capítulo`, `Seção`, `Parte`) nas primeiras 25 páginas ou segmenta em blocos lógicos de 20 páginas.
2. **Fatiamento Semântico (*Chunking*):** Blocos de texto de 900 caracteres com overlap de 150 caracteres, identificando página e capítulo de origem.
3. **Vetorização em Lotes:** Chamada ao modelo de embeddings local no LM Studio em lotes seguros para evitar sobrecarga de GPU.
4. **Coleções Particionadas no ChromaDB:** Armazenamento na coleção dedicada `pdf_{user}_{doc_id}` com persistência em disco em `data/chroma/`.
5. **Q&A com Citação Factual:** Recuperação dos Top 4 fragmentos e instrução obrigatória para citar `[Página X]`, com suporte opcional a áudio sintetizado TTS (Francisca) para usuários com preferência multimodal.

---

## 5. Comandos Disponíveis (`!`)

Todos os comandos são registrados em [`commands/knowledge_commands.py`](file:///Users/rodrigomodel/antigravity/discord/commands/knowledge_commands.py):

### 5.1 `!pdfs` (aliases: `listar_pdfs`, `meus_pdfs`)
* **Descrição:** Lista todos os documentos PDF salvos na pasta pessoal com título, páginas, tamanho e indicador de indexação RAG (`🟢 RAG Ativo` / `⚪ Não Indexado`).
* **Exemplo:** `!pdfs`.

### 5.2 `!enviar <nome_do_arquivo>` (aliases: `baixar`, `disponibilizar`, `download`)
* **Descrição:** Localiza um PDF da pasta do usuário e anexa o arquivo físico no Discord para download imediato.
* **Exemplo:** `!enviar relatorio`.

### 5.3 `!pdf [subcomando] [arquivo] [argumentos...]` (aliases: `livro`, `livros`, `ebook`, `documento`)
* **`!pdf` ou `!pdf status`:** Lista livros e status RAG.
* **`!pdf info <arquivo>`:** Exibe a ficha catalográfica detalhada, autor, total de páginas e sinopse inicial.
* **`!pdf sumario <arquivo>`:** Exibe a árvore de capítulos mapeados e anexa a view interativa `PDFChapterSelectView`.
* **`!pdf capitulo <arquivo> <n>`:** Gera ou resgata do cache o resumo estruturado de um capítulo específico (com suporte a áudio).
* **`!pdf indexar <arquivo>`:** Executa o fatiamento e vetorização do documento no ChromaDB.
* **`!pdf perguntar <arquivo> <dúvida>`:** Realiza busca semântica no livro e responde à pergunta citando as páginas exatas.

---

## 6. Componentes Visuais Interativos do Discord UI (`PDFChapterSelectView`)

Ao executar `!pdf sumario <arquivo>`, se `DISCORD_UI_COMPONENTS_ENABLED = True`, o bot anexa um menu interativo nativo [`PDFChapterSelectView`](file:///Users/rodrigomodel/antigravity/discord/ui_components.py#L320-L347):
* **Select Menu de Capítulos:** Apresenta até 25 opções formatadas com o número do capítulo, título e página inicial (`📖 Cap. 1: Introdução — Inicia na página 1`).
* **Resumo com 1 Clique:** Ao selecionar um capítulo no dropdown, o bot gera o resumo analítico automaticamente sem necessidade de digitar novos comandos.

---

## 7. Ferramentas da LLM (*Function Calling*)

O módulo disponibiliza 7 ferramentas completas em [`tools/pdf_tools.py`](file:///Users/rodrigomodel/antigravity/discord/tools/pdf_tools.py), retornando o formato canônico `{"sucesso": bool, "dados": Any, "erro": Optional[str]}`:

| Ferramenta | Parâmetros | Descrição |
|---|---|---|
| `listar_meus_pdfs` | *(sem parâmetros)* | Retorna os PDFs salvos na pasta pessoal com tamanho e status RAG. |
| `disponibilizar_pdf_usuario` | `nome_arquivo: str` | Localiza o PDF e agenda o envio do arquivo físico como anexo via `add_pending_file`. |
| `consultar_metadados_pdf` | `arquivo: str` | Consulta ficha catalográfica, autor, páginas e sinopse da obra. |
| `obter_sumario_pdf` | `arquivo: str` | Retorna o sumário com lista de capítulos e páginas correspondentes. |
| `resumir_capitulo_pdf` | `arquivo: str`, `capitulo: str` | Retorna trecho do capítulo para síntese didática (sem chamada recursiva). |
| `indexar_pdf_rag` | `arquivo: str` | Dispara a indexação vetorial da obra no ChromaDB. |
| `consultar_conteudo_pdf_rag` | `arquivo: str`, `pergunta: str` | Realiza busca semântica e injeta os trechos com páginas para resposta com citação. |

---

## 8. Fallback Offline sem LLM

Se o servidor de IA estiver offline e o usuário solicitar arquivos por mensagens simples como *"quais pdfs eu tenho?"* ou *"me manda o pdf do contrato"*, o `message_handler` intercepta localmente e realiza o atendimento direto utilizando o `pdf_manager`, devolvendo a lista de arquivos ou o anexo solicitado.

---

## 9. 📋 Matriz de Rastreabilidade & Aderência (Auditada em 2026-11-14)

Auditoria realizada via [`/spec-audit`](file:///Users/rodrigomodel/antigravity/.agents/skills/spec-audit/SKILL.md) com homologação do [`/review`](file:///Users/rodrigomodel/antigravity/gerencial/reviews/REV-014_auditoria_arquivos_e_pdfs.md) e [`/doc_master`](file:///Users/rodrigomodel/antigravity/gerencial/auditorias/auditoria_2026-11-14_05_ARQUIVOS_E_PDFS.md):

| ID | Requisito da Especificação | Status | Implementação no Código | Linhas & Símbolos Auditados |
| :--- | :--- | :---: | :--- | :--- |
| **REQ-01** | Armazenamento isolado por usuário (`pdf/{user}/`) | 🟢 Aderente | [`pdf_manager.py`](file:///Users/rodrigomodel/antigravity/discord/pdf_manager.py#L122-L135) | `obter_pasta_usuario()` (L129-135) |
| **REQ-02** | Sanitização anti-path-traversal | 🟢 Aderente | [`pdf_manager.py`](file:///Users/rodrigomodel/antigravity/discord/pdf_manager.py#L234-L265) | `localizar_pdf_usuario()` |
| **REQ-03** | Ingestão e salvamento de anexo PDF do Discord | 🟢 Aderente | [`pdf_manager.py`](file:///Users/rodrigomodel/antigravity/discord/pdf_manager.py#L181-L197) | `salvar_anexo_pdf()` (L181-197) |
| **REQ-04** | Formatação legível de tamanho de arquivo | 🟢 Aderente | [`pdf_manager.py`](file:///Users/rodrigomodel/antigravity/discord/pdf_manager.py#L137-L145) | `formatar_tamanho()` (L137-145) |
| **REQ-05** | Comando `!pdfs` para listar arquivos e status RAG | 🟢 Aderente | [`knowledge_commands.py`](file:///Users/rodrigomodel/antigravity/discord/commands/knowledge_commands.py#L47-L78) | `cmd_pdfs` (L47-78) |
| **REQ-06** | Comando `!enviar <arquivo>` para envio de anexo | 🟢 Aderente | [`knowledge_commands.py`](file:///Users/rodrigomodel/antigravity/discord/commands/knowledge_commands.py#L80-L113) | `cmd_enviar` (L80-113) |
| **REQ-07** | Tool LLM `listar_meus_pdfs` | 🟢 Aderente | [`pdf_tools.py`](file:///Users/rodrigomodel/antigravity/discord/tools/pdf_tools.py#L24-L67) | `tool_listar_meus_pdfs` (L24-67) |
| **REQ-08** | Tool LLM `disponibilizar_pdf_usuario` | 🟢 Aderente | [`pdf_tools.py`](file:///Users/rodrigomodel/antigravity/discord/tools/pdf_tools.py#L69-L107) | `tool_disponibilizar_pdf` (L69-107) |
| **REQ-09** | Fallback Offline sem LLM no `message_handler` | 🟢 Aderente | `discord/message_handler.py` | Interceptação local de PDFs |
| **REQ-10** | Catálogo relacional SQLite: `user_pdf_documents` e `user_pdf_chapters` *(Scope Creep Incorporado)* | 🟢 Aderente | [`pdf_manager.py`](file:///Users/rodrigomodel/antigravity/discord/pdf_manager.py#L67-L120) | `init_pdf_db()` (L67-120) |
| **REQ-11** | Extração de TOC e Heurísticas PyMuPDF *(Scope Creep Incorporado)* | 🟢 Aderente | [`pdf_manager.py`](file:///Users/rodrigomodel/antigravity/discord/pdf_manager.py#L273-L379) | `_extrair_estrutura_pdf_sync()` |
| **REQ-12** | Indexação vetorial RAG no ChromaDB *(Scope Creep Incorporado)* | 🟢 Aderente | [`pdf_manager.py`](file:///Users/rodrigomodel/antigravity/discord/pdf_manager.py#L838-L960) | `indexar_documento_rag()` |
| **REQ-13** | Q&A Semântico com Citação Obrigatória de Páginas *(Scope Creep Incorporado)* | 🟢 Aderente | [`pdf_manager.py`](file:///Users/rodrigomodel/antigravity/discord/pdf_manager.py#L963-L1118) | `consultar_documento_rag()` |
| **REQ-14** | Comando unificado `!pdf` com 5 subcomandos *(Scope Creep Incorporado)* | 🟢 Aderente | [`knowledge_commands.py`](file:///Users/rodrigomodel/antigravity/discord/commands/knowledge_commands.py#L115-L282) | `cmd_pdf` (L115-282) |
| **REQ-15** | Discord UI: `PDFChapterSelectView` *(Scope Creep Incorporado)* | 🟢 Aderente | [`ui_components.py`](file:///Users/rodrigomodel/antigravity/discord/ui_components.py#L267-L347) | `PDFChapterSelectView` |
| **REQ-16** | Tool LLM `consultar_metadados_pdf` *(Scope Creep Incorporado)* | 🟢 Aderente | [`pdf_tools.py`](file:///Users/rodrigomodel/antigravity/discord/tools/pdf_tools.py#L109-L135) | `tool_consultar_metadados_pdf` |
| **REQ-17** | Tool LLM `obter_sumario_pdf` *(Scope Creep Incorporado)* | 🟢 Aderente | [`pdf_tools.py`](file:///Users/rodrigomodel/antigravity/discord/tools/pdf_tools.py#L137-L163) | `tool_obter_sumario_pdf` |
| **REQ-18** | Tool LLM `resumir_capitulo_pdf` *(Scope Creep Incorporado)* | 🟢 Aderente | [`pdf_tools.py`](file:///Users/rodrigomodel/antigravity/discord/tools/pdf_tools.py#L165-L195) | `tool_resumir_capitulo_pdf` |
| **REQ-19** | Tool LLM `indexar_pdf_rag` *(Scope Creep Incorporado)* | 🟢 Aderente | [`pdf_tools.py`](file:///Users/rodrigomodel/antigravity/discord/tools/pdf_tools.py#L197-L223) | `tool_indexar_pdf_rag` |
| **REQ-20** | Tool LLM `consultar_conteudo_pdf_rag` *(Scope Creep Incorporado)* | 🟢 Aderente | [`pdf_tools.py`](file:///Users/rodrigomodel/antigravity/discord/tools/pdf_tools.py#L225-L254) | `tool_consultar_conteudo_pdf_rag` |
