# ERP Hortifruti

Sistema web completo para distribuidora de hortifruti com foco em gestão financeira, DRE, EBITDA e controle de perdas (CMV).

## Estrutura do Projeto

- `/backend`: API FastAPI (Python 3.12), SQLAlchemy 2.0 (async), PostgreSQL 16
- `/frontend`: Aplicação SPA (React/Vite) — *Em desenvolvimento*
- `docker-compose.yml`: Orquestração do banco de dados, Redis e API.

## Funcionalidades Principais (Backend)

- **Contas a Pagar (CAP):** Cadastro de fornecedores, pagamentos parciais, parcelamento e alertas de vencimento.
- **Contas a Receber (CAR):** Controle de clientes, recebimentos parciais e relatórios de inadimplência.
- **Inteligência Financeira:** 
  - **DRE:** Geração da Demonstração do Resultado do Exercício por regime de competência e caixa.
  - **EBITDA / LAJIDA:** Cálculo automatizado das margens operacionais.
  - **Fluxo de Caixa:** Visão realizada e projetada (integração entre Caixa, CAP e CAR).
  - **Ponto de Equilíbrio:** Cálculo automático baseado na margem de contribuição.
- **Controle de Perdas:** Registro detalhado de quebras que impactam diretamente o CMV e DRE.

## Como Iniciar (Ambiente Local)

1. Certifique-se de ter o Docker e Docker Compose instalados.
2. Na raiz do projeto (`C:\Users\Usuário\.gemini\antigravity\scratch\hortifruti-erp`), execute:
   ```bash
   docker-compose up --build
   ```
3. O banco de dados PostgreSQL será iniciado e automaticamente populado pelo script `backend/schema.sql` (Tabelas, Plano de Contas e Categorias).
4. A API estará disponível em: `http://localhost:8000`
5. Acesse a documentação interativa da API:
   - Swagger UI: `http://localhost:8000/api/docs`
   - ReDoc: `http://localhost:8000/api/redoc`
