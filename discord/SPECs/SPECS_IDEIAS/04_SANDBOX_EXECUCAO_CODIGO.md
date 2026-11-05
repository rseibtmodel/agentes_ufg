# Especificação de Ideia de Módulo: Execução Segura de Código (Code Sandbox)

**Código da Proposta:** `IDEA-04`  
**Status:** Proposto / Refinado via `idea_generator` (Prioridade Média )  
**Impacto:** Permite ao bot resolver problemas numéricos complexos, simulações estatísticas e plotar gráficos científicos diretamente no Discord.  

---

## 1. Origem e Validação no Pipeline `idea_generator`

Esta especificação foi submetida e processada pelo pipeline multi-agente da skill **`idea_generator`**:

1. **💡 Geração Criativa (`Ideator`):**
   O módulo IDEA-04 introduz um Code Interpreter nativo no Discord AI Bot. A IA ganha autonomia para programar e executar scripts Python em tempo real, realizando simulações matemáticas avançadas, análise de dados e renderização de gráficos científicos via matplotlib/seaborn. A proposta de valor transforma o bot de um mero gerador de texto probabilístico em um assistente analítico determinístico de alta precisão, essencial para comunidades técnicas, científicas, acadêmicas e financeiras.

2. **😈 Análise Crítica (`Devil's Advocate`):**
   Riscos críticos identificados: 1) Segurança de Execução: Sandboxes baseados apenas em subprocessos locais e diretórios temporários são vulneráveis a escapes de container, ataques de negação de serviço (DoS) via loops infinitos inteligentes e esgotamento de memória. 2) Custos e Recursos: Execuções simultâneas de scripts pesados e renderização de gráficos podem sobrecarregar a CPU do host e estourar banda de rede com arquivos de imagem. 3) Custo de API/Token: A IA pode entrar em loops de tentativa e erro, gerando custos excessivos de chamadas de LLM para corrigir erros de código em cadeia.

3. **🏆 Defesa Estratégica (`Champion`):**
   Apesar dos riscos severos, o IDEA-04 é o divisor de águas definitivo para o engajamento e retenção de usuários power-users e comunidades de engenharia/dados no Discord. Nenhum bot concorrente oferece essa capacidade de forma nativa e segura com facilidade. Ele posiciona o Discord AI Bot como uma ferramenta de produtividade indispensável, elevando o valor percebido do bot de entretenimento/utilidade básica para um ambiente de desenvolvimento e análise de dados colaborativo.

4. **⚖️ Veredito do Gatekeeper & Mitigação:**
   * **Status:** `[APROVADA]`
   * **Diretrizes e Condicionantes:** APROVADA sob condições restritivas de segurança absoluta. O uso de subprocessos locais simples (`/tmp/sandbox_xxx`) é totalmente vetado por riscos de segurança. A implementação deve obrigatoriamente ocorrer em ambientes conteinerizados isolados por hardware virtualizado (ex: gVisor, Firecracker ou Docker rootless com perfis rigorosos de AppArmor/Seccomp) ou via APIs de execução terceirizadas e isoladas (ex: Judge0, E2B ou Pyodide rodando em WebAssembly severamente limitado). Limites de timeout estritos (máximo 5s) e quotas rígidas de CPU/RAM são mandatórios.

5. **✍️ Síntese do Editor (`Editor/Enricher`):**
   Síntese Executiva e Plano de Mitigação: 1) Arquitetura de Isolamento Fortalecida: Substituição do modelo de subprocesso local por uma arquitetura baseada em containers efêmeros isolados com restrições severas de rede (sem acesso à internet) e sem privilégios de root. 2) Sanitização de Entrada/Saída: Blacklist rigorosa de módulos perigosos (os, sys, subprocess, socket) e validação estática via AST (Abstract Syntax Tree) prévia à execução. 3) Gestão de Recursos e Custo: Implementação de circuit breakers para evitar loops de correção de código pela LLM, limitando a 3 tentativas de retry por prompt. 4) Entrega Visual: Captura automática e otimização de imagens geradas via matplotlib antes do envio via Discord Webhook/Message, garantindo limpeza imediata dos arquivos temporários.

---

## 2. Justificativa e Motivação

LLMs são modelos de inferência probabilística e cometem erros frequentes em cálculos de álgebra, estatística, conversões de moedas compostas e análise de dados tabulares. Capacitar a LLM a **escrever e executar scripts Python em um ambiente sandbox isolado** (*Code Interpreter*) eleva a precisão analítica a 100%, além de permitir gerar imagens com gráficos (`matplotlib` / `seaborn`) entregues diretamente no canal.

---

## 3. Arquitetura de Segurança e Isolamento

Executar código gerado por IA requer controle rigoroso para evitar acesso indevido ao sistema de arquivos do host ou comandos maliciosos:

1. **Restrições de Execução:**
   - Execução em subprocesso temporário com limites rígidos de tempo (timeout de 5 segundos) e consumo de memória (max 256MB).
   - Bloqueio de chamadas perigosas (`os.system`, `subprocess`, remoção de arquivos do host).
   - Diretório temporário efêmero em `/tmp/sandbox_xxx/` descartado imediatamente após a execução.
2. **Entrega de Gráficos e Imagens:**
   Se o script gerar uma imagem (ex: `plt.savefig("grafico.png")`), o arquivo de imagem é automaticamente capturado pelo `context_manager` e anexado na resposta do Discord.

---

## 4. Ferramenta da LLM Proposta

### `executar_codigo_python(codigo: str) -> str`
* **Parâmetros:** `codigo: str` — Script Python auto-suficiente contendo imports permitidos (`math`, `datetime`, `numpy`, `pandas`, `matplotlib`).
* **Retorno:** Saída capturada do `stdout` (prints) ou mensagem de erro formatada, além de eventuais gráficos gerados anexados como imagem.

---

## 5. Exemplo de Caso de Uso

* **Usuário:** *"Trace um gráfico comparando o crescimento exponencial com base 2 e base 1.5 de 0 a 10."*
* **LLM:** Invoca `executar_codigo_python(...)` gerando o script `matplotlib`.
* **Bot:** Executa o script em sandbox, anexa a imagem `grafico.png` no canal e responde: *"Aqui está o gráfico comparando as duas curvas de crescimento."*
