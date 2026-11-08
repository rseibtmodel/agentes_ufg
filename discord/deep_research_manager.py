"""
Gerenciador do Agente Autônomo de Pesquisa Profunda (Deep Research — IDEA-17).

Responsável por:
1. Decompor temas complexos em múltiplos eixos de busca analítica via LLM.
2. Executar varreduras paralelas e raspagem limpa de 8 a 15 fontes web com controle de concorrência.
3. Cruzar evidências, descartar dados espúrios e sintetizar Dossiês Executivos formais com citações.
4. Persistir relatórios no SQLite WAL e gerar arquivos Markdown estruturados para anexo no chat.
"""

from __future__ import annotations

import asyncio
from datetime import datetime
import json
import logging
from pathlib import Path
import re
import sqlite3
from typing import Any, Callable, Coroutine, Dict, List, Optional
import uuid

from config import BASE_DIR, DB_FILE
from database import obter_preferencia_modelo
from web_search_manager import web_search_manager

def _obter_llm_client():
    from llm_client import llm_client
    return llm_client

logger = logging.getLogger("deep_research_manager")

# Diretório padrão para armazenamento físico dos relatórios gerados
REPORTS_DIR = BASE_DIR / "relatorios_pesquisa"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


def _get_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    caminho = db_path or DB_FILE
    conn = sqlite3.connect(caminho, timeout=30.0)
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    return conn


def init_deep_research_db(db_path: Optional[str] = None) -> None:
    """Inicializa a tabela de relatórios de pesquisa profunda no SQLite."""
    with _get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS deep_research_reports (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                topic TEXT NOT NULL,
                summary TEXT NOT NULL,
                file_path TEXT NOT NULL,
                sources_json TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'concluido',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_research_user ON deep_research_reports(user_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_research_created ON deep_research_reports(created_at DESC);")
        conn.commit()
    logger.info("Tabela deep_research_reports inicializada com sucesso no SQLite.")


class DeepResearchManager:
    """Orquestrador do ciclo autônomo de pesquisa profunda multi-iteração."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path
        init_deep_research_db(self.db_path)

    async def planejar_subconsultas(self, tema: str, provider: str = "auto", model: Optional[str] = None) -> List[str]:
        """Decompõe o tema principal em 3 a 4 subconsultas de pesquisa específicas na web."""
        prompt = (
            f"Você é um planejador de pesquisas sênior. O usuário solicitou uma pesquisa profunda sobre:\n"
            f"\"{tema}\"\n\n"
            f"Gere exatamente 3 a 4 buscas curtas e eficientes para o DuckDuckGo/Google em português que cubram:\n"
            f"1. Definição / Estado da arte recente\n"
            f"2. Principais trade-offs, problemas ou comparação de abordagens\n"
            f"3. Melhores práticas e recomendações de mercado\n\n"
            f"Responda EXCLUSIVAMENTE com um array JSON de strings, sem blocos markdown adicionais. Exemplo:\n"
            f"[\"termo de busca 1\", \"termo de busca 2\", \"termo de busca 3\"]"
        )
        try:
            llm = _obter_llm_client()
            resposta = await llm.gerar_resposta(
                mensagens=[{"role": "user", "content": prompt}],
                provider=provider,
                model=model,
                temperatura=0.2,
                permitir_failover=True,
            )
            match = re.search(r"\[.*\]", resposta, re.DOTALL)
            if match:
                queries = json.loads(match.group(0))
                if isinstance(queries, list) and queries:
                    return [str(q).strip() for q in queries[:4]]
        except Exception as e:
            logger.warning("Falha ao gerar plano de subconsultas via LLM: %s. Usando fallback.", e)

        # Fallback determinístico caso a LLM falhe na extração JSON
        return [
            f"{tema} estado da arte analise",
            f"{tema} comparativo vantagens desvantagens",
            f"{tema} melhores praticas recomendacoes",
        ]

    async def coletar_e_ler_fontes(
        self,
        subconsultas: List[str],
        max_fontes_total: int = 10,
    ) -> List[Dict[str, str]]:
        """Busca e extrai o conteúdo de artigos web em paralelo com controle de concorrência."""
        # 1. Coleta URLs candidatas
        tarefas_busca = [
            web_search_manager.buscar_na_web(query=q, max_resultados=3)
            for q in subconsultas
        ]
        resultados_busca = await asyncio.gather(*tarefas_busca, return_exceptions=True)

        urls_vistas = set()
        candidatos = []
        for res in resultados_busca:
            if isinstance(res, list):
                for item in res:
                    url = (item.get("url") or item.get("href") or "").strip()
                    if url and url not in urls_vistas:
                        urls_vistas.add(url)
                        item["url"] = url
                        candidatos.append(item)
                    if len(candidatos) >= max_fontes_total:
                        break

        # 2. Raspagem concorrente com semáforo (máximo 3 conexões simultâneas)
        semaphore = asyncio.Semaphore(3)

        async def _ler_com_limite(candidato: Dict[str, str]) -> Optional[Dict[str, str]]:
            async with semaphore:
                try:
                    url = candidato["url"]
                    conteudo_res = await web_search_manager.ler_pagina_web(url, max_caracteres=2800)
                    titulo_candidato = candidato.get("titulo") or candidato.get("title") or "Fonte Web"
                    if isinstance(conteudo_res, dict):
                        if conteudo_res.get("sucesso") and conteudo_res.get("conteudo"):
                            return {
                                "titulo": conteudo_res.get("titulo") or titulo_candidato,
                                "url": url,
                                "texto": conteudo_res["conteudo"],
                            }
                    elif isinstance(conteudo_res, str) and conteudo_res.strip():
                        return {
                            "titulo": titulo_candidato,
                            "url": url,
                            "texto": conteudo_res,
                        }
                except Exception as err:
                    logger.debug("Falha na raspagem da URL %s: %s", candidato.get("url"), err)
                return None

        tarefas_leitura = [_ler_com_limite(c) for c in candidatos]
        fontes_lidas = await asyncio.gather(*tarefas_leitura, return_exceptions=True)

        fontes_validas = [f for f in fontes_lidas if isinstance(f, dict) and f.get("texto")]
        return fontes_validas

    async def sintetizar_dossie(
        self,
        tema: str,
        fontes: List[Dict[str, str]],
        provider: str = "auto",
        model: Optional[str] = None,
    ) -> Dict[str, str]:
        """Gera o dossiê analítico aprofundado a partir dos artigos coletados."""
        bloco_fontes = []
        for idx, f in enumerate(fontes, start=1):
            bloco_fontes.append(
                f"--- [FONTE {idx}]: {f['titulo']} ({f['url']}) ---\n{f['texto'][:2500]}\n"
            )
        fontes_texto = "\n".join(bloco_fontes)

        prompt_dossie = (
            f"Você é um Analista de Inteligência e Estrategista Técnico de elite.\n"
            f"Com base EXCLUSIVAMENTE nas fontes reais coletadas abaixo, redija um Dossiê Técnico Aprofundado (Deep Research) sobre:\n"
            f"\"{tema}\"\n\n"
            f"Estrutura Obrigatória do Documento (Markdown):\n"
            f"# Dossiê Técnico: {tema}\n\n"
            f"## 1. Sumário Executivo\n"
            f"(Síntese clara das conclusões centrais em 2 parágrafos).\n\n"
            f"## 2. Contexto & Estado da Arte\n"
            f"(Cenário atual, definições e como o ecossistema tem abordado o tema).\n\n"
            f"## 3. Análise Crítica e Comparativa\n"
            f"(Tabela comparativa ou tópicos com prós, contras, trade-offs de custo, escala e resiliência).\n\n"
            f"## 4. Riscos, Armadilhas e Pontos de Atenção\n"
            f"(Erros comuns cometidos por quem implementa ou adota essa tecnologia/estratégia).\n\n"
            f"## 5. Recomendações Práticas Acionáveis\n"
            f"(Plano de ação em etapas objetivas).\n\n"
            f"## 6. Referências & Fontes Consultadas\n"
            f"(Lista de referências enumeradas com links originais das fontes coletadas).\n\n"
            f"FONTES COLETADAS:\n{fontes_texto}"
        )

        llm = _obter_llm_client()
        dossie_markdown = await llm.gerar_resposta(
            mensagens=[{"role": "user", "content": prompt_dossie}],
            provider=provider,
            model=model,
            temperatura=0.3,
            permitir_failover=True,
        )

        # Extrai os dois primeiros parágrafos para o resumo executivo no chat
        paragrafos = [p.strip() for p in dossie_markdown.split("\n\n") if p.strip() and not p.startswith("#")]
        resumo_chat = "\n\n".join(paragrafos[:2]) if paragrafos else "Dossiê técnico gerado com sucesso."
        if len(resumo_chat) > 1700:
            resumo_chat = resumo_chat[:1690] + "..."

        return {
            "dossie_completo": dossie_markdown,
            "resumo_chat": resumo_chat,
        }

    async def executar_pesquisa_completa(
        self,
        tema: str,
        user_id: str,
        profundidade: int = 3,
        progress_callback: Optional[Callable[[str], Coroutine[Any, Any, None]]] = None,
    ) -> Dict[str, Any]:
        """Coordena o pipeline de ponta a ponta com emissão de status e persistência."""
        logger.info("Iniciando Deep Research para usuário '%s' sobre: %s", user_id, tema)
        report_id = str(uuid.uuid4())[:8]

        pref = obter_preferencia_modelo(user_id)
        if isinstance(pref, dict):
            provider = pref.get("provider", "auto")
            model = pref.get("model_name")
        else:
            provider = "auto"
            model = str(pref) if pref else None

        # 1. Planejamento
        if progress_callback:
            await progress_callback("🧭 **Etapa 1/4:** Decompondo o tema em eixos analíticos de pesquisa...")
        subqueries = await self.planejar_subconsultas(tema, provider=provider, model=model)

        # 2. Varredura e Coleta
        if progress_callback:
            queries_str = " • ".join(f"`{q}`" for q in subqueries)
            await progress_callback(f"🔍 **Etapa 2/4:** Varrendo a web e extraindo artigos em paralelo...\n*(Eixos: {queries_str})*")
        fontes = await self.coletar_e_ler_fontes(subqueries, max_fontes_total=8)

        if not fontes:
            return {
                "sucesso": False,
                "dados": None,
                "erro": "Não foi possível coletar fontes web suficientes para compor o dossiê analítico.",
            }

        # 3. Síntese do Dossiê
        if progress_callback:
            await progress_callback(f"📑 **Etapa 3/4:** Analisando `{len(fontes)}` fontes coletadas e redigindo o Dossiê Técnico...")
        sintese = await self.sintetizar_dossie(tema, fontes, provider=provider, model=model)

        # 4. Gravação física do arquivo Markdown
        nome_arquivo = f"dossie_{report_id}_{re.sub(r'[^a-zA-Z0-9]', '_', tema[:30]).strip('_').lower()}.md"
        caminho_arquivo = REPORTS_DIR / nome_arquivo

        def _salvar_arquivo_sync():
            caminho_arquivo.write_text(sintese["dossie_completo"], encoding="utf-8")

        await asyncio.to_thread(_salvar_arquivo_sync)

        # 5. Persistência relacional no SQLite WAL
        sources_meta = [{"titulo": f["titulo"], "url": f["url"]} for f in fontes]

        def _salvar_db_sync():
            with _get_connection(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO deep_research_reports (id, user_id, topic, summary, file_path, sources_json)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (report_id, str(user_id), tema, sintese["resumo_chat"], str(caminho_arquivo), json.dumps(sources_meta, ensure_ascii=False)),
                )
                conn.commit()

        await asyncio.to_thread(_salvar_db_sync)

        if progress_callback:
            await progress_callback("✅ **Etapa 4/4:** Dossiê concluído e formatado com sucesso!")

        return {
            "sucesso": True,
            "dados": {
                "report_id": report_id,
                "tema": tema,
                "resumo_executivo": sintese["resumo_chat"],
                "file_path": str(caminho_arquivo),
                "total_fontes": len(fontes),
                "fontes": sources_meta,
            },
            "erro": None,
        }

    def listar_relatorios(self, user_id: str, limite: int = 5) -> List[Dict[str, Any]]:
        """Lista os relatórios de pesquisa já elaborados para o usuário."""
        with _get_connection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, topic, summary, file_path, sources_json, created_at
                FROM deep_research_reports
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (str(user_id), max(1, min(20, limite))),
            )
            rows = cursor.fetchall()
            relatorios = []
            for r in rows:
                try:
                    fontes = json.loads(r[4])
                except Exception:
                    fontes = []
                relatorios.append({
                    "id": r[0],
                    "topic": r[1],
                    "summary": r[2],
                    "file_path": r[3],
                    "total_sources": len(fontes),
                    "created_at": r[5],
                })
            return relatorios

    def obter_relatorio(self, report_id: str) -> Optional[Dict[str, Any]]:
        """Recupera metadados e caminho de um relatório específico pelo ID."""
        with _get_connection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, user_id, topic, summary, file_path, sources_json, created_at
                FROM deep_research_reports
                WHERE id = ?
                """,
                (str(report_id).strip(),),
            )
            row = cursor.fetchone()
            if not row:
                return None
            try:
                fontes = json.loads(row[5])
            except Exception:
                fontes = []
            return {
                "id": row[0],
                "user_id": row[1],
                "topic": row[2],
                "summary": row[3],
                "file_path": row[4],
                "sources": fontes,
                "created_at": row[6],
            }


# Instância global singleton do Deep Research Manager
deep_research_manager = DeepResearchManager()
