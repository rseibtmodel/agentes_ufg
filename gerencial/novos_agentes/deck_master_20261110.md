# Registro de Novo Agente: Deck Master (Arquiteto de Apresentações Executivas & Técnicas)

- **ID:** `NEW-015`
- **Data de Concepção:** 10/11/2026
- **Nome Funcional:** `deck_master` (Deck Master)
- **Comandos Oficiais:** `/deck`, `/slides`, `/apresentacao`
- **Camada:** Comunicação & Estratégia Executiva
- **Status:** Criado (Homologado & Integrado)

---

## 📌 Justificativa no Projeto
O ecossistema multiagente alcançou alta maturidade técnica (14 agentes, roteamento híbrido, outbox com leaky bucket, metamorfose de personas, deep research e RAG multimodal), porém carecia de uma entidade dedicada a comunicar e demonstrar o valor dessa arquitetura para diferentes públicos (diretoria, investidores, desenvolvedores e clientes). O `deck_master` supre essa lacuna ao traduzir documentação e código em apresentações executivas concisas de 5 minutos (formato Marp), com métricas reais auditadas do repositório e notas cronometradas de oratória.

---

## 🛠️ Stack Dominada & Ferramentas
- Markdown & Ecossistema Marp (Marp Core / Marp CLI)
- Diagramas visuais em código Mermaid (Flowcharts, Sequence Diagrams)
- Storytelling técnico e oratória executiva
- Inspeção fática de repositórios (specs, testes unitários, git logs)

---

## 🛡️ Cláusula "O que NÃO faz" (Blast Radius)
- **NÃO altera código em produção:** Escrita restrita a `gerencial/apresentacoes/`.
- **NÃO alucina métricas ou dados:** Obrigação de fidelidade fática estrita aos testes e código.
- **NÃO quebra a densidade de slides:** Teto rigoroso de 40 a 50 palavras por slide e 1 ideia central.

---

## 📦 Artefatos Vinculados
- Skill: [`.agents/skills/deck_master/SKILL.md`](file:///Users/rodrigomodel/antigravity/.agents/skills/deck_master/SKILL.md)
- Regras: [`.agents/rules/deck_master.md`](file:///Users/rodrigomodel/antigravity/.agents/rules/deck_master.md)
- Roster: [`AGENTS.md`](file:///Users/rodrigomodel/antigravity/AGENTS.md)
- Diretório de Saída: [`gerencial/apresentacoes/`](file:///Users/rodrigomodel/antigravity/gerencial/apresentacoes/)
