import React from 'react';
import { Outlet, Link, useLocation } from 'react-router-dom';
import { LayoutDashboard, Receipt, TrendingUp, Package, Users, Settings } from 'lucide-react';

export default function Layout() {
  const location = useLocation();
  
  const menu = [
    { name: 'Dashboard', path: '/', icon: <LayoutDashboard size={20} /> },
    { name: 'Contas a Pagar', path: '/cap', icon: <Receipt size={20} /> },
    { name: 'Contas a Receber', path: '/car', icon: <TrendingUp size={20} /> },
    { name: 'Estoque & Perdas', path: '/estoque', icon: <Package size={20} /> },
    { name: 'Clientes/Forn.', path: '/cadastros', icon: <Users size={20} /> },
  ];

  return (
    <div className="flex h-screen bg-slate-100">
      <aside className="w-64 bg-slate-900 text-white flex flex-col">
        <div className="p-4 text-xl font-bold border-b border-slate-800 flex items-center gap-2">
          <span className="text-primary text-2xl">🌱</span> ERP Hortifruti
        </div>
        <nav className="flex-1 p-4 space-y-2">
          {menu.map((item) => (
            <Link
              key={item.path}
              to={item.path}
              className={`flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${
                location.pathname === item.path ? 'bg-primary text-white' : 'text-slate-300 hover:bg-slate-800'
              }`}
            >
              {item.icon}
              {item.name}
            </Link>
          ))}
        </nav>
        <div className="p-4 border-t border-slate-800">
          <button className="flex items-center gap-3 text-slate-400 hover:text-white transition-colors w-full px-4 py-2">
            <Settings size={20} /> Configurações
          </button>
        </div>
      </aside>

      <main className="flex-1 overflow-auto">
        <header className="bg-white shadow-sm h-16 flex items-center px-8 justify-between">
          <h2 className="text-xl font-semibold text-slate-800">
            {menu.find(m => m.path === location.pathname)?.name || 'Sistema'}
          </h2>
          <div className="flex items-center gap-4">
            <div className="w-8 h-8 bg-primary rounded-full flex items-center justify-center text-white font-bold">
              A
            </div>
          </div>
        </header>
        <div className="p-8">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
