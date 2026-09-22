"""
ENGINE DE RELATÓRIOS FINANCEIROS
DRE (Demonstração do Resultado do Exercício) + EBITDA + Fluxo de Caixa
Módulo central de inteligência financeira do ERP Hortifruti
"""
from datetime import date, datetime
from decimal import Decimal
from typing import Optional, Dict, List, Any
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.core.database import get_db

router = APIRouter()


# =============================================================================
# FÓRMULAS E REGRAS DE NEGÓCIO IMPLEMENTADAS
# =============================================================================
#
# RECEITA LÍQUIDA = Receita Bruta - Deduções (Impostos, Devoluções)
#
# LUCRO BRUTO = Receita Líquida - CMV
#   CMV = Custo Aquisição + Frete Compras + Perdas/Quebras
#
# EBITDA = Lucro Bruto - Despesas Operacionais (SEM Depreciação/Amortização)
#   (Earnings Before Interest, Taxes, Depreciation and Amortization)
#   Em PT-BR: LAJIDA (Lucro Antes de Juros, Impostos, Depr. e Amort.)
#
# EBIT = EBITDA - Depreciação - Amortização
#
# LUCRO ANTES IR = EBIT + Receitas Financeiras - Despesas Financeiras
#
# LUCRO LÍQUIDO = Lucro Antes IR - IRPJ - CSLL
#
# MARGENS:
#   Margem Bruta      = Lucro Bruto / Receita Líquida * 100
#   Margem EBITDA     = EBITDA / Receita Líquida * 100
#   Margem Operacional = EBIT / Receita Líquida * 100
#   Margem Líquida    = Lucro Líquido / Receita Líquida * 100
#
# PONTO DE EQUILÍBRIO (PE):
#   PE Financeiro = Custos Fixos / Margem de Contribuição Média %
#   Margem Contribuição = (Receita - Custos Variáveis) / Receita
# =============================================================================


async def _buscar_lancamentos_competencia(
    db: AsyncSession,
    data_inicio: date,
    data_fim: date,
    dre_grupo: Optional[str] = None,
) -> List[Dict]:
    """
    Busca todos os lançamentos contábeis no período por competência.
    Retorna agrupado por dre_grupo e conta para montagem do DRE.
    """
    filtro_grupo = f"AND pc.dre_grupo = '{dre_grupo}'" if dre_grupo else ""

    result = await db.execute(
        text(f"""
            SELECT
                pc.dre_grupo,
                pc.codigo,
                pc.descricao,
                pc.tipo,
                pc.natureza,
                pc.dre_ordem,
                COALESCE(SUM(
                    CASE
                        WHEN lc.conta_debito_id = pc.id THEN lc.valor
                        WHEN lc.conta_credito_id = pc.id THEN -lc.valor
                        ELSE 0
                    END
                ), 0) as valor_periodo
            FROM plano_de_contas pc
            LEFT JOIN lancamentos_contabeis lc ON (
                (lc.conta_debito_id = pc.id OR lc.conta_credito_id = pc.id)
                AND lc.data_competencia BETWEEN :inicio AND :fim
                AND lc.estornado = FALSE
            )
            WHERE pc.aceita_lancamento = TRUE
              AND pc.ativo = TRUE
              {filtro_grupo}
            GROUP BY pc.id, pc.dre_grupo, pc.codigo, pc.descricao, pc.tipo, pc.natureza, pc.dre_ordem
            ORDER BY pc.dre_ordem ASC
        """),
        {"inicio": data_inicio, "fim": data_fim}
    )
    return [dict(r) for r in result.mappings().all()]


async def _buscar_dados_caixa(
    db: AsyncSession,
    data_inicio: date,
    data_fim: date,
) -> Dict:
    """Dados de caixa realizado (regime de caixa)."""
    result = await db.execute(
        text("""
            SELECT
                COALESCE(SUM(CASE WHEN tipo = 'E' THEN valor ELSE 0 END), 0) as total_entradas,
                COALESCE(SUM(CASE WHEN tipo = 'S' THEN valor ELSE 0 END), 0) as total_saidas,
                COALESCE(SUM(CASE WHEN tipo = 'E' THEN valor ELSE -valor END), 0) as saldo_periodo
            FROM transacoes_caixa
            WHERE data_transacao BETWEEN :inicio AND :fim
        """),
        {"inicio": data_inicio, "fim": data_fim}
    )
    return dict(result.mappings().first())


def _calcular_dre_estruturado(lancamentos: List[Dict]) -> Dict:
    """
    Monta a estrutura completa do DRE a partir dos lançamentos contábeis.
    Retorna um dicionário com todos os grupos e indicadores calculados.
    """
    # Agrupa por dre_grupo e soma os valores
    grupos: Dict[str, Decimal] = {}
    detalhes: Dict[str, List] = {}

    for lanc in lancamentos:
        grupo = lanc["dre_grupo"] or "SEM_CLASSIFICACAO"
        valor = Decimal(str(lanc["valor_periodo"]))

        # Ajusta sinal: para contas de natureza Débito (D), valor positivo = despesa
        # Para natureza Crédito (C), valor positivo = receita
        if lanc["natureza"] == "D":
            # Débito: valor já reflete saída (positivo = gasto)
            valor_ajustado = valor
        else:
            # Crédito: valor positivo = receita
            valor_ajustado = -valor  # invertemos pois somamos créditos como negativos no saldo contábil

        if grupo not in grupos:
            grupos[grupo] = Decimal("0")
            detalhes[grupo] = []

        grupos[grupo] += valor_ajustado
        detalhes[grupo].append({
            "conta": lanc["codigo"],
            "descricao": lanc["descricao"],
            "valor": float(valor_ajustado),
        })

    # Extrai os grupos principais
    receita_bruta     = abs(float(grupos.get("RECEITA", 0)))
    deducoes          = abs(float(grupos.get("DEDUCAO", 0)))
    cmv               = abs(float(grupos.get("CMV", 0)))
    desp_operacional  = abs(float(grupos.get("DESP_OPER", 0)))
    depreciacao       = abs(float(grupos.get("DEPR_AMORT", 0)))
    desp_financeira   = abs(float(grupos.get("RESULT_FINANC", 0)))
    rec_financeira    = 0.0  # Separar se necessário
    impostos_lucro    = abs(float(grupos.get("IMPOSTOS_LUCRO", 0)))

    # Calcular linha a linha do DRE
    receita_liquida   = receita_bruta - deducoes
    lucro_bruto       = receita_liquida - cmv
    ebitda            = lucro_bruto - desp_operacional
    ebit              = ebitda - depreciacao
    lucro_antes_ir    = ebit - desp_financeira + rec_financeira
    lucro_liquido     = lucro_antes_ir - impostos_lucro

    # Margens (em % da Receita Líquida)
    def margem(valor: float) -> float:
        if receita_liquida == 0:
            return 0.0
        return round(valor / receita_liquida * 100, 2)

    return {
        "receita_bruta":         round(receita_bruta, 2),
        "deducoes_receita":      round(deducoes, 2),
        "receita_liquida":       round(receita_liquida, 2),
        "cmv":                   round(cmv, 2),
        "lucro_bruto":           round(lucro_bruto, 2),
        "margem_bruta_pct":      margem(lucro_bruto),
        "despesas_operacionais": round(desp_operacional, 2),
        "ebitda":                round(ebitda, 2),
        "margem_ebitda_pct":     margem(ebitda),
        "depreciacao_amort":     round(depreciacao, 2),
        "ebit":                  round(ebit, 2),
        "margem_operacional_pct":margem(ebit),
        "resultado_financeiro":  round(rec_financeira - desp_financeira, 2),
        "lucro_antes_ir":        round(lucro_antes_ir, 2),
        "impostos_lucro":        round(impostos_lucro, 2),
        "lucro_liquido":         round(lucro_liquido, 2),
        "margem_liquida_pct":    margem(lucro_liquido),
        "detalhes":              {k: v for k, v in detalhes.items()},
    }


def _calcular_ponto_equilibrio(dre: Dict) -> Dict:
    """
    Calcula o Ponto de Equilíbrio financeiro e operacional.
    
    PE Financeiro = Custos Fixos / (1 - (Custos Variáveis / Receita Bruta))
    
    Premissas para Hortifruti:
    - Custos Fixos: Despesas Operacionais (pessoal, aluguel, energia...)
    - Custos Variáveis: CMV (diretamente proporcional às vendas)
    """
    receita = dre["receita_bruta"]
    cmv = dre["cmv"]
    desp_fixas = dre["despesas_operacionais"]

    if receita == 0:
        return {"pe_financeiro": 0, "pe_operacional": 0, "margem_contribuicao_pct": 0}

    custo_variavel_pct = cmv / receita if receita > 0 else 0
    margem_contribuicao_pct = 1 - custo_variavel_pct

    if margem_contribuicao_pct == 0:
        return {
            "pe_financeiro": 0,
            "pe_operacional": 0,
            "margem_contribuicao_pct": 0,
            "alerta": "Margem de contribuição zero — verifique os dados"
        }

    pe_financeiro   = desp_fixas / margem_contribuicao_pct
    pe_operacional  = (desp_fixas + dre["depreciacao_amort"]) / margem_contribuicao_pct

    return {
        "pe_financeiro":           round(pe_financeiro, 2),
        "pe_operacional":          round(pe_operacional, 2),
        "margem_contribuicao_pct": round(margem_contribuicao_pct * 100, 2),
        "receita_atual":           receita,
        "folga_pe_financeiro":     round(receita - pe_financeiro, 2),
        "indice_seguranca_pct":    round((receita - pe_financeiro) / receita * 100, 2) if receita > 0 else 0,
    }


# =============================================================================
# ENDPOINTS DE RELATÓRIOS
# =============================================================================

@router.get("/dre", summary="DRE — Demonstração do Resultado do Exercício")
async def gerar_dre(
    data_inicio: date = Query(..., description="Data início (AAAA-MM-DD)"),
    data_fim: date    = Query(..., description="Data fim (AAAA-MM-DD)"),
    regime: str       = Query("COMPETENCIA", enum=["COMPETENCIA", "CAIXA"],
                               description="Regime contábil"),
    db: AsyncSession = Depends(get_db),
):
    """
    Gera a DRE completa para o período informado.
    
    - **Regime de Competência**: baseado nos lançamentos contábeis por data de competência
    - **Regime de Caixa**: baseado nas transações efetivamente pagas/recebidas
    
    Retorna: todas as linhas do DRE + EBITDA + margens + ponto de equilíbrio.
    """
    if regime == "COMPETENCIA":
        lancamentos = await _buscar_lancamentos_competencia(db, data_inicio, data_fim)
        dre = _calcular_dre_estruturado(lancamentos)
    else:
        # Regime de Caixa: usa receitas e despesas efetivamente movimentadas
        caixa = await _buscar_dados_caixa(db, data_inicio, data_fim)

        # Busca valores de vendas recebidas e compras pagas no período
        result_receitas = await db.execute(
            text("""
                SELECT COALESCE(SUM(valor), 0) as total
                FROM transacoes_caixa
                WHERE tipo = 'E' AND data_transacao BETWEEN :inicio AND :fim
                  AND conta_receber_id IS NOT NULL
            """),
            {"inicio": data_inicio, "fim": data_fim}
        )
        result_cmv = await db.execute(
            text("""
                SELECT COALESCE(SUM(valor), 0) as total
                FROM transacoes_caixa
                WHERE tipo = 'S' AND data_transacao BETWEEN :inicio AND :fim
                  AND conta_pagar_id IS NOT NULL
            """),
            {"inicio": data_inicio, "fim": data_fim}
        )

        receita_caixa = float(result_receitas.scalar())
        cmv_caixa     = float(result_cmv.scalar())
        lucro_bruto   = receita_caixa - cmv_caixa

        dre = {
            "receita_bruta": receita_caixa,
            "deducoes_receita": 0,
            "receita_liquida": receita_caixa,
            "cmv": cmv_caixa,
            "lucro_bruto": lucro_bruto,
            "margem_bruta_pct": round(lucro_bruto / receita_caixa * 100, 2) if receita_caixa else 0,
            "despesas_operacionais": 0,
            "ebitda": lucro_bruto,
            "margem_ebitda_pct": round(lucro_bruto / receita_caixa * 100, 2) if receita_caixa else 0,
            "depreciacao_amort": 0,
            "ebit": lucro_bruto,
            "margem_operacional_pct": 0,
            "resultado_financeiro": 0,
            "lucro_antes_ir": lucro_bruto,
            "impostos_lucro": 0,
            "lucro_liquido": lucro_bruto,
            "margem_liquida_pct": round(lucro_bruto / receita_caixa * 100, 2) if receita_caixa else 0,
            "nota": "Regime de Caixa — valores simplificados baseados em transações",
        }

    ponto_equilibrio = _calcular_ponto_equilibrio(dre)

    # Busca dados de perdas do período para destacar impacto
    perdas_result = await db.execute(
        text("""
            SELECT COALESCE(SUM(custo_total), 0) as total_perdas,
                   COUNT(*) as qtd_ocorrencias
            FROM perdas
            WHERE data_perda BETWEEN :inicio AND :fim
        """),
        {"inicio": data_inicio, "fim": data_fim}
    )
    perdas_row = perdas_result.mappings().first()

    return {
        "periodo": {
            "data_inicio": data_inicio.isoformat(),
            "data_fim":    data_fim.isoformat(),
            "regime":      regime,
        },
        "dre": dre,
        "ebitda_detalhado": {
            "ebitda":                   dre["ebitda"],
            "margem_ebitda_pct":        dre["margem_ebitda_pct"],
            "depreciacao_amortizacao":  dre["depreciacao_amort"],
            "ebit_lajir":               dre["ebit"],
        },
        "ponto_equilibrio": ponto_equilibrio,
        "impacto_perdas": {
            "valor_total_perdas": float(perdas_row["total_perdas"]),
            "qtd_ocorrencias":    int(perdas_row["qtd_ocorrencias"]),
            "pct_receita":        round(float(perdas_row["total_perdas"]) / dre["receita_bruta"] * 100, 2)
                                  if dre["receita_bruta"] > 0 else 0,
        },
        "gerado_em": datetime.utcnow().isoformat(),
    }


@router.get("/fluxo-caixa", summary="Fluxo de Caixa Projetado e Realizado")
async def fluxo_caixa(
    data_inicio: date = Query(...),
    data_fim:    date = Query(...),
    granularidade: str = Query("DIARIO", enum=["DIARIO", "SEMANAL", "MENSAL"]),
    db: AsyncSession = Depends(get_db),
):
    """
    Fluxo de caixa realizado + projetado (baseado em CAP e CAR em aberto).
    """
    # REALIZADO: transações efetivas
    if granularidade == "DIARIO":
        trunc = "day"
    elif granularidade == "SEMANAL":
        trunc = "week"
    else:
        trunc = "month"

    realizado = await db.execute(
        text(f"""
            SELECT
                DATE_TRUNC('{trunc}', data_transacao)::date as periodo,
                SUM(CASE WHEN tipo = 'E' THEN valor ELSE 0 END) as entradas,
                SUM(CASE WHEN tipo = 'S' THEN valor ELSE 0 END) as saidas,
                SUM(CASE WHEN tipo = 'E' THEN valor ELSE -valor END) as saldo_periodo
            FROM transacoes_caixa
            WHERE data_transacao BETWEEN :inicio AND :fim
            GROUP BY periodo
            ORDER BY periodo
        """),
        {"inicio": data_inicio, "fim": data_fim}
    )

    # PROJETADO: CAP e CAR em aberto no período
    projetado_pagar = await db.execute(
        text(f"""
            SELECT
                DATE_TRUNC('{trunc}', data_vencimento)::date as periodo,
                SUM(valor_saldo) as saidas_previstas
            FROM contas_pagar
            WHERE data_vencimento BETWEEN :inicio AND :fim
              AND status NOT IN ('PAGA','CANCELADA')
            GROUP BY periodo
            ORDER BY periodo
        """),
        {"inicio": data_inicio, "fim": data_fim}
    )

    projetado_receber = await db.execute(
        text(f"""
            SELECT
                DATE_TRUNC('{trunc}', data_vencimento)::date as periodo,
                SUM(valor_saldo) as entradas_previstas
            FROM contas_receber
            WHERE data_vencimento BETWEEN :inicio AND :fim
              AND status NOT IN ('RECEBIDA','CANCELADA')
            GROUP BY periodo
            ORDER BY periodo
        """),
        {"inicio": data_inicio, "fim": data_fim}
    )

    # Saldo atual de todas as contas bancárias ativas
    saldo_atual = await db.execute(
        text("SELECT COALESCE(SUM(saldo_atual), 0) as saldo FROM contas_bancarias WHERE ativa = TRUE")
    )

    return {
        "periodo": {"inicio": data_inicio.isoformat(), "fim": data_fim.isoformat(), "granularidade": granularidade},
        "saldo_atual_total": float(saldo_atual.scalar()),
        "realizado": [dict(r) for r in realizado.mappings().all()],
        "projetado_pagar": [dict(r) for r in projetado_pagar.mappings().all()],
        "projetado_receber": [dict(r) for r in projetado_receber.mappings().all()],
        "gerado_em": datetime.utcnow().isoformat(),
    }


@router.get("/perdas", summary="Relatório de Perdas e Quebras")
async def relatorio_perdas(
    data_inicio: date = Query(...),
    data_fim:    date = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """Relatório de perdas com impacto no CMV."""
    result = await db.execute(
        text("""
            SELECT
                p.data_perda,
                pr.nome as produto,
                cat.nome as categoria,
                p.quantidade,
                um.sigla as unidade,
                p.custo_unitario,
                p.custo_total,
                p.motivo,
                p.descricao,
                l.numero_lote,
                l.data_validade
            FROM perdas p
            JOIN produtos pr ON pr.id = p.produto_id
            JOIN categorias cat ON cat.id = pr.categoria_id
            JOIN unidades_medida um ON um.id = p.unidade_id
            LEFT JOIN lotes_estoque l ON l.id = p.lote_id
            WHERE p.data_perda BETWEEN :inicio AND :fim
            ORDER BY p.custo_total DESC
        """),
        {"inicio": data_inicio, "fim": data_fim}
    )
    rows = result.mappings().all()

    total_perda = sum(r["custo_total"] for r in rows)
    por_motivo = {}
    for r in rows:
        motivo = r["motivo"] or "OUTROS"
        por_motivo[motivo] = por_motivo.get(motivo, 0) + float(r["custo_total"])

    return {
        "periodo": {"inicio": data_inicio.isoformat(), "fim": data_fim.isoformat()},
        "total_perdas": float(total_perda),
        "qtd_ocorrencias": len(rows),
        "por_motivo": por_motivo,
        "detalhes": [dict(r) for r in rows],
    }
