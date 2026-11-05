# Especificação de Ideia de Módulo: Gestão Financeira Pessoal & Controle de Gastos por Chat

**Código da Proposta:** `IDEA-09`  
**Status:** Proposto / Refinado via `idea_generator` (Prioridade Alta )  
**Impacto:** Permite controlar despesas diárias, registrar receitas, acompanhar tetos de gastos e receber relatórios financeiros sem abrir planilhas.

---

## 1. Origem e Validação no Pipeline `idea_generator`

Esta especificação foi submetida e processada pelo pipeline multi-agente da skill **`idea_generator`**:

1. **💡 Geração Criativa (`Ideator`):**
   O módulo IDEA-09 resolve a maior dor do controle financeiro pessoal: a fricção operacional. Ao integrar o registro de despesas e receitas diretamente via linguagem natural (texto e áudio) no Discord, transformamos um hábito chato e evitado (abrir planilhas ou apps complexos) em uma interação de 2 segundos. A IA categoriza automaticamente a transação, cruza com o banco de dados e emite alertas proativos de teto de gastos (ex: 80% ou 100% da categoria), gerando relatórios instantâneos e mantendo o usuário no controle sem atrito.

2. **😈 Análise Crítica (`Devil's Advocate`):**
   Riscos críticos identificados: 1. Segurança e Privacidade (LGPD/GDPR): Armazenar dados financeiros sensíveis em banco de dados padrão (SQLite) sem criptografia em repouso e sem mascaramento de dados é uma falha grave de segurança. 2. Ambiguidade de Linguagem Natural: Mensagens como 'gastei 50 com meu irmão' podem gerar falsos positivos na categorização ou atribuição de contas. 3. Alucinação da IA: Modelos de linguagem podem extrair valores errados, corrompendo o histórico financeiro do usuário. 4. Confiabilidade e Fuso Horário: O tratamento incorreto de timestamps em áudios e mensagens pode bagunçar relatórios diários e mensais.

3. **🏆 Defesa Estratégica (`Champion`):**
   Apesar dos riscos, o potencial de retenção e engajamento diário (DAU) é massivo. Ferramentas financeiras falham porque exigem esforço ativo; este módulo traz a ferramenta para onde o usuário já passa o dia. Para mitigar as falhas apontadas, podemos implementar uma etapa de confirmação rápida (botões interativos do Discord: Confirmar/Editar) antes de salvar no banco, garantindo precisão de 100%. Além disso, o valor agregado de transformar o bot de chat em um assistente de vida pessoal (LifeOps) eleva drasticamente o LTV (Lifetime Value) e a percepção de valor do ecossistema.

4. **⚖️ Veredito do Gatekeeper & Mitigação:**
   * **Status:** `[APROVADA]`
   * **Diretrizes e Condicionantes:** A proposta está APROVADA sob condições estritas de segurança da informação e validação humana na interface do Discord. Condicionantes obrigatórias: 1. Criptografia ponta a ponta e mascaramento estrito de dados financeiros no banco. 2. Obrigigatoriedade de um painel de confirmação rápida via componentes do Discord (botões de confirmação/edição) para evitar alucinações da IA em valores monetários. 3. Isenção expressa de responsabilidade financeira (o bot fornece controle e estimativas, não consultoria financeira oficial).

5. **✍️ Síntese do Editor (`Editor/Enricher`):**
   O módulo IDEA-09 (Gestão Financeira Pessoal & Controle de Gastos) foi aprovado e enriquecido com um protocolo rigoroso de segurança e precisão. Plano de mitigação executivo: 1. Arquitetura de Confirmação em Duas Etapas: A IA processa o texto/áudio/comprovante e exibe um card interativo no Discord com os dados extraídos (Valor, Categoria, Tipo) e botões 'Confirmar', 'Editar' ou 'Cancelar'. 2. Segurança Reforçada: Dados transacionais anonimizados/criptografados e isolamento por ID de usuário do Discord. 3. Alertas Proativos: Notificações inteligentes quando o usuário atingir 80% e 100% dos limites de orçamento definidos. Próximos passos: Implementar o parser NLP/LLM, criar o esquema seguro no SQLite com chaves de criptografia e desenvolver os componentes de UI interativos via Discord v14.

---

## 2. Justificativa e Motivação

A maior causa de fracasso no controle financeiro pessoal é a fricção de registro: ter que abrir um aplicativo de banco, aplicativo de finanças ou planilha a cada pequeno café, almoço ou corrida de aplicativo.

Como o usuário já conversa diariamente com o bot no Discord (por texto e áudio), permitir o registro instantâneo em linguagem natural — *"Gastei 45 reais no almoço com a equipe"* ou enviar foto/áudio de comprovante — elimina totalmente a barreira de entrada, criando uma visão orçamentária viva e sempre atualizada.

---

## 3. Arquitetura Proposta

```mermaid
flowchart LR
    UserMsg[Usuário: 'Paguei 120 de gasolina no posto Shell'] --> NLPParser{Extração Inteligente}
    NLPParser --> ExtractedData[Valor: 120.00 | Cat: Transporte | Tipo: Despesa]
    ExtractedData --> SQLiteDB[(Tabela: financial_transactions)]
    SQLiteDB --> BudgetCheck{Verifica Teto da Categoria}
    BudgetCheck -->|Dentro da Meta| OKMsg[Confirmação com Saldo Restante]
    BudgetCheck -->|Alerta > 80%| WarningMsg[⚠️ Alerta: Você atingiu 85% do teto de Transporte!]
    OKMsg & WarningMsg --> DiscordReply[Resposta no Discord]
```

---

## 4. Capacidades e Comandos

### 3.1 Registro Conversacional Fluido
- O usuário pode digitar ou enviar áudio:
  - *"Anote um gasto de R$ 38 na farmácia"*
  - *"Recebi 1.500 reais de um projeto freelance"*
  - *"Paguei a conta de luz, deu 240 reais"*
- A IA classifica a categoria automaticamente (`Alimentação`, `Transporte`, `Moradia`, `Saúde`, `Lazer`, `Educação`, `Trabalho`).

### 3.2 Comandos com Prefixo
- `!gasto <valor> <descrição>`: Registro direto sem necessidade de interpretação longa (ex: `!gasto 45.90 Almoço`).
- `!gastos [mes/semana]`: Exibe o extrato consolidado do período com gráfico de barras em texto ou distribuição percentual por categoria.
- `!orcamento definir <categoria> <valor_limite>`: Define um teto mensal (ex: `!orcamento definir Transporte 600`).
- `!balanco`: Exibe o resultado financeiro líquido do mês (Receitas - Despesas).

### 3.3 Integração com Resumo Matinal (`!digest`)
- O Resumo Matinal ganha um card opcional de acompanhamento financeiro:
  > 💳 **Finanças do Mês:** R$ 1.840 gastos de R$ 3.000 da meta (61%).  
  > *Ontem você registrou 2 despesas somando R$ 83,00.*

---

## 5. Ferramentas da LLM (Function Calling)

1. `registrar_transacao_financeira(valor: float, categoria: str, descricao: str, tipo: str = "despesa", data: Optional[str] = None)`
2. `consultar_resumo_gastos(periodo: str = "mes_atual", categoria: Optional[str] = None)`
3. `definir_orcamento_categoria(categoria: str, valor_limite: float)`

---

## 6. Estrutura do Banco de Dados (SQLite)

```sql
CREATE TABLE IF NOT EXISTS financial_transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    tipo TEXT NOT NULL CHECK(tipo IN ('despesa', 'receita')),
    valor REAL NOT NULL,
    categoria TEXT NOT NULL,
    descricao TEXT NOT NULL,
    data_transacao DATE DEFAULT (date('now', 'localtime')),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS financial_budgets (
    user_id TEXT NOT NULL,
    categoria TEXT NOT NULL,
    teto_mensal REAL NOT NULL,
    PRIMARY KEY (user_id, categoria)
);
```

---

## 7. Configurações em `.env`

```ini
FINANCE_MODULE_ENABLED=true
FINANCE_DEFAULT_CURRENCY=BRL
FINANCE_ALERT_THRESHOLD_PERCENT=80
```
