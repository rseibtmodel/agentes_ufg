"""
Ferramentas de FinOps e Observabilidade de Tokens para IA (Function Calling — IDEA-28).

Permite à LLM consultar o balanço de cotas diárias de tokens, ranking de custos
e economia gerada pela execução no nó local LM Studio.
"""

from typing import Any, Dict, Optional
from context_manager import get_current_user_id
from finops_manager import finops_manager
from tools.registry import register_tool


@register_tool(
    name="consultar_metricas_finops",
    description=(
        "Consulta o resumo consolidado de custos, tokens processados, "
        "saldo de cotas diárias e economia financeira gerada pelo nó local."
    ),
    parameters={
        "type": "object",
        "properties": {
            "dias": {
                "type": "integer",
                "description": "Período em dias para a análise estatística (padrão: 30).",
                "default": 30,
            },
        },
    },
)
def tool_consultar_metricas_finops(dias: int = 30) -> Dict[str, Any]:
    """Retorna os dados consolidados de consumo e custos de FinOps."""
    try:
        user_id = get_current_user_id() or "SYSTEM"
        resumo = finops_manager.obter_resumo_finops(dias=dias)
        cotas = finops_manager.obter_saldo_cotas(user_id=user_id)
        ranking = finops_manager.obter_ranking_modelos(dias=dias)

        return {
            "sucesso": True,
            "dados": {
                "resumo_periodo": resumo,
                "cotas_usuario": cotas,
                "top_modelos": ranking[:5],
            },
            "erro": None,
        }
    except Exception as e:
        return {
            "sucesso": False,
            "dados": None,
            "erro": f"Falha ao consultar métricas FinOps: {e}",
        }
