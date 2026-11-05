# Especificação de Ideia de Módulo: Resumo Matinal Diário (Morning Digest)

**Código da Proposta:** `IDEA-02`  
**Status:** ✅ **ENTREGUE / EM PRODUÇÃO (v2.5.0)**  
**Módulo Oficial:** Veja a especificação ativa em [`../modulos_visiveis/08_RESUMO_MATINAL_DIGEST.md`](file:///Users/rodrigomodel/antigravity/discord/SPECs/modulos_visiveis/08_RESUMO_MATINAL_DIGEST.md)  
**Impacto:** Converte o bot de um assistente puramente reativo para um assistente proativo matinal diário.  

---

## 1. Justificativa e Motivação

Atualmente, o bot só interage quando provocado pelo usuário ou quando um alarme de lembrete dispara. Um assistente pessoal de alto padrão deve iniciar o dia do usuário com um resumo consolidado das atividades planejadas, compromissos na agenda do Google, itens pendentes na lista de tarefas e previsão do tempo, tudo narrado em voz (áudio) e sumarizado em texto elegante.

---

## 2. Funcionamento do Módulo

1. **Agendamento Cron:** Um worker assíncrono dispara diariamente em horário configurado (ex: `08:00` no fuso local).
2. **Coleta de Informações:**
   - **Google Calendar:** Busca todos os eventos agendados para o dia (`google_calendar.listar_compromissos(dias=1)`).
   - **Lembretes:** Coleta todos os lembretes pendentes agendados para o dia de hoje.
   - **Listas:** Verifica itens pendentes na lista principal de tarefas ou mercado.
   - **Clima (opcional):** Consulta temperatura e condição meteorológica via Open-Meteo API (gratuita e sem chave).
3. **Geração Cognitiva pela LLM:**
   A LLM recebe o JSON consolidado e redige uma saudação matinal personalizada, entusiasmada e sucinta.
4. **Entrega Multimodal:**
   - O texto formatado é postado no canal ou na DM do usuário.
   - Se o usuário tiver preferência de áudio ou ambos, a voz Francisca narra o resumo matinal.

---

## 3. Comandos Propostos

* `!digest agora`: Força o disparo do resumo matinal imediatamente para testes.
* `!digest config [hora]`: Define o horário preferido do usuário (ex: `!digest config 07:30`).
* `!digest on` / `!digest off`: Ativa ou suspende o recebimento automático diário.

---

## 4. Exemplo de Saída Esperada

```markdown
☀️ **BOM DIA, RODRIGO! Aqui está o seu resumo de hoje (19/10/2026):**

📅 **Compromissos na sua Agenda:**
• `10:00` — Reunião de Planejamento de Sprint (Google Meet)
• `15:30` — Alinhamento com time de arquitetura

⏰ **Lembretes Agendados:**
• `12:30` — Tomar suplementação de vitamina D

🛒 **Tarefas & Listas Pendentes:**
• 2 itens pendentes na lista de Mercado (*Café em pó, Pão integral*)

🌦️ **Previsão do Tempo:** Curitiba — 18°C, parcialmente nublado, sem chuva prevista.

🎙️ *(Áudio narrado em anexo pela Francisca)*
```
