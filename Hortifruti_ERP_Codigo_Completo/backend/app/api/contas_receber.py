"""
API - Contas a Receber (CAR)
Endpoints para gerenciamento do modulo financeiro contas a receber
"""
from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from pydantic import BaseModel, Field
from app.core.database import get_db

router = APIRouter()

class ContaReceberCreate(BaseModel):
    descricao: str = Field(..., min_length=3)
    cliente_id: Optional[int] = None
    venda_id: Optional[int] = None
    conta_id: Optional[int] = None
    valor_original: Decimal = Field(..., gt=0)
    data_emissao: date = Field(default_factory=date.today)
    data_vencimento: date
    total_parcelas: int = Field(default=1, ge=1)
    forma_recebimento: Optional[str] = None
    observacoes: Optional[str] = None

class RecebimentoCreate(BaseModel):
    valor: Decimal = Field(..., gt=0)
    data_recebimento: date = Field(default_factory=date.today)
    forma_recebimento: Optional[str] = None
    banco_destino: Optional[str] = None
    observacoes: Optional[str] = None

@router.get("/", summary="Listar Contas a Receber")
async def listar_contas_receber(
    status_filtro: Optional[str] = Query(None, alias="status"),
    apenas_vencidas: bool = False,
    cliente_id: Optional[int] = None,
    vencimento_de: Optional[date] = None,
    vencimento_ate: Optional[date] = None,
    skip: int = 0, limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    filters = []
    if status_filtro: filters.append(f"cr.status = '{status_filtro}'")
    if apenas_vencidas: filters.append("cr.data_vencimento < CURRENT_DATE AND cr.status NOT IN ('RECEBIDA','CANCELADA')")
    if cliente_id: filters.append(f"cr.cliente_id = {cliente_id}")
    if vencimento_de: filters.append(f"cr.data_vencimento >= '{vencimento_de}'")
    if vencimento_ate: filters.append(f"cr.data_vencimento <= '{vencimento_ate}'")

    where = " AND ".join(filters) if filters else "1=1"

    r = await db.execute(
        text(f"""
            SELECT cr.*, c.nome_razao as cliente_nome,
                CASE WHEN cr.data_vencimento < CURRENT_DATE AND cr.status NOT IN ('RECEBIDA','CANCELADA')
                     THEN EXTRACT(DAY FROM NOW() - cr.data_vencimento::timestamptz)::int ELSE 0 END as dias_atraso
            FROM contas_receber cr
            LEFT JOIN clientes c ON c.id = cr.cliente_id
            WHERE {where} ORDER BY cr.data_vencimento ASC LIMIT :limit OFFSET :skip
        """),
        {"limit": limit, "skip": skip}
    )
    rows = r.mappings().all()

    totais = await db.execute(
        text(f"""
            SELECT
                COALESCE(SUM(CASE WHEN status NOT IN ('RECEBIDA','CANCELADA') THEN valor_saldo END),0) as total_a_receber,
                COALESCE(SUM(CASE WHEN data_vencimento < CURRENT_DATE AND status NOT IN ('RECEBIDA','CANCELADA') THEN valor_saldo END),0) as total_vencido,
                COALESCE(SUM(CASE WHEN status = 'RECEBIDA' THEN valor_recebido END),0) as total_recebido
            FROM contas_receber cr WHERE {where}
        """)
    )
    t = totais.mappings().first()
    return {"data": [dict(x) for x in rows], "total_a_receber": float(t["total_a_receber"]),
            "total_vencido": float(t["total_vencido"]), "total_recebido": float(t["total_recebido"]), "count": len(rows)}

@router.post("/", status_code=201, summary="Criar Conta a Receber")
async def criar_conta_receber(payload: ContaReceberCreate, db: AsyncSession = Depends(get_db)):
    from uuid import uuid4
    from dateutil.relativedelta import relativedelta

    grupo_id = str(uuid4())
    parcelas = []

    for i in range(1, payload.total_parcelas + 1):
        venc = payload.data_vencimento + relativedelta(months=i-1) if payload.total_parcelas > 1 else payload.data_vencimento
        vp = round(float(payload.valor_original) / payload.total_parcelas, 2)
        if i == payload.total_parcelas and payload.total_parcelas > 1:
            vp = float(payload.valor_original) - round(float(payload.valor_original) / payload.total_parcelas, 2) * (payload.total_parcelas - 1)

        desc = f"{payload.descricao} ({i}/{payload.total_parcelas})" if payload.total_parcelas > 1 else payload.descricao
        res = await db.execute(
            text("""
                INSERT INTO contas_receber (descricao, cliente_id, venda_id, conta_id, valor_original,
                    data_emissao, data_vencimento, parcela_atual, total_parcelas, grupo_parcela,
                    forma_recebimento, observacoes, status)
                VALUES (:desc, :cli, :ven, :conta, :val, :emissao, :venc, :parc_at, :parc_tot, :grupo::uuid,
                    :forma, :obs, 'ABERTA')
                RETURNING id, descricao, valor_original, data_vencimento, status
            """),
            {"desc": desc, "cli": payload.cliente_id, "ven": payload.venda_id, "conta": payload.conta_id,
             "val": vp, "emissao": payload.data_emissao, "venc": venc, "parc_at": i, "parc_tot": payload.total_parcelas,
             "grupo": grupo_id, "forma": payload.forma_recebimento, "obs": payload.observacoes}
        )
        parcelas.append(dict(res.mappings().first()))

    return {"message": f"{payload.total_parcelas} parcela(s) criada(s)", "parcelas": parcelas}

@router.post("/{conta_id}/receber", summary="Baixar Recebimento")
async def registrar_recebimento(conta_id: int, payload: RecebimentoCreate, db: AsyncSession = Depends(get_db)):
    r = await db.execute(text("SELECT * FROM contas_receber WHERE id = :id FOR UPDATE"), {"id": conta_id})
    conta = r.mappings().first()
    if not conta: raise HTTPException(404, "Conta nao encontrada")
    if conta["status"] in ("RECEBIDA", "CANCELADA"): raise HTTPException(400, "Conta ja liquidada")

    novo_rec = float(conta["valor_recebido"]) + float(payload.valor)
    novo_saldo = float(conta["valor_original"]) + float(conta["valor_acrescimo"]) - float(conta["valor_desconto"]) - novo_rec
    novo_status = "RECEBIDA" if novo_saldo <= 0.01 else "RECEBIDA_PARCIAL"

    await db.execute(
        text("INSERT INTO recebimentos_car (conta_receber_id, valor, data_recebimento, forma_recebimento, banco_destino, observacoes) VALUES (:cid, :val, :drec, :forma, :banco, :obs)"),
        {"cid": conta_id, "val": float(payload.valor), "drec": payload.data_recebimento, "forma": payload.forma_recebimento, "banco": payload.banco_destino, "obs": payload.observacoes}
    )
    await db.execute(
        text("UPDATE contas_receber SET valor_recebido=:vr, status=:st, data_recebimento=CASE WHEN :st='RECEBIDA' THEN :drec ELSE data_recebimento END, updated_at=NOW() WHERE id=:id"),
        {"vr": novo_rec, "st": novo_status, "drec": payload.data_recebimento, "id": conta_id}
    )
    return {"message": "Recebimento registrado", "novo_saldo": round(novo_saldo, 2), "novo_status": novo_status}
