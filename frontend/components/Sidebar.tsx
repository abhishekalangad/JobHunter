'use client';

import { ActiveView } from '@/app/page';
import {
  LayoutDashboard, FileText, Crosshair, Mail, Bot, Zap
} from 'lucide-react';

interface SidebarProps {
  activeView: ActiveView;
  onNavigate: (view: ActiveView) => void;
}

const navItems: { id: ActiveView; label: string; icon: React.ReactNode; badge?: string }[] = [
  { id: 'dashboard',    label: 'Dashboard',     icon: <LayoutDashboard size={17} /> },
  { id: 'resumes',      label: 'Resumes',        icon: <FileText size={17} /> },
  { id: 'jd-match',     label: 'JD Matcher',     icon: <Crosshair size={17} />, badge: 'RAG' },
  { id: 'applications', label: 'Applications',   icon: <Mail size={17} /> },
];

export default function Sidebar({ activeView, onNavigate }: SidebarProps) {
  return (
    <aside style={{
      width: 230,
      minWidth: 230,
      background: 'var(--bg-secondary)',
      borderRight: '1px solid var(--border)',
      display: 'flex',
      flexDirection: 'column',
      padding: '20px 12px',
      gap: 4,
    }}>
      {/* Logo */}
      <div style={{ padding: '8px 14px 24px', display: 'flex', alignItems: 'center', gap: 10 }}>
        <div style={{
          width: 34, height: 34, borderRadius: 10,
          background: 'var(--gradient-primary)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          boxShadow: '0 4px 14px rgba(139,92,246,0.4)',
        }}>
          <Bot size={18} color="white" />
        </div>
        <div>
          <div style={{ fontWeight: 700, fontSize: 14, color: 'var(--text-primary)', lineHeight: 1.2 }}>
            AI Job Hunter
          </div>
          <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 1 }}>
            RAG-Powered
          </div>
        </div>
      </div>

      {/* Section label */}
      <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', padding: '0 14px 6px', letterSpacing: '0.08em', textTransform: 'uppercase' }}>
        Navigation
      </div>

      {/* Nav items */}
      {navItems.map(item => (
        <button
          key={item.id}
          className={`nav-item ${activeView === item.id ? 'active' : ''}`}
          onClick={() => onNavigate(item.id)}
        >
          {item.icon}
          <span style={{ flex: 1, textAlign: 'left' }}>{item.label}</span>
          {item.badge && (
            <span style={{
              fontSize: 10, fontWeight: 700, padding: '2px 6px',
              background: 'rgba(139,92,246,0.2)', color: 'var(--accent-violet)',
              borderRadius: 4, letterSpacing: '0.05em',
            }}>
              {item.badge}
            </span>
          )}
        </button>
      ))}

      {/* Bottom info */}
      <div style={{ marginTop: 'auto', padding: '16px 14px 4px' }}>
        <div style={{
          background: 'linear-gradient(135deg, rgba(139,92,246,0.1), rgba(99,102,241,0.1))',
          border: '1px solid rgba(139,92,246,0.2)',
          borderRadius: 10, padding: '12px',
        }}>
          <div style={{ display: 'flex', gap: 10, alignItems: 'center', marginBottom: 6 }}>
            <Zap size={16} color="var(--accent-violet)" />
            <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--accent-violet)' }}>Powered by AI</span>
          </div>
          <div style={{ fontSize: 11, color: 'var(--text-secondary)', lineHeight: 1.5, opacity: 0.8 }}>
            Google Gemini AI<br/>
            Your data is safe.
          </div>
        </div>
      </div>
    </aside>
  );
}
