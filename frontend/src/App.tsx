import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom';
import Dashboard from './pages/Dashboard';
import AsinDetail from './pages/AsinDetail';
import Chat from './pages/Chat';

function Layout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-[#0f1117]">
      <nav className="bg-[#1a1b23] border-b border-gray-800 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 flex items-center h-14 gap-6">
          <span className="text-gray-100 font-bold text-sm tracking-wide">ASIN Health</span>
          <NavLink to="/" end
            className={({ isActive }) => `text-sm transition-colors ${isActive ? 'text-indigo-400' : 'text-gray-400 hover:text-gray-200'}`}>
            仪表盘
          </NavLink>
          <NavLink to="/chat"
            className={({ isActive }) => `text-sm transition-colors ${isActive ? 'text-indigo-400' : 'text-gray-400 hover:text-gray-200'}`}>
            智能分析
          </NavLink>
        </div>
      </nav>
      <main className="max-w-7xl mx-auto px-4 py-6">
        {children}
      </main>
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/asin/:asinId" element={<AsinDetail />} />
          <Route path="/chat" element={<Chat />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  );
}
