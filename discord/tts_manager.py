"""
Módulo de Síntese de Voz (Text-to-Speech / TTS) via edge-tts.

Utiliza o serviço edge-tts com a voz feminina 'pt-BR-FranciscaNeural' (Francisca Brasil),
limpa textos gerados em Markdown para uma fala fluida e natural, gera arquivos de áudio
temporários em formato MP3 e garante a exclusão dos arquivos após o envio no Discord.
"""

import asyncio
import logging
from pathlib import Path
import re
import tempfile
from typing import Optional, Tuple
import edge_tts
from config import TTS_ENABLED, TTS_VOICE

logger = logging.getLogger(__name__)


def limpar_texto_para_tts(texto: str) -> str:
    """Prepara o texto gerado pela LLM para narração falada, removendo artefatos de Markdown."""
    if not texto:
        return ""

    t = texto

    # 1. Substitui blocos de código grandes por uma menção amigável
    t = re.sub(r"```[\w+-]*\n[\s\S]*?```", " (código omitido no áudio) ", t)

    # 2. Converte links Markdown [texto](url) para apenas 'texto'
    t = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", t)

    # 3. Substitui URLs puras por 'link'
    t = re.sub(r"https?://\S+", " link ", t)

    # 4. Remove menções do Discord (<@123456>, <#123456>)
    t = re.sub(r"<@!?\d+>", "", t)
    t = re.sub(r"<#\d+>", "canal", t)

    # 5. Remove formatação Markdown (negrito, itálico, tachado, crases)
    t = t.replace("**", "")
    t = t.replace("__", "")
    t = t.replace("~~", "")
    t = t.replace("`", "")
    t = re.sub(r"(?<!\w)\*([^*]+)\*(?!\w)", r"\1", t)

    # 6. Remove marcadores de listas e cabeçalhos Markdown (#, ##, •, -, >)
    t = re.sub(r"^[#>•\-\*]\s*", "", t, flags=re.MULTILINE)

    # 7. Remove múltiplos espaços em branco e quebras consecutivas
    t = re.sub(r"\n{2,}", ". ", t)
    t = re.sub(r"\s+", " ", t)

    limpo = t.strip()

    # Limita o tamanho máximo de texto falado a ~2000 caracteres para síntese rápida
    if len(limpo) > 2000:
        limpo = limpo[:1990] + "..."

    return limpo


async def sintetizar_fala_edge(
    texto: str,
    voz: str = TTS_VOICE,
) -> Tuple[Optional[Path], Optional[str]]:
    """Gera um arquivo de áudio temporário MP3 narrado via edge-tts (voz Francisca).
    
    Retorna uma tupla: (caminho_arquivo_temporario, erro)
    IMPORTANTE: O chamador é responsável por apagar o arquivo temporário após o envio!
    """
    if not TTS_ENABLED:
        return None, "TTS está desativado nas configurações."

    texto_falado = limpar_texto_para_tts(texto)
    if not texto_falado:
        return None, "Texto vazio após sanitização para fala."

    temp_path: Optional[Path] = None

    try:
        # Cria arquivo temporário .mp3
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
            temp_path = Path(tmp.name)

        logger.info(
            "Iniciando síntese de voz edge-tts (voz: %s, %d caracteres)...",
            voz,
            len(texto_falado),
        )

        communicate = edge_tts.Communicate(texto_falado, voz)
        await communicate.save(str(temp_path))

        tamanho_bytes = temp_path.stat().st_size
        logger.info(
            "Áudio TTS gerado com sucesso: %s (%d bytes)",
            temp_path,
            tamanho_bytes,
        )
        return temp_path, None

    except Exception as e:
        logger.exception("Erro ao sintetizar áudio com edge-tts: %s", e)
        # Se houve erro e o arquivo foi criado, apaga imediatamente
        if temp_path and temp_path.exists():
            try:
                temp_path.unlink()
            except Exception:
                pass
        return None, str(e)
