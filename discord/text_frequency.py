"""
Módulo de Extração de Frequência Semântica e Bag-of-Words Local (IDEA-27).

Extrai com altíssima eficiência e custo zero de tokens os termos mais frequentes
e relevantes do histórico conversacional de um canal, ignorando ruídos, stopwords,
menções, links e comandos.
"""

from collections import Counter
import re
from typing import List, Optional, Set, Tuple

# Lista defensiva de Stopwords (Português e Inglês)
STOPWORDS_PT_EN: Set[str] = {
    # Português: Artigos, preposições, conjunções e pronomes comuns
    "de", "a", "o", "que", "e", "do", "da", "em", "um", "para", "com", "nao", "uma", "os", "no",
    "se", "na", "por", "mais", "as", "dos", "como", "mas", "foi", "ao", "ele", "das", "tem",
    "aqui", "esse", "isso", "pra", "voce", "bot", "mesmo", "meu", "sua", "nos", "ja", "vai",
    "muito", "seu", "suas", "pelo", "pela", "ate", "tudo", "so", "bem", "dia", "bom", "boa",
    "noite", "tarde", "olá", "ola", "oi", "sim", "estou", "esta", "estao", "estava", "era",
    "sao", "ser", "ter", "fazer", "pode", "podem", "quero", "queria", "quando", "onde", "qual",
    "quem", "qualquer", "cada", "outro", "outra", "outros", "outras", "tanto", "quanto", "ainda",
    "assim", "entao", "tambem", "nem", "sem", "sobre", "depois", "desde", "entre", "num", "numa",
    "pelos", "pelas", "deste", "desta", "desse", "dessa", "disso", "daquele", "daquela", "naquele",
    "naquela", "algo", "nada", "pouco", "muitos", "muitas", "algum", "alguma", "alguns", "algumas",
    # Inglês comum
    "the", "and", "to", "of", "in", "is", "that", "for", "it", "as", "was", "with", "on", "at",
    "by", "this", "be", "are", "from", "or", "an", "they", "which", "one", "you", "we", "all",
    "can", "has", "have", "had", "not", "but", "what", "there", "their", "will", "so", "if",
    "out", "about", "up", "more", "when", "like", "just", "into", "some", "them", "then", "now",
}


def sanitizar_texto_mensagem(texto: str) -> str:
    """Remove URLs, menções, comandos, blocos de código markdown e caracteres especiais."""
    if not texto:
        return ""
    # Remove blocos de código markdown (```...```) e inline code (`...`)
    t = re.sub(r"```[\s\S]*?```", " ", texto)
    t = re.sub(r"`[^`]*`", " ", t)
    # Remove URLs
    t = re.sub(r"https?://\S+|www\.\S+", " ", t)
    # Remove menções e canais do Discord (<@...>, <#...>, <@&...>)
    t = re.sub(r"<[@#&]!?\d+>", " ", t)
    # Remove comandos iniciados com prefixo (ex: !persona, !modelo)
    t = re.sub(r"!\w+", " ", t)
    # Remove emojis customizados do Discord (<:nome:id>)
    t = re.sub(r"<a?:\w+:\d+>", " ", t)
    return t.lower()


def extrair_top_palavras_canal(
    mensagens: List[str],
    top_n: int = 100,
    stopwords_adicionais: Optional[Set[str]] = None,
) -> List[Tuple[str, int]]:
    """Extrai os termos mais frequentes de uma lista de mensagens de um canal.
    
    Args:
        mensagens: Lista de strings com o conteúdo das mensagens trocadas.
        top_n: Quantidade máxima de palavras mais frequentes a retornar.
        stopwords_adicionais: Conjunto opcional de palavras a ignorar.
        
    Returns:
        Lista de tuplas (palavra, contagem) ordenadas por frequência decrescente.
    """
    stopwords = STOPWORDS_PT_EN.union(stopwords_adicionais or set())
    contador: Counter = Counter()

    for msg in mensagens:
        texto_limpo = sanitizar_texto_mensagem(msg)
        if not texto_limpo:
            continue
        # Captura palavras com 3 ou mais caracteres alfanuméricos
        palavras = re.findall(r"\b[a-záéíóúâêîôûãõç]{3,}\b", texto_limpo)
        for p in palavras:
            if p not in stopwords:
                contador[p] += 1

    return contador.most_common(top_n)


def formatar_bag_of_words_prompt(top_termos: List[Tuple[str, int]], max_termos: int = 70) -> str:
    """Formata os termos e suas frequências em uma string compacta e densa para injeção na LLM."""
    if not top_termos:
        return "Nenhum termo relevante identificado."
    termos_selecionados = top_termos[:max_termos]
    itens = [f"{termo} ({freq}x)" for termo, freq in termos_selecionados]
    return ", ".join(itens)

