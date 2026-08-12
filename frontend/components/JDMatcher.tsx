'use client';

import { useState, useEffect } from 'react';
import { useDropzone } from 'react-dropzone';
import toast from 'react-hot-toast';
import { jdApi, resumeApi } from '@/lib/api';
import { AxiosError } from 'axios';
import {
  FileText, Image as ImageIcon, Link, AlignLeft, Crosshair,
  Upload, Zap, Copy, Send, CheckCircle,
  AlertCircle, ExternalLink
} from 'lucide-react';

type InputMode = 'text' | 'pdf' | 'image' | 'url';

interface MatchResult {
  job_id: string;
  job_title: string;
  company: string;
  best_match: {
    resume_id: string;
    resume_name: string;
    candidate_name: string;
    semantic_score: number;
    overall_score: number;
    skill_match_percentage: number;
    matched_skills: string[];
    missing_skills: string[];
  };
  all_matches: { resume_id: string; score: number; metadata?: Record<string, unknown> }[];
  generated_email: { subject: string; body: string; error?: string } | null;
  generated_cover_letter: string | null;
  application_id?: string;
}

export default function JDMatcher() {
  const [mode, setMode] = useState<InputMode>('text');
  const [text, setText] = useState('');
  const [url, setUrl] = useState('');
  const [company, setCompany] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [step, setStep] = useState('');
  const [result, setResult] = useState<MatchResult | null>(null);
  const [generateCoverLetter, setGenerateCoverLetter] = useState(false);
  const [recipientEmail, setRecipientEmail] = useState('');
  const [sending, setSending] = useState(false);
  const [copiedField, setCopiedField] = useState<string | null>(null);
  const [resumesList, setResumesList] = useState<{ id: string; original_filename?: string; filename?: string; name?: string }[]>([]);
  const [switchingResume, setSwitchingResume] = useState(false);

  useEffect(() => {
    resumeApi.list().then(res => {
      const list = Array.isArray(res.data) ? res.data : (res.data.resumes || []);
      setResumesList(list);
    }).catch(() => {});
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop: files => setFile(files[0] ?? null),
    accept: mode === 'pdf'
      ? { 'application/pdf': ['.pdf'] }
      : { 'image/*': ['.jpg', '.jpeg', '.png', '.webp'] },
    multiple: false,
  });

  const handleSubmit = async () => {
    setLoading(true);
    setResult(null);
    try {
      let jobRes: { data: { id: string } };

      if (mode === 'text') {
        if (!text.trim()) { toast.error('Please enter a job description'); setLoading(false); return; }
        setStep('Parsing job description…');
        jobRes = await jdApi.submitText(text, company || undefined);
      } else if (mode === 'url') {
        if (!url.trim()) { toast.error('Please enter a URL'); setLoading(false); return; }
        setStep('Fetching job from URL…');
        jobRes = await jdApi.submitUrl(url, company || undefined);
      } else {
        if (!file) { toast.error('Please select a file'); setLoading(false); return; }
        setStep('Uploading and parsing file…');
        jobRes = mode === 'pdf'
          ? await jdApi.submitPdf(file)
          : await jdApi.submitImage(file);
      }

      const jobId = jobRes.data.id;
      setStep('Running RAG matching against your resume library…');
      const matchRes = await jdApi.match(jobId, true, generateCoverLetter);
      setResult(matchRes.data);
      toast.success('Match complete!');
    } catch (err: unknown) {
      const error = err as AxiosError<{ detail?: string }>;
      const msg = error?.response?.data?.detail || (err as Error).message || 'Something went wrong';
      toast.error(msg);
    } finally {
      setLoading(false);
      setStep('');
    }
  };

  const handleSend = async () => {
    if (!recipientEmail || !result?.application_id) return;
    setSending(true);
    try {
      const { emailApi } = await import('@/lib/api');
      await emailApi.send(result.application_id, recipientEmail);
      toast.success(`Email sent to ${recipientEmail}!`);
    } catch (err: unknown) {
      const error = err as AxiosError<{ detail?: string }>;
      toast.error(error?.response?.data?.detail || 'Send failed');
    } finally {
      setSending(false);
    }
  };

  const copy = (text: string, key: string) => {
    navigator.clipboard.writeText(text);
    setCopiedField(key);
    setTimeout(() => setCopiedField(null), 2000);
  };

  const scoreClass = (s: number) => s >= 75 ? 'score-high' : s >= 50 ? 'score-mid' : 'score-low';

  const modes: { id: InputMode; label: string; icon: React.ReactNode }[] = [
    { id: 'text',  label: 'Paste Text', icon: <AlignLeft   size={15} /> },
    { id: 'pdf',   label: 'Upload PDF', icon: <FileText    size={15} /> },
    { id: 'image', label: 'Screenshot', icon: <ImageIcon   size={15} /> },
    { id: 'url',   label: 'From URL',   icon: <Link        size={15} /> },
  ];

  return (
    <div className="fade-in" style={{ maxWidth: 1050 }}>
      <div style={{ marginBottom: 28 }}>
        <h1 style={{ fontSize: 24, fontWeight: 800, color: 'var(--text-primary)', margin: 0 }}>
          JD Matcher <span className="gradient-text">— RAG Engine</span>
        </h1>
        <p style={{ color: 'var(--text-secondary)', marginTop: 4, fontSize: 14 }}>
          Input a job description → semantic matching → AI-generated application email.
        </p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: result ? '1fr 1.1fr' : '1fr', gap: 24 }}>
        {/* Left: Input panel */}
        <div className="glass-card" style={{ padding: 24 }}>
          {/* Mode tabs */}
          <div style={{ display: 'flex', gap: 6, marginBottom: 20, background: 'var(--bg-secondary)', padding: 4, borderRadius: 10 }}>
            {modes.map(m => (
              <button
                key={m.id}
                className={`tab-btn ${mode === m.id ? 'active' : ''}`}
                style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6 }}
                onClick={() => { setMode(m.id); setFile(null); }}
              >
                {m.icon} {m.label}
              </button>
            ))}
          </div>

          {/* Company (optional) */}
          <div style={{ marginBottom: 14 }}>
            <input
              className="input-field"
              placeholder="Company name (optional)"
              value={company}
              onChange={e => setCompany(e.target.value)}
            />
          </div>

          {/* Input area */}
          {mode === 'text' && (
            <textarea
              className="input-field"
              style={{ minHeight: 200 }}
              placeholder="Paste the full job description here…&#10;&#10;Include: role title, required skills, responsibilities, company info, contact details."
              value={text}
              onChange={e => setText(e.target.value)}
            />
          )}
          {mode === 'url' && (
            <input
              className="input-field"
              placeholder="https://www.linkedin.com/jobs/view/..."
              value={url}
              onChange={e => setUrl(e.target.value)}
            />
          )}
          {(mode === 'pdf' || mode === 'image') && (
            <div {...getRootProps()} className={`drop-zone ${isDragActive ? 'active' : ''}`} style={{ minHeight: 120 }}>
              <input {...getInputProps()} />
              {file ? (
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <FileText size={20} color="var(--accent-violet)" />
                  <span style={{ fontSize: 14, color: 'var(--text-primary)' }}>{file.name}</span>
                  <button onClick={e => { e.stopPropagation(); setFile(null); }} style={{ marginLeft: 'auto', background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}>
                    ✕
                  </button>
                </div>
              ) : (
                <div style={{ color: 'var(--text-muted)', fontSize: 14 }}>
                  <Upload size={20} style={{ margin: '0 auto 8px', display: 'block' }} />
                  Drop your {mode === 'pdf' ? 'PDF' : 'screenshot'} here
                </div>
              )}
            </div>
          )}

          {/* Options */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginTop: 14 }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer', fontSize: 13, color: 'var(--text-secondary)' }}>
              <input
                type="checkbox"
                checked={generateCoverLetter}
                onChange={e => setGenerateCoverLetter(e.target.checked)}
                style={{ accentColor: 'var(--accent-violet)' }}
              />
              Generate cover letter too
            </label>
          </div>

          <button
            className="btn-primary"
            style={{ width: '100%', marginTop: 16, padding: '12px', fontSize: 15, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8 }}
            onClick={handleSubmit}
            disabled={loading}
          >
            {loading ? (
              <><div className="spinner" style={{ borderColor: 'rgba(255,255,255,0.3)', borderTopColor: 'white' }} /> {step || 'Processing…'}</>
            ) : (
              <><Crosshair size={17} /> Match & Generate</>
            )}
          </button>
        </div>

        {/* Right: Results panel */}
        {result && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }} className="fade-in">
            {/* Best match card */}
            <div className="glass-card" style={{ padding: 20 }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16, flexWrap: 'wrap', gap: 10 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <CheckCircle size={16} color="var(--accent-emerald)" />
                  <span style={{ fontWeight: 700, color: 'var(--text-primary)', fontSize: 14 }}>Matched Resume</span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--accent-violet)' }}>Change Resume:</span>
                  <select
                    className="input-field"
                    style={{
                      padding: '5px 12px', fontSize: 12, width: 'auto',
                      background: 'var(--bg-secondary)', cursor: 'pointer',
                      borderColor: 'rgba(139,92,246,0.4)', color: 'var(--text-primary)',
                      fontWeight: 600, borderRadius: 8,
                    }}
                    value={result.best_match.resume_id}
                    onChange={async e => {
                      const newResumeId = e.target.value;
                      if (!result.job_id) return;
                      setSwitchingResume(true);
                      const tid = toast.loading('Switching resume & regenerating email…');
                      try {
                        const res = await jdApi.match(result.job_id, true, generateCoverLetter, newResumeId);
                        setResult(res.data);
                        toast.success('Resume switched & email regenerated!', { id: tid });
                      } catch (err: unknown) {
                        const error = err as AxiosError<{ detail?: string }>;
                        toast.error(error?.response?.data?.detail || 'Switch failed', { id: tid });
                      } finally {
                        setSwitchingResume(false);
                      }
                    }}
                    disabled={switchingResume}
                  >
                    {resumesList.length > 0 ? (
                      resumesList.map(r => (
                        <option key={r.id} value={r.id}>
                          {r.original_filename || r.filename || r.name || 'Resume'}
                        </option>
                      ))
                    ) : (
                      <option value={result.best_match.resume_id}>
                        {result.best_match.resume_name}
                      </option>
                    )}
                  </select>
                </div>
              </div>

              {/* Score + resume */}
              <div style={{ display: 'flex', gap: 16, alignItems: 'flex-start' }}>
                {/* Score ring */}
                <ScoreRing score={result.best_match.overall_score} />

                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 700, color: 'var(--text-primary)', fontSize: 15 }}>
                    {result.best_match.resume_name}
                  </div>
                  {result.best_match.candidate_name && (
                    <div style={{ color: 'var(--text-secondary)', fontSize: 13, marginTop: 2 }}>
                      {result.best_match.candidate_name}
                    </div>
                  )}
                  <div style={{ display: 'flex', gap: 8, marginTop: 10, flexWrap: 'wrap' }}>
                    <span className={`score-badge ${scoreClass(result.best_match.semantic_score)}`}>
                      Semantic: {result.best_match.semantic_score.toFixed(1)}%
                    </span>
                    <span className={`score-badge ${scoreClass(result.best_match.skill_match_percentage)}`}>
                      Skills: {result.best_match.skill_match_percentage.toFixed(1)}%
                    </span>
                  </div>
                </div>
              </div>

              {/* Skill breakdown */}
              {result.best_match.matched_skills.length > 0 && (
                <div style={{ marginTop: 14 }}>
                  <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                    Matched Skills
                  </div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 5 }}>
                    {result.best_match.matched_skills.slice(0, 10).map(s => (
                      <span key={s} style={{
                        fontSize: 11, padding: '2px 8px', borderRadius: 5,
                        background: 'rgba(16,185,129,0.1)', color: '#10b981',
                        border: '1px solid rgba(16,185,129,0.2)',
                      }}>{s}</span>
                    ))}
                  </div>
                </div>
              )}
              {result.best_match.missing_skills.length > 0 && (
                <div style={{ marginTop: 10 }}>
                  <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                    Gaps
                  </div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 5 }}>
                    {result.best_match.missing_skills.slice(0, 8).map(s => (
                      <span key={s} style={{
                        fontSize: 11, padding: '2px 8px', borderRadius: 5,
                        background: 'rgba(244,63,94,0.1)', color: '#fb7185',
                        border: '1px solid rgba(244,63,94,0.2)',
                      }}>{s}</span>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Generated email */}
            {result.generated_email && !result.generated_email.error && (
              <div className="glass-card" style={{ padding: 20 }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <Zap size={15} color="var(--accent-violet)" />
                    <span style={{ fontWeight: 700, color: 'var(--text-primary)', fontSize: 14 }}>Generated Email</span>
                  </div>
                  <button
                    className="btn-ghost"
                    style={{ padding: '5px 10px', fontSize: 12, display: 'flex', alignItems: 'center', gap: 5 }}
                    onClick={() => copy(
                      `Subject: ${result.generated_email!.subject}\n\n${result.generated_email!.body}`,
                      'email'
                    )}
                  >
                    {copiedField === 'email' ? <CheckCircle size={13} color="#10b981" /> : <Copy size={13} />}
                    {copiedField === 'email' ? 'Copied!' : 'Copy'}
                  </button>
                </div>

                {/* Subject */}
                <div style={{
                  padding: '8px 12px',
                  background: 'var(--bg-secondary)',
                  borderRadius: 8, marginBottom: 10,
                  fontSize: 13, color: 'var(--text-primary)', fontWeight: 500,
                }}>
                  <span style={{ color: 'var(--text-muted)', marginRight: 6 }}>Subject:</span>
                  {result.generated_email.subject}
                </div>

                {/* Body */}
                <div className="email-preview" style={{ maxHeight: 280 }}>
                  {result.generated_email.body}
                </div>

                {/* Send & Gmail Draft section */}
                {result.application_id && (
                  <div style={{ marginTop: 14, display: 'flex', flexDirection: 'column', gap: 10 }}>
                    <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                      <input
                        className="input-field"
                        style={{ flex: 1, minWidth: 200 }}
                        placeholder="Recipient email (HR / hiring manager)"
                        value={recipientEmail}
                        onChange={e => setRecipientEmail(e.target.value)}
                        type="email"
                      />
                      <button
                        className="btn-primary"
                        style={{
                          padding: '10px 18px', display: 'flex', alignItems: 'center', gap: 6, whiteSpace: 'nowrap',
                          background: 'linear-gradient(135deg, #ea4335 0%, #c5221f 100%)',
                          boxShadow: '0 4px 14px rgba(234,67,53,0.35)',
                        }}
                        onClick={() => {
                          const subject = result.generated_email?.subject || '';
                          const rawBody = result.generated_email?.body || '';
                          // Strip markdown bold/italic asterisks & underscores that LLM may output
                          const body = rawBody
                            .replace(/\*\*([^*]+)\*\*/g, '$1')
                            .replace(/\*([^*]+)\*/g, '$1')
                            .replace(/__([^_]+)__/g, '$1')
                            .replace(/_([^_]+)_/g, '$1');
                          const gmailUrl = `https://mail.google.com/mail/?view=cm&fs=1&to=${encodeURIComponent(recipientEmail)}&su=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
                          window.open(gmailUrl, '_blank');
                          toast.success('Opened in Gmail Draft!');
                        }}
                      >
                        <ExternalLink size={15} /> Draft in Gmail
                      </button>
                      <button
                        className="btn-ghost"
                        style={{ padding: '10px 16px', display: 'flex', alignItems: 'center', gap: 6, whiteSpace: 'nowrap' }}
                        onClick={handleSend}
                        disabled={sending || !recipientEmail}
                      >
                        {sending ? <div className="spinner" style={{ borderColor: 'rgba(255,255,255,0.3)', borderTopColor: 'white' }} /> : <Send size={14} />}
                        Send via SMTP
                      </button>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Cover letter */}
            {result.generated_cover_letter && (
              <div className="glass-card" style={{ padding: 20 }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
                  <span style={{ fontWeight: 700, color: 'var(--text-primary)', fontSize: 14 }}>Cover Letter</span>
                  <button className="btn-ghost" style={{ padding: '5px 10px', fontSize: 12, display: 'flex', alignItems: 'center', gap: 5 }}
                    onClick={() => copy(result.generated_cover_letter!, 'cover')}>
                    {copiedField === 'cover' ? <CheckCircle size={13} color="#10b981" /> : <Copy size={13} />}
                    {copiedField === 'cover' ? 'Copied!' : 'Copy'}
                  </button>
                </div>
                <div className="email-preview" style={{ maxHeight: 260 }}>
                  {result.generated_cover_letter}
                </div>
              </div>
            )}

            {/* AI Error Warning */}
            {result.generated_email?.error && (
              <div style={{
                padding: '12px 16px', borderRadius: 10,
                background: 'rgba(245,158,11,0.08)',
                border: '1px solid rgba(245,158,11,0.2)',
                display: 'flex', gap: 10, alignItems: 'flex-start',
              }}>
                <AlertCircle size={16} color="#f59e0b" style={{ flexShrink: 0, marginTop: 1 }} />
                <div>
                  <div style={{ fontWeight: 600, color: '#f59e0b', fontSize: 13 }}>AI Generation Error</div>
                  <div style={{ color: 'var(--text-muted)', fontSize: 12, marginTop: 2 }}>
                    {result.generated_email.error}
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function ScoreRing({ score }: { score: number }) {
  const r = 36, cx = 44, cy = 44;
  const circumference = 2 * Math.PI * r;
  const filled = (score / 100) * circumference;
  const color = score >= 75 ? '#10b981' : score >= 50 ? '#f59e0b' : '#f43f5e';

  return (
    <div style={{ position: 'relative', width: 88, height: 88, flexShrink: 0 }}>
      <svg width="88" height="88" style={{ transform: 'rotate(-90deg)' }}>
        <circle cx={cx} cy={cy} r={r} fill="none" stroke="var(--border)" strokeWidth="7" />
        <circle
          cx={cx} cy={cy} r={r} fill="none"
          stroke={color} strokeWidth="7"
          strokeDasharray={`${filled} ${circumference - filled}`}
          strokeLinecap="round"
          style={{ transition: 'stroke-dasharray 0.8s ease' }}
        />
      </svg>
      <div style={{
        position: 'absolute', top: 0, left: 0, width: '100%', height: '100%',
        display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
      }}>
        <span style={{ fontSize: 16, fontWeight: 800, color, lineHeight: 1 }}>
          {score.toFixed(0)}%
        </span>
        <span style={{ fontSize: 9, color: 'var(--text-muted)', marginTop: 2 }}>Match</span>
      </div>
    </div>
  );
}
