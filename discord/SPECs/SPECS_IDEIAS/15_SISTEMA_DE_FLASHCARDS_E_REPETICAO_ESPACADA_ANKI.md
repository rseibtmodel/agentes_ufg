# Especificação de Ideia de Módulo: Flashcards & Repetição Espaçada (Algoritmo SM-2 / Anki)

**Código da Proposta:** `IDEA-15`  
**Status:** Proposto / Refinado via `idea_generator` (Aprendizado & Produtividade )  
**Impacto:** Converte automaticamente livros, PDFs e artigos lidos em cartões de estudo mnemônicos, gerenciando revisões diárias no Discord baseadas na curva do esquecimento.

---

## 1. Origem e Validação no Pipeline `idea_generator`

Esta especificação foi submetida e processada pelo pipeline multi-agente da skill **`idea_generator`**:

1. **💡 Geração Criativa (`Ideator`):**
   O módulo IDEA-15 transforma o Discord Bot em um sistema de estudo ativo e mnemônico de alto nível, integrando o algoritmo SM-2 para repetição espaçada. A partir de PDFs, resumos ou anotações já processadas pelo bot, a LLM extrai conceitos-chave e gera flashcards automaticamente. O usuário executa rodadas diárias de 2 minutos diretamente no chat via embeds interativos e botões, combatendo a curva do esquecimento de Ebbinghaus e integrando o ecossistema com exportação direta para o Anki (.apkg).

2. **😈 Análise Crítica (`Devil's Advocate`):**
   A implementação de flashcards no Discord apresenta fricções significativas de UX: interfaces baseadas em chats de texto são inerentemente poluídas para revisões rápidas, o tempo de resposta da API de componentes (botões) pode gerar frustração, e a lógica de persistência do SM-2 (intervalos, facilidade, repetições) em SQLite exige alta integridade transacional para evitar perda de dados de progresso. Além disso, a geração automática de flashcards por LLMs frequentemente produz perguntas ambíguas, cartões longos demais ou factóides irrelevantes se não houver validação estrita de prompt e filtros de qualidade.

3. **🏆 Defesa Estratégica (`Champion`):**
   Apesar dos desafios de interface do Discord, o ganho de retenção e engajamento recorrente (retenção diária) compensa amplamente o esforço de desenvolvimento. O Discord já é o hub central de estudo e produtividade das comunidades onde o bot opera; trazer o hábito de revisão para dentro da plataforma elimina a necessidade de alternar entre aplicativos. A exportação para o formato .apkg do Anki serve como uma poderosa porta de saída, garantindo que o usuário não se sinta preso a um formato proprietário, o que aumenta a confiança e a adoção do recurso.

4. **⚖️ Veredito do Gatekeeper & Mitigação:**
   * **Status:** `[APROVADA]`
   * **Diretrizes e Condicionantes:** A proposta é altamente sinérgica com a proposta de valor educacional do bot. A aprovação é concedida sob as seguintes condições obrigatórias de segurança e viabilidade técnica: 1) Utilização estrita de Ephemeral Messages nas revisões para não poluir os canais públicos do servidor; 2) Validação rigorosa do JSON de saída da LLM na geração de flashcards para evitar quebras de parsing; 3) Estruturação otimizada do banco SQLite com índices em `user_id` e `due_date` para garantir consultas rápidas em escala.

5. **✍️ Síntese do Editor (`Editor/Enricher`):**
   O módulo IDEA-15 será implementado com foco em usabilidade mobile e desktop via Discord UI (Embeds + Buttons efêmeros). Plano de mitigação de riscos: o motor SM-2 será encapsulado em um módulo Python dedicado e testado unitariamente; a geração de flashcards incluirá um passo de triagem onde o usuário pode aprovar, editar ou descartar os cartões gerados pela LLM antes de salvá-los no deck pessoal; e será disponibilizado um comando de exportação nativo para pacotes `.apkg` do Anki. Próximos passos: criação do schema SQL para os decks e flashcards, desenvolvimento do script do algoritmo SM-2 e prototipagem dos componentes interativos no Discord.

---

## 2. Justificativa e Motivação

Estudos mostram que esquecemos mais de 70% do que lemos em menos de 48 horas se não houver reforço ativo (*Ebbinghaus Forgetting Curve*). Embora o bot já permita resumir livros e conversar com PDFs, a retenção duradoura do conhecimento só ocorre quando o usuário é desafiado a lembrar (*active recall*).

Ao implementar o algoritmo **SM-2** (o mesmo utilizado pelo Anki e SuperMemo), o bot se torna um tutor pessoal de retenção: ele formula perguntas desafiadoras baseadas nos materiais salvos e apresenta pequenas rodadas diárias de revisão de 2 minutos no Discord.

---

## 3. Arquitetura do Ciclo de Repetição Espaçada

```mermaid
flowchart TD
    DocSource[Capítulo de Livro / Artigo Web] --> CardGenerator[LLM: Extração de Fatos e Conceitos-Chave]
    CardGenerator --> CardStore[(SQLite: Tabela flashcards com parâmetros SM-2)]
    
    DailyTrigger[Horário de Estudo / Comando !estudar] --> CardSelector[Seleciona Cards com due_date <= hoje]
    CardSelector --> DiscordQuiz[Envia Pergunta no Discord com Botão 'Revelar Resposta']
    
    DiscordQuiz --> UserReveal[Usuário clica: 'Revelar Resposta']
    UserReveal --> ScoreButtons[Exibe Resposta + Botões de Dificuldade: 🔴 Errei | 🟡 Difícil | 🟢 Bom | 🔵 Fácil]
    
    ScoreButtons --> SM2Engine[Algoritmo SM-2 recalcula: Repetições, Fator de Facilidade e Próximo Intervalo]
    SM2Engine --> CardStore
```

---

## 4. Comandos de Usuário

- **`!flashcards gerar <arquivo_pdf> [capitulo]`**: Analisa o texto do documento e extrai de 5 a 10 flashcards conceituais de alta qualidade.
- **`!estudar`**: Inicia uma sessão de revisão ativa com os cartões agendados para hoje.
- **`!flashcards status`**: Exibe o total de cartões ativos, cartões aprendidos e taxa de retenção.
- **`!flashcards exportar`**: Gera um arquivo de texto compatível para importação direta no Anki Desktop/Mobile.

---

## 5. O Algoritmo SM-2 Integrado

Para cada cartão, o sistema armazena:
- `repetitions` (contagem de revisões consecutivas corretas).
- `interval` (intervalo em dias até a próxima revisão).
- `ease_factor` (fator de facilidade, padrão 2.5).

A cada resposta do usuário (nota de 0 a 5):
$$EF' = EF + (0.1 - (5 - nota) \times (0.08 + (5 - nota) \times 0.02))$$
Garantindo que cartões difíceis apareçam com mais frequência e cartões fáceis sejam espaçados por semanas ou meses.

---

## 6. Estrutura do Banco de Dados (SQLite)

```sql
CREATE TABLE IF NOT EXISTS flashcards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    origem TEXT, -- nome do PDF ou URL
    pergunta TEXT NOT NULL,
    resposta TEXT NOT NULL,
    repetitions INTEGER DEFAULT 0,
    interval_days INTEGER DEFAULT 1,
    ease_factor REAL DEFAULT 2.5,
    due_date DATE DEFAULT (date('now', 'localtime')),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

---

## 7. Configurações em `.env`

```ini
FLASHCARDS_MODULE_ENABLED=true
FLASHCARDS_DAILY_LIMIT=10
FLASHCARDS_INCLUDE_IN_DIGEST=true
```
