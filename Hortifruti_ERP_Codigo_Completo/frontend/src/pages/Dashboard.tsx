import React, { useEffect, useState } from 'react';
import { api } from '../services/api';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar, Legend } from 'recharts';

export default function Dashboard() {
  const [dreData, setDreData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Busca dados do mes atual. Idealmente teriamos um date picker.
    const today = new Date();
    const firstDay = new Date(today.getFullYear(), today.getMonth(), 1).toISOString().split('T')[0];
    const lastDay = new Date(today.getFullYear(), today.getMonth() + 1, 0).toISOString().split('T')[0];

    api.get(`/relatorios/dre?data_inicio=${firstDay}&data_fim=${lastDay}&regime=COMPETENCIA`)
      .then(res => {
        setDreData(res.data);
      })
      .catch(err => console.error(err))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="text-center py-20">Carregando indicadores financeiros...</div>;
  if (!dreData) return <div className="text-center py-20 text-red-500">Erro ao carregar dados.</div>;

  const fmt = (val: number) => new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(val);

  // Mock data for charts if API is empty
  const chartData = [
    { name: 'Sem 1', receitas: 40000, cmv: 24000 },
    { name: 'Sem 2', receitas: 30000, cmv: 13980 },
    { name: 'Sem 3', receitas: 20000, cmv: 9800 },
    { name: 'Sem 4', receitas: 27800, cmv: 19080 },
  ];

  return (
    <div className="space-y-6">
      {/* KPIs Principais */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-100">
          <h3 className="text-sm font-medium text-slate-500 mb-1">Receita Líquida</h3>
          <p className="text-3xl font-bold text-slate-800">{fmt(dreData.dre.receita_liquida)}</p>
        </div>
        <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-100">
          <h3 className="text-sm font-medium text-slate-500 mb-1">Lucro Bruto</h3>
          <p className="text-3xl font-bold text-slate-800">{fmt(dreData.dre.lucro_bruto)}</p>
          <p className="text-xs text-primary mt-1">{dreData.dre.margem_bruta_pct}% Margem</p>
        </div>
        <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-100">
          <h3 className="text-sm font-medium text-slate-500 mb-1">EBITDA</h3>
          <p className="text-3xl font-bold text-slate-800">{fmt(dreData.dre.ebitda)}</p>
          <p className="text-xs text-primary mt-1">{dreData.dre.margem_ebitda_pct}% Margem</p>
        </div>
        <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-100">
          <h3 className="text-sm font-medium text-slate-500 mb-1">Lucro Líquido</h3>
          <p className="text-3xl font-bold text-slate-800">{fmt(dreData.dre.lucro_liquido)}</p>
          <p className="text-xs text-primary mt-1">{dreData.dre.margem_liquida_pct}% Margem</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Resumo DRE */}
        <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-100 lg:col-span-1">
          <h3 className="font-semibold text-slate-800 mb-4">Estrutura DRE (Competência)</h3>
          <div className="space-y-3 text-sm">
            <div className="flex justify-between text-slate-600">
              <span>Receita Bruta</span>
              <span>{fmt(dreData.dre.receita_bruta)}</span>
            </div>
            <div className="flex justify-between text-red-500">
              <span>(-) Deduções</span>
              <span>{fmt(dreData.dre.deducoes_receita)}</span>
            </div>
            <div className="flex justify-between font-semibold text-slate-800 border-t pt-2">
              <span>= Receita Líquida</span>
              <span>{fmt(dreData.dre.receita_liquida)}</span>
            </div>
            <div className="flex justify-between text-red-500">
              <span>(-) CMV</span>
              <span>{fmt(dreData.dre.cmv)}</span>
            </div>
            <div className="flex justify-between font-semibold text-slate-800 border-t pt-2">
              <span>= Lucro Bruto</span>
              <span>{fmt(dreData.dre.lucro_bruto)}</span>
            </div>
            <div className="flex justify-between text-red-500">
              <span>(-) Desp. Operacionais</span>
              <span>{fmt(dreData.dre.despesas_operacionais)}</span>
            </div>
            <div className="flex justify-between font-semibold text-slate-800 border-t pt-2">
              <span>= EBITDA</span>
              <span>{fmt(dreData.dre.ebitda)}</span>
            </div>
          </div>
        </div>

        {/* Graficos */}
        <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-100 lg:col-span-2">
          <h3 className="font-semibold text-slate-800 mb-4">Receitas vs Custos (Mês Atual)</h3>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="name" />
                <YAxis />
                <Tooltip formatter={(value: number) => fmt(value)} />
                <Legend />
                <Bar dataKey="receitas" name="Receitas" fill="#4CAF50" radius={[4, 4, 0, 0]} />
                <Bar dataKey="cmv" name="CMV" fill="#E91E63" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
      
      {/* Alertas */}
      {dreData.impacto_perdas && dreData.impacto_perdas.valor_total_perdas > 0 && (
        <div className="bg-red-50 border border-red-200 text-red-800 p-4 rounded-xl flex items-center justify-between">
          <div>
            <h4 className="font-semibold">Alerta de Perdas Elevadas</h4>
            <p className="text-sm">Tivemos {dreData.impacto_perdas.qtd_ocorrencias} registros de perda neste mês.</p>
          </div>
          <div className="text-right">
            <p className="text-2xl font-bold">{fmt(dreData.impacto_perdas.valor_total_perdas)}</p>
            <p className="text-sm">({dreData.impacto_perdas.pct_receita}% da Receita)</p>
          </div>
        </div>
      )}
    </div>
  );
}
