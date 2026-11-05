"""
Módulo de Funções Utilitárias.

Fornece rotinas auxiliares para divisão inteligente de mensagens no limite do Discord,
manipulação de fusos horários, formatação de texto e manipulação de comandos.
"""

from datetime import datetime
from typing import List, Optional, Tuple
import zoneinfo
from config import MAX_CHUNK_LENGTH


def obter_hora_formatada(fuso_horario: str = "America/Sao_Paulo") -> str:
    """Retorna a data e hora atual em um formato legível para o usuário."""
    try:
        tz = zoneinfo.ZoneInfo(fuso_horario)
        agora = datetime.now(tz)
        return agora.strftime("%Y-%m-%d %H:%M:%S (%Z)")
    except Exception as e:
        return f"Erro ao obter horário com fuso '{fuso_horario}': {str(e)}"


def dividir_mensagem(
    texto: str,
    limite: int = MAX_CHUNK_LENGTH,
    max_length: Optional[int] = None,
) -> List[str]:
    """Divide mensagens longas em pedaços de no máximo `limite` caracteres.
    
    A divisão prioriza quebras naturais de parágrafo (\n\n), quebras de linha (\n)
    ou espaços em branco para evitar cortar palavras no meio.
    """
    alvo_limite = max_length if max_length is not None else limite
    if not texto:
        return []

    if len(texto) <= alvo_limite:
        return [texto]

    chunks: List[str] = []
    restante = texto.strip()

    while len(restante) > alvo_limite:
        ponto_corte = -1

        # 1. Tenta cortar no último parágrafo antes do limite
        ultimo_paragrafo = restante.rfind("\n\n", 0, alvo_limite)
        if ultimo_paragrafo != -1 and ultimo_paragrafo > alvo_limite // 3:
            ponto_corte = ultimo_paragrafo + 2

        # 2. Se não encontrou parágrafo razoável, tenta quebra de linha simples
        if ponto_corte == -1:
            ultima_linha = restante.rfind("\n", 0, alvo_limite)
            if ultima_linha != -1 and ultima_linha > alvo_limite // 3:
                ponto_corte = ultima_linha + 1

        # 3. Se não encontrou linha, tenta espaço em branco
        if ponto_corte == -1:
            ultimo_espaco = restante.rfind(" ", 0, alvo_limite)
            if ultimo_espaco != -1 and ultimo_espaco > alvo_limite // 3:
                ponto_corte = ultimo_espaco + 1

        # 4. Caso extremo: corta rigidamente no limite
        if ponto_corte == -1:
            ponto_corte = alvo_limite

        pedaco = restante[:ponto_corte].strip()
        if pedaco:
            chunks.append(pedaco)
        restante = restante[ponto_corte:].strip()

    if restante:
        chunks.append(restante)

    return chunks


def parse_comando(conteudo: str, prefixo: str = "!") -> Tuple[Optional[str], str, List[str]]:
    """Analisa se uma mensagem é um comando com prefixo.
    
    Retorna uma tupla (nome_comando, arg_str, args_list).
    Caso não seja comando, retorna (None, "", []).
    """
    if not conteudo or not conteudo.startswith(prefixo):
        return None, "", []

    sem_prefixo = conteudo[len(prefixo):].strip()
    if not sem_prefixo:
        return None, "", []

    partes = sem_prefixo.split()
    cmd_name = partes[0].lower()
    args_list = partes[1:]
    arg_str = sem_prefixo[len(partes[0]):].strip()

    return cmd_name, arg_str, args_list


def formatar_bloco_codigo(conteudo: str, linguagem: str = "") -> str:
    """Envolve o conteúdo em um bloco de código markdown seguro."""
    return f"```{linguagem}\n{conteudo}\n```"
