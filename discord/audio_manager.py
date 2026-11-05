"""
Módulo de Gerenciamento e Transcrição de Áudio (faster-whisper).

Recebe mensagens de voz e arquivos de áudio enviados no Discord, salva temporariamente,
transcreve para texto em português (pt-br) de forma assíncrona/não-bloqueante e garante
a exclusão de todos os arquivos temporários após o processamento.
"""

import asyncio
import logging
from pathlib import Path
import tempfile
from typing import Optional, Tuple
import discord

logger = logging.getLogger(__name__)

# Compatibilidade com versões modernas do PyAV (av >= 14) que descontinuaram metadata_errors
try:
    import av
    _orig_av_open = av.open

    def _compat_av_open(*args, **kwargs):
        kwargs.pop("metadata_errors", None)
        return _orig_av_open(*args, **kwargs)

    av.open = _compat_av_open
except Exception as _e_av:
    logger.debug("Shim de PyAV não aplicado: %s", _e_av)

from faster_whisper import WhisperModel
from config import (
    WHISPER_COMPUTE_TYPE,
    WHISPER_DEVICE,
    WHISPER_LANGUAGE,
    WHISPER_MODEL_SIZE,
)

# Extensões comuns de arquivos de áudio e notas de voz do Discord
AUDIO_EXTENSIONS = {
    ".ogg",
    ".mp3",
    ".wav",
    ".m4a",
    ".aac",
    ".flac",
    ".opus",
    ".wma",
    ".webm",
}

# Singleton do modelo WhisperModel para reuso em memória
_whisper_model: Optional[WhisperModel] = None
_model_lock = asyncio.Lock()


def get_whisper_model() -> WhisperModel:
    """Retorna a instância singleton do modelo faster-whisper carregado em memória."""
    global _whisper_model
    if _whisper_model is None:
        logger.info(
            "Carregando modelo faster-whisper '%s' (device=%s, compute_type=%s)...",
            WHISPER_MODEL_SIZE,
            WHISPER_DEVICE,
            WHISPER_COMPUTE_TYPE,
        )
        _whisper_model = WhisperModel(
            WHISPER_MODEL_SIZE,
            device=WHISPER_DEVICE,
            compute_type=WHISPER_COMPUTE_TYPE,
        )
        logger.info("Modelo faster-whisper carregado com sucesso!")
    return _whisper_model


def eh_anexo_audio(attachment: discord.Attachment) -> bool:
    """Verifica se o anexo do Discord é uma mensagem de voz ou arquivo de áudio suportado."""
    # 1. Verifica flag nativa de mensagem de voz do Discord (discord.py >= 2.3)
    try:
        is_vm = getattr(attachment, "is_voice_message", None)
        if callable(is_vm) and is_vm() is True:
            return True
    except Exception:
        pass

    # 2. Verifica content_type (MIME type)
    ct = (attachment.content_type or "").lower()
    if any(tipo in ct for tipo in ("audio/", "ogg", "opus")):
        return True

    # 3. Verifica extensão do arquivo
    ext = Path(attachment.filename.lower()).suffix
    return ext in AUDIO_EXTENSIONS


def transcrever_arquivo_audio(
    caminho_arquivo: Path | str,
    idioma: str = WHISPER_LANGUAGE,
) -> str:
    """Transcreve um arquivo de áudio local em texto usando faster-whisper (síncrono)."""
    model = get_whisper_model()
    segments, info = model.transcribe(
        str(caminho_arquivo),
        language=idioma,
        beam_size=5,
        vad_filter=True,  # Filtro de detecção de atividade de voz (ignora silêncio)
    )

    textos = []
    for segment in segments:
        texto_seg = segment.text.strip()
        if texto_seg:
            textos.append(texto_seg)

    transcricao = " ".join(textos).strip()
    logger.info(
        "Áudio processado (duracao=%.1fs, idioma detectado=%s, prob=%.2f): '%s'",
        info.duration,
        info.language,
        info.language_probability,
        transcricao[:80],
    )
    return transcricao


async def baixar_e_transcrever_anexo_audio(
    attachment: discord.Attachment,
    idioma: str = WHISPER_LANGUAGE,
) -> Tuple[Optional[str], Optional[str]]:
    """Baixa o anexo de áudio em arquivo temporário, transcreve com faster-whisper
    e garante que o arquivo temporário seja apagado imediatamente ao finalizar.
    
    Retorna uma tupla: (texto_transcrito, mensagem_de_erro)
    """
    temp_path: Optional[Path] = None

    try:
        # Extrai extensão original ou assume .ogg (padrão de mensagens de voz do Discord)
        ext = Path(attachment.filename.lower()).suffix or ".ogg"

        # Cria arquivo temporário com a extensão correspondente
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
            temp_path = Path(tmp.name)

        logger.info(
            "Baixando áudio temporário de %s (%s, %d bytes) em %s...",
            attachment.filename,
            attachment.content_type,
            attachment.size,
            temp_path,
        )

        # Salva o arquivo de áudio recebido no disco temporário
        await attachment.save(temp_path)

        # Executa a inferência de transcrição em thread pool para não travar o loop do bot
        logger.info("Transcrevendo áudio com faster-whisper (idioma: %s)...", idioma)
        texto_transcrito = await asyncio.to_thread(transcrever_arquivo_audio, temp_path, idioma)

        return (texto_transcrito if texto_transcrito else None), None

    except Exception as e:
        logger.exception("Falha na transcrição do áudio %s: %s", attachment.filename, e)
        return None, str(e)

    finally:
        # REGRA CRÍTICA: Apaga arquivos temporários imediatamente
        if temp_path and temp_path.exists():
            try:
                temp_path.unlink()
                logger.info("Arquivo de áudio temporário apagado com sucesso: %s", temp_path)
            except Exception as ex_delete:
                logger.warning("Falha ao apagar arquivo temporário %s: %s", temp_path, ex_delete)
