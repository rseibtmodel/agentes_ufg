"""
Gerenciador do Antigravity Remote Runner (Modo Leitura & Consulta — IDEA-23).

Permite:
1. Escanear e inspecionar o catálogo local de skills e agentes em `.agents/skills/`.
2. Extrair regras, personas e descrições dos arquivos SKILL.md.
3. Coletar telemetria de runtime local (memória, CPU, tarefas assíncronas ativas, modelo).
4. Executar consultas analíticas com a persona e diretrizes especializadas de uma skill específica (Read-Only).
"""

from __future__ import annotations

import asyncio
from datetime import datetime
import logging
import os
from pathlib import Path
import platform
import re
import resource
import time
from typing import Any, Dict, List, Optional

from config import BASE_DIR
from database import obter_preferencia_modelo

logger = logging.getLogger("agy_manager")

# Início do processo para cálculo de uptime
_INICIO_PROCESSO = time.time()


def _obter_llm_client():
    """Importação lazy para prevenir ciclos de importação com o pacote tools."""
    from llm_client import llm_client
    return llm_client


class AGYManager:
    """Gerenciador de leitura, inspeção e execução consultiva de skills locais."""

    def __init__(self, workspace_root: Optional[Path] = None):
        # Raiz do projeto (onde fica .agents/)
        self.workspace_root = workspace_root or BASE_DIR.parent
        self.skills_dir = self.workspace_root / ".agents" / "skills"

    def listar_skills(self) -> List[Dict[str, Any]]:
        """Varre o diretório .agents/skills/ e retorna a lista de skills e seus metadados."""
        skills: List[Dict[str, Any]] = []
        if not self.skills_dir.exists() or not self.skills_dir.is_dir():
            logger.warning("Diretório de skills não encontrado: %s", self.skills_dir)
            return skills

        for pasta in sorted(self.skills_dir.iterdir()):
            if pasta.is_dir():
                skill_file = pasta / "SKILL.md"
                if skill_file.exists():
                    info = self._fazer_parse_skill_file(skill_file, pasta.name)
                    skills.append(info)

        return skills

    def obter_skill(self, nome: str) -> Optional[Dict[str, Any]]:
        """Retorna os detalhes de uma skill específica pelo nome ou slug."""
        nome_limpo = nome.strip().lower()
        skills = self.listar_skills()
        for s in skills:
            if s["name"].lower() == nome_limpo or s["pasta"].lower() == nome_limpo:
                return s
        return None

    def _fazer_parse_skill_file(self, caminho: Path, pasta_nome: str) -> Dict[str, Any]:
        """Extrai frontmatter YAML e o resumo de conteúdo de um SKILL.md."""
        conteudo = caminho.read_text(encoding="utf-8", errors="replace")
        name = pasta_nome
        description = "Sem descrição informada."

        # Extrai frontmatter delimitado por ---
        match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", conteudo, re.DOTALL)
        corpo = conteudo
        if match:
            frontmatter_raw = match.group(1)
            corpo = match.group(2).strip()

            # Extração simples de name e description
            name_match = re.search(r"^name:\s*(.+)$", frontmatter_raw, re.MULTILINE)
            if name_match:
                name = name_match.group(1).strip().strip("'\"")

            desc_match = re.search(r"^description:\s*(?:>-\s*)?(.+?)(?=\n\w+:|\Z)", frontmatter_raw, re.DOTALL | re.MULTILINE)
            if desc_match:
                description = " ".join(desc_match.group(1).split())

        return {
            "name": name,
            "pasta": pasta_nome,
            "description": description,
            "path": str(caminho),
            "corpo": corpo,
        }

    def obter_status_telemetria(self) -> Dict[str, Any]:
        """Coleta telemetria do ambiente de execução local do bot."""
        uptime_segundos = int(time.time() - _INICIO_PROCESSO)
        horas = uptime_segundos // 3600
        minutos = (uptime_segundos % 3600) // 60
        segundos = uptime_segundos % 60
        uptime_formatado = f"{horas:02d}h {minutos:02d}m {segundos:02d}s"

        # Uso de memória do processo
        try:
            # Em macOS getrusage retorna bytes; em Linux retorna kilobytes
            ru_maxrss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            if platform.system() == "Darwin":
                mem_mb = round(ru_maxrss / (1024 * 1024), 2)
            else:
                mem_mb = round(ru_maxrss / 1024, 2)
        except Exception:
            mem_mb = 0.0

        # Tarefas ativas no event loop
        try:
            tarefas_ativas = len([t for t in asyncio.all_tasks() if not t.done()])
        except Exception:
            tarefas_ativas = 0

        skills_count = len(self.listar_skills())

        return {
            "plataforma": f"{platform.system()} {platform.release()}",
            "arquitetura": platform.machine(),
            "uptime": uptime_formatado,
            "memoria_processo_mb": mem_mb,
            "tarefas_async_ativas": tarefas_ativas,
            "total_skills_locais": skills_count,
            "modo_execucao": "Read-Only Runner (Seguro)",
            "pid": os.getpid(),
        }

    async def consultar_skill(
        self,
        nome_skill: str,
        consulta: str,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Executa uma consulta analítica no modo Read-Only injetando as diretrizes
        e persona da skill requisitada via LLM.
        """
        skill = self.obter_skill(nome_skill)
        if not skill:
            return {
                "sucesso": False,
                "dados": None,
                "erro": f"Skill ou Agente '{nome_skill}' não encontrado em .agents/skills/.",
            }

        user_str = str(user_id) if user_id else "padrao"
        pref = obter_preferencia_modelo(user_str)
        if isinstance(pref, dict):
            provider = pref.get("provider", "auto")
            model = pref.get("model_name")
        else:
            provider = "auto"
            model = str(pref) if pref else None

        # Monta prompt especializado incorporando as regras da skill
        prompt_sistema = (
            f"Você é o especialista atuando sob a persona da skill/agente '{skill['name']}'.\n\n"
            f"DIRETRIZES DA SKILL ({skill['pasta']}):\n"
            f"{skill['corpo'][:3500]}\n\n"
            f"IMPORTANTE: Você está operando em MODO LEITURA & CONSULTA no Discord.\n"
            f"Responda à dúvida do usuário com base rigorosa nas suas especialidades e padrões técnicos."
        )

        try:
            llm = _obter_llm_client()
            resposta = await llm.gerar_resposta(
                mensagens=[
                    {"role": "system", "content": prompt_sistema},
                    {"role": "user", "content": consulta},
                ],
                provider=provider,
                model=model,
                temperatura=0.3,
                permitir_failover=True,
            )

            return {
                "sucesso": True,
                "dados": {
                    "skill": skill["name"],
                    "pasta": skill["pasta"],
                    "consulta": consulta,
                    "resposta": resposta,
                    "modo": "read_only",
                },
                "erro": None,
            }
        except Exception as err:
            logger.exception("Erro ao executar consulta na skill '%s': %s", nome_skill, err)
            return {
                "sucesso": False,
                "dados": None,
                "erro": f"Falha ao processar consulta com a skill '{nome_skill}': {err}",
            }


# Instância global padrão do AGYManager
agy_manager = AGYManager()

