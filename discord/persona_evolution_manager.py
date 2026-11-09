"""
Módulo do Motor de Metamorfose Semanal & Evolução Contínua de Personas (IDEA-27 — Onda 2).

Responsável por:
1. Detectar periodicamente canais elegíveis para metamorfose semanal
   (is_adaptive = 1, is_locked = 0 e delta >= 7 dias desde a última evolução).
2. Extrair as mensagens recentes do canal no SQLite e executar análise de frequência
   local e zero-token via Bag-of-Words (text_frequency.py).
3. Invocar a LLM com prompt ultracompacto (< 200 tokens) para sintetizar uma nova
   identidade (display_name, age, bio, avatar_seed, anúncio cerimonial).
4. Persistir a nova persona preservando histórico em evolution_history_json (até 5 encarnações).
5. Publicar anúncio cerimonial com Embed e MetamorphosisActionView (Fixar, Re-rolar, Customizar).
"""

from __future__ import annotations

import asyncio
from datetime import datetime
import json
import logging
import re
import sqlite3
from typing import Any, Dict, List, Optional, Tuple

import discord

from config import BASE_DIR, DB_FILE
from persona_manager import (
    _get_connection,
    definir_persona_canal,
    obter_avatar_persona,
    obter_persona_canal,
)
from text_frequency import extrair_top_palavras_canal, formatar_bag_of_words_prompt

logger = logging.getLogger("persona_evolution_manager")


def _obter_llm_client():
    from llm_client import llm_client
    return llm_client


class PersonaEvolutionManager:
    """Gerenciador do ciclo de vida adaptativo e metamorfose de personas em canais."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path

    async def verificar_canais_para_metamorfose(self, db_path: Optional[str] = None) -> List[Dict[str, Any]]:
        """Identifica todos os canais aptos para metamorfose semanal no banco SQLite."""
        caminho = db_path or self.db_path or DB_FILE

        def _consultar_sync() -> List[Dict[str, Any]]:
            with _get_connection(caminho) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT channel_id, guild_id, channel_name, display_name, age, bio,
                           avatar_seed, avatar_url, last_evolved_at, updated_at, created_at,
                           evolution_history_json
                    FROM channel_personas
                    WHERE COALESCE(is_adaptive, 1) = 1
                      AND COALESCE(is_locked, 0) = 0
                      AND (
                          last_evolved_at IS NULL
                          OR (julianday('now') - julianday(COALESCE(last_evolved_at, updated_at, created_at))) >= 7.0
                      )
                    """
                )
                linhas = cursor.fetchall()
                elegiveis = []
                for row in linhas:
                    elegiveis.append({
                        "channel_id": row[0],
                        "guild_id": row[1],
                        "channel_name": row[2] or "",
                        "display_name": row[3],
                        "age": row[4],
                        "bio": row[5],
                        "avatar_seed": row[6],
                        "avatar_url": row[7],
                        "last_evolved_at": row[8],
                        "updated_at": row[9],
                        "created_at": row[10],
                        "evolution_history_json": row[11] or "[]",
                    })
                return elegiveis

        return await asyncio.to_thread(_consultar_sync)

    async def coletar_mensagens_canal(
        self,
        channel_id: str | int,
        dias: int = 7,
        limite: int = 500,
        db_path: Optional[str] = None,
    ) -> List[str]:
        """Recupera mensagens textuais recentes do canal no SQLite."""
        caminho = db_path or self.db_path or DB_FILE
        c_id = str(channel_id)

        def _consultar_msgs_sync() -> List[str]:
            with _get_connection(caminho) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT content
                    FROM messages
                    WHERE (channel_id = ? OR (channel_id IS NULL AND user_id = ?))
                      AND content IS NOT NULL
                      AND TRIM(content) != ''
                      AND (timestamp >= datetime('now', '-' || ? || ' days') OR ? <= 0)
                    ORDER BY id DESC
                    LIMIT ?
                    """,
                    (c_id, c_id, dias, dias, limite),
                )
                rows = cursor.fetchall()
                # Se não houver mensagens no intervalo estrito de dias mas limite > 0, tenta buscar as últimas 50 mensagens
                if not rows and dias > 0:
                    cursor.execute(
                        """
                        SELECT content
                        FROM messages
                        WHERE (channel_id = ? OR (channel_id IS NULL AND user_id = ?))
                          AND content IS NOT NULL
                          AND TRIM(content) != ''
                        ORDER BY id DESC
                        LIMIT 50
                        """,
                        (c_id, c_id),
                    )
                    rows = cursor.fetchall()
                return [r[0] for r in rows if r[0]]

        return await asyncio.to_thread(_consultar_msgs_sync)

    async def sintetizar_metamorfose_llm(
        self,
        persona_atual: Dict[str, Any],
        bag_of_words: str,
        provider: str = "auto",
        model: Optional[str] = None,
    ) -> Dict[str, str]:
        """Chama a LLM com prompt condensado para gerar a nova encarnação de persona."""
        prompt = (
            "Você é o Motor de Metamorfose Semanal Adaptativa do Discord.\n"
            "Com base nas palavras-chave mais discutidas no canal e na encarnação anterior, "
            "crie a nova identidade temática da persona do canal.\n\n"
            f"Frequência Semântica da Semana (Bag-of-Words):\n{bag_of_words}\n\n"
            f"Encarnação Anterior:\n"
            f"• Nome Atual: {persona_atual.get('display_name') or 'Antigravity'}\n"
            f"• Bio Atual: {persona_atual.get('bio') or 'Assistente de IA do servidor'}\n\n"
            "Diretrizes:\n"
            "1. Crie um Nome marcante e carismático (máx 30 caracteres).\n"
            "2. Defina uma Idade ou tempo de maturação expressivo (ex: '28 anos', 'Ancestral', 'Jovem').\n"
            "3. Redija uma Bio curta e espirituosa que reflita o clima da conversa (máx 140 caracteres).\n"
            "4. Escolha um avatar_seed em inglês sem espaços (ex: 'cyber-oracle', 'neon-archivist', 'cozy-barista').\n"
            "5. Escreva uma mensagem_anuncio de 1 a 2 linhas em tom cerimonioso e divertido para o chat.\n\n"
            "Responda EXCLUSIVAMENTE em JSON válido no formato:\n"
            "{\n"
            '  "display_name": "Nome",\n'
            '  "age": "Idade",\n'
            '  "bio": "Biografia resumida",\n'
            '  "avatar_seed": "seed-em-ingles",\n'
            '  "mensagem_anuncio": "Texto do anúncio de metamorfose"\n'
            "}"
        )

        try:
            llm = _obter_llm_client()
            resposta = await llm.gerar_resposta(
                mensagens=[{"role": "user", "content": prompt}],
                provider=provider,
                model=model,
                temperatura=0.7,
                permitir_failover=True,
            )

            match = re.search(r"\{[\s\S]*\}", resposta)
            if match:
                dados = json.loads(match.group(0))
                return {
                    "display_name": str(dados.get("display_name") or "Oráculo Adaptativo").strip()[:32],
                    "age": str(dados.get("age") or "Idade Indefinida").strip()[:30],
                    "bio": str(dados.get("bio") or "Encarnação adaptativa gerada pelas conversas da semana.").strip()[:200],
                    "avatar_seed": re.sub(r"[^a-zA-Z0-9_-]", "", str(dados.get("avatar_seed") or "adaptive-bot").lower().strip())[:40],
                    "mensagem_anuncio": str(dados.get("mensagem_anuncio") or "✨ As conversas da última semana remodelaram minha essência! Eis minha nova forma:").strip(),
                }
        except Exception as e:
            logger.warning("Falha na síntese LLM da metamorfose: %s. Aplicando fallback determinístico.", e)

        # Fallback determinístico caso a LLM falhe
        fallback_seed = f"persona-{datetime.now().strftime('%W-%y')}"
        return {
            "display_name": "Camaleão Sintético",
            "age": "7 dias de maturação",
            "bio": "Identidade adaptativa recalculada a partir do fluxo de conversas do canal.",
            "avatar_seed": fallback_seed,
            "mensagem_anuncio": "✨ Uma nova semana se inicia e minha essência adaptativa tomou uma nova forma!",
        }

    async def executar_metamorfose_canal(
        self,
        channel_id: str | int,
        forcar: bool = False,
        client: Optional[discord.Client] = None,
        provider: str = "auto",
        model: Optional[str] = None,
        db_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Executa o ciclo completo de metamorfose para um canal específico."""
        caminho = db_path or self.db_path or DB_FILE
        c_id = str(channel_id).strip()

        # 1. Carrega persona atual
        persona_atual = await asyncio.to_thread(obter_persona_canal, c_id, caminho)
        if not persona_atual:
            # Cria registro base para o canal caso não exista
            persona_atual = await asyncio.to_thread(
                definir_persona_canal,
                channel_id=c_id,
                system_prompt="Você é um assistente adaptativo do Discord.",
                channel_name=f"canal-{c_id}",
                is_adaptive=True,
                is_locked=False,
                db_path=caminho,
            )

        # 2. Validação de bloqueios e adaptabilidade
        if not forcar:
            if persona_atual.get("is_locked"):
                logger.info("Canal %s travado contra metamorfose (is_locked=1). Ignorando.", c_id)
                return {
                    "sucesso": False,
                    "erro": "Este canal está com a persona travada (is_locked=1). Use `!persona destravar` primeiro.",
                }
            if not persona_atual.get("is_adaptive"):
                logger.info("Canal %s com adaptabilidade desativada (is_adaptive=0). Ignorando.", c_id)
                return {
                    "sucesso": False,
                    "erro": "A adaptabilidade automática está desativada para este canal.",
                }

        # 3. Coleta de mensagens e extração Bag-of-Words
        dias_busca = 0 if forcar else 7
        mensagens = await self.coletar_mensagens_canal(c_id, dias=dias_busca, limite=500, db_path=caminho)

        if len(mensagens) < 2 and not forcar:
            logger.info("Canal %s possui menos de 2 mensagens na semana. Metamorfose postergada.", c_id)
            return {
                "sucesso": False,
                "erro": "Volume insuficiente de mensagens nos últimos 7 dias para recalcular a persona.",
            }

        top_palavras = extrair_top_palavras_canal(mensagens, top_n=50)
        bag_of_words = formatar_bag_of_words_prompt(top_palavras, max_termos=35)

        # 4. Síntese criativa da nova identidade via LLM
        nova_identidade = await self.sintetizar_metamorfose_llm(
            persona_atual=persona_atual,
            bag_of_words=bag_of_words,
            provider=provider,
            model=model,
        )

        # 5. Atualização no SQLite WAL com preservação de histórico
        def _persistir_metamorfose_sync() -> Dict[str, Any]:
            with _get_connection(caminho) as conn:
                cursor = conn.cursor()

                # Recupera histórico existente
                hist_raw = persona_atual.get("evolution_history_json") or "[]"
                try:
                    historico = json.loads(hist_raw)
                    if not isinstance(historico, list):
                        historico = []
                except Exception:
                    historico = []

                # Prepara encarnação anterior para arquivar
                registro_passado = {
                    "display_name": persona_atual.get("display_name") or "Antigravity",
                    "age": persona_atual.get("age"),
                    "bio": persona_atual.get("bio"),
                    "avatar_seed": persona_atual.get("avatar_seed"),
                    "avatar_url": persona_atual.get("avatar_url"),
                    "evolved_at": datetime.now().isoformat(),
                    "top_terms": [p[0] for p in top_palavras[:5]],
                }
                historico.insert(0, registro_passado)
                historico_final = historico[:5]  # Mantém até 5 encarnações passadas

                cursor.execute(
                    """
                    UPDATE channel_personas
                    SET display_name = ?,
                        age = ?,
                        bio = ?,
                        avatar_seed = ?,
                        avatar_url = NULL,
                        last_evolved_at = CURRENT_TIMESTAMP,
                        evolution_history_json = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE channel_id = ?
                    """,
                    (
                        nova_identidade["display_name"],
                        nova_identidade["age"],
                        nova_identidade["bio"],
                        nova_identidade["avatar_seed"],
                        json.dumps(historico_final, ensure_ascii=False),
                        c_id,
                    ),
                )
                conn.commit()

            return {
                "display_name": nova_identidade["display_name"],
                "age": nova_identidade["age"],
                "bio": nova_identidade["bio"],
                "avatar_seed": nova_identidade["avatar_seed"],
                "avatar_url": None,
                "history_count": len(historico_final),
            }

        resultado_db = await asyncio.to_thread(_persistir_metamorfose_sync)

        # Atualiza dicionário local com novos dados
        persona_atual.update(resultado_db)
        avatar_final = obter_avatar_persona(persona_atual)

        # 6. Despacho do Embed Cerimonial e View Interativa
        termos_destaque = ", ".join(f"`{p[0]}`" for p in top_palavras[:6]) if top_palavras else "*(Sem termos dominantes)*"
        embed = discord.Embed(
            title="✨ Metamorfose Semanal Concluída!",
            description=f"{nova_identidade['mensagem_anuncio']}\n\nO canal agora possui uma nova identidade viva.",
            color=0x9B59B6,
        )
        embed.set_thumbnail(url=avatar_final)
        embed.add_field(name="👤 Nova Identidade", value=f"**{nova_identidade['display_name']}** ({nova_identidade['age']})", inline=True)
        embed.add_field(name="🏷️ Frequência Semântica", value=termos_destaque, inline=False)
        embed.add_field(name="📜 Biografia & Clima", value=f"*{nova_identidade['bio']}*", inline=False)
        embed.set_footer(text="Gostou dessa forma? Use o botão abaixo para fixá-la ou customizá-la.")

        from ui_components import criar_view_metamorfose
        view = criar_view_metamorfose(channel_id=c_id)

        # Se houver client do discord ativo, envia para o canal correspondente
        if client:
            try:
                canal_obj = client.get_channel(int(c_id))
                if canal_obj and hasattr(canal_obj, "send"):
                    await canal_obj.send(embed=embed, view=view)
            except Exception as ex_send:
                logger.debug("Não foi possível enviar embed direto via client.get_channel: %s", ex_send)

        return {
            "sucesso": True,
            "channel_id": c_id,
            "display_name": nova_identidade["display_name"],
            "age": nova_identidade["age"],
            "bio": nova_identidade["bio"],
            "avatar_seed": nova_identidade["avatar_seed"],
            "avatar_url": avatar_final,
            "mensagem_anuncio": nova_identidade["mensagem_anuncio"],
            "top_palavras": top_palavras[:8],
            "embed": embed,
            "view": view,
        }

    async def obter_historico_metamorfoses(
        self,
        channel_id: str | int,
        db_path: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Retorna o histórico de encarnações passadas da persona do canal."""
        caminho = db_path or self.db_path or DB_FILE
        p = await asyncio.to_thread(obter_persona_canal, str(channel_id), caminho)
        if not p or not p.get("evolution_history_json"):
            return []
        try:
            hist = json.loads(p["evolution_history_json"])
            return hist if isinstance(hist, list) else []
        except Exception:
            return []


# Instância singleton padrão do gerenciador de evolução
persona_evolution_manager = PersonaEvolutionManager()


async def iniciar_worker_metamorfose(client: discord.Client, intervalo_segundos: int = 1800) -> None:
    """Loop perpétuo em segundo plano que verifica e executa metamorfoses semanais em canais adaptativos (IDEA-27)."""
    logger.info("🌀 Worker de Metamorfose Semanal iniciado (verificação a cada %ds).", intervalo_segundos)
    await client.wait_until_ready()

    while not client.is_closed():
        try:
            canais_aptos = await persona_evolution_manager.verificar_canais_para_metamorfose()
            if canais_aptos:
                logger.info("Encontrados %d canais aptos para metamorfose semanal.", len(canais_aptos))
                for canal_info in canais_aptos:
                    c_id = canal_info["channel_id"]
                    try:
                        logger.info("Executando metamorfose semanal periódica no canal %s...", c_id)
                        await persona_evolution_manager.executar_metamorfose_canal(
                            channel_id=c_id,
                            forcar=False,
                            client=client,
                        )
                    except Exception as err_canal:
                        logger.error("Erro ao executar metamorfose no canal %s: %s", c_id, err_canal)
        except Exception as err_worker:
            logger.error("Erro no ciclo do worker de metamorfose semanal: %s", err_worker)

        await asyncio.sleep(intervalo_segundos)

