# Dossiê de Brainstorm Dialético: Roteirização Fonética & Translação Oral Híbrida para TTS

- **Sessão:** `BRN-26110901`
- **Data:** 09/11/2026
- **Status:** Concluído & Transmutado (Classificação: **OURO PURO 9.52**)
- **Orquestrador:** [`agent_manager`](file:///Users/rodrigomodel/antigravity/.agents/skills/agent_manager/SKILL.md)
- **Artefato Lapidado:** [`alquimista_ideias/ouro/26110901_alquimia_95_translacao_oral_hibrida_tts.json`](file:///Users/rodrigomodel/antigravity/alquimista_ideias/ouro/26110901_alquimia_95_translacao_oral_hibrida_tts.json)

---

## 1. Provocação Original do Arquiteto-Chefe [Usuário]

> *"Hoje quando eu escuto o áudio, o áudio vem com tudo que está no texto escrito, inclusive lê emojis, figurinhas, modelo utilizado, etc. O áudio deveria focar mais apenas no texto em si, pois lê informações que não são necessariamente relevantes faladas. Rediscutir via `/brainstorm`."*

---

## 2. Fase 0: Divergência Ontológica com o Oráculo Hermético (`/oraculo`)

O Oráculo desafiou a premissa de que o áudio de um assistente de IA deve ser um espelho fidedigno da tipografia do chat. Ele apontou a "ilusão grafocêntrica" de forçar um sintetizador neural a mastigar hieróglifos e emojis visuais.

### As 7 Anomalias Ontológicas Geradas:
1. **A Hipocrisia do Espelho Textual (O Fim do TTS Clone):** Áudio e texto são mídias com gramáticas distintas; o áudio precisa de cadência e respiração.
2. **O Exorcismo dos Glifos Retinianos (Purificação Fonética Estrita):** Eliminação compulsória de qualquer emoji Unicode, badge de latência ou metadado de infraestrutura.
3. **O Roteirista de Bolso (Translação Oral Assistida):** Conversão de números, siglas e artigos técnicos para formas naturalmente faladas.
4. **A Ilusão da Cadência (Pausas de Respiração Prosódica):** Emprego de micro-pausas para dar ritmo orgânico à voz da Francisca.
5. **O Dilema da Assimetria de Informação:** Como sintetizar sem perder o valor analítico do parecer escrito.
6. **O Audio-Tagging Holográfico (Persona por Prosódia):** Transmitir a autoridade da persona pelo tom e velocidade, não por ler o currículo em voz alta.
7. **A Assinatura Acústica Orgânica:** Aberturas e fechamentos conversacionais humanizados.

**Gema Selecionada:** *"A Dualidade de Mídia & O Pipeline de Roteirização Fonética (O Desacoplamento Radical entre Texto de Chat e Roteiro de Áudio)"*.

---

## 3. Fase 1: A Mesa de Discussão dos 5 Especialistas

### 🔹 Rodada 1: Diagnóstico Inicial Independente
- **`/hacker`:** Propôs sanitização por regex em Python puro com custo zero de latência e tokens.
- **`/critic`:** Alertou para os riscos de omissão de prazos ou números caso o áudio fosse resumido arbitrariamente.
- **`/impact`:** Enxergou o potencial de retenção 10x ao transformar o bot em uma experiência humanizada de mensagem de voz.
- **`/ux_designer`:** Destacou a heurística de reconhecimento sobre memorização e desenhou o modelo mental de áudio sem atrito.
- **`/architect`:** Esboçou a separação de responsabilidades em pipeline de 2 estágios.

### ⏸️ Calibração Humana (Diretrizes Soberanas do Usuário):
1. **Manter a integralidade absoluta do texto:** Nada de cortar ou omitir argumentos técnicos.
2. **Submenu de Escolha no `!voz`:** O usuário pode alternar entre motor `Local` (rápido/regex) e `IA` (roteirizado com prosódia).
3. **Modo Áudio Nativo:** Quando configurado em `modo = audio`, a chamada primária da LLM já deve receber no System Prompt a instrução de gerar texto oral direto na fonte, sem gastar uma segunda chamada de LLM!

### 🔹 Rodada 2: Confronto Cruzado & Desmontes
- O Hacker celebrou a economia de tokens do Modo Áudio Nativo, mostrando que ele resolve a latência.
- O Crítico exigiu temperatura zero e prompt estrito na rota IA para blindar contra alucinações na translação oral.
- O UX Designer apresentou o wireframe do submenu interativo do comando `!voz`.
- O Arquiteto formalizou o modelo de dados em `user_voice_settings` e o módulo `audio_normalizer.py`.

### 🔹 Rodada 3: Posições Finais & Consenso Unânime
- **`/hacker`:** *"Aprovado com louvor! O Modo Áudio Nativo é engenharia pura de bypass de custo. Exijo apenas que a rota Local tenha cobertura completa de regex para emojis e símbolos matemáticos."*
- **`/critic`:** *"Aprovado com a exigência mandatória de blindagem: integridade factual de 100% dos dados na rota IA e segmentação fonética segura no Edge-TTS."*
- **`/ux_designer`:** *"Aprovado! O submenu de seleção no Discord UI dá soberania total ao usuário entre velocidade e riqueza prosódica."*
- **`/impact`:** *"Aprovado! O ecossistema ganha um diferencial competitivo que nenhum outro bot no Discord possui."*
- **`/architect`:** *"Aprovado! Arquitetura desacoplada, extensível e 100% não-bloqueante no Event Loop."*

---

## 4. Fase 2: Parecer e Score do Alquimista (`/alquimista`)

- **ID da Alquimia:** `ALQ-26110901`
- **Classificação:** **OURO PURO**
- **Score:** **9.52 / 10.0**
  - *Singularidade:* 9.6
  - *Assimetria de Valor:* 9.5
  - *Viabilidade / Custo:* 9.4
- **Justificativa:** A proposta resolve de forma definitiva o maior atrito auditivo de bots conversacionais, transformando o TTS numa mídia autônoma de altíssima elegância, sem custos adicionais de tokens no modo áudio puro e com flexibilidade total no modo misto.

---

## 5. Próximos Passos
1. Formalização da **`IDEA-28`** pelo `/architect` em [`discord/SPECs/SPECS_IDEIAS/28_ROTEIRIZACAO_FONETICA_E_AUDIO_TRANSLATION_TTS.md`](file:///Users/rodrigomodel/antigravity/discord/SPECs/SPECS_IDEIAS/28_ROTEIRIZACAO_FONETICA_E_AUDIO_TRANSLATION_TTS.md).
2. Emissão de Ordem de Serviço pelo `/agent_manager` para implementação pelo `/coder`.

