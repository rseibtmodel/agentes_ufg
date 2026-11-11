# ⏱️ Script de Apresentação de 1 Minuto (Segmento Integrado)
## Bloco Temático: Roteamento de Intenções & Engenharia de Prompt

> **Contexto de Apresentação:** Este pitch é um **módulo técnico intermediário** de 60 segundos inserido dentro de uma apresentação maior (há apresentadores antes e apresentadores depois).  
> **Diretriz de Oratória:** **Zero saudações iniciais** ("olá a todos/professor") e **zero despedidas finais** ("muito obrigado/dúvidas"). A fala entra direto no ponto técnico e entrega o bastão de forma fluida para o próximo colega.

---

## 🎯 1. Mapa dos 4 Slides do Bloco

| Slide | Foco Temático do Segmento | Duração Estimada |
| :---: | :--- | :---: |
| **Slide 1** | **Roteamento de Intenções: Fast-Path vs Slow-Path** *(Parcimônia Operacional)* | `00s - 15s` |
| **Slide 2** | **Estratificação Hierárquica do System Prompt Único** *(Jinja & Camadas)* | `15s - 30s` |
| **Slide 3** | **Dynamic Tool RAG por Similaridade de Cosseno** *(Poda de 80% dos Tokens)* | `30s - 45s` |
| **Slide 4** | **Isolamento Concorrente com ContextVars & Outbox** *(Handoff Técnico)* | `45s - 60s` |

---

## 🎙️ 2. Roteiro de Fala Palavra-por-Palavra (60 Segundos Cravados)
> **Métrica:** 148 palavras faladas em ritmo seguro, articulado e direto (~2.4 palavras/segundo).

---

### `[00:00 - 00:15]` • Slide 1: Roteamento de Intenções: Fast-Path vs Slow-Path
*(Projetar Slide 1)*
> *"Entrando agora no núcleo de roteamento e decisão cognitiva da arquitetura: nossa primeira regra de engenharia de prompt foi a parcimônia. Comandos determinísticos com prefixo entram no Fast-Path e respondem em menos de 50 milissegundos sem acionar LLM, reservando a inferência neural exclusivamente para consultas abertas."*

### `[00:15 - 00:30]` • Slide 2: Estratificação Hierárquica do System Prompt Único
*(Avançar para Slide 2)*
> *"Quando o Slow-Path é ativado, montamos um System Prompt único em quatro camadas hierárquicas — do núcleo inviolável e persona do canal até o RAG de notas e memórias de longo prazo. Tudo é consolidado no índice zero para compatibilidade estrita com chat templates Jinja de modelos locais."*

### `[00:30 - 00:45]` • Slide 3: Dynamic Tool RAG por Similaridade de Cosseno
*(Avançar para Slide 3)*
> *"Para viabilizar 46 ferramentas sem explodir a janela de contexto, implementamos o Dynamic Tool RAG: calculamos a similaridade de cosseno entre a intenção do usuário e as tools, injetando apenas o Top-K de três a cinco ferramentas. Isso poupa 80% dos tokens e praticamente aniquila alucinações de schema."*

### `[00:45 - 01:00]` • Slide 4: Isolamento Concorrente & Ciclo de Execução
*(Avançar para Slide 4)*
> *"Por fim, toda a execução é blindada por ContextVars para impedir contaminação cruzada de prompts entre canais concorrentes, enquanto o Outbox Gateway com Leaky Bucket garante despacho seguro e sem rate-limits. Com essa esteira cognitiva consolidada, passo a palavra para o próximo bloco da apresentação."*

---

## 💡 Dicas de Transição para o Apresentador
1. **Entrada Natural:** Quando o apresentador anterior terminar (por exemplo, falando sobre o Discord Gateway ou sobre os dados brutos), você engata imediatamente: *"Entrando agora no núcleo de roteamento..."*.
2. **Saída sem Vácuo:** Ao terminar o Slide 4, use a frase final como deixa combinada: *"Passo a palavra para o [Nome do Colega]..."* para que a troca seja imperceptível e profissional.
