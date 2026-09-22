"""
API - Contas a Pagar (CAP)
Endpoints para gerenciamento do modulo financeiro contas a pagar
"""
from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from pydantic import BaseModel, Field
from app.core.database import get_db

router = APIRouter()


class ContaPagarCreate(BaseModel):
    descricao: str = Field(..., min_length=3, max_length=250)
    fornecedor_id: Optional[int] = None
    compra_id: Optional[int] = None
    conta_id: Optional[int] = None
    centro_custo_id: Optional[int] = None
    valor_original: Decimal = Field(..., gt=0)
    data_emissao: date = Field(default_factory=date.today)
    data_vencimento: date
    recorrente: bool = False
    recorrencia_tipo: Optional[str] = None
    total_parcelas: int = Field(default=1, ge=1, le=360)
    forma_pagamento: Optional[str] = None
    observacoes: Optional[str] = None


class PagamentoCreate(BaseModel):
    valor: Decimal = Field(..., gt=0)
    data_pagamento: date = Field(default_factory=date.today)
    forma_pagamento: Optional[str] = None
    banco_origem: Optional[str] = None
    observacoes: Optional[str] = None


@router.get("/", summary="Listar Contas a Pagar")
async def listar_contas_pagar(
    status_filtro: Optional[str] = Query(None, alias="status"),
    vencimento_de: Optional[date] = None,
    vencimento_ate: Optional[date] = None,
    fornecedor_id: Optional[int] = None,
    apenas_vencidas: bool = False,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    filters = []
    if status_filtro:
        filters.append(f"cp.status = '{status_filtro}'")
    if apenas_vencidas:
        filters.append("cp.data_vencimento < CURRENT_DATE AND cp.status NOT IN ('PAGA','CANCELADA')")
    if vencimento_de:
        filters.append(f"cp.data_vencimento >= '{vencimento_de}'")
    if vencimento_ate:
        filters.append(f"cp.data_vencimento <= '{vencimento_ate}'")
    if fornecedor_id:
        filters.append(f"cp.fornecedor_id = {fornecedor_id}")

    where = " AND ".join(filters) if filters else "1=1"

    result = await db.execute(
        text(f"""
            SELECT cp.*, f.nome_razao as fornecedor_nome,
                CASE WHEN cp.data_vencimento < CURRENT_DATE AND cp.status NOT IN ('PAGA','CANCELADA')
                     THEN EXTRACT(DAY FROM NOW() - cp.data_vencimento::timestamptz)::int ELSE 0 END as dias_atraso
            FROM contas_pagar cp
            LEFT JOIN fornecedores f ON f.id = cp.fornecedor_id
            WHERE {where}
            ORDER BY cp.data_vencimento ASC
            LIMIT :limit OFFSET :skip
        """),
        {"limit": limit, "skip": skip}
    )
    rows = result.mappings().all()

    totais = await db.execute(
        text(f"""
            SELECT
                COALESCE(SUM(CASE WHEN status NOT IN ('PAGA','CANCELADA') THEN valor_saldo END),0) as total_aberto,
                COALESCE(SUM(CASE WHEN data_vencimento < CURRENT_DATE AND status NOT IN ('PAGA','CANCELADA') THEN valor_saldo END),0) as total_vencido,
                COALESCE(SUM(CASE WHEN status = 'PAGA' THEN valor_pago END),0) as total_pago
            FROM contas_pagar cp WHERE {where}
        """),
        {}
    )
    t = totais.mappings().first()
    return {"data": [dict(r) for r in rows], "total_aberto": float(t["total_aberto"]),
            "total_vencido": float(t["total_vencido"]), "total_pago": float(t["total_pago"]), "count": len(rows)}


@router.post("/", status_code=201, summary="Criar Conta a Pagar (com parcelamento)")
async def criar_conta_pagar(payload: ContaPagarCreate, db: AsyncSession = Depends(get_db)):
    """Cria conta a pagar. Com total_parcelas > 1, gera todas as parcelas com vencimentos mensais."""
    from uuid import uuid4
    from dateutil.relativedelta import relativedelta

    grupo_id = str(uuid4())
    parcelas = []

    for i in range(1, payload.total_parcelas + 1):
        venc = payload.data_vencimento + relativedelta(months=i-1) if payload.total_parcelas > 1 else payload.data_vencimento
        valor_p = round(float(payload.valor_original) / payload.total_parcelas, 2)
        if i == payload.total_parcelas and payload.total_parcelas > 1:
            valor_p = float(payload.valor_original) - round(float(payload.valor_original) / payload.total_parcelas, 2) * (payload.total_parcelas - 1)

        desc = f"{payload.descricao} ({i}/{payload.total_parcelas})" if payload.total_parcelas > 1 else payload.descricao
        result = await db.execute(
            text("""
                INSERT INTO contas_pagar (descricao, fornecedor_id, compra_id, conta_id, centro_custo_id,
                    valor_original, data_emissao, data_vencimento, recorrente, recorrencia_tipo,
                    parcela_atual, total_parcelas, grupo_parcela, forma_pagamento, observacoes, status)
                VALUES (:desc, :forn, :comp, :conta, :cc, :valor, :emissao, :venc,
                    :rec, :rec_tipo, :parc_at, :parc_tot, :grupo::uuid, :forma, :obs, 'ABERTA')
                RETURNING id, descricao, valor_original, data_vencimento, status
            """),
            {"desc": desc, "forn": payload.fornecedor_id, "comp": payload.compra_id, "conta": payload.conta_id,
             "cc": payload.centro_custo_id, "valor": valor_p, "emissao": payload.data_emissao, "venc": venc,
             "rec": payload.recorrente, "rec_tipo": payload.recorrencia_tipo, "parc_at": i,
             "parc_tot": payload.total_parcelas, "grupo": grupo_id, "forma": payload.forma_pagamento, "obs": payload.observacoes}
        )
        parcelas.append(dict(result.mappings().first()))

    return {"message": f"{payload.total_parcelas} parcela(s) criada(s)", "grupo_parcela": grupo_id, "parcelas": parcelas}


@router.post("/{conta_id}/pagar", summary="Registrar Pagamento (parcial ou total)")
async def registrar_pagamento(conta_id: int, payload: PagamentoCreate, db: AsyncSession = Depends(get_db)):
    """Baixa parcial ou total de conta a pagar. Atualiza status automaticamente."""
    r = await db.execute(text("SELECT * FROM contas_pagar WHERE id = :id FOR UPDATE"), {"id": conta_id})
    conta = r.mappings().first()
    if not conta:
        raise HTTPException(404, "Conta a pagar nao encontrada")
    if conta["status"] in ("PAGA", "CANCELADA"):
        raise HTTPException(400, f"Conta com status '{conta['status']}' nao pode ser paga")

    novo_pago = float(conta["valor_pago"]) + float(payload.valor)
    novo_saldo = float(conta["valor_original"]) + float(conta["valor_acrescimo"]) - float(conta["valor_desconto"]) - novo_pago
    novo_status = "PAGA" if novo_saldo <= 0.01 else "PAGA_PARCIAL"

    await db.execute(
        text("INSERT INTO pagamentos_cap (conta_pagar_id, valor, data_pagamento, forma_pagamento, banco_origem, observacoes) VALUES (:cid, :val, :dpag, :forma, :banco, :obs)"),
        {"cid": conta_id, "val": float(payload.valor), "dpag": payload.data_pagamento, "forma": payload.forma_pagamento, "banco": payload.banco_origem, "obs": payload.observacoes}
    )
    await db.execute(
        text("UPDATE contas_pagar SET valor_pago=:vp, status=:st, data_pagamento=CASE WHEN :st='PAGA' THEN :dpag ELSE data_pagamento END, updated_at=NOW() WHERE id=:id"),
        {"vp": novo_pago, "st": novo_status, "dpag": payload.data_pagamento, "id": conta_id}
    )
    return {"message": "Pagamento registrado", "conta_id": conta_id, "valor_pago": float(payload.valor), "novo_saldo": round(novo_saldo, 2), "novo_status": novo_status}


@router.get("/alertas/vencimentos", summary="Alertas de Vencimento")
async def alertas_vencimento(dias_antecedencia: int = Query(7, ge=1, le=60), db: AsyncSession = Depends(get_db)):
    r = await db.execute(
        text("""
            SELECT cp.id, cp.descricao, cp.valor_saldo, cp.data_vencimento, f.nome_razao as fornecedor,
                EXTRACT(DAY FROM cp.data_vencimento::timestamptz - NOW())::int as dias_para_vencer,
                CASE WHEN cp.data_vencimento < CURRENT_DATE THEN 'VENCIDA'
                     WHEN cp.data_vencimento <= CURRENT_DATE + :dias * INTERVAL '1 day' THEN 'VENCE_EM_BREVE' END as alerta
            FROM contas_pagar cp
            LEFT JOIN fornecedores f ON f.id = cp.fornecedor_id
            WHERE cp.status NOT IN ('PAGA','CANCELADA')
              AND (cp.data_vencimento < CURRENT_DATE OR cp.data_vencimento <= CURRENT_DATE + :dias * INTERVAL '1 day')
            ORDER BY cp.data_vencimento
        """),
        {"dias": dias_antecedencia}
    )
    rows = r.mappings().all()
    return {"alertas": [dict(x) for x in rows], "total": len(rows)}
