# Módulo: [Nome do Módulo]

## 1. Responsabilidade Única
[Descrição sucinta do papel do módulo no ecossistema da aplicação.]

## 2. Classificação
- **Tipo:** [Módulo Interno | Módulo Externo]
- **Localização dos Fontes:** `caminho/para/o/codigo/`

## 3. Pontos de Entrada e Interfaces
- **Endpoints Expostos / Métodos Públicos:**
  - `funcaoOuEndpoint(param: Tipo): Retorno` — Descrição do comportamento.
- **Assinaturas de Eventos ou Comandos Consumidos:**
  - `NomeDoEvento` — Payload esperado e ação disparada.

## 4. Dependências Diretas
- **Módulos Internos:** `[modulo-a]`, `[modulo-b]`
- **Bibliotecas / Serviços Externos:** `[lib-ou-sdk]`

## 5. Contratos e Entidades de Dados
- **Entidades de Domínio / Estruturas de Dados:**
  ```json
  {
    "campo": "tipo"
  }
  ```
- **Payloads Manipulados:**
  - Entrada: `SchemaEntrada`
  - Saída: `SchemaSaida`

## 6. Histórico de Validação (`idea_generator`)
- **Status:** [APROVADA | REFINADA]
- **Melhorias Aplicadas:**
  - [Melhoria/simplificação 1]
  - [Melhoria/simplificação 2]
