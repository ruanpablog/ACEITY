-- ERP HORTIFRUTI - SCHEMA SQL (PostgreSQL 16)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

CREATE TABLE unidades_medida (id SERIAL PRIMARY KEY, sigla VARCHAR(10) NOT NULL UNIQUE, descricao VARCHAR(50) NOT NULL, fator_base NUMERIC(10,4) DEFAULT 1, created_at TIMESTAMPTZ DEFAULT NOW());
CREATE TABLE categorias (id SERIAL PRIMARY KEY, nome VARCHAR(100) NOT NULL UNIQUE, descricao TEXT, cor_hex VARCHAR(7) DEFAULT '#4CAF50', created_at TIMESTAMPTZ DEFAULT NOW());

CREATE TABLE plano_de_contas (
    id SERIAL PRIMARY KEY, codigo VARCHAR(20) NOT NULL UNIQUE, descricao VARCHAR(150) NOT NULL,
    tipo VARCHAR(30) NOT NULL CHECK (tipo IN ('RECEITA_BRUTA','DEDUCAO_RECEITA','CMV','DESPESA_OPERACIONAL','DESPESA_FINANCEIRA','RECEITA_FINANCEIRA','DEPRECIACAO','AMORTIZACAO','IMPOSTO','RESULTADO')),
    natureza CHAR(1) NOT NULL CHECK (natureza IN ('D','C')), nivel INT DEFAULT 1, pai_id INT REFERENCES plano_de_contas(id),
    aceita_lancamento BOOLEAN DEFAULT TRUE, dre_grupo VARCHAR(50), dre_ordem INT DEFAULT 0, ativo BOOLEAN DEFAULT TRUE, created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE TABLE centros_custo (id SERIAL PRIMARY KEY, codigo VARCHAR(20) NOT NULL UNIQUE, nome VARCHAR(100) NOT NULL, descricao TEXT, pai_id INT REFERENCES centros_custo(id), ativo BOOLEAN DEFAULT TRUE, created_at TIMESTAMPTZ DEFAULT NOW());

CREATE TABLE clientes (
    id SERIAL PRIMARY KEY, tipo_pessoa CHAR(1) NOT NULL CHECK (tipo_pessoa IN ('F','J')), nome_razao VARCHAR(200) NOT NULL,
    cpf_cnpj VARCHAR(20) UNIQUE, ie VARCHAR(30), email VARCHAR(150), telefone VARCHAR(20), whatsapp VARCHAR(20), segmento VARCHAR(50),
    cep VARCHAR(10), logradouro VARCHAR(200), numero VARCHAR(20), bairro VARCHAR(100), cidade VARCHAR(100), estado CHAR(2),
    limite_credito NUMERIC(12,2) DEFAULT 0, prazo_padrao INT DEFAULT 30, bloqueado BOOLEAN DEFAULT FALSE,
    motivo_bloqueio TEXT, observacoes TEXT, ativo BOOLEAN DEFAULT TRUE, created_at TIMESTAMPTZ DEFAULT NOW(), updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE TABLE fornecedores (
    id SERIAL PRIMARY KEY, tipo_pessoa CHAR(1) NOT NULL CHECK (tipo_pessoa IN ('F','J')), nome_razao VARCHAR(200) NOT NULL,
    cpf_cnpj VARCHAR(20) UNIQUE, ie VARCHAR(30), email VARCHAR(150), telefone VARCHAR(20), tipo VARCHAR(50),
    cep VARCHAR(10), logradouro VARCHAR(200), numero VARCHAR(20), bairro VARCHAR(100), cidade VARCHAR(100), estado CHAR(2),
    prazo_padrao INT DEFAULT 7, banco VARCHAR(50), agencia VARCHAR(10), conta VARCHAR(20), tipo_conta VARCHAR(20), chave_pix VARCHAR(150),
    observacoes TEXT, ativo BOOLEAN DEFAULT TRUE, created_at TIMESTAMPTZ DEFAULT NOW(), updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE TABLE produtos (
    id SERIAL PRIMARY KEY, codigo VARCHAR(30) UNIQUE, nome VARCHAR(150) NOT NULL, descricao TEXT,
    categoria_id INT REFERENCES categorias(id), unidade_compra_id INT NOT NULL REFERENCES unidades_medida(id),
    unidade_venda_id INT NOT NULL REFERENCES unidades_medida(id), fator_conversao NUMERIC(10,4) DEFAULT 1,
    custo_medio NUMERIC(12,4) DEFAULT 0, preco_minimo_venda NUMERIC(12,4) DEFAULT 0,
    margem_minima_pct NUMERIC(5,2) DEFAULT 20, taxa_perda_media_pct NUMERIC(5,2) DEFAULT 5,
    estoque_atual NUMERIC(12,4) DEFAULT 0, estoque_minimo NUMERIC(12,4) DEFAULT 0, ativo BOOLEAN DEFAULT TRUE,
    ncm VARCHAR(10), created_at TIMESTAMPTZ DEFAULT NOW(), updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE TABLE compras (
    id SERIAL PRIMARY KEY, numero_documento VARCHAR(50), fornecedor_id INT NOT NULL REFERENCES fornecedores(id),
    data_emissao DATE NOT NULL, data_entrada DATE NOT NULL DEFAULT CURRENT_DATE,
    valor_produtos NUMERIC(14,2) DEFAULT 0, valor_frete NUMERIC(14,2) DEFAULT 0,
    valor_outros NUMERIC(14,2) DEFAULT 0, valor_desconto NUMERIC(14,2) DEFAULT 0,
    valor_total NUMERIC(14,2) GENERATED ALWAYS AS (valor_produtos + valor_frete + valor_outros - valor_desconto) STORED,
    condicao_pagamento VARCHAR(50), status VARCHAR(20) DEFAULT 'RASCUNHO' CHECK (status IN ('RASCUNHO','CONFIRMADA','RECEBIDA','CANCELADA')),
    observacoes TEXT, centro_custo_id INT REFERENCES centros_custo(id), usuario_id INT, created_at TIMESTAMPTZ DEFAULT NOW(), updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE TABLE itens_compra (
    id SERIAL PRIMARY KEY, compra_id INT NOT NULL REFERENCES compras(id) ON DELETE CASCADE,
    produto_id INT NOT NULL REFERENCES produtos(id), lote_id INT, quantidade NUMERIC(12,4) NOT NULL,
    unidade_id INT NOT NULL REFERENCES unidades_medida(id), custo_unitario NUMERIC(12,4) NOT NULL,
    custo_frete_rateado NUMERIC(12,4) DEFAULT 0,
    custo_total NUMERIC(14,4) GENERATED ALWAYS AS (quantidade * (custo_unitario + custo_frete_rateado)) STORED, created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE TABLE lotes_estoque (
    id SERIAL PRIMARY KEY, produto_id INT NOT NULL REFERENCES produtos(id), compra_id INT REFERENCES compras(id),
    numero_lote VARCHAR(50), data_entrada DATE NOT NULL DEFAULT CURRENT_DATE, data_validade DATE,
    quantidade_inicial NUMERIC(12,4) NOT NULL, quantidade_atual NUMERIC(12,4) NOT NULL, custo_unitario NUMERIC(12,4) NOT NULL,
    status VARCHAR(20) DEFAULT 'ATIVO' CHECK (status IN ('ATIVO','ESGOTADO','VENCIDO','DESCARTADO')), created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE TABLE movimentacoes_estoque (
    id SERIAL PRIMARY KEY, produto_id INT NOT NULL REFERENCES produtos(id), lote_id INT REFERENCES lotes_estoque(id),
    tipo VARCHAR(20) NOT NULL CHECK (tipo IN ('ENTRADA','SAIDA_VENDA','SAIDA_PERDA','SAIDA_TRANSFERENCIA','AJUSTE','INVENTARIO')),
    quantidade NUMERIC(12,4) NOT NULL, custo_unitario NUMERIC(12,4), custo_total NUMERIC(14,4),
    referencia_id INT, referencia_tipo VARCHAR(30), observacoes TEXT, data_movimento TIMESTAMPTZ DEFAULT NOW(), usuario_id INT, created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE TABLE perdas (
    id SERIAL PRIMARY KEY, produto_id INT NOT NULL REFERENCES produtos(id), lote_id INT REFERENCES lotes_estoque(id),
    data_perda DATE NOT NULL DEFAULT CURRENT_DATE, quantidade NUMERIC(12,4) NOT NULL, unidade_id INT NOT NULL REFERENCES unidades_medida(id),
    custo_unitario NUMERIC(12,4) NOT NULL, custo_total NUMERIC(14,4) GENERATED ALWAYS AS (quantidade * custo_unitario) STORED,
    motivo VARCHAR(50) CHECK (motivo IN ('DETERIORACAO','AVARIA_TRANSPORTE','VENCIMENTO','AVARIA_INTERNA','OUTROS')),
    descricao TEXT, conta_debito_id INT REFERENCES plano_de_contas(id), centro_custo_id INT REFERENCES centros_custo(id),
    lancado_dre BOOLEAN DEFAULT FALSE, usuario_id INT, created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE TABLE vendas (
    id SERIAL PRIMARY KEY, numero_pedido VARCHAR(30) UNIQUE, cliente_id INT NOT NULL REFERENCES clientes(id),
    data_venda DATE NOT NULL DEFAULT CURRENT_DATE, data_entrega DATE,
    valor_bruto NUMERIC(14,2) DEFAULT 0, valor_desconto NUMERIC(14,2) DEFAULT 0, valor_frete NUMERIC(14,2) DEFAULT 0,
    valor_impostos NUMERIC(14,2) DEFAULT 0, valor_liquido NUMERIC(14,2) DEFAULT 0,
    cmv_total NUMERIC(14,4) DEFAULT 0, margem_bruta_valor NUMERIC(14,4) DEFAULT 0, margem_bruta_pct NUMERIC(6,3) DEFAULT 0,
    condicao_pagamento VARCHAR(50), data_vencimento DATE,
    status VARCHAR(20) DEFAULT 'ABERTA' CHECK (status IN ('ABERTA','CONFIRMADA','FATURADA','ENTREGUE','CANCELADA')),
    observacoes TEXT, centro_custo_id INT REFERENCES centros_custo(id), usuario_id INT, created_at TIMESTAMPTZ DEFAULT NOW(), updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE TABLE itens_venda (
    id SERIAL PRIMARY KEY, venda_id INT NOT NULL REFERENCES vendas(id) ON DELETE CASCADE,
    produto_id INT NOT NULL REFERENCES produtos(id), lote_id INT REFERENCES lotes_estoque(id),
    quantidade NUMERIC(12,4) NOT NULL, unidade_id INT NOT NULL REFERENCES unidades_medida(id),
    preco_unitario NUMERIC(12,4) NOT NULL, desconto_unitario NUMERIC(12,4) DEFAULT 0,
    preco_liquido NUMERIC(12,4) NOT NULL, custo_unitario NUMERIC(12,4) NOT NULL, margem_item_pct NUMERIC(6,3), created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE TABLE contas_pagar (
    id SERIAL PRIMARY KEY, descricao VARCHAR(250) NOT NULL, fornecedor_id INT REFERENCES fornecedores(id),
    compra_id INT REFERENCES compras(id), conta_id INT REFERENCES plano_de_contas(id), centro_custo_id INT REFERENCES centros_custo(id),
    valor_original NUMERIC(14,2) NOT NULL, valor_acrescimo NUMERIC(14,2) DEFAULT 0, valor_desconto NUMERIC(14,2) DEFAULT 0,
    valor_pago NUMERIC(14,2) DEFAULT 0,
    valor_saldo NUMERIC(14,2) GENERATED ALWAYS AS (valor_original + valor_acrescimo - valor_desconto - valor_pago) STORED,
    data_emissao DATE NOT NULL DEFAULT CURRENT_DATE, data_vencimento DATE NOT NULL, data_pagamento DATE,
    recorrente BOOLEAN DEFAULT FALSE, recorrencia_tipo VARCHAR(20) CHECK (recorrencia_tipo IN ('MENSAL','SEMANAL','QUINZENAL','ANUAL')),
    recorrencia_fim DATE, parcela_atual INT DEFAULT 1, total_parcelas INT DEFAULT 1, grupo_parcela UUID DEFAULT gen_random_uuid(),
    status VARCHAR(20) DEFAULT 'ABERTA' CHECK (status IN ('ABERTA','PAGA','PAGA_PARCIAL','VENCIDA','CANCELADA')),
    forma_pagamento VARCHAR(30), observacoes TEXT, created_at TIMESTAMPTZ DEFAULT NOW(), updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE TABLE pagamentos_cap (
    id SERIAL PRIMARY KEY, conta_pagar_id INT NOT NULL REFERENCES contas_pagar(id), valor NUMERIC(14,2) NOT NULL,
    data_pagamento DATE NOT NULL DEFAULT CURRENT_DATE, forma_pagamento VARCHAR(30), banco_origem VARCHAR(50),
    comprovante_url VARCHAR(300), observacoes TEXT, usuario_id INT, created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE TABLE contas_receber (
    id SERIAL PRIMARY KEY, descricao VARCHAR(250) NOT NULL, cliente_id INT REFERENCES clientes(id),
    venda_id INT REFERENCES vendas(id), conta_id INT REFERENCES plano_de_contas(id), centro_custo_id INT REFERENCES centros_custo(id),
    valor_original NUMERIC(14,2) NOT NULL, valor_acrescimo NUMERIC(14,2) DEFAULT 0, valor_desconto NUMERIC(14,2) DEFAULT 0,
    valor_recebido NUMERIC(14,2) DEFAULT 0,
    valor_saldo NUMERIC(14,2) GENERATED ALWAYS AS (valor_original + valor_acrescimo - valor_desconto - valor_recebido) STORED,
    data_emissao DATE NOT NULL DEFAULT CURRENT_DATE, data_vencimento DATE NOT NULL, data_recebimento DATE,
    parcela_atual INT DEFAULT 1, total_parcelas INT DEFAULT 1, grupo_parcela UUID DEFAULT gen_random_uuid(),
    status VARCHAR(20) DEFAULT 'ABERTA' CHECK (status IN ('ABERTA','RECEBIDA','RECEBIDA_PARCIAL','VENCIDA','INADIMPLENTE','CANCELADA')),
    forma_recebimento VARCHAR(30), observacoes TEXT, created_at TIMESTAMPTZ DEFAULT NOW(), updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE TABLE recebimentos_car (
    id SERIAL PRIMARY KEY, conta_receber_id INT NOT NULL REFERENCES contas_receber(id), valor NUMERIC(14,2) NOT NULL,
    data_recebimento DATE NOT NULL DEFAULT CURRENT_DATE, forma_recebimento VARCHAR(30), banco_destino VARCHAR(50),
    comprovante_url VARCHAR(300), observacoes TEXT, usuario_id INT, created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE TABLE contas_bancarias (
    id SERIAL PRIMARY KEY, nome VARCHAR(100) NOT NULL, banco VARCHAR(50), agencia VARCHAR(10), conta VARCHAR(20),
    tipo VARCHAR(20) DEFAULT 'CORRENTE' CHECK (tipo IN ('CORRENTE','POUPANCA','CAIXA_FISICO','CARTAO_CREDITO')),
    saldo_inicial NUMERIC(14,2) DEFAULT 0, saldo_atual NUMERIC(14,2) DEFAULT 0, ativa BOOLEAN DEFAULT TRUE, created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE TABLE transacoes_caixa (
    id SERIAL PRIMARY KEY, conta_bancaria_id INT NOT NULL REFERENCES contas_bancarias(id),
    tipo CHAR(1) NOT NULL CHECK (tipo IN ('E','S')), descricao VARCHAR(250) NOT NULL, valor NUMERIC(14,2) NOT NULL,
    data_transacao DATE NOT NULL DEFAULT CURRENT_DATE, data_competencia DATE NOT NULL DEFAULT CURRENT_DATE,
    conta_pagar_id INT REFERENCES contas_pagar(id), conta_receber_id INT REFERENCES contas_receber(id),
    conta_id INT REFERENCES plano_de_contas(id), centro_custo_id INT REFERENCES centros_custo(id),
    conciliado BOOLEAN DEFAULT FALSE, id_extrato_bancario INT, saldo_apos NUMERIC(14,2), observacoes TEXT, usuario_id INT, created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE TABLE extrato_bancario (
    id SERIAL PRIMARY KEY, conta_bancaria_id INT NOT NULL REFERENCES contas_bancarias(id), data_lancamento DATE NOT NULL,
    descricao VARCHAR(300), valor NUMERIC(14,2) NOT NULL, tipo CHAR(1) NOT NULL CHECK (tipo IN ('D','C')),
    saldo NUMERIC(14,2), codigo_banco VARCHAR(50), transacao_id INT REFERENCES transacoes_caixa(id),
    conciliado BOOLEAN DEFAULT FALSE, fonte VARCHAR(30) DEFAULT 'OFX', created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE TABLE lancamentos_contabeis (
    id SERIAL PRIMARY KEY, data_competencia DATE NOT NULL, historico VARCHAR(300) NOT NULL,
    conta_debito_id INT NOT NULL REFERENCES plano_de_contas(id), centro_custo_debito_id INT REFERENCES centros_custo(id),
    conta_credito_id INT NOT NULL REFERENCES plano_de_contas(id), centro_custo_credito_id INT REFERENCES centros_custo(id),
    valor NUMERIC(14,2) NOT NULL, origem_tipo VARCHAR(30), origem_id INT,
    estornado BOOLEAN DEFAULT FALSE, estorno_id INT REFERENCES lancamentos_contabeis(id), usuario_id INT, created_at TIMESTAMPTZ DEFAULT NOW()
);

-- INDICES
CREATE INDEX idx_lotes_produto_validade ON lotes_estoque(produto_id, data_validade) WHERE status = 'ATIVO';
CREATE INDEX idx_cap_vencimento ON contas_pagar(data_vencimento, status);
CREATE INDEX idx_car_vencimento ON contas_receber(data_vencimento, status);
CREATE INDEX idx_vendas_cliente_data ON vendas(cliente_id, data_venda);
CREATE INDEX idx_transacoes_conta_data ON transacoes_caixa(conta_bancaria_id, data_transacao);
CREATE INDEX idx_lancamentos_competencia ON lancamentos_contabeis(data_competencia);

-- DADOS INICIAIS
INSERT INTO unidades_medida (sigla, descricao, fator_base) VALUES ('KG','Quilograma',1),('UN','Unidade',1),('CX','Caixa',20),('SC','Saco',50),('BDJ','Bandeja',1),('MT','Maco',1),('LT','Litro',1),('G','Grama',0.001);
INSERT INTO categorias (nome, cor_hex) VALUES ('Folhosas','#4CAF50'),('Legumes','#FF9800'),('Frutas','#E91E63'),('Temperos','#8BC34A'),('Raizes','#795548'),('Cogumelos','#9E9E9E'),('Graos','#FF5722'),('Outros','#607D8B');
INSERT INTO plano_de_contas (codigo,descricao,tipo,natureza,nivel,dre_grupo,dre_ordem) VALUES
('1.0','RECEITAS','RECEITA_BRUTA','C',1,'RECEITA',1),('1.1','Receita Bruta de Vendas','RECEITA_BRUTA','C',2,'RECEITA',2),
('1.1.1','Venda de Hortifruti','RECEITA_BRUTA','C',3,'RECEITA',3),('1.2','Deducoes da Receita','DEDUCAO_RECEITA','D',2,'DEDUCAO',5),
('1.2.1','Impostos s/ Vendas','IMPOSTO','D',3,'DEDUCAO',6),('1.2.2','Devolucoes','DEDUCAO_RECEITA','D',3,'DEDUCAO',7),
('2.0','CMV','CMV','D',1,'CMV',10),('2.1','CMV - Aquisicao','CMV','D',2,'CMV',11),('2.2','CMV - Frete','CMV','D',2,'CMV',12),('2.3','CMV - Perdas','CMV','D',2,'CMV',13),
('3.0','DESP. OPERACIONAIS','DESPESA_OPERACIONAL','D',1,'DESP_OPER',20),('3.1','Pessoal','DESPESA_OPERACIONAL','D',2,'DESP_OPER',21),
('3.1.1','Salarios','DESPESA_OPERACIONAL','D',3,'DESP_OPER',22),('3.2','Administrativo','DESPESA_OPERACIONAL','D',2,'DESP_OPER',24),
('3.2.1','Aluguel','DESPESA_OPERACIONAL','D',3,'DESP_OPER',25),('3.2.2','Energia','DESPESA_OPERACIONAL','D',3,'DESP_OPER',26),
('3.2.3','Combustivel','DESPESA_OPERACIONAL','D',3,'DESP_OPER',27),('3.3','Comercial','DESPESA_OPERACIONAL','D',2,'DESP_OPER',30),
('3.3.1','Frete s/ Vendas','DESPESA_OPERACIONAL','D',3,'DESP_OPER',31),('3.3.2','Comissoes','DESPESA_OPERACIONAL','D',3,'DESP_OPER',32),
('4.0','DEPRECIACAO','DEPRECIACAO','D',1,'DEPR_AMORT',40),('4.1','Depr. Equipamentos','DEPRECIACAO','D',2,'DEPR_AMORT',41),
('5.0','RESULT. FINANCEIRO','DESPESA_FINANCEIRA','D',1,'RESULT_FINANC',50),('5.1','Desp. Financeiras','DESPESA_FINANCEIRA','D',2,'RESULT_FINANC',51),
('5.2','Rec. Financeiras','RECEITA_FINANCEIRA','C',2,'RESULT_FINANC',52),
('6.0','IMPOSTOS S/ LUCRO','IMPOSTO','D',1,'IMPOSTOS_LUCRO',60),('6.1','IRPJ','IMPOSTO','D',2,'IMPOSTOS_LUCRO',61),('6.2','CSLL','IMPOSTO','D',2,'IMPOSTOS_LUCRO',62);
