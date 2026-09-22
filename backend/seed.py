import asyncio
from datetime import date, timedelta
from app.core.database import AsyncSessionLocal
from sqlalchemy import text

async def seed_data():
    async with AsyncSessionLocal() as db:
        print("Limpando dados antigos (se existirem)...")
        await db.execute(text("TRUNCATE TABLE transacoes_caixa, pagamentos_cap, recebimentos_car, contas_pagar, contas_receber, perdas, itens_venda, vendas, itens_compra, compras, movimentacoes_estoque, lotes_estoque, produtos, fornecedores, clientes CASCADE"))
        
        print("Inserindo Clientes e Fornecedores...")
        await db.execute(text("INSERT INTO clientes (tipo_pessoa, nome_razao) VALUES ('J', 'Supermercado Central'), ('J', 'Restaurante Sabor da Terra'), ('F', 'João da Feira')"))
        await db.execute(text("INSERT INTO fornecedores (tipo_pessoa, nome_razao, tipo) VALUES ('J', 'Fazenda São Paulo', 'Produtor Rural'), ('J', 'Distribuidora Ceasa', 'Distribuidor')"))
        
        print("Inserindo Produtos...")
        # 1 - Alface (Folhosas, un, un), 2 - Tomate (Legumes, kg, kg), 3 - Banana (Frutas, cx, kg)
        await db.execute(text("""
            INSERT INTO produtos (nome, categoria_id, unidade_compra_id, unidade_venda_id, custo_medio, preco_minimo_venda) VALUES 
            ('Alface Crespa', 1, 2, 2, 0.80, 2.50),
            ('Tomate Carmem', 2, 1, 1, 3.50, 7.00),
            ('Banana Prata', 3, 3, 1, 40.00, 4.50)
        """))
        
        hoje = date.today()
        inicio_mes = date(hoje.year, hoje.month, 1)
        
        print("Inserindo Lançamentos Contábeis (Simulando DRE)...")
        # Para o DRE puxar os dados, precisamos de lançamentos.
        # Vamos simular receitas, custos (CMV) e despesas usando as contas já criadas no schema
        
        # Receita de Vendas (Conta 1.1.1 - Natureza C)
        await db.execute(text("INSERT INTO lancamentos_contabeis (data_competencia, historico, conta_debito_id, conta_credito_id, valor) VALUES (:data, 'Venda Balcão', 1, 3, 45000.00)"), {"data": inicio_mes + timedelta(days=5)})
        await db.execute(text("INSERT INTO lancamentos_contabeis (data_competencia, historico, conta_debito_id, conta_credito_id, valor) VALUES (:data, 'Venda Atacado', 1, 3, 85000.00)"), {"data": inicio_mes + timedelta(days=15)})
        
        # Deduções - Impostos (Conta 1.2.1 - Natureza D)
        await db.execute(text("INSERT INTO lancamentos_contabeis (data_competencia, historico, conta_debito_id, conta_credito_id, valor) VALUES (:data, 'Simples Nacional', 5, 1, 7800.00)"), {"data": inicio_mes + timedelta(days=20)})
        
        # CMV - Aquisição (Conta 2.1 - Natureza D)
        await db.execute(text("INSERT INTO lancamentos_contabeis (data_competencia, historico, conta_debito_id, conta_credito_id, valor) VALUES (:data, 'Custo das Mercadorias', 8, 1, 62000.00)"), {"data": inicio_mes + timedelta(days=28)})
        
        # CMV - Perdas (Conta 2.3 - Natureza D) - Hortifruti tem muita perda!
        await db.execute(text("INSERT INTO lancamentos_contabeis (data_competencia, historico, conta_debito_id, conta_credito_id, valor) VALUES (:data, 'Perdas Deterioração', 10, 1, 4500.00)"), {"data": inicio_mes + timedelta(days=29)})
        
        # Inserindo registro físico na tabela de perdas para acionar o alerta no Dashboard
        await db.execute(text("INSERT INTO perdas (produto_id, data_perda, quantidade, unidade_id, custo_unitario, motivo, descricao) VALUES (2, :data, 150, 1, 3.50, 'DETERIORACAO', 'Tomate maduro demais')"), {"data": inicio_mes + timedelta(days=10)})
        await db.execute(text("INSERT INTO perdas (produto_id, data_perda, quantidade, unidade_id, custo_unitario, motivo, descricao) VALUES (3, :data, 5, 3, 40.00, 'AVARIA_TRANSPORTE', 'Caixas amassadas')"), {"data": inicio_mes + timedelta(days=12)})
        
        # Despesas Operacionais (Contas 3.1.1 Salários, 3.2.1 Aluguel, 3.2.2 Energia - Natureza D)
        await db.execute(text("INSERT INTO lancamentos_contabeis (data_competencia, historico, conta_debito_id, conta_credito_id, valor) VALUES (:data, 'Folha de Pagamento', 13, 1, 15000.00)"), {"data": inicio_mes + timedelta(days=4)})
        await db.execute(text("INSERT INTO lancamentos_contabeis (data_competencia, historico, conta_debito_id, conta_credito_id, valor) VALUES (:data, 'Aluguel Galpão', 15, 1, 8000.00)"), {"data": inicio_mes + timedelta(days=10)})
        await db.execute(text("INSERT INTO lancamentos_contabeis (data_competencia, historico, conta_debito_id, conta_credito_id, valor) VALUES (:data, 'Conta de Luz', 16, 1, 2500.00)"), {"data": inicio_mes + timedelta(days=15)})
        
        await db.commit()
        print("Seed finalizado com sucesso!")

if __name__ == "__main__":
    asyncio.run(seed_data())
