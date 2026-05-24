'use client';

import { useEffect, useState } from 'react';
import { systemApi } from '@/lib/api';
import { ActiveView } from '@/app/page';
import {
  FileText, Crosshair, Mail, Search, TrendingUp,
  CheckCircle, Clock, XCircle, Zap, ChevronRight, AlertCircle
} from 'lucide-react';

interface Stats {
  resumes: number;
  jobs: number;
  applications: number;
  sent_applications: number;
  resume_chunks_embedded: number;
  jobs_embedded: number;
}

interface DashboardProps {
  onNavigate: (view: ActiveView) => void;
}

export default function Dashboard({ onNavigate }: DashboardProps) {
  const [stats, setStats] = useState<Stats | null>(null);
  const [health, setHealth] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        const [statsRes, healthRes] = await Promise.allSettled([
          systemApi.stats(),
          systemApi.health(),
        ]);
        if (statsRes.status === 'fulfilled')  setStats(statsRes.value.data);
        if (healthRes.status === 'fulfilled') setHealth(healthRes.value.data);
      } catch {}
      setLoading(false);
    };
    load();
  }, []);

  const statCards = [
    {
      label: 'Resumes',
      value: stats?.resumes ?? '—',
      icon: <FileText size={20} />,
      color: '#8b5cf6',
      action: () => onNavigate('resumes'),
      sub: `${stats?.resume_chunks_embedded ?? 0} chunks embedded`,
    },
    {
      label: 'Jobs Tracked',
      value: stats?.jobs ?? '—',
      icon: <Search size={20} />,
      color: '#06b6d4',
      action: () => onNavigate('job-search'),
      sub: `${stats?.jobs_embedded ?? 0} indexed`,
    },
    {
      label: 'Applications',
      value: stats?.applications ?? '—',
      icon: <Mail size={20} />,
      color: '#6366f1',
      action: () => onNavigate('applications'),
      sub: `${stats?.sent_applications ?? 0} emails sent`,
    },
    {
      label: 'Success Rate',
      value: stats ? (stats.applications > 0
        ? `${Math.round((stats.sent_applications / stats.applications) * 100)}%`
        : '0%') : '—',
      icon: <TrendingUp size={20} />,
      color: '#10b981',
      action: () => onNavigate('applications'),
      sub: 'Emails dispatched',
    },
  ];

  const quickActions = [
    { label: 'Upload Resume', desc: 'Add a new CV to your library', view: 'resumes' as ActiveView, icon: <FileText size={16} />, color: '#8b5cf6' },
    { label: 'Match a JD',    desc: 'Paste or upload a job description', view: 'jd-match' as ActiveView, icon: <Crosshair size={16} />, color: '#6366f1' },
    { label: 'Search Jobs',   desc: 'Find fresh openings automatically', view: 'job-search' as ActiveView, icon: <Search size={16} />, color: '#06b6d4' },
    { label: 'Track Apps',    desc: 'View sent applications & status', view: 'applications' as ActiveView, icon: <Mail size={16} />, color: '#10b981' },
  ];

  const llmProvider = health?.ollama?.provider || 'Ollama';
  const ollamaOk   = health?.ollama?.running && health?.ollama?.model_available;
  const ollamaWarn = health?.ollama?.running && !health?.ollama?.model_available;
  const ollamaDown = !health?.ollama?.running;

  return (
    <div className="fade-in" style={{ maxWidth: 1100 }}>
      {/* Header */}
      <div style={{ marginBottom: 32 }}>
        <h1 style={{ fontSize: 28, fontWeight: 800, color: 'var(--text-primary)', margin: 0 }}>
          Welcome back 👋
        </h1>
        <p style={{ color: 'var(--text-secondary)', marginTop: 6, fontSize: 15 }}>
          Your AI-powered job application hub. Upload resumes, match JDs, generate emails.
        </p>
      </div>

      {/* System status bar */}
      {health && (
        <div style={{
          display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: 28,
          padding: '12px 16px',
          background: 'var(--bg-card)', borderRadius: 12,
          border: '1px solid var(--border)',
        }}>
          <StatusPill
            label="API"
            ok={true}
            icon={<CheckCircle size={12} />}
          />
          <StatusPill
            label={ollamaOk ? `${llmProvider} (${health.ollama?.target_model})` : ollamaWarn ? `${llmProvider} (model missing)` : `${llmProvider} (offline)`}
            ok={ollamaOk}
            warn={ollamaWarn}
            icon={ollamaDown ? <XCircle size={12} /> : ollamaOk ? <CheckCircle size={12} /> : <AlertCircle size={12} />}
          />
          <StatusPill
            label={health.email?.connected ? `Gmail (${health.email?.email})` : 'Gmail (not configured)'}
            ok={health.email?.connected}
            warn={!health.email?.connected}
            icon={health.email?.connected ? <CheckCircle size={12} /> : <AlertCircle size={12} />}
          />
          <StatusPill label="ChromaDB" ok={true} icon={<CheckCircle size={12} />} />

          {ollamaDown && (
            <span style={{ marginLeft: 'auto', fontSize: 12, color: 'var(--accent-amber)' }}>
              ⚠ Run <code style={{ background: 'rgba(245,158,11,0.1)', padding: '1px 6px', borderRadius: 4 }}>ollama serve</code> to enable AI generation
            </span>
          )}
        </div>
      )}

      {/* Stat cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16, marginBottom: 32 }}>
        {statCards.map(card => (
          <button
            key={card.label}
            className="glass-card"
            onClick={card.action}
            style={{
              padding: 20, cursor: 'pointer', textAlign: 'left',
              border: '1px solid var(--border)', background: 'none',
              display: 'flex', flexDirection: 'column', gap: 12,
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <div style={{
                width: 40, height: 40, borderRadius: 10,
                background: `${card.color}20`,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                color: card.color,
              }}>
                {card.icon}
              </div>
              <ChevronRight size={14} color="var(--text-muted)" />
            </div>
            <div>
              <div style={{ fontSize: 28, fontWeight: 800, color: 'var(--text-primary)', lineHeight: 1 }}>
                {loading ? <span className="spinner" style={{ width: 24, height: 24 }} /> : card.value}
              </div>
              <div style={{ fontSize: 13, color: 'var(--text-secondary)', marginTop: 4 }}>{card.label}</div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>{card.sub}</div>
            </div>
          </button>
        ))}
      </div>

      {/* Quick actions + pipeline info */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
        {/* Quick actions */}
        <div className="glass-card" style={{ padding: 24 }}>
          <h2 style={{ fontSize: 15, fontWeight: 700, color: 'var(--text-primary)', marginBottom: 16 }}>
            Quick Actions
          </h2>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {quickActions.map(action => (
              <button
                key={action.label}
                onClick={() => onNavigate(action.view)}
                style={{
                  display: 'flex', alignItems: 'center', gap: 12,
                  padding: '12px 14px',
                  background: 'var(--bg-secondary)',
                  border: '1px solid var(--border)',
                  borderRadius: 10, cursor: 'pointer',
                  transition: 'all 0.15s', textAlign: 'left',
                }}
                onMouseEnter={e => {
                  (e.currentTarget as HTMLElement).style.borderColor = action.color;
                  (e.currentTarget as HTMLElement).style.background = `${action.color}10`;
                }}
                onMouseLeave={e => {
                  (e.currentTarget as HTMLElement).style.borderColor = 'var(--border)';
                  (e.currentTarget as HTMLElement).style.background = 'var(--bg-secondary)';
                }}
              >
                <div style={{
                  width: 32, height: 32, borderRadius: 8,
                  background: `${action.color}20`, color: action.color,
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                }}>
                  {action.icon}
                </div>
                <div>
                  <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)' }}>{action.label}</div>
                  <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>{action.desc}</div>
                </div>
                <ChevronRight size={14} color="var(--text-muted)" style={{ marginLeft: 'auto' }} />
              </button>
            ))}
          </div>
        </div>

        {/* RAG pipeline overview */}
        <div className="glass-card" style={{ padding: 24 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16 }}>
            <Zap size={16} color="var(--accent-violet)" />
            <h2 style={{ fontSize: 15, fontWeight: 700, color: 'var(--text-primary)', margin: 0 }}>
              RAG Pipeline
            </h2>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {[
              { step: '01', label: 'Resume Upload', desc: 'PDF/DOCX → parse & chunk', color: '#8b5cf6' },
              { step: '02', label: 'Embedding',    desc: 'all-MiniLM-L6-v2 → ChromaDB', color: '#6366f1' },
              { step: '03', label: 'JD Input',     desc: 'Text / PDF / Image / URL', color: '#06b6d4' },
              { step: '04', label: 'Retrieval',    desc: 'Semantic cosine similarity', color: '#10b981' },
              { step: '05', label: 'Generation',   desc: 'LLM → Email', color: '#f59e0b' },
            ].map(item => (
              <div key={item.step} style={{
                display: 'flex', alignItems: 'center', gap: 12,
                padding: '9px 12px',
                background: 'var(--bg-secondary)',
                borderRadius: 8,
                border: '1px solid var(--border)',
              }}>
                <span style={{
                  fontSize: 10, fontWeight: 800, color: item.color,
                  background: `${item.color}15`, padding: '2px 7px', borderRadius: 5,
                  fontFamily: 'JetBrains Mono, monospace',
                }}>
                  {item.step}
                </span>
                <div>
                  <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)' }}>{item.label}</div>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>{item.desc}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

function StatusPill({ label, ok, warn, icon }: { label: string; ok: boolean; warn?: boolean; icon: React.ReactNode }) {
  const color = ok ? '#10b981' : warn ? '#f59e0b' : '#f43f5e';
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 5,
      padding: '3px 10px', borderRadius: 999,
      background: `${color}15`, border: `1px solid ${color}30`,
      color, fontSize: 12, fontWeight: 500,
    }}>
      {icon}
      {label}
    </div>
  );
}
