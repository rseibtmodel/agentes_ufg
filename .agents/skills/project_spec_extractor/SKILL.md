---
name: project_spec_extractor
description: >-
  Analisa o código-fonte e as dependências do repositório para extrair, organizar e manter a documentação de arquitetura, roadmaps e especificações modulares na pasta `specs/`, validando módulos com a skill `idea_generator` e resolvendo ambiguidades com opções estruturadas.
---

# SKILL: project_spec_extractor

## 1. Metadados
- **Nome:** project_spec_extractor
- **Descrição:** Analisa o código-fonte e as dependências do repositório para extrair, organizar e manter a documentação de arquitetura, roadmaps e especificações modulares na pasta `specs/`, validando módulos com a skill `idea_generator` e resolvendo ambiguidades com opções estruturadas.

---

## 2. Estrutura de Diretórios e Arquivos Obrigatória

Toda a documentação gerada ou mantida por esta skill deve residir exclusivamente no diretório `specs/`, respeitando a seguinte árvore:

```plaintext
specs/
├── SPECS.md
├── roadmap.md
├── arquitetura.md
├── modulos_internos/
│   └── [nome-do-modulo].md
└── modulos_externos/
    └── [nome-do-modulo].md
```

### Especificação dos Arquivos Raiz

1. **`specs/SPECS.md`**:
   - Propósito geral, escopo e problema resolvido pelo software.
   - Stack tecnológica completa (linguagens, frameworks, bibliotecas principais, runtimes, ferramentas de build).
   - Guia prático de inicialização/execução identificado nas configurações do repositório.
   - Padrões de código e convenções adotadas.

2. **`specs/roadmap.md`**:
   - Status atual: mapeamento de funcionalidades implementadas vs. pendências identificadas (baseando-se em `TODO`, `FIXME` e lacunas funcionais do código).
   - Linha de evolução sugerida dividida em curto, médio e longo prazo (estabilidade, escalabilidade, refatoração e novas features).

3. **`specs/arquitetura.md`**:
   - Padrão arquitetural identificado (Clean Architecture, Hexagonal, Monolito Modular, Microservices, MVC, etc.).
   - Diagrama conceitual e fluxo de dados de ponta a ponta (usando Mermaid).
   - Decisões técnicas sobre persistência, mensageria/filas, autenticação, tratamento de erros e estado.
   - Trade-offs e débitos técnicos notáveis observados no código.

---

## 3. Classificação e Especificação dos Módulos

Cada funcionalidade ou serviço isolável do sistema deve ser mapeado em um arquivo `.md` próprio dentro de uma das duas pastas:

* **`specs/modulos_internos/[nome-do-modulo].md`**:
  - Abrange regras de negócio centrais, casos de uso, entidades de domínio, controladores, serviços internos e bibliotecas utilitárias proprietárias.

* **`specs/modulos_externos/[nome-do-modulo].md`**:
  - Abrange integrações de terceiros, clientes HTTP/APIs externas, adaptadores de banco de dados, brokers de mensageria (RabbitMQ, Kafka, SQS, etc.), SDKs e gateways de pagamento.

### Conteúdo Mínimo de Cada Arquivo de Módulo:

* **Responsabilidade Única:** Descrição sucinta do papel do módulo.
* **Pontos de Entrada e Interfaces:** Endpoints expostos, métodos públicos, assinaturas de eventos ou comandos consumidos.
* **Dependências Diretas:** O que este módulo consome (outros módulos ou libs).
* **Contratos e Entidades de Dados:** Estruturas de dados e payloads manipulados.

---

## 4. Regras Obrigatórias de Execução

### A. Validação via Skill `idea_generator`

* Antes de gravar ou atualizar qualquer arquivo em `specs/modulos_internos/` ou `specs/modulos_externos/`, o agente deve acionar a skill `idea_generator` ativa no ambiente.
* Submeta a proposta preliminar do módulo (responsabilidade, escopo e dependências).
* Aplique as melhorias, simplificações e correções conceituais sugeridas pela `idea_generator` antes de salvar o arquivo final em disco.

### B. Protocolo de Incertezas (Mínimo de 5 Opções)

* Sempre que houver ambiguidade sobre:
  1. A responsabilidade ou fronteira de um trecho de código;
  2. Se um módulo deve ser classificado como interno ou externo;
  3. Se um componente deve ser desacoplado em um novo módulo ou agrupado em um existente.

* **Ação:** O agente deve pausar imediatamente a escrita e solicitar a decisão do usuário, apresentando obrigatoriamente **pelo menos 5 opções distintas e numeradas**.
* Cada opção deve conter: resumo da abordagem, prós e contras. O processamento do módulo em questão só prossegue após a resposta do usuário.

#### Formato Obrigatório do Protocolo de Incertezas:
```markdown
### ⚠️ Incerteza Arquitetural Identificada
- **Componente / Trecho:** [Identificação do arquivo/código]
- **Dilema:** [Descrição concisa do ponto de dúvida]

#### Opções de Resolução:
1. **Opção 1 — [Título]:** [Resumo]
   - *Prós:* ...
   - *Contras:* ...
2. **Opção 2 — [Título]:** [Resumo]
   - *Prós:* ...
   - *Contras:* ...
3. **Opção 3 — [Título]:** [Resumo]
   - *Prós:* ...
   - *Contras:* ...
4. **Opção 4 — [Título]:** [Resumo]
   - *Prós:* ...
   - *Contras:* ...
5. **Opção 5 — [Título]:** [Resumo]
   - *Prós:* ...
   - *Contras:* ...

Aguardando a sua escolha para prosseguir com a documentação do módulo.
```

---

## 5. Fluxo de Trabalho Operacional

1. **Varredura e Análise:**
   - Inspecione manifests de dependência (`package.json`, `pyproject.toml`, `go.mod`, `pom.xml`, etc.), scripts de automação, variáveis de ambiente de exemplo e o grafo de arquivos do repositório.

2. **Construção dos Documentos Globais:**
   - Escreva ou atualize `specs/SPECS.md`, `specs/arquitetura.md` e `specs/roadmap.md`.

3. **Mapeamento e Validação de Módulos:**
   - Liste os módulos potenciais.
   - Em caso de dúvida arquitetural, consulte o usuário via protocolo de 5 opções.
   - Submeta cada módulo validado à skill `idea_generator`.
   - Crie os arquivos finais em `specs/modulos_internos/` ou `specs/modulos_externos/`.

4. **Finalização:**
   - Gere um resumo com a árvore criada e os módulos documentados.

---

## 6. Recursos e Templates

Para garantir consistência estrutural na criação dos arquivos, consulte os templates:
- **Especificações Globais:** [template_specs.md](./resources/template_specs.md) (`SPECS.md`, `roadmap.md`, `arquitetura.md`)
- **Módulos Internos e Externos:** [template_modulo.md](./resources/template_modulo.md)

