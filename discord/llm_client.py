"""
Cliente Assíncrono para LLM (LM Studio / OpenAI API).

Gerencia a comunicação assíncrona não-bloqueante com o LM Studio,
mantendo o heartbeat do Discord ativo e orquestrando o ciclo de chamadas
de ferramentas (function calling / tools).
"""

import logging
from typing import Any, Dict, List, Optional, Tuple
from openai import AsyncOpenAI
from config import (
    DEFAULT_LLM_PROVIDER,
    ENABLE_AUTO_FAILOVER,
    GEMINI_API_BASE_URL,
    GEMINI_API_KEY,
    GEMINI_FLASH_MODEL,
    GEMINI_PRO_MODEL,
    LLM_TEMPERATURE,
    LLM_TIMEOUT_SECONDS,
    LM_STUDIO_API_KEY,
    LM_STUDIO_URL,
    LOCAL_TIMEOUT_FAILOVER_SECONDS,
    MAX_TOOL_CALL_ITERATIONS,
    MODELO_LLM,
)
from tools import execute_tool, get_tools_schema

logger = logging.getLogger(__name__)


def sanitizar_mensagens_jinja(mensagens: List[Any]) -> List[Any]:
    """Garante total compatibilidade com templates Jinja estritos de modelos no LM Studio.
    
    1. Aglutina múltiplos blocos com role 'system' em uma única mensagem no início (índice 0).
    2. Impede que mensagens subsequentes tenham role 'system' (evitando o erro 'System message must be at the beginning').
    3. Normaliza a ordem para: [system (se houver), ...user/assistant/tool].
    """
    system_partes = []
    outras_mensagens = []

    for msg in mensagens:
        if isinstance(msg, dict):
            role = msg.get("role")
            content = msg.get("content")
        else:
            role = getattr(msg, "role", None)
            content = getattr(msg, "content", None)

        if role == "system":
            if content and str(content).strip():
                system_partes.append(str(content).strip())
        else:
            outras_mensagens.append(msg)

    mensagens_finais = []
    if system_partes:
        mensagens_finais.append({
            "role": "system",
            "content": "\n\n".join(system_partes),
        })

    mensagens_finais.extend(outras_mensagens)
    return mensagens_finais


def classificar_complexidade_demanda(conteudo: str) -> Tuple[str, str]:
    """Analisa heuristicamente a intenção e densidade da mensagem do usuário para o modo auto.

    Retorna uma tupla (provedor_sugerido, modelo_sugerido):
    - Tarefas pesadas (livros, RAG, código, análise conceitual profunda) -> ('google', GEMINI_FLASH_MODEL / GEMINI_PRO_MODEL)
    - Tarefas cotidianas (saudações, hora, listas, lembretes, conversas curtas) -> ('local', MODELO_LLM)
    """
    if not conteudo:
        return "local", MODELO_LLM

    texto = conteudo.lower()

    # 1. Padrões de alta complexidade analítica / raciocínio avançado -> Gemini Pro
    padroes_pro = [
        "analise detalhada", "análise detalhada", "profundamente", "artigo cientifico",
        "artigo científico", "dissertação", "tese", "refatore esse codigo", "refatore esse código",
        "algoritmo complexo", "demonstre matematicamente", "prove que", "comparativo aprofundado",
    ]
    if any(p in texto for p in padroes_pro):
        return "google", GEMINI_PRO_MODEL

    # 2. Padrões de leitura de livros / PDFs / RAG / código / tradução / web browsing -> Gemini Flash
    padroes_flash = [
        "livro", "capítulo", "capitulo", "sumário", "sumario", "no pdf", "sobre o pdf",
        "rag", "graph rag", "graphrag", "resuma", "síntese", "sintese", "explique o conceito",
        "escreva um script", "crie um codigo", "crie um código", "função em python",
        "traduza o texto", "tradução", "redija um ensaio", "artigo",
        "pesquise na web", "pesquise na internet", "busque na web", "procure no google",
        "leia o link", "resuma o link", "http://", "https://",
    ]
    if any(p in texto for p in padroes_flash) or len(conteudo) > 350:
        return "google", GEMINI_FLASH_MODEL

    # 3. Padrão diário / rotina -> LM Studio Local
    return "local", MODELO_LLM


class LLMClient:
    """Cliente Híbrido Assíncrono para LLMs (LM Studio Local + Google Gemini Cloud)."""

    def __init__(
        self,
        base_url: str = LM_STUDIO_URL,
        api_key: str = LM_STUDIO_API_KEY,
        model: str = MODELO_LLM,
        timeout: float = LLM_TIMEOUT_SECONDS,
    ):
        self.local_base_url = base_url
        self.local_api_key = api_key
        self.local_model = model
        self.timeout = timeout

        self.gemini_api_key = GEMINI_API_KEY
        self.gemini_base_url = GEMINI_API_BASE_URL
        self.gemini_flash_model = GEMINI_FLASH_MODEL
        self.gemini_pro_model = GEMINI_PRO_MODEL

        # Cliente LM Studio Local (com timeout de failover rápido)
        self.local_client = AsyncOpenAI(
            base_url=self.local_base_url,
            api_key=self.local_api_key,
            timeout=LOCAL_TIMEOUT_FAILOVER_SECONDS,
        )

        # Cliente Google Gemini (inicializado se houver chave)
        self.google_client: Optional[AsyncOpenAI] = None
        if self.gemini_api_key and self.gemini_api_key.strip():
            self._inicializar_google_client(self.gemini_api_key)

        # Metadados da última execução
        self.ultimo_resultado: Dict[str, Any] = {
            "provider": "local",
            "model": self.local_model,
            "failover": False,
            "badge": "",
        }

    def _inicializar_google_client(self, api_key: str) -> None:
        """Inicializa o cliente OpenAI-compatible conectado à Google Gemini API."""
        self.gemini_api_key = api_key.strip()
        self.google_client = AsyncOpenAI(
            base_url=self.gemini_base_url,
            api_key=self.gemini_api_key,
            timeout=self.timeout,
        )
        logger.info("Cliente Google Gemini inicializado com sucesso (Modelos: %s, %s).", self.gemini_flash_model, self.gemini_pro_model)

    def atualizar_gemini_api_key(self, api_key: str) -> bool:
        """Atualiza a chave do Google Gemini em tempo de execução."""
        if not api_key or not api_key.strip():
            return False
        self._inicializar_google_client(api_key)
        return True

    def tem_gemini_disponivel(self) -> bool:
        """Retorna True se o Google Gemini estiver configurado e pronto para uso."""
        return self.google_client is not None and bool(self.gemini_api_key)

    async def _executar_loop_completions(
        self,
        client: AsyncOpenAI,
        model_name: str,
        mensagens: List[Any],
        tools: Optional[List[Dict[str, Any]]],
        temperatura: float,
        provider_label: str,
    ) -> str:
        """Executa o loop de chat completions resolvendo chamadas de tools."""
        historico_conversa = sanitizar_mensagens_jinja(mensagens)
        ferramentas = tools if tools is not None else get_tools_schema()

        iteracao = 0
        while iteracao < MAX_TOOL_CALL_ITERATIONS:
            iteracao += 1
            kwargs: Dict[str, Any] = {
                "model": model_name,
                "messages": historico_conversa,
                "temperature": temperatura,
            }
            if ferramentas:
                kwargs["tools"] = ferramentas
                kwargs["tool_choice"] = "auto"

            response = await client.chat.completions.create(**kwargs)
            msg_obj = response.choices[0].message

            if not getattr(msg_obj, "tool_calls", None):
                return msg_obj.content or ""

            logger.info("[%s] Iteração %d: Modelo solicitou %d tool(s)", provider_label, iteracao, len(msg_obj.tool_calls))
            historico_conversa.append(msg_obj)

            for tool_call in msg_obj.tool_calls:
                func_name = tool_call.function.name
                func_args = tool_call.function.arguments or "{}"
                logger.info("[%s] Executando tool '%s' com args: %s", provider_label, func_name, func_args)
                resultado = await execute_tool(func_name, func_args)

                historico_conversa.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": str(resultado),
                })

        logger.warning("[%s] Limite máximo de iterações de tools atingido (%d)", provider_label, MAX_TOOL_CALL_ITERATIONS)
        return (
            "⚠️ Limite máximo de chamadas automáticas de ferramentas atingido. "
            "A resposta foi interrompida para evitar looping infinito."
        )

    async def gerar_resposta(
        self,
        mensagens: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperatura: float = LLM_TEMPERATURE,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        permitir_failover: bool = True,
        incluir_badge: bool = False,
    ) -> str:
        """Gera resposta da LLM orquestrando o roteamento (Local vs Google Gemini vs Auto)."""
        prov_alvo = (provider or DEFAULT_LLM_PROVIDER).lower()
        modelo_alvo = model

        # Tratamento do modo 'auto': seleção de provedor com base no conteúdo
        if prov_alvo == "auto":
            conteudo_user = ""
            for m in reversed(mensagens):
                if m.get("role") == "user" and m.get("content"):
                    conteudo_user = str(m["content"])
                    break
            prov_auto, mod_auto = classificar_complexidade_demanda(conteudo_user)
            prov_alvo = prov_auto
            modelo_alvo = modelo_alvo or mod_auto

        # Se o usuário escolheu 'google' mas não há chave configurada
        if prov_alvo == "google" and not self.tem_gemini_disponivel():
            logger.warning("Google Gemini solicitado, mas GEMINI_API_KEY não configurada. Usando LM Studio Local como fallback.")
            prov_alvo = "local"
            modelo_alvo = self.local_model

        # ---------------------------------------------------------------------
        # ROTA 1: EXECUÇÃO NO GOOGLE GEMINI
        # ---------------------------------------------------------------------
        if prov_alvo == "google" and self.google_client:
            mod_google = modelo_alvo or self.gemini_flash_model
            logger.info("Executando inferência via Google Gemini API (Modelo: %s)...", mod_google)
            badge_icon = "🧠" if "pro" in mod_google.lower() else "⚡"
            badge = f"{badge_icon} `[Google Gemini: {mod_google}]`"

            try:
                texto_res = await self._executar_loop_completions(
                    self.google_client,
                    mod_google,
                    mensagens,
                    tools,
                    temperatura,
                    f"Gemini-{mod_google}",
                )
                self.ultimo_resultado = {
                    "provider": "google",
                    "model": mod_google,
                    "failover": False,
                    "badge": badge,
                }
                return f"{badge}\n\n{texto_res}" if incluir_badge else texto_res

            except Exception as e_gemini:
                logger.error("Falha na chamada ao Google Gemini: %s. Tentando fallback local...", e_gemini)
                prov_alvo = "local"
                modelo_alvo = self.local_model

        # ---------------------------------------------------------------------
        # ROTA 2: EXECUÇÃO NO LM STUDIO LOCAL (COM FAILOVER AUTOMÁTICO)
        # ---------------------------------------------------------------------
        mod_local = modelo_alvo or self.local_model
        logger.info("Executando inferência via LM Studio Local (Modelo: %s)...", mod_local)
        badge_local = f"🏠 `[LM Studio: {mod_local}]`"

        try:
            texto_res = await self._executar_loop_completions(
                self.local_client,
                mod_local,
                mensagens,
                tools,
                temperatura,
                "LM-Studio-Local",
            )
            self.ultimo_resultado = {
                "provider": "local",
                "model": mod_local,
                "failover": False,
                "badge": badge_local,
            }
            return f"{badge_local}\n\n{texto_res}" if incluir_badge else texto_res

        except Exception as e_local:
            logger.warning("Falha na chamada ao LM Studio Local: %s", e_local)

            # Auto-Failover para Google Gemini se permitido e chave disponível
            if permitir_failover and ENABLE_AUTO_FAILOVER and self.tem_gemini_disponivel():
                logger.warning("⚡ ATIVANDO AUTO-FAILOVER: LM Studio offline ou indisponível. Transbordando para Google Gemini...")
                mod_failover = self.gemini_flash_model
                badge_failover = f"⚡ `[Google Gemini: {mod_failover} | Auto-Failover]`"

                try:
                    texto_res = await self._executar_loop_completions(
                        self.google_client,
                        mod_failover,
                        mensagens,
                        tools,
                        temperatura,
                        "Gemini-Failover",
                    )
                    nota_failover = "\n\n*(⚡ Resposta gerada via Google Gemini devido à indisponibilidade temporária do LM Studio local)*"
                    self.ultimo_resultado = {
                        "provider": "google",
                        "model": mod_failover,
                        "failover": True,
                        "badge": badge_failover,
                    }
                    res_final = texto_res + nota_failover
                    return f"{badge_failover}\n\n{res_final}" if incluir_badge else res_final
                except Exception as e_failover:
                    logger.error("Falha também no failover para Google Gemini: %s", e_failover)

            raise ConnectionError(
                f"Não foi possível obter resposta do LM Studio ({self.local_base_url}). "
                f"Verifique se o LM Studio está aberto com o servidor local ativo. Detalhes: {e_local}"
            ) from e_local


# Instância global reutilizável
llm_client = LLMClient()

