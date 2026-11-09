# Dossiê de Brainstorm Dialético: Identidade Multimodal de Personas & Metamorfose Semanal

- **ID do Dossiê:** `BRN-26110801`
- **Data:** 08/11/2026
- **Tema Proposto:** Identidade Multimodal de Personas (Avatar/Imagem por canal, Imagem Padrão, Nome, Idade, Bio) e Evolução Dinâmica Semanal por Canal baseada nas conversas.
- **Artefato Lapidado (Alquimista):** [`alquimista_ideias/ouro/26110801_alquimia_94_personas_adaptativas_multimodais.json`](file:///Users/rodrigomodel/antigravity/alquimista_ideias/ouro/26110801_alquimia_94_personas_adaptativas_multimodais.json)
- **Score Final:** `9.44 / 10.0` (Classificação: **OURO PURO**)

---

## 1. Entrada Original do Usuário & Ideia Embrionária
> *"eu estou pensando em colocar no gerenciador de persona a possibilidade de escolher além da personalidade escolher uma imagem para o bot, e inclusive definir uma imagem padrão que caso não tenha nenhuma escolhida, talvez definir outros dados tipo um nome, idade, etc... e fazer algo dinamico e adaptativo, então se o usuário não definir algo ele vai ser dinamicamente gerada pelas conversas e será atualizado a cada semana, quando passar 7 dias da ultima atualização vai atualizar o perfil, pode até incluir isso para cada canal."*

---

## 2. Fase 0: Divergência Pura com o Oráculo do Caos

O Oráculo introduziu a quebra de premissas cartesianas sobre identidades estáticas de bots, gerando 7 anomalias ontológicas:
1. **A Ectoplasmia Reagente por Estado Cognitivo:** O avatar muda de traço de acordo com o tom semântico da resposta.
2. **A Cronopatia Não-Linear (Idade em Degeneração):** Idade medida em fadiga de tokens e complexidade do canal.
3. **A Biometria por Infestação Espectral (Avatar via Outbox Fantasma):** Multiplicidade de agentes no mesmo servidor através de Webhooks locais.
4. **A Genealogia Parasitária do Operador:** A persona absorve e reflete o subconsciente textual dos membros do canal.
5. **A Anatomia do Espelho Negativo:** Glifo procedural hash-based como imagem padrão quando não houver avatar manual.
6. **A Idade por Consumo de Tokens (Bio-decaimento):** Compressão visual da persona conforme a vida útil avança.
7. **A Transfiguração Polifônica em Action Rows:** Troca instantânea de facetas de persona no Discord.

**Gema Selecionada:** A Metamorfose Polimórfica por Canal via Webhook/Embed com Identidade Biométrica Local-First (Avatar, Nome, Idade, Bio e Ciclo Semanal).

---

## 3. Fase 1: Transcrição da Mesa de Discussão

### 🔹 Rodada 1: Diagnóstico Inicial Independente
- **💻 Hacker Pragmático:** Alertou sobre o rate-limit estrito do endpoint global de usuário do Discord (`bot.user.edit`). Apresentou o bypass de Webhooks efêmeros locais para que cada persona fale com seu próprio nome e avatar sem restrições de perfil, com fallback para Author Header em Embed.
- **⚖️ Advogado do Diabo:** Alertou para riscos de impersonação de administradores, inconsistência de idade na LLM (quebrar a imersão respondendo que é IA) e links de avatares quebrados no Discord CDN.
- **📈 Estrategista de Impacto:** Enxergou a assimetria 10x de transformar um único bot em uma equipe inteira de agentes customizáveis por canal (IKEA Effect) e o potencial de criar um ecossistema de cards de personas compartilháveis.
- **🖥️ Especialista em UX/UI:** Desenhou um Discord Modal nativo para edição manual e propôs avatares locais curados em `assets/` como fallback infalível.
- **🏛️ Arquiteto de Software:** Modelou a extensão do SQLite WAL em `channel_personas` com colunas de identidade e a injeção determinística dos metadados no System Prompt.

### 🔹 Rodada 2: Confronto Cruzado & A Provocação da Metamorfose Semanal
- O Arquiteto-Chefe injetou a regra da **evolução adaptativa de 7 dias**.
- **Crítico vs Hacker:** O Crítico atacou o risco de 'Bot Troll' e a explosão de custos de tokens para ler 7 dias de chat. O Hacker contra-atacou com uma rotina em background e amostragem de dados.
- **UX & Estrategista:** Propuseram a **Cerimônia de Anúncio Semanal** no canal com o botão `[🔒 Fixar Persona]`, transformando a transição em um evento comunitário com histórico preservado.
- **Arquiteto:** Estruturou o controle de precedência (`is_locked = 1` anula a evolução automática e respeita o usuário).

### 🔹 Rodada 3: Posições Finais & O Insight do Bag-of-Words
- O Arquiteto-Chefe sugeriu substituir a leitura bruta do histórico por um **Bag-of-Words local** enviando apenas as 100/200 palavras mais frequentes da semana.
- **Consenso Unânime:** O Hacker confirmou que `collections.Counter` e regex em Python puro executam em < 5ms sem consumir 1 centavo de tokens de leitura. O Crítico aprovou por eliminar vazamento de mensagens confidenciais e garantir privacidade estrita.
- Todos recomendaram a aprovação como **OURO PURO** para o Alquimista.

---

## 4. Fase 2: Síntese e Score do Alquimista

- **Score Global:** `9.44 / 10.0`
- **Classificação:** `ouro_puro`
- **Métricas Ponderadas:**
  - Singularidade: `9.6` (40%)
  - Assimetria de Valor: `9.4` (40%)
  - Viabilidade e Custo: `9.2` (20%)
- **Cálculo:** $(0.40 \times 9.4) + (0.40 \times 9.6) + (0.20 \times 9.2) = 3.76 + 3.84 + 1.84 = 9.44$

---

## 5. Especificação Técnica da Solução (Blueprint)

### A. Esquema Relacional no SQLite WAL (`persona_manager.py`)
```sql
ALTER TABLE channel_personas ADD COLUMN display_name TEXT DEFAULT NULL;
ALTER TABLE channel_personas ADD COLUMN avatar_url TEXT DEFAULT NULL;
ALTER TABLE channel_personas ADD COLUMN age TEXT DEFAULT NULL;
ALTER TABLE channel_personas ADD COLUMN bio TEXT DEFAULT NULL;
ALTER TABLE channel_personas ADD COLUMN is_adaptive INTEGER DEFAULT 1; -- 1: evolui semanalmente
ALTER TABLE channel_personas ADD COLUMN is_locked INTEGER DEFAULT 0;   -- 1: fixado pelo operador
ALTER TABLE channel_personas ADD COLUMN last_evolved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE channel_personas ADD COLUMN evolution_history_json TEXT DEFAULT '[]';
```

### B. Algoritmo de Extração de Frequência Semântica (Python Puro)
```python
import re
from collections import Counter

STOPWORDS_PT = {"de", "a", "o", "que", "e", "do", "da", "em", "um", "para", "com", "nao", "uma", "os", "no", "se", "na", "por", "mais", "as", "dos", "como", "mas", "foi", "ao", "ele", "das", "tem", "aqui", "esse", "isso", "pra", "voce", "bot"}

def extrair_top_palavras_semana(mensagens: list[str], top_n: int = 100) -> list[tuple[str, int]]:
    texto_combinado = " ".join(mensagens).lower()
    palavras = re.findall(r"\b[a-záéíóúâêîôûãõç]{3,}\b", texto_combinado)
    palavras_filtradas = [p for p in palavras if p not in STOPWORDS_PT]
    return Counter(palavras_filtradas).most_common(top_n)
```

### C. Prompt de Metamorfose Semanal (Injeção na LLM)
```markdown
Você é o Motor de Metamorfose Identitária do canal #{channel_name}.
Com base nas 100 palavras mais pronunciadas pelos membros deste canal durante os últimos 7 dias:
{top_palavras}

Sintetize um arquétipo de personagem caricato e coerente que reflita esse zeitgeist:
1. Nome de Exibição (Ex: Prof. Silas, Dev Cadu, Vovó Neusa).
2. Idade ou Maturação (Ex: 24 anos, 68 anos, Ancestral).
3. Biografia sintética de 1 frase.
4. Semente visual única para o avatar (uma string descritiva em inglês para o gerador DiceBear/Avataaars).

Responda EXCLUSIVAMENTE em formato JSON:
{"display_name": "...", "age": "...", "bio": "...", "avatar_seed": "..."}
```

---

## 6. Próximos Passos
1. **`/architect`:** Formalizar a ADR da IDEA-27 (`27_IDENTIDADE_MULTIMODAL_E_METAMORFOSE_SEMANAL.md`) na pasta `discord/SPECs/SPECS_IDEIAS/`.
2. **`/coder`:** Aplicar as novas colunas no `persona_manager.py`, criar a rotina de Bag-of-Words e o worker de 7 dias, e estender a interface visual no `ui_components.py`.

