"""
Ferramentas de Consulta e Configuração de Personas por Canal para a LLM — IDEA-26.
"""

from context_manager import (
    add_pending_view,
    get_current_channel_id,
    get_current_channel_name,
    get_current_guild_id,
    get_current_user_id,
)
from persona_manager import (
    aplicar_preset_canal,
    definir_persona_canal,
    listar_personas_disponiveis,
    obter_persona_canal,
    resetar_persona_canal,
    salvar_nova_persona,
)
from tools.registry import register_tool
from ui_components import criar_view_selecao_persona
from typing import Optional


@register_tool(
    name="consultar_persona_canal",
    description="Inspeciona a persona ativa, temperatura e diretrizes de comportamento configuradas para o canal atual.",
    parameters={"type": "object", "properties": {}},
)
async def tool_consultar_persona_canal() -> str:
    """Retorna as diretrizes da persona do canal ativo."""
    channel_id = get_current_channel_id()
    user_id = get_current_user_id()
    guild_id = get_current_guild_id()
    channel_name = get_current_channel_name()
    if not channel_id:
        return "Erro: Canal atual não identificado."

    # Anexa a interface interativa com dropdown de seleção de persona
    if channel_id and user_id:
        v = criar_view_selecao_persona(
            channel_id=channel_id,
            author_id=user_id,
            guild_id=guild_id,
            channel_name=channel_name,
        )
        if v:
            add_pending_view(v)

    persona = obter_persona_canal(channel_id)
    if not persona:
        return "Este canal não possui persona específica ativa; ele utiliza o comportamento padrão do assistente. Um menu dropdown interativo foi disponibilizado para seleção rápida de persona."

    modelo_txt = f" | Modelo: `{persona['model_override']}`" if persona["model_override"] else ""
    return (
        f"🎭 **Persona Ativa no Canal:** `{persona['channel_name'] or channel_id}`\n"
        f"🌡️ **Temperatura:** `{persona['temperature']}`{modelo_txt}\n\n"
        f"**Diretrizes:**\n{persona['system_prompt']}"
    )


@register_tool(
    name="configurar_persona_canal",
    description="Configura um System Prompt customizado com diretrizes especializadas para o canal de conversa atual.",
    parameters={
        "type": "object",
        "properties": {
            "prompt_persona": {
                "type": "string",
                "description": "Texto contendo as instruções de comportamento, estilo e especialidade da IA para este canal.",
            },
            "temperatura": {
                "type": "number",
                "description": "Temperatura de amostragem da LLM entre 0.0 e 1.0 (opcional).",
            },
        },
        "required": ["prompt_persona"],
    },
)
async def tool_configurar_persona_canal(
    prompt_persona: str,
    temperatura: Optional[float] = None,
) -> str:
    """Define as diretrizes de persona para o canal."""
    channel_id = get_current_channel_id()
    user_id = get_current_user_id()
    if not channel_id:
        return "Erro: Canal atual não identificado."

    res = definir_persona_canal(
        channel_id=channel_id,
        system_prompt=prompt_persona,
        user_id=user_id,
        temperature=temperatura,
    )
    return res["mensagem"]


@register_tool(
    name="aplicar_preset_persona_canal",
    description="Aplica instantaneamente um preset ou template da Central de Prompts (ex: dev, cfo, direto, revisor, socrates, tributarista) no canal atual.",
    parameters={
        "type": "object",
        "properties": {
            "nome_preset": {
                "type": "string",
                "description": "Slug do preset a aplicar (ex: 'dev', 'cfo', 'direto', 'socrates', 'tributarista').",
            }
        },
        "required": ["nome_preset"],
    },
)
async def tool_aplicar_preset_persona_canal(nome_preset: str) -> str:
    """Aplica um preset do catálogo no canal."""
    channel_id = get_current_channel_id()
    user_id = get_current_user_id()
    guild_id = get_current_guild_id()
    channel_name = get_current_channel_name()
    if not channel_id:
        return "Erro: Canal atual não identificado."

    res = aplicar_preset_canal(
        channel_id=channel_id,
        preset_slug=nome_preset,
        user_id=user_id,
        guild_id=guild_id,
        channel_name=channel_name,
    )

    if channel_id and user_id:
        v = criar_view_selecao_persona(
            channel_id=channel_id,
            author_id=user_id,
            guild_id=guild_id,
            channel_name=channel_name,
        )
        if v:
            add_pending_view(v)

    return res["mensagem"]


@register_tool(
    name="listar_personas_disponiveis",
    description="Lista todas as personas e presets cognitivos disponíveis no catálogo do bot (incluindo oficiais como dev, cfo, direto, revisor, socrates, tributarista e personas customizadas criadas pelos usuários), com suas especialidades e temperaturas.",
    parameters={
        "type": "object",
        "properties": {
            "categoria": {
                "type": "string",
                "description": "Filtro opcional por categoria temática (ex: 'desenvolvimento', 'negocios', 'personas').",
            }
        },
    },
)
async def tool_listar_personas_disponiveis(categoria: Optional[str] = None) -> str:
    """Lista as personas disponíveis no catálogo."""
    channel_id = get_current_channel_id()
    user_id = get_current_user_id()
    guild_id = get_current_guild_id()
    channel_name = get_current_channel_name()

    # Anexa o dropdown de seleção interativo à mensagem de resposta
    if channel_id and user_id:
        v = criar_view_selecao_persona(
            channel_id=channel_id,
            author_id=user_id,
            guild_id=guild_id,
            channel_name=channel_name,
        )
        if v:
            add_pending_view(v)

    personas = listar_personas_disponiveis(categoria=categoria)
    if not personas:
        return "Nenhuma persona encontrada no catálogo."

    linhas = [f"🎭 **Personas Disponíveis no Catálogo ({len(personas)}):**\n"]
    for p in personas:
        tipo = "🌟 [Oficial]" if p["is_preset"] else "👤 [Custom]"
        linhas.append(
            f"• `{p['id']}` — **{p['nome']}** {tipo} (Temp: `{p['temperatura']}`)\n"
            f"  *{p['descricao']}*"
        )
    linhas.extend([
        "\n💡 **Troca Rápida de Persona:**",
        "Você pode alternar a persona deste canal instantaneamente utilizando o **menu dropdown interativo** anexado abaixo, ou digitar `!persona canal aplicar <id>`.",
    ])
    return "\n".join(linhas)


@register_tool(
    name="cadastrar_nova_persona",
    description="Cadastra e salva uma nova persona especializada no catálogo geral do bot. Permite que o usuário crie especialistas sob medida com instruções, estilo e temperatura que ficam imediatamente disponíveis para qualquer canal.",
    parameters={
        "type": "object",
        "properties": {
            "identificador": {
                "type": "string",
                "description": "Slug/identificador único sem espaços em minúsculas (ex: 'arquiteto_cloud', 'copywriter', 'advogado_trabalhista').",
            },
            "prompt_diretrizes": {
                "type": "string",
                "description": "Texto completo contendo o System Prompt, tom de voz, regras e diretrizes da persona.",
            },
            "nome": {
                "type": "string",
                "description": "Nome legível amigável para exibição (ex: 'Arquiteto de Soluções Cloud').",
            },
            "descricao": {
                "type": "string",
                "description": "Breve resumo da especialidade e foco da persona.",
            },
            "temperatura": {
                "type": "number",
                "description": "Temperatura de amostragem sugerida para a LLM entre 0.0 e 1.0 (padrão: 0.7).",
            },
        },
        "required": ["identificador", "prompt_diretrizes"],
    },
)
async def tool_cadastrar_nova_persona(
    identificador: str,
    prompt_diretrizes: str,
    nome: Optional[str] = None,
    descricao: Optional[str] = None,
    temperatura: Optional[float] = None,
) -> str:
    """Cadastra uma nova persona no catálogo."""
    channel_id = get_current_channel_id()
    user_id = get_current_user_id()
    guild_id = get_current_guild_id()
    channel_name = get_current_channel_name()

    temp_val = float(temperatura) if temperatura is not None else 0.7
    res = salvar_nova_persona(
        slug_id=identificador,
        prompt=prompt_diretrizes,
        nome=nome,
        descricao=descricao,
        temperatura=temp_val,
        user_id=user_id,
    )

    if channel_id and user_id:
        v = criar_view_selecao_persona(
            channel_id=channel_id,
            author_id=user_id,
            guild_id=guild_id,
            channel_name=channel_name,
        )
        if v:
            add_pending_view(v)

    return res["mensagem"]
