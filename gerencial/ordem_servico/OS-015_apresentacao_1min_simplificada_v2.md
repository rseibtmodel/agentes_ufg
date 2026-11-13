# OS-015: Apresentação de 1 Minuto Simplificada (Versão 2)

**Data:** 13 de Novembro de 2026  
**Status:** Em Execução / Concluída  
**Autor:** Agent Manager (`/gerente`)  
**Especialista Convocado:** Deck Master (`/deck_master`)  
**Alvo:** `gerencial/apresentacoes/`  

---

## 👑 Diretriz do Arquiteto-Chefe [Usuário]
Criar a Versão 2 (v2) da apresentação e script de 1 minuto baseando-se no arquivo `script_apresentacao_1min_arquitetura.md`. A nova versão deve utilizar menos termos técnicos pesados, tornando a linguagem mais simples, didática e objetiva, mantendo a versão 1 intacta e gerando os novos arquivos com identificador v2.

---

## 📌 Racional da Tradução Técnica para Linguagem Clara

| Termo Técnico Pesado (v1) | Tradução Simples & Direta (v2) | Benefício de Comunicação |
| :--- | :--- | :--- |
| **Fast-Path vs Slow-Path / Parcimônia** | **O Rápido vs O Inteligente** | Qualquer pessoa entende que tarefas simples não precisam gastar inteligência artificial cara. |
| **System Prompt Único / Jinja Templates** | **Instruções em 4 Camadas Organizadas** | Mostra organização lógica sem se prender a sintaxe Jinja de tokenização. |
| **Dynamic Tool RAG por Cosseno / Embedding** | **Caixa de Ferramentas sob Medida** | Explica a metáfora de entregar apenas as 3 ou 4 ferramentas certas em vez das 46 de uma vez. |
| **ContextVars / Leaky Bucket / Deduplicação** | **Privacidade Total e Entrega sem Travamentos** | Destaca o valor para o usuário: dados isolados e chat fluido sem bloqueios. |

---

## 📦 Artefatos Gerados
- Script v2: `gerencial/apresentacoes/script_apresentacao_1min_arquitetura_v2.md`
- Deck Marp v2: `gerencial/apresentacoes/20261113_pitch_1min_arquitetura_e_prompt_v2.md`
- HTML Interativo v2: `gerencial/apresentacoes/apresentacao_pitch_1min_v2.html`
- Deck Marp v2 com Background (Todos os Slides): `gerencial/apresentacoes/20261113_pitch_1min_arquitetura_e_prompt_v2_bg.md`
- HTML Interativo v2 com Backgrounds: `gerencial/apresentacoes/apresentacao_pitch_1min_v2_bg.html`
- Deck Marp v3 (Animações): `gerencial/apresentacoes/20261113_pitch_1min_arquitetura_e_prompt_v3.md`
- HTML Interativo v3 (Canvas 60FPS em tempo real): `gerencial/apresentacoes/apresentacao_pitch_1min_v3.html`
- Ativos Visuais Integrados (`assets/`):
  * Slide 1: `central_de_ajuda_bot.jpg` (Central de Ajuda Discord com 34 comandos diretos)
  * Slide 2: `pipeline_4_camadas_prompt.jpg` (Pipeline isométrico 3D em 4 camadas de prompt)
  * Slide 3: `tool_rag_selecao_dinamica.jpg` (Varredura semântica vetorial isolando 3 de 46 ferramentas)
  * Slide 4: `concorrencia_isolada_resiliencia.jpg` (Concorrência isolada com ContextVars e fila Leaky Bucket)

