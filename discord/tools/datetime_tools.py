"""
Ferramentas de Data, Hora e Cálculos para a LLM.

Implementa a tool original `obter_hora_atual` e uma tool auxiliar `calcular_expressao`
utilizando o decorador `@register_tool`.
"""

from datetime import datetime
import math
from typing import Any, Dict
import zoneinfo
from tools.registry import register_tool


@register_tool(
    name="obter_hora_atual",
    description="Retorna a data e a hora atual em um formato legível. Útil para responder perguntas sobre o momento presente, que dia é hoje ou que horas são.",
    parameters={
        "type": "object",
        "properties": {
            "fuso_horario": {
                "type": "string",
                "description": "Nome da timezone no formato IANA (ex: 'America/Sao_Paulo', 'UTC', 'America/New_York'). Padrão: 'America/Sao_Paulo'.",
            }
        },
        "required": [],
    },
)
def obter_hora_atual(fuso_horario: str = "America/Sao_Paulo") -> Dict[str, Any]:
    """Retorna a data e hora atual em um formato legível."""
    try:
        tz = zoneinfo.ZoneInfo(fuso_horario)
        agora = datetime.now(tz)
        return {
            "sucesso": True,
            "dados": {
                "fuso_horario": fuso_horario,
                "data_hora": agora.strftime("%Y-%m-%d %H:%M:%S (%Z)"),
                "iso": agora.isoformat(),
            },
            "erro": None,
        }
    except Exception as e:
        return {
            "sucesso": False,
            "dados": None,
            "erro": f"Erro ao obter horário para o fuso '{fuso_horario}': {str(e)}",
        }


@register_tool(
    name="calcular_expressao",
    description="Calcula o resultado de uma expressão matemática simples ou avançada (soma, subtração, multiplicação, divisão, potências).",
    parameters={
        "type": "object",
        "properties": {
            "expressao": {
                "type": "string",
                "description": "Expressão matemática para avaliar (ex: '150 * 1.15', '2 ** 8', 'sqrt(144)').",
            }
        },
        "required": ["expressao"],
    },
)
def calcular_expressao(expressao: str) -> Dict[str, Any]:
    """Avalia uma expressão matemática de forma segura."""
    # Ambiente restrito com funções matemáticas seguras
    safe_dict = {
        "abs": abs,
        "round": round,
        "min": min,
        "max": max,
        "sqrt": math.sqrt,
        "sin": math.sin,
        "cos": math.cos,
        "tan": math.tan,
        "pi": math.pi,
        "e": math.e,
        "pow": pow,
    }
    try:
        # Avaliação com builtins desativados para segurança
        resultado = eval(expressao, {"__builtins__": {}}, safe_dict)
        return {
            "sucesso": True,
            "dados": {
                "expressao": expressao,
                "resultado": resultado,
            },
            "erro": None,
        }
    except Exception as e:
        return {
            "sucesso": False,
            "dados": None,
            "erro": f"Erro ao calcular expressão '{expressao}': {str(e)}",
        }
