import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Dashboard />} />
          <Route path="cap" element={<div className="p-4 bg-white rounded-xl shadow-sm border border-slate-100 h-96 flex items-center justify-center text-slate-500">Módulo de Contas a Pagar em desenvolvimento.</div>} />
          <Route path="car" element={<div className="p-4 bg-white rounded-xl shadow-sm border border-slate-100 h-96 flex items-center justify-center text-slate-500">Módulo de Contas a Receber em desenvolvimento.</div>} />
          <Route path="estoque" element={<div className="p-4 bg-white rounded-xl shadow-sm border border-slate-100 h-96 flex items-center justify-center text-slate-500">Módulo de Estoque e Perdas em desenvolvimento.</div>} />
          <Route path="cadastros" element={<div className="p-4 bg-white rounded-xl shadow-sm border border-slate-100 h-96 flex items-center justify-center text-slate-500">Gestão de Clientes e Fornecedores em desenvolvimento.</div>} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
