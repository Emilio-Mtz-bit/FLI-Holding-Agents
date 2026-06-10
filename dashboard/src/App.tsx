import { Routes, Route, NavLink, Navigate } from 'react-router-dom';
import { useAnalysisStore } from '@/store/analysis';
import Setup from '@/pages/Setup';
import Overview from '@/pages/Overview';
import WhatIfLab from '@/pages/WhatIfLab';
import Memo from '@/pages/Memo';
import { BarChart3, FlaskConical, FileText, Settings } from 'lucide-react';

const NAV = [
  { to: '/setup', icon: Settings, label: 'Setup' },
  { to: '/overview', icon: BarChart3, label: 'Overview' },
  { to: '/whatif', icon: FlaskConical, label: 'What-If Lab' },
  { to: '/memo', icon: FileText, label: 'Memo' },
];

export default function App() {
  const status = useAnalysisStore((s) => s.status);
  const done = status === 'done';

  return (
    <div className="flex h-screen bg-background text-foreground">
      {/* Sidebar */}
      <nav className="w-56 flex-shrink-0 border-r bg-card flex flex-col pt-6 gap-1 px-2">
        <div className="px-4 mb-6">
          <p className="text-xs font-semibold text-muted-foreground uppercase tracking-widest">RGA Copilot</p>
        </div>
        {NAV.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              `flex items-center gap-3 px-4 py-2 rounded-md text-sm transition-colors
               ${isActive ? 'bg-primary text-primary-foreground' : 'text-muted-foreground hover:bg-muted hover:text-foreground'}
               ${!done && to !== '/setup' ? 'pointer-events-none opacity-40' : ''}`
            }
          >
            <Icon size={16} />
            {label}
          </NavLink>
        ))}
      </nav>

      {/* Main content */}
      <main className="flex-1 overflow-auto">
        <Routes>
          <Route path="/" element={<Navigate to="/setup" replace />} />
          <Route path="/setup" element={<Setup />} />
          <Route path="/overview" element={<Overview />} />
          <Route path="/whatif" element={<WhatIfLab />} />
          <Route path="/memo" element={<Memo />} />
        </Routes>
      </main>
    </div>
  );
}
