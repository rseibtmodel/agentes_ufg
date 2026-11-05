"""
Sistema de Registro e Despacho de Tools (Function Calling).

Fornece um mecanismo desacoplado para registrar ferramentas que podem ser
invocadas pela LLM (OpenAI / LM Studio), gerando automaticamente o schema JSON
e executando chamadas síncronas ou assíncronas em threads dedicadas.
"""

import asyncio
from dataclasses import dataclass
import inspect
import json
import logging
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ToolDefinition:
    """Metadados e referência executável de uma ferramenta da LLM."""
    name: str
    description: str
    parameters: Dict[str, Any]
    func: Callable
    is_async: bool


def _inferir_schema_funcao(func: Callable) -> Dict[str, Any]:
    """Gera automaticamente o schema JSON dos parâmetros a partir da assinatura e type hints."""
    sig = inspect.signature(func)
    properties: Dict[str, Any] = {}
    required: List[str] = []

    tipo_map = {
        str: "string",
        int: "integer",
        float: "number",
        bool: "boolean",
        list: "array",
        dict: "object",
    }

    for param_name, param in sig.parameters.items():
        if param_name in ("self", "cls"):
            continue

        param_type = "string"
        if param.annotation != inspect.Parameter.empty:
            orig = getattr(param.annotation, "__origin__", param.annotation)
            param_type = tipo_map.get(orig, "string")

        prop: Dict[str, Any] = {
            "type": param_type,
            "description": f"Parâmetro '{param_name}'",
        }

        if param.default != inspect.Parameter.empty:
            prop["default"] = param.default
        else:
            required.append(param_name)

        properties[param_name] = prop

    return {
        "type": "object",
        "properties": properties,
        "required": required,
    }


class ToolRegistry:
    """Registro central de ferramentas disponíveis para a LLM."""

    def __init__(self):
        self._tools: Dict[str, ToolDefinition] = {}

    def register(
        self,
        name: Optional[str] = None,
        description: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
    ):
        """Decorador para registrar uma função como tool da LLM."""
        def decorator(func: Callable):
            tool_name = name or func.__name__
            tool_desc = description or (func.__doc__ or "").strip() or f"Executa a função {tool_name}"
            tool_params = parameters or _inferir_schema_funcao(func)

            is_async = inspect.iscoroutinefunction(func)

            self._tools[tool_name] = ToolDefinition(
                name=tool_name,
                description=tool_desc,
                parameters=tool_params,
                func=func,
                is_async=is_async,
            )
            logger.info("Tool registrada: %s (async=%s)", tool_name, is_async)
            return func

        return decorator

    def get_schemas(self) -> List[Dict[str, Any]]:
        """Retorna o catálogo de ferramentas no formato compatível com a API da OpenAI/LM Studio."""
        schemas = []
        for tool in self._tools.values():
            schemas.append({
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters,
                }
            })
        return schemas

    async def execute(self, name: str, arguments: Any) -> str:
        """Executa uma ferramenta registrada pelo nome passando os argumentos.
        
        Suporta chamadas síncronas (executadas em thread separada para não bloquear
        o event loop) e assíncronas. Retorna sempre uma string serializada.
        """
        if name not in self._tools:
            return f"Erro: Ferramenta '{name}' não encontrada ou não implementada."

        tool = self._tools[name]

        # Parse de argumentos (se vier como string JSON)
        if isinstance(arguments, str):
            try:
                args_dict = json.loads(arguments) if arguments.strip() else {}
            except Exception as e:
                return f"Erro ao decodificar argumentos JSON para '{name}': {str(e)}"
        elif isinstance(arguments, dict):
            args_dict = arguments
        else:
            args_dict = {}

        try:
            # Filtra argumentos inesperados caso a função não aceite **kwargs (evita TypeError por alucinação da LLM)
            sig = inspect.signature(tool.func)
            tem_varkw = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values())
            if not tem_varkw:
                args_sanitizados = {k: v for k, v in args_dict.items() if k in sig.parameters}
            else:
                args_sanitizados = args_dict

            if tool.is_async:
                resultado = await tool.func(**args_sanitizados)
            else:
                # Executa funções síncronas em thread dedicada para preservar o heartbeat do Discord
                resultado = await asyncio.to_thread(tool.func, **args_sanitizados)

            if isinstance(resultado, (dict, list)):
                return json.dumps(resultado, ensure_ascii=False, indent=2)
            return str(resultado)

        except Exception as e:
            logger.exception("Exceção ao executar tool '%s'", name)
            return f"Erro na execução da tool '{name}': {str(e)}"

    def get_registered_names(self) -> List[str]:
        """Retorna os nomes de todas as ferramentas registradas."""
        return list(self._tools.keys())


# Instância global padrão
registry = ToolRegistry()
register_tool = registry.register
