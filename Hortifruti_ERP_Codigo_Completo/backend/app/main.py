from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime

app = FastAPI(
    title="ERP Hortifruti API",
    description="Sistema de Gestao Financeira para Distribuidora de Hortifruti",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.api import relatorios
app.include_router(relatorios.router, prefix="/api/v1/relatorios", tags=["Relatorios DRE/EBITDA"])

@app.get("/api/health")
async def health_check():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat(), "sistema": "ERP Hortifruti v1.0"}
