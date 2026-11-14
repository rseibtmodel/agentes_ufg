# Parecer Técnico do Coder: Scope Creep em Resumo Matinal Diário (`MOD-VIS-08`)

**Data:** 2026-11-14  
**Módulo Auditado:** `discord/SPECs/modulos_visiveis/08_RESUMO_MATINAL_DIGEST.md`  
**Autor:** Estagiário Codificador (Junior Coder)  
**Destinatário:** Auditor Forense de Specs (`/spec-audit`) & Arquiteto-Chefe  

---

## 1. Contexto das Funcionalidades Não Documentadas na Spec Original

O módulo de Resumo Matinal (`MOD-VIS-08`) foi projetado como o principal assistente proativo matinal do bot. Durante a integração com a API Open-Meteo e a esteira de mensageria assíncrona, foram incorporadas salvaguardas de concorrência e normalização de geocodificação para municípios brasileiros.

---

## 2. Detalhamento e Justificativas Técnicas

### 2.1 Desambiguação de Municípios Brasileiros com Tabela de UFs (`BRAZIL_UFS`)
- **Implementação:** [`digest_manager.py`](file:///Users/rodrigomodel/antigravity/discord/digest_manager.py#L188-L245).
- **Racional Técnico:** Ao buscar cidades homônimas ou formatadas como `"Canela/RS"` ou `"Campinas, SP"`, o Open-Meteo frequentemente retornava cidades de outros países ou estados incorretos. A função `normalizar_cidade_busca` fatiou a string e o dicionário de UFs filtrou a resposta pelo campo `admin1` e `country_code == "BR"`, assegurando precisão meteorológica.

### 2.2 Trava de Concorrência em Memória (`_digests_em_andamento`)
- **Implementação:** [`digest_manager.py`](file:///Users/rodrigomodel/antigravity/discord/digest_manager.py#L472-L491).
- **Racional Técnico:** Evita condições de corrida em que o worker assíncrono perpétuo acorda às `08:00` exatamente enquanto o usuário dispara `!digest agora`, impedindo síntese dupla e consumo desnecessário de GPU/Tokens.

### 2.3 Roteamento Centralizado via Outbox Gateway (`MessagePriority.BACKGROUND`)
- **Implementação:** [`digest_manager.py`](file:///Users/rodrigomodel/antigravity/discord/digest_manager.py#L551-L581).
- **Racional Técnico:** Em conformidade com o módulo interno `MOD-INT-07`, todas as mensagens proativas emitidas em background pelo bot devem fluir pelo barramento central com prioridade assíncrona de segundo plano, garantindo anti-spam e reconexão transparente.

### 2.4 Destruição Imediata de Arquivos Temporários de Áudio no Bloco `finally`
- **Implementação:** [`digest_manager.py`](file:///Users/rodrigomodel/antigravity/discord/digest_manager.py#L588-L598).
- **Racional Técnico:** Quando o usuário opta pelo modo `audio` ou `ambos`, o arquivo `.mp3` gerado pela síntese da Francisca é rigidamente excluído do disco temporário no bloco `finally`, prevenindo vazamento de inodes ou espaço em disco.

---

## 3. Recomendação do Coder
Recomenda-se a **Opção A (Manter no código e incorporar à SPEC)**: as adições tornam o módulo extremamente resiliente contra homônimos geográficos, eliminam corridas de concorrência e garantem conformidade com o Outbox Gateway.

