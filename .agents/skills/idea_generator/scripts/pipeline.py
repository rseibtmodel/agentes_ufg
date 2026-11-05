#!/usr/bin/env python3
"""
Pipeline Multi-Agente de Ideação e Refinamento de Conceitos (CLI).

Implementa as 5 etapas do idea_generator:
1. Ideator (Geração Criativa)
2. Devil's Advocate (Análise Crítica de Riscos)
3. Champion (Análise de Oportunidades e Mercado)
4. Gatekeeper (Decisão de Aprovação/Rejeição)
5. Editor/Enricher (Saneamento, Mitigação e Roadmap Final)
"""

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

# Tenta carregar variáveis de ambiente do projeto se existirem
PROJECT_DIR = Path(__file__).resolve().parents[4]
DISCORD_ENV = PROJECT_DIR / "discord" / ".env"
if DISCORD_ENV.exists():
    try:
        from dotenv import load_dotenv
        load_dotenv(DISCORD_ENV)
    except ImportError:
        pass


class IdeaPipelineRunner:
    """Orquestrador do pipeline de ideação multi-agente."""

    def __init__(self, provider: str = "auto", mock: bool = False):
        self.provider = provider
        self.mock = mock
        self.gemini_key = os.getenv("GEMINI_API_KEY", "")
        self.gemini_model = os.getenv("GEMINI_FLASH_MODEL", "gemini-3.5-flash")
        self.local_url = os.getenv("LM_STUDIO_URL", "http://localhost:1234/v1")
        self.local_model = os.getenv("MODELO_LLM", "qwen/qwen3.5-9b")

    async def _call_llm(self, system_prompt: str, user_prompt: str) -> str:
        """Invoca a LLM configurada (Gemini ou LM Studio local) ou retorna mock."""
        if self.mock:
            return ""

        # 1. Tentativa via Google Gemini se houver chave
        if (self.provider in ("google", "gemini", "auto")) and self.gemini_key:
            try:
                from openai import AsyncOpenAI
                client = AsyncOpenAI(
                    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
                    api_key=self.gemini_key,
                )
                resp = await client.chat.completions.create(
                    model=self.gemini_model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0.7,
                )
                return resp.choices[0].message.content or ""
            except Exception as e:
                if self.provider == "google":
                    raise RuntimeError(f"Falha na API Google Gemini: {e}")

        # 2. Tentativa via LM Studio Local
        try:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(base_url=self.local_url, api_key="lm-studio")
            resp = await client.chat.completions.create(
                model=self.local_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.7,
                timeout=60.0,
            )
            return resp.choices[0].message.content or ""
        except Exception as e:
            raise RuntimeError(f"Não foi possível conectar a nenhum provedor de LLM: {e}")

    # =========================================================================
    # ETAPAS DO PIPELINE
    # =========================================================================

    async def etapa_1_ideator(self, tema: str) -> str:
        """Etapa 1: Pensamento divergente e conceituação inicial."""
        if self.mock:
            return (
                f"### 💡 Ideia Inicial: AutoSync Hub\n"
                f"- **Problema Resolvido:** Fragmentação de tarefas para profissionais remotos ao redor do tema '{tema}'.\n"
                f"- **Conceito Central:** Hub unificado que consolida e sincroniza demandas em tempo real com micro-automações de IA.\n"
                f"- **Proposta de Valor:** Economizar até 8 horas semanais em trabalho operacional invisível."
            )

        sys_p = (
            "Você é o IDEATOR em um pipeline criativo multi-agente. "
            "Seu papel é o pensamento divergente, inovador e livre de autocrítica. "
            "Gere uma proposta de alto impacto estruturada com:\n"
            "- Título da Ideia\n"
            "- Problema Resolvido\n"
            "- Conceito Central\n"
            "- Proposta de Valor"
        )
        usr_p = f"Gere uma ideia inovadora e promissora sobre o seguinte tema/desafio:\n\n\"{tema}\""
        return await self._call_llm(sys_p, usr_p)

    async def etapa_2_critic(self, ideia: str) -> str:
        """Etapa 2: Análise cética de riscos e falhas (Devil's Advocate)."""
        if self.mock:
            return (
                "1. **Risco Técnico:** Complexidade de manter integrações com dezenas de APIs instáveis.\n"
                "2. **Custo de Aquisição:** Dificuldade em se destacar no mar de ferramentas de produtividade sem alto investimento em tráfego pago.\n"
                "3. **Falta de Moat:** Concorrentes gigantes podem clonar o recurso principal como um mero botão em seus sistemas."
            )

        sys_p = (
            "Você é o DEVIL'S ADVOCATE (Crítico Implacável) em um pipeline multi-agente. "
            "Sua única função é encontrar os pontos fracos da proposta fornecida. "
            "Aponte estritamente: riscos técnicos/operacionais, custos ocultos, barreiras de entrada, "
            "falhas lógicas e motivos para falhar. Seja cético, direto e pragmático."
        )
        return await self._call_llm(sys_p, f"Avalie criticamente esta proposta conceitual:\n\n{ideia}")

    async def etapa_3_champion(self, ideia: str) -> str:
        """Etapa 3: Análise otimista de oportunidades e escala (Champion)."""
        if self.mock:
            return (
                "1. **Demanda em Alta:** A dor de sobrecarga cognitiva em trabalhadores do conhecimento é recorde.\n"
                "2. **Monetização Clara:** Disposição comprovada para pagar R$ 49-99/mês se houver ROI de tempo evidente.\n"
                "3. **Efeito Viral:** Compartilhamento natural em equipes de trabalho, gerando crescimento orgânico (product-led growth)."
            )

        sys_p = (
            "Você é o CHAMPION (Defensor Visionário) em um pipeline multi-agente. "
            "Sua função é defender o potencial desta ideia. "
            "Destaque estritamente: potencial de mercado, alavancas de escala, diferenciais competitivos (moats), "
            "tendências favoráveis e por que vale muito a pena construí-la. Seja entusiasmado e estratégico."
        )
        return await self._call_llm(sys_p, f"Defenda as forças e oportunidades desta proposta conceitual:\n\n{ideia}")

    async def etapa_4_gatekeeper(self, ideia: str, critica: str, defesa: str) -> Tuple[str, str]:
        """Etapa 4: Juiz pragmático (Gatekeeper). Retorna (status, justificativa)."""
        if self.mock:
            return (
                "APROVADA",
                "1. A dor abordada é frequente e dolorosa no público-alvo.\n"
                "2. Os riscos técnicos apontados pelo Crítico são contornáveis com escopo inicial enxuto.\n"
                "3. O modelo de receita direta (SaaS) apresenta viabilidade econômica saudável."
            )

        sys_p = (
            "Você é o GATEKEEPER em um pipeline multi-agente de decisão de projetos. "
            "Você recebe a ideia original, as críticas mais severas e os argumentos do defensor. "
            "Você deve avaliar com frieza se os riscos superam as oportunidades. "
            "Emita obrigatoriamente a sua decisão no seguinte formato estrito:\n\n"
            "STATUS: [APROVADA] ou STATUS: [REJEITADA]\n\n"
            "JUSTIFICATIVA:\n"
            "1. [Ponto-chave da decisão]\n"
            "2. [Balanço entre riscos vs oportunidades]\n"
            "3. [Condição de viabilidade ou motivo fatal de rejeição]"
        )
        prompt = (
            f"--- PROPOSTA ORIGINAL ---\n{ideia}\n\n"
            f"--- ANÁLISE DO CRÍTICO ---\n{critica}\n\n"
            f"--- ANÁLISE DO DEFENSOR ---\n{defesa}\n\n"
            "Decida: Esta ideia deve ser [APROVADA] para a fase de refinamento e execução ou [REJEITADA]?"
        )
        resposta = await self._call_llm(sys_p, prompt)

        status = "REJEITADA"
        if "[APROVADA]" in resposta.upper() or "STATUS: APROVADA" in resposta.upper():
            status = "APROVADA"

        return status, resposta

    async def etapa_5_enricher(self, ideia: str, critica: str, defesa: str) -> str:
        """Etapa 5: Refinamento, mitigação de riscos e plano de execução (Editor)."""
        if self.mock:
            return (
                "### 📌 Título e Resumo Executivo\n"
                "**AutoSync Hub MVP:** Plataforma leve de orquestração assíncrona focada no nicho de pequenas agências digitais.\n\n"
                "### 🎯 Conceito Aprimorado e Proposta de Valor\n"
                "Em vez de integrar 100 ferramentas, o MVP conecta exclusivamente WhatsApp, Google Calendar e Trello/Notion, entregando valor imediato sem complexidade de suporte.\n\n"
                "### 🛡️ Plano de Mitigação dos Riscos Levantados\n"
                "- *Risco de APIs:* Uso exclusivo de webhooks oficiais e camadas de fallback para evitar quebras silenciosas.\n"
                "- *Custo de Aquisição:* Foco em marketing de conteúdo e parcerias com comunidades de gestores remotos.\n\n"
                "### 🚀 Próximos Passos Práticos de Execução\n"
                "1. Montar protótipo funcional em 7 dias com n8n/Python.\n"
                "2. Validar com 5 agências parceiras em regime beta.\n"
                "3. Lançar versão comercial com plano de R$ 79/mês."
            )

        sys_p = (
            "Você é o EDITOR & ENRICHER em um pipeline multi-agente de produtos. "
            "A proposta foi APROVADA pelo Gatekeeper. "
            "Seu papel é saneá-la e refiná-la em um plano executivo maduro. "
            "Neutralize ativamente cada fragilidade levantada pelo Crítico e integre os diferenciais do Defensor.\n\n"
            "Forneça a resposta estruturada nas 4 seções:\n"
            "📌 Título e Resumo Executivo\n"
            "🎯 Conceito Aprimorado e Proposta de Valor\n"
            "🛡️ Plano de Mitigação dos Riscos Levantados\n"
            "🚀 Próximos Passos Práticos de Execução"
        )
        prompt = (
            f"--- PROPOSTA INICIAL ---\n{ideia}\n\n"
            f"--- APONTAMENTOS DO CRÍTICO (A MITIGAR) ---\n{critica}\n\n"
            f"--- DESTAQUES DO DEFENSOR (A POTENCIALIZAR) ---\n{defesa}\n\n"
            "Produza a entrega final executiva estruturada."
        )
        return await self._call_llm(sys_p, prompt)

    # =========================================================================
    # ORQUESTRAÇÃO COMPLETA
    # =========================================================================

    async def run(self, tema: str) -> Dict[str, Any]:
        """Executa o pipeline completo para o tema informado."""
        print(f"\n🚀 [PIPELINE] Iniciando ideação para o tema: \"{tema}\"...")

        # Etapa 1: Ideator
        print("\n💡 [Etapa 1/5] Executando Ideator (Geração Criativa)...")
        ideia = await self.etapa_1_ideator(tema)

        # Etapas 2 e 3: Fan-Out Paralelo
        print("⚡ [Etapas 2 e 3/5] Executando Análise Paralela (Crítico vs Defensor)...")
        critica_task = asyncio.create_task(self.etapa_2_critic(ideia))
        defesa_task = asyncio.create_task(self.etapa_3_champion(ideia))
        critica, defesa = await asyncio.gather(critica_task, defesa_task)

        # Etapa 4: Gatekeeper
        print("⚖️ [Etapa 4/5] Executando Gatekeeper (Avaliação e Decisão)...")
        status, veredito = await self.etapa_4_gatekeeper(ideia, critica, defesa)
        print(f"   -> Veredito emitido: [{status}]")

        resultado: Dict[str, Any] = {
            "tema": tema,
            "etapa_1_ideia": ideia,
            "etapa_2_critica": critica,
            "etapa_3_defesa": defesa,
            "etapa_4_status": status,
            "etapa_4_veredito": veredito,
            "etapa_5_entrega_final": None,
        }

        # Verificação do Gatekeeper
        if status != "APROVADA":
            print(f"\n🛑 [PIPELINE INTERROMPIDO] A proposta foi {status} pelo Gatekeeper.")
            return resultado

        # Etapa 5: Enricher
        print("✨ [Etapa 5/5] Executando Editor & Enricher (Refinamento e Mitigação)...")
        entrega_final = await self.etapa_5_enricher(ideia, critica, defesa)
        resultado["etapa_5_entrega_final"] = entrega_final
        print("✅ [PIPELINE CONCLUÍDO COM SUCESSO!]")
        return resultado


def formatar_relatorio_markdown(res: Dict[str, Any]) -> str:
    """Gera um documento Markdown completo com todas as etapas do pipeline."""
    blocos = [
        f"# Relatório do Pipeline de Ideação (`idea_generator`)\n",
        f"**Tema:** *\"{res['tema']}\"*\n",
        f"**Decisão do Gatekeeper:** `[{res['etapa_4_status']}]`\n",
        "---\n",
        "## 💡 Etapa 1 — Geração Criativa (`Ideator`)\n",
        res["etapa_1_ideia"],
        "\n---\n",
        "## 😈 Etapa 2 — Análise do Crítico (`Devil's Advocate`)\n",
        res["etapa_2_critica"],
        "\n---\n",
        "## 🏆 Etapa 3 — Análise do Defensor (`Champion`)\n",
        res["etapa_3_defesa"],
        "\n---\n",
        "## ⚖️ Etapa 4 — Decisão do Gatekeeper\n",
        res["etapa_4_veredito"],
    ]

    if res["etapa_4_status"] == "APROVADA" and res["etapa_5_entrega_final"]:
        blocos.extend([
            "\n---\n",
            "## ✨ Etapa 5 — Saneamento e Entrega Final (`Editor/Enricher`)\n",
            res["etapa_5_entrega_final"],
        ])
    else:
        blocos.extend([
            "\n---\n",
            "> 🛑 **Fluxo Interrompido:** A Etapa 5 não foi executada porque o conceito foi rejeitado pelo Gatekeeper.",
        ])

    return "\n".join(blocos)


async def main():
    parser = argparse.ArgumentParser(
        description="Pipeline Multi-Agente de Ideação e Refinamento de Conceitos (idea_generator)"
    )
    parser.add_argument("--theme", "-t", type=str, help="Tema ou problema para ideação")
    parser.add_argument("--interactive", "-i", action="store_true", help="Modo interativo no terminal")
    parser.add_argument("--mock", "-m", action="store_true", help="Execução simulada sem chamadas a LLMs")
    parser.add_argument("--provider", "-p", default="auto", choices=["auto", "google", "local"], help="Provedor de LLM")
    parser.add_argument("--output", "-o", type=str, help="Caminho para salvar o relatório em arquivo Markdown")
    parser.add_argument("--json", action="store_true", help="Imprimir saída em formato JSON estruturado")

    args = parser.parse_args()

    tema = args.theme
    if args.interactive or not tema:
        print("🧠 --- IDEA GENERATOR: PIPELINE MULTI-AGENTE ---")
        tema = input("Digite o tema, desafio ou problema para ideação: ").strip()
        if not tema:
            print("Erro: Nenhum tema fornecido. Encerrando.")
            sys.exit(1)

    runner = IdeaPipelineRunner(provider=args.provider, mock=args.mock)
    try:
        resultado = await runner.run(tema)
    except Exception as e:
        print(f"\n❌ Erro durante a execução do pipeline: {e}")
        sys.exit(1)

    if args.json:
        print(json.dumps(resultado, indent=2, ensure_ascii=False))
    else:
        md = formatar_relatorio_markdown(resultado)
        print("\n" + "=" * 60)
        print(md)
        print("=" * 60)

    if args.output:
        p = Path(args.output)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(formatar_relatorio_markdown(resultado), encoding="utf-8")
        print(f"\n📁 Relatório salvo com sucesso em: {p.resolve()}")


if __name__ == "__main__":
    asyncio.run(main())
