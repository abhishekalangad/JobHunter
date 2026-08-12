'use client';

import { useEffect, useState } from 'react';
import toast from 'react-hot-toast';
import { emailApi } from '@/lib/api';
import {
  Mail, Send, CheckCircle, XCircle, Clock, Star,
  ChevronDown, ChevronUp, RefreshCw, Copy, Eye, ExternalLink
} from 'lucide-react';

interface Application {
  id: string;
  job_title: string;
  company: string;
  resume_name: string;
  candidate_name: string;
  similarity_score: number;
  status: string;
  generated_subject: string;
  email_recipient: string;
  email_sent_at: string;
  created_at: string;
}

const STATUS_OPTIONS = ['pending', 'draft', 'sent', 'interview', 'offer', 'rejected', 'withdrawn'];

const statusIcon: Record<string, React.ReactNode> = {
  sent:      <CheckCircle size={13} />,
  interview: <Star size={13} />,
  offer:     <Star size={13} />,
  rejected:  <XCircle size={13} />,
  draft:     <Clock size={13} />,
  pending:   <Clock size={13} />,
};

export default function ApplicationTracker() {
  const [apps, setApps] = useState<Application[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [detailData, setDetailData] = useState<Record<string, any>>({});
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [recipientMap, setRecipientMap] = useState<Record<string, string>>({});
  const [sendingId, setSendingId] = useState<string | null>(null);

  const load = async () => {
    try {
      const res = await emailApi.listApplications();
      setApps(res.data);
    } catch { toast.error('Failed to load applications'); }
    finally { setLoading(false); }
  };

  useEffect(() => { load(); }, []);

  const toggleExpand = async (id: string) => {
    if (expandedId === id) { setExpandedId(null); return; }
    setExpandedId(id);
    if (!detailData[id]) {
      try {
        const res = await emailApi.getApplication(id);
        setDetailData(d => ({ ...d, [id]: res.data }));
      } catch {}
    }
  };

  const updateStatus = async (id: string, status: string) => {
    try {
      await emailApi.updateStatus(id, status);
      setApps(prev => prev.map(a => a.id === id ? { ...a, status } : a));
      toast.success(`Status updated to "${status}"`);
    } catch { toast.error('Update failed'); }
  };

  const handleSend = async (appId: string) => {
    const email = recipientMap[appId];
    if (!email) { toast.error('Enter recipient email'); return; }
    setSendingId(appId);
    try {
      await emailApi.send(appId, email);
      toast.success(`Email sent to ${email}!`);
      await load();
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || 'Send failed');
    } finally { setSendingId(null); }
  };

  const handleRegenerate = async (appId: string) => {
    const tid = toast.loading('Regenerating email…');
    try {
      const res = await emailApi.regenerate(appId);
      setDetailData(d => ({ ...d, [appId]: { ...d[appId], ...res.data } }));
      toast.success('Email regenerated!', { id: tid });
    } catch { toast.error('Regeneration failed', { id: tid }); }
  };

  const filtered = statusFilter === 'all' ? apps : apps.filter(a => a.status === statusFilter);
  const scoreColor = (s: number) => s >= 75 ? '#10b981' : s >= 50 ? '#f59e0b' : '#f43f5e';

  return (
    <div className="fade-in" style={{ maxWidth: 1000 }}>
      <div style={{ marginBottom: 28 }}>
        <h1 style={{ fontSize: 24, fontWeight: 800, color: 'var(--text-primary)', margin: 0 }}>
          Application Tracker
        </h1>
        <p style={{ color: 'var(--text-secondary)', marginTop: 4, fontSize: 14 }}>
          Monitor all your job applications, email status, and interview progress.
        </p>
      </div>

      {/* Summary row */}
      {apps.length > 0 && (
        <div style={{ display: 'flex', gap: 12, marginBottom: 24, flexWrap: 'wrap' }}>
          {[
            { label: 'Total',     value: apps.length,                                  color: '#8b5cf6' },
            { label: 'Sent',      value: apps.filter(a => a.status === 'sent').length,      color: '#10b981' },
            { label: 'Interview', value: apps.filter(a => a.status === 'interview').length, color: '#f59e0b' },
            { label: 'Offer',     value: apps.filter(a => a.status === 'offer').length,     color: '#6366f1' },
            { label: 'Rejected',  value: apps.filter(a => a.status === 'rejected').length,  color: '#f43f5e' },
          ].map(s => (
            <div key={s.label} style={{
              padding: '8px 18px', borderRadius: 10,
              background: `${s.color}10`, border: `1px solid ${s.color}25`,
              cursor: 'pointer',
            }} onClick={() => setStatusFilter(s.label.toLowerCase() === 'total' ? 'all' : s.label.toLowerCase())}>
              <span style={{ fontSize: 20, fontWeight: 800, color: s.color }}>{s.value}</span>
              <span style={{ fontSize: 12, color: 'var(--text-muted)', marginLeft: 6 }}>{s.label}</span>
            </div>
          ))}
        </div>
      )}

      {/* Filter bar */}
      <div style={{ display: 'flex', gap: 6, marginBottom: 20, flexWrap: 'wrap' }}>
        {['all', ...STATUS_OPTIONS].map(s => (
          <button
            key={s}
            className={`tab-btn ${statusFilter === s ? 'active' : ''}`}
            onClick={() => setStatusFilter(s)}
            style={{ textTransform: 'capitalize' }}
          >
            {s}
          </button>
        ))}
      </div>

      {/* Application list */}
      {loading ? (
        <div style={{ textAlign: 'center', padding: 40 }}>
          <div className="spinner" style={{ margin: '0 auto', width: 32, height: 32 }} />
        </div>
      ) : filtered.length === 0 ? (
        <div className="glass-card" style={{ padding: 40, textAlign: 'center' }}>
          <Mail size={40} color="var(--text-muted)" style={{ margin: '0 auto 12px' }} />
          <p style={{ color: 'var(--text-muted)', margin: 0 }}>
            {apps.length === 0
              ? 'No applications yet. Use the JD Matcher to generate your first application!'
              : `No applications with status "${statusFilter}".`}
          </p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {filtered.map(app => (
            <div key={app.id} className="glass-card" style={{ overflow: 'hidden' }}>
              <div style={{ padding: '14px 20px', display: 'flex', alignItems: 'center', gap: 14 }}>
                {/* Match score */}
                <div style={{
                  width: 46, height: 46, borderRadius: 12, flexShrink: 0,
                  background: `${scoreColor(app.similarity_score ?? 0)}15`,
                  display: 'flex', flexDirection: 'column',
                  alignItems: 'center', justifyContent: 'center',
                }}>
                  <span style={{ fontSize: 14, fontWeight: 800, color: scoreColor(app.similarity_score ?? 0), lineHeight: 1 }}>
                    {(app.similarity_score ?? 0).toFixed(0)}
                  </span>
                  <span style={{ fontSize: 9, color: 'var(--text-muted)' }}>%</span>
                </div>

                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontWeight: 600, color: 'var(--text-primary)', fontSize: 14, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {app.job_title || 'Unknown Position'}
                    {app.company && <span style={{ color: 'var(--text-muted)', fontWeight: 400 }}> @ {app.company}</span>}
                  </div>
                  <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>
                    {app.resume_name} · {new Date(app.created_at).toLocaleDateString()}
                    {app.email_sent_at && ` · Sent: ${new Date(app.email_sent_at).toLocaleDateString()}`}
                  </div>
                </div>

                {/* Status selector */}
                <select
                  value={app.status}
                  onChange={e => updateStatus(app.id, e.target.value)}
                  className={`status-badge status-${app.status}`}
                  style={{ cursor: 'pointer', background: 'transparent', border: 'none', outline: 'none', fontWeight: 500 }}
                >
                  {STATUS_OPTIONS.map(s => (
                    <option key={s} value={s} style={{ background: 'var(--bg-card)' }}>{s}</option>
                  ))}
                </select>

                <button
                  className="btn-ghost"
                  style={{ padding: '6px 8px' }}
                  onClick={() => toggleExpand(app.id)}
                >
                  {expandedId === app.id ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                </button>
              </div>

              {/* Expanded */}
              {expandedId === app.id && (
                <div style={{ borderTop: '1px solid var(--border)', padding: '16px 20px', background: 'var(--bg-secondary)' }}>
                  {!detailData[app.id] ? (
                    <div className="spinner" />
                  ) : (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
                      {/* Subject */}
                      {detailData[app.id].generated_subject && (
                        <div>
                          <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 6 }}>Subject</div>
                          <div style={{ fontSize: 13, color: 'var(--text-primary)', padding: '8px 12px', background: 'var(--bg-card)', borderRadius: 8 }}>
                            {detailData[app.id].generated_subject}
                          </div>
                        </div>
                      )}

                      {/* Email body */}
                      {detailData[app.id].generated_email && (
                        <div>
                          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
                            <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>Email Body</div>
                            <div style={{ display: 'flex', gap: 6 }}>
                              <button
                                className="btn-ghost"
                                style={{ padding: '4px 10px', fontSize: 12, display: 'flex', alignItems: 'center', gap: 5 }}
                                onClick={() => { navigator.clipboard.writeText(detailData[app.id].generated_email); toast.success('Copied!'); }}
                              >
                                <Copy size={12} /> Copy
                              </button>
                              <button
                                className="btn-ghost"
                                style={{ padding: '4px 10px', fontSize: 12, display: 'flex', alignItems: 'center', gap: 5 }}
                                onClick={() => handleRegenerate(app.id)}
                              >
                                <RefreshCw size={12} /> Regenerate
                              </button>
                            </div>
                          </div>
                          <div className="email-preview" style={{ maxHeight: 220 }}>
                            {detailData[app.id].generated_email}
                          </div>
                        </div>
                      )}

                      {/* Send & Draft section */}
                      {app.status !== 'sent' && (
                        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                          <input
                            className="input-field"
                            style={{ flex: 1, minWidth: 200 }}
                            placeholder="Recipient email"
                            value={recipientMap[app.id] || ''}
                            onChange={e => setRecipientMap(r => ({ ...r, [app.id]: e.target.value }))}
                            type="email"
                          />
                          <button
                            className="btn-primary"
                            style={{
                              padding: '10px 16px', display: 'flex', alignItems: 'center', gap: 6, whiteSpace: 'nowrap',
                              background: 'linear-gradient(135deg, #ea4335 0%, #c5221f 100%)',
                              boxShadow: '0 4px 14px rgba(234,67,53,0.35)',
                            }}
                            onClick={() => {
                              const subject = detailData[app.id]?.generated_subject || '';
                              const rawBody = detailData[app.id]?.generated_email || '';
                              // Strip markdown bold/italic asterisks & underscores that LLM may output
                              const body = rawBody
                                .replace(/\*\*([^*]+)\*\*/g, '$1')
                                .replace(/\*([^*]+)\*/g, '$1')
                                .replace(/__([^_]+)__/g, '$1')
                                .replace(/_([^_]+)_/g, '$1');
                              const recipient = recipientMap[app.id] || '';
                              const gmailUrl = `https://mail.google.com/mail/?view=cm&fs=1&to=${encodeURIComponent(recipient)}&su=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
                              window.open(gmailUrl, '_blank');
                              toast.success('Opened in Gmail Draft!');
                            }}
                          >
                            <ExternalLink size={14} /> Draft in Gmail
                          </button>
                          <button
                            className="btn-ghost"
                            style={{ padding: '10px 16px', display: 'flex', alignItems: 'center', gap: 6, whiteSpace: 'nowrap' }}
                            onClick={() => handleSend(app.id)}
                            disabled={sendingId === app.id}
                          >
                            {sendingId === app.id
                              ? <div className="spinner" style={{ borderColor: 'rgba(255,255,255,0.3)', borderTopColor: 'white' }} />
                              : <Send size={14} />}
                            Send via SMTP
                          </button>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
