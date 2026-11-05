# Especificação de Ideia de Módulo: Pesquisa na Web em Tempo Real (Web Search & Browsing)

**Código da Proposta:** `IDEA-01`  
**Status:** ✅ ENTREGUE / EM PRODUÇÃO (`v2.8.0`)  
**Módulo Oficial:** [11_PESQUISA_WEB_E_BROWSING.md](file:///Users/rodrigomodel/antigravity/discord/SPECs/modulos_visiveis/11_PESQUISA_WEB_E_BROWSING.md)  
**Impacto:** Permite à LLM e aos usuários acessar fatos atualizados, notícias, cotações e resumos de artigos em tempo real via DuckDuckGo, Tavily e scraping limpo.  

---

## 1. Justificativa e Motivação

Modelos de linguagem locais no LM Studio possuem dados congelados na data de corte do seu treinamento (*knowledge cutoff*). Quando o usuário pergunta sobre notícias do dia, cotações financeiras, resultados esportivos ou documentações de bibliotecas recém-lançadas, o modelo não consegue responder com precisão factual sem acesso à web.

Este módulo propõe a criação de ferramentas de busca e extração de conteúdo na internet, integradas ao pipeline assíncrono do bot.

---

## 2. Arquitetura Proposta

```mermaid
flowchart LR
    UserQuery[Usuário: 'Qual a previsão do tempo para amanhã em SP?'] --> LLM[LM Studio]
    LLM --> ToolCall[Tool: buscar_na_web(query='previsao tempo sao paulo')]
    ToolCall --> ProviderSelector{Provedor de Busca}
    ProviderSelector -->|Opção 1| TavilyAPI[Tavily Search API - Otimizado para IA]
    ProviderSelector -->|Opção 2| DuckDuckGo[DuckDuckGo Search - Gratuito]
    ProviderSelector -->|Opção 3| SearXNG[SearXNG Local - Self-Hosted Privado]
    
    TavilyAPI & DuckDuckGo & SearXNG --> ExtractText[Extrai Títulos, Snippets e URLs]
    ExtractText --> RankFilter[Seleciona os 3 resultados mais relevantes]
    RankFilter --> ToolResult[Retorna texto estruturado para a LLM]
    ToolResult --> FinalLLM[LLM sintetiza a resposta com fontes]
    FinalLLM --> DiscordOutput[Envia no Discord com Links Citados]
```

---

## 3. Especificação das Ferramentas da LLM

### 3.1 Tool: `buscar_na_web(query: str, max_resultados: int = 3)`
* **Descrição:** Executa uma busca na internet para encontrar informações atualizadas sobre qualquer tema.
* **Retorno:** Lista de snippets contendo título, resumo do conteúdo e URL da fonte.

### 3.2 Tool: `ler_pagina_web(url: str)`
* **Descrição:** Faz a raspagem (*scraping*) limpa do corpo textual de uma página ou artigo específico através de bibliotecas como `trafilatura` ou `BeautifulSoup`, convertendo o conteúdo para Markdown enxuto para análise pela LLM.

---

## 4. Tecnologias Recomendadas
* **Bibliotecas Python:** `duckduckgo-search` (gratuito e sem API key), `httpx` (requisições assíncronas), `trafilatura` (extração de texto sem poluição de tags HTML).
* **Configuração em `.env`:**
  ```ini
  WEB_SEARCH_ENABLED=true
  WEB_SEARCH_PROVIDER=duckduckgo # ou tavily
  TAVILY_API_KEY=tvly-xxxx
  ```
