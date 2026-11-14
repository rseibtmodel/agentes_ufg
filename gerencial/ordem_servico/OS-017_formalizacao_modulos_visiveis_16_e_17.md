# Ordem de Serviço: OS-017 — Formalização e Auditoria dos Módulos Visíveis MOD-VIS-16 e MOD-VIS-17

**Data de Emissão:** 14 de Novembro de 2026  
**Emissor:** Gerente de Engenharia & Orquestrador do Ecossistema (`/gerente`)  
**Destinatários:** [`/doc_master`](file:///Users/rodrigomodel/antigravity/.agents/skills/doc_master/SKILL.md), [`/spec-audit`](file:///Users/rodrigomodel/antigravity/.agents/skills/spec-audit/SKILL.md) e [`/review`](file:///Users/rodrigomodel/antigravity/.agents/skills/review/SKILL.md)  
**Status:** Em Execução  

---

## 👑 1. Diretriz do Arquiteto-Chefe [Usuário]
O Arquiteto-Chefe aprovou a **Rota Recomendada**, determinando a formalização dos dois subsistemas ativos em produção que careciam de especificações canônicas no diretório `discord/SPECs/modulos_visiveis/`:
1. `MOD-VIS-16`: Pesquisa Profunda & Dossiês Analíticos (`deep_research_manager.py`).
2. `MOD-VIS-17`: Antigravity Remote Runner & Telemetria Read-Only (`agy_manager.py`).

---

## 📌 2. Objetivos Imediatos

1. **Despacho ao `/doc_master`:**
   - Criar `discord/SPECs/modulos_visiveis/16_PESQUISA_PROFUNDA_DEEP_RESEARCH.md` com taxonomia estrita, frontmatter YAML, arquitetura de pesquisa recursiva em paralelo, semáforo assíncrono (`asyncio.Semaphore(3)`), comandos `!pesquisa_profunda` e persistência em `discord/relatorios_pesquisa/`.
   - Criar `discord/SPECs/modulos_visiveis/17_EXECUCAO_LOCAL_DE_SKILLS_E_TELEMETRIA_AGY.md` com taxonomia estrita, frontmatter YAML, arquitetura segura Read-Only, telemetria de processo (`resource.getrusage`), comandos `!agy` e ferramentas de IA (`listar_skills_antigravity`, `consultar_skill_antigravity`).
   - Sincronizar o arquivo `discord/SPECs/SPECS_IDEIAS_IMPLEMENTADAS/README.md` incorporando as entradas de `IDEA-17` e `IDEA-23`.
2. **Despacho ao `/spec-audit` & `/review`:**
   - Executar auditoria de rastreabilidade reversa em ambos os novos módulos.
   - Emitir os laudos técnicos formais `REV-029` (Deep Research) e `REV-030` (AGY Runner).
   - Salvar relatórios consolidados em `gerencial/auditorias/`.
   - Anexar as matrizes de rastreabilidade com links clicáveis ao final de cada nova especificação.

---

## 🛡️ 3. Limites & Blast Radius

- Escrita de código de produção estritamente proibida (zero alterações em `discord/*.py`).
- Escrita permitida exclusivamente em `discord/SPECs/`, `gerencial/reviews/`, `gerencial/auditorias/` e `gerencial/ordem_servico/`.
- Preservar a estabilidade da suíte de 41 testes unitários sem regressões.

---

## 📦 4. Artefatos Esperados

1. `discord/SPECs/modulos_visiveis/16_PESQUISA_PROFUNDA_DEEP_RESEARCH.md`
2. `discord/SPECs/modulos_visiveis/17_EXECUCAO_LOCAL_DE_SKILLS_E_TELEMETRIA_AGY.md`
3. `discord/SPECs/SPECS_IDEIAS_IMPLEMENTADAS/README.md` atualizado
4. `gerencial/reviews/REV-029_auditoria_pesquisa_profunda_deep_research.md`
5. `gerencial/reviews/REV-030_auditoria_execucao_local_skills_telemetria_agy.md`
6. `gerencial/auditorias/auditoria_2026-11-14_16_PESQUISA_PROFUNDA_DEEP_RESEARCH.md`
7. `gerencial/auditorias/auditoria_2026-11-14_17_EXECUCAO_LOCAL_DE_SKILLS_E_TELEMETRIA_AGY.md`

