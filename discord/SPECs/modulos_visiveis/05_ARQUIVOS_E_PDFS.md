# Especificação do Módulo: Gestão de Arquivos & PDFs

**Código do Módulo:** `MOD-VIS-05`  
**Escopo:** Armazenamento Isolado por Usuário, Ingestão de Anexos PDF e Entrega Sob Demanda  
**Arquivos de Implementação:** [`pdf_manager.py`](file:///Users/rodrigomodel/antigravity/discord/pdf_manager.py), [`tools/pdf_tools.py`](file:///Users/rodrigomodel/antigravity/discord/tools/pdf_tools.py)  

---

## 1. Descrição e Finalidade

O módulo de **Arquivos & PDFs** provê um diretório seguro de armazenamento pessoal para cada usuário no Discord (`discord/pdf/{user}/`). Quando um usuário envia um documento PDF no canal ou por mensagem direta, o bot faz o download automático, calcula metadados (tamanho, nome seguro) e o disponibiliza para consulta ou reenvio futuro pela LLM.

---

## 2. Isolamento de Diretórios e Sanitização

Para prevenir vazamento de dados entre usuários ou ataques de travessia de diretório (*Path Traversal*):
1. **Nome Sanitizado:** O nome de usuário do Discord é sanitizado através de `re.sub(r"[^a-zA-Z0-9_\-]", "_", user_name)`.
2. **Caminho Particionado:** Cada usuário tem seu diretório exclusivo: `discord/pdf/{sanitized_user}/`.
3. **Prevenção de Sobrescrita:** Ao salvar arquivos com o mesmo nome, o sistema adiciona um contador incremental `(1)`, `(2)`, preservando versões anteriores.

---

## 3. Comandos Disponíveis (`!`)

### 3.1 `!pdfs`
* **Descrição:** Lista todos os documentos PDF atualmente salvos na pasta pessoal do usuário, com nomes e tamanhos formatados (KB/MB).

### 3.2 `!enviar <nome_ou_termo>`
* **Descrição:** Localiza um PDF da pasta do usuário por nome exato ou termo aproximado e o anexa diretamente no Discord para download.
* **Exemplo:** `!enviar relatorio` ou `!enviar fatura_outubro.pdf`.

---

## 4. Ferramentas da LLM (*Function Calling*)

| Ferramenta | Parâmetros | Descrição |
|---|---|---|
| `listar_meus_pdfs` | *(sem parâmetros)* | Retorna à LLM a lista dos arquivos PDF salvos na pasta do usuário para que ela possa responder sobre quais documentos estão disponíveis. |
| `disponibilizar_pdf_usuario` | `nome_arquivo_ou_termo: str` | Localiza o PDF na pasta do usuário e registra na fila de anexos pendentes (`context_manager.add_pending_file`) para que o bot envie o arquivo físico como anexo na resposta. |

---

## 5. Fallback Offline sem LLM

Se o servidor LM Studio estiver offline e o usuário enviar uma mensagem como *"quais pdfs eu tenho?"* ou *"me manda o pdf do contrato"*, o `message_handler` intercepta a mensagem localmente e realiza o atendimento direto utilizando o `pdf_manager`, devolvendo a lista ou o anexo solicitado mesmo sem a inteligência artificial ativa.
