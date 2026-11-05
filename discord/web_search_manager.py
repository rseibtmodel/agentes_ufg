"""
Módulo de Pesquisa na Web em Tempo Real e Web Scraping / Browsing.

Permite à LLM e aos usuários do bot acessar fatos atualizados, notícias,
cotações, previsão do tempo e documentações online em tempo real.
Suporta DuckDuckGo (gratuito e sem API key), Tavily e SearXNG.
"""

import asyncio
import logging
import re
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from config import (
    SEARXNG_URL,
    TAVILY_API_KEY,
    WEB_SEARCH_ENABLED,
    WEB_SEARCH_MAX_RESULTS,
    WEB_SEARCH_PROVIDER,
    WEB_SEARCH_TIMEOUT,
)

logger = logging.getLogger("web_search_manager")

# User-Agent realista de navegador moderno para evitar bloqueios triviais
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


class WebSearchManager:
    """Gerenciador de pesquisa na internet e extração de conteúdo de páginas web."""

    def __init__(self):
        self.enabled = WEB_SEARCH_ENABLED
        self.default_provider = WEB_SEARCH_PROVIDER
        self.max_results_default = WEB_SEARCH_MAX_RESULTS
        self.timeout = WEB_SEARCH_TIMEOUT
        self.tavily_key = TAVILY_API_KEY
        self.searxng_url = SEARXNG_URL.rstrip("/") if SEARXNG_URL else ""

    # =========================================================================
    # 1. PESQUISA NA WEB
    # =========================================================================
    async def buscar_na_web(
        self,
        query: str,
        max_resultados: Optional[int] = None,
        provedor: Optional[str] = None,
    ) -> List[Dict[str, str]]:
        """Executa uma busca na web e retorna uma lista estruturada de resultados.

        Cada item contém:
        - titulo: Título da página/artigo
        - url: Link clicável
        - resumo: Trecho de texto relevante (snippet)
        - fonte: Identificador do buscador utilizado
        """
        if not self.enabled:
            logger.warning("Pesquisa na web solicitada, mas WEB_SEARCH_ENABLED=false.")
            return []

        q = query.strip()
        if not q:
            return []

        limite = max_resultados if max_resultados and max_resultados > 0 else self.max_results_default
        prov = (provedor or self.default_provider).lower().strip()

        logger.info("Executando busca web ['%s'] via provedor '%s' (max=%d)...", q, prov, limite)

        # 1. Tentativa via Tavily se solicitado e com chave presente
        if prov == "tavily" and self.tavily_key:
            try:
                res = await self._buscar_tavily(q, limite)
                if res:
                    return res
            except Exception as e:
                logger.warning("Falha na busca Tavily (%s), caindo para DuckDuckGo: %s", prov, e)

        # 2. Tentativa via SearXNG se configurado
        if prov == "searxng" and self.searxng_url:
            try:
                res = await self._buscar_searxng(q, limite)
                if res:
                    return res
            except Exception as e:
                logger.warning("Falha na busca SearXNG, caindo para DuckDuckGo: %s", e)

        # 3. Provedor padrão robusto: DuckDuckGo (ddgs)
        try:
            return await self._buscar_duckduckgo(q, limite)
        except Exception as e:
            logger.error("Erro ao pesquisar via DuckDuckGo: %s", e)
            return []

    async def _buscar_duckduckgo(self, query: str, max_resultados: int) -> List[Dict[str, str]]:
        """Busca assíncrona via biblioteca ddgs / DuckDuckGo."""
        def _executar_ddgs():
            try:
                from ddgs import DDGS
            except ImportError:
                from duckduckgo_search import DDGS

            resultados_formatados = []
            with DDGS() as ddgs:
                # Usa text() para busca ampla e estável
                raw_results = ddgs.text(query, max_results=max_resultados)
                for item in raw_results:
                    titulo = (item.get("title") or "").strip()
                    url = (item.get("href") or item.get("link") or "").strip()
                    resumo = (item.get("body") or item.get("snippet") or "").strip()
                    if titulo and url:
                        resultados_formatados.append({
                            "titulo": titulo,
                            "url": url,
                            "resumo": resumo,
                            "fonte": "DuckDuckGo",
                        })
            return resultados_formatados

        return await asyncio.wait_for(
            asyncio.to_thread(_executar_ddgs),
            timeout=self.timeout,
        )

    async def _buscar_tavily(self, query: str, max_resultados: int) -> List[Dict[str, str]]:
        """Busca assíncrona via Tavily Search API."""
        headers = {"Content-Type": "application/json"}
        payload = {
            "api_key": self.tavily_key,
            "query": query,
            "max_results": max_resultados,
            "search_depth": "basic",
            "include_answer": False,
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post("https://api.tavily.com/search", json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            resultados = []
            for item in data.get("results", []):
                resultados.append({
                    "titulo": item.get("title", "").strip(),
                    "url": item.get("url", "").strip(),
                    "resumo": item.get("content", "").strip(),
                    "fonte": "Tavily",
                })
            return resultados

    async def _buscar_searxng(self, query: str, max_resultados: int) -> List[Dict[str, str]]:
        """Busca assíncrona via SearXNG."""
        params = {
            "q": query,
            "format": "json",
            "engines": "google,bing,duckduckgo",
        }
        headers = {"User-Agent": DEFAULT_USER_AGENT}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(f"{self.searxng_url}/search", params=params, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            resultados = []
            for item in data.get("results", [])[:max_resultados]:
                resultados.append({
                    "titulo": item.get("title", "").strip(),
                    "url": item.get("url", "").strip(),
                    "resumo": item.get("content", "").strip(),
                    "fonte": "SearXNG",
                })
            return resultados

    # =========================================================================
    # 2. EXTRAÇÃO E LEITURA DE PÁGINAS WEB (BROWSING / SCRAPING LIMPO)
    # =========================================================================
    async def ler_pagina_web(
        self,
        url: str,
        max_caracteres: int = 3500,
    ) -> Dict[str, Any]:
        """Acessa uma página web via HTTP e extrai seu texto limpo e legível.

        Remove menus, scripts, estilos, rodapés e anúncios, retornando o corpo
        textual principal formatado para consumo por LLMs.
        """
        url_limpa = url.strip()
        parsed = urlparse(url_limpa)
        if not parsed.scheme or parsed.scheme not in ("http", "https"):
            return {
                "sucesso": False,
                "erro": "URL inválida. O link deve começar com http:// ou https://.",
            }

        headers = {
            "User-Agent": DEFAULT_USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
            "Cache-Control": "no-cache",
        }

        logger.info("Extraindo conteúdo web da URL: %s (limite: %d chars)...", url_limpa, max_caracteres)

        try:
            async with httpx.AsyncClient(
                timeout=self.timeout,
                follow_redirects=True,
                headers=headers,
                verify=True,
            ) as client:
                resp = await client.get(url_limpa)
                resp.raise_for_status()
                html_content = resp.text

            # Parse e limpeza de HTML via BeautifulSoup
            soup = BeautifulSoup(html_content, "html.parser")

            # 1. Extração do título
            titulo = ""
            if soup.title and soup.title.string:
                titulo = soup.title.string.strip()

            # 2. Remoção de elementos ruidosos (scripts, styles, menus, banners)
            elementos_para_remover = [
                "script", "style", "noscript", "nav", "header", "footer",
                "aside", "form", "svg", "iframe", "button", "input"
            ]
            for tag in soup(elementos_para_remover):
                tag.decompose()

            # Remove tags com classes comuns de anúncios e popups
            for bad_tag in soup.find_all(
                attrs={"class": re.compile(r"(banner|ad-|ads-|cookie|popup|modal|share|social)", re.IGNORECASE)}
            ):
                bad_tag.decompose()

            # 3. Localização do container principal de conteúdo
            container_principal = (
                soup.find("article")
                or soup.find("main")
                or soup.find("div", attrs={"role": "main"})
                or soup.find(id=re.compile(r"(content|main|article|post|materia)", re.IGNORECASE))
                or soup.find(class_=re.compile(r"(content|article|post-content|materia-body)", re.IGNORECASE))
                or soup.body
                or soup
            )

            # 4. Extração e limpeza do texto
            linhas = [
                line.strip()
                for line in container_principal.stripped_strings
                if len(line.strip()) > 1
            ]
            texto_completo = "\n\n".join(linhas)

            # Normalização de múltiplos espaços e quebras
            texto_normalizado = re.sub(r"\n{3,}", "\n\n", texto_completo).strip()

            if not texto_normalizado:
                return {
                    "sucesso": False,
                    "erro": "Não foi possível extrair texto legível desta página (possível conteúdo renderizado apenas por JavaScript).",
                    "url": url_limpa,
                    "titulo": titulo,
                }

            # Truncamento seguro para não estourar a janela de contexto da LLM
            truncado = False
            if len(texto_normalizado) > max_caracteres:
                texto_normalizado = (
                    texto_normalizado[:max_caracteres]
                    + "\n\n... [Conteúdo truncado para síntese de leitura]"
                )
                truncado = True

            return {
                "sucesso": True,
                "url": url_limpa,
                "titulo": titulo or "Sem título",
                "conteudo": texto_normalizado,
                "caracteres": len(texto_normalizado),
                "truncado": truncado,
            }

        except httpx.HTTPStatusError as e:
            logger.error("Erro HTTP ao acessar URL %s: %s", url_limpa, e)
            return {
                "sucesso": False,
                "erro": f"Servidor web retornou código HTTP {e.response.status_code}.",
                "url": url_limpa,
            }
        except httpx.TimeoutException:
            logger.error("Timeout ao acessar URL %s", url_limpa)
            return {
                "sucesso": False,
                "erro": f"Tempo limite de {self.timeout}s esgotado ao tentar acessar a página.",
                "url": url_limpa,
            }
        except Exception as e:
            logger.error("Falha inesperada ao ler URL %s: %s", url_limpa, e)
            return {
                "sucesso": False,
                "erro": f"Falha ao processar página web: {str(e)}",
                "url": url_limpa,
            }

    # =========================================================================
    # 3. FORMATAÇÃO DE RESULTADOS
    # =========================================================================
    def formatar_para_llm(self, resultados: List[Dict[str, str]], query: str) -> str:
        """Formata a lista de resultados em texto conciso para consumo como retorno de tool."""
        if not resultados:
            return f"Nenhum resultado encontrado na web para a pesquisa: '{query}'."

        linhas = [f"Resultados da pesquisa na web para: '{query}':"]
        for idx, item in enumerate(resultados, 1):
            linhas.append(
                f"[{idx}] {item['titulo']}\n"
                f"    Link: {item['url']}\n"
                f"    Resumo: {item['resumo']}\n"
                f"    Fonte: {item['fonte']}"
            )
        return "\n\n".join(linhas)

    def formatar_para_discord(self, resultados: List[Dict[str, str]], query: str) -> str:
        """Formata os resultados com links markdown bonitos para exibição no Discord."""
        if not resultados:
            return f"🔍 **Pesquisa na Web:** Nenhum resultado encontrado para `{query}`."

        linhas = [f"🔍 **Resultados da Pesquisa na Web para:** *\"{query}\"*\n"]
        for idx, item in enumerate(resultados, 1):
            resumo_curto = item["resumo"]
            if len(resumo_curto) > 220:
                resumo_curto = resumo_curto[:217] + "..."
            linhas.append(
                f"**{idx}. [{item['titulo']}]({item['url']})**\n"
                f"> {resumo_curto}\n"
            )
        linhas.append(f"*Pesquisado via {resultados[0]['fonte']} • Tempo real*")
        return "\n".join(linhas)


# Instância singleton global do gerenciador de pesquisa na web
web_search_manager = WebSearchManager()
