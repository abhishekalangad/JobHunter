'use client';

import { useState } from 'react';
import toast from 'react-hot-toast';
import { jobSearchApi, jdApi } from '@/lib/api';
import {
  Search, Briefcase, MapPin, ExternalLink, Zap,
  Globe, ChevronRight, RefreshCw
} from 'lucide-react';

interface Job {
  title: string;
  company: string;
  location: string;
  description: string;
  url: string;
  source: string;
  skills?: string[];
  salary_range?: string;
  job_type?: string;
  posted_date?: string;
}

const SOURCE_COLORS: Record<string, string> = {
  remotive: '#06b6d4',
  adzuna:   '#f59e0b',
  career_page: '#10b981',
  manual:   '#8b5cf6',
};

export default function JobSearch() {
  const [keywords, setKeywords] = useState('');
  const [location, setLocation] = useState('India');
  const [limit, setLimit] = useState(20);
  const [loading, setLoading] = useState(false);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [total, setTotal] = useState(0);
  const [selectedJob, setSelectedJob] = useState<Job | null>(null);
  const [matchingId, setMatchingId] = useState<string | null>(null);

  const handleSearch = async () => {
    if (!keywords.trim()) { toast.error('Enter keywords to search'); return; }
    setLoading(true);
    setJobs([]);
    try {
      const res = await jobSearchApi.search(keywords, location, limit);
      setJobs(res.data.jobs || []);
      setTotal(res.data.total || 0);
      if (res.data.total === 0) toast('No jobs found. Try different keywords.', { icon: '🔍' });
      else toast.success(`Found ${res.data.total} jobs`);
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || 'Search failed');
    } finally {
      setLoading(false);
    }
  };

  const handleMatchJob = async (job: Job) => {
    setMatchingId(job.url || job.title);
    const tid = toast.loading('Submitting JD for RAG matching…');
    try {
      const jdRes = await jdApi.submitText(
        `${job.title}\n${job.company}\n${job.location}\n\n${job.description}`,
        job.company,
        job.title
      );
      toast.success('JD submitted! Go to JD Matcher to generate your email.', { id: tid, duration: 5000 });
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || 'Matching failed', { id: tid });
    } finally {
      setMatchingId(null);
    }
  };

  return (
    <div className="fade-in" style={{ maxWidth: 1100 }}>
      <div style={{ marginBottom: 28 }}>
        <h1 style={{ fontSize: 24, fontWeight: 800, color: 'var(--text-primary)', margin: 0 }}>
          Job Search
        </h1>
        <p style={{ color: 'var(--text-secondary)', marginTop: 4, fontSize: 14 }}>
          Fetch fresh job listings from Remotive, Adzuna, and more. One-click submit to JD Matcher.
        </p>
      </div>

      {/* Search bar */}
      <div className="glass-card" style={{ padding: 20, marginBottom: 24 }}>
        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
          <input
            className="input-field"
            style={{ flex: 2, minWidth: 200 }}
            placeholder="Keywords (e.g. Python Developer, React, ERPNext)"
            value={keywords}
            onChange={e => setKeywords(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleSearch()}
          />
          <input
            className="input-field"
            style={{ flex: 1, minWidth: 130 }}
            placeholder="Location"
            value={location}
            onChange={e => setLocation(e.target.value)}
          />
          <select
            className="input-field"
            style={{ flex: '0 0 100px' }}
            value={limit}
            onChange={e => setLimit(Number(e.target.value))}
          >
            {[10, 20, 30, 50].map(n => <option key={n} value={n}>{n} results</option>)}
          </select>
          <button
            className="btn-primary"
            style={{ padding: '10px 22px', display: 'flex', alignItems: 'center', gap: 8 }}
            onClick={handleSearch}
            disabled={loading}
          >
            {loading ? <div className="spinner" style={{ borderColor: 'rgba(255,255,255,0.3)', borderTopColor: 'white' }} /> : <Search size={16} />}
            {loading ? 'Searching…' : 'Search Jobs'}
          </button>
        </div>

        {/* Source tags */}
        <div style={{ display: 'flex', gap: 8, marginTop: 14, flexWrap: 'wrap', alignItems: 'center' }}>
          <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>Sources:</span>
          {[
            { name: 'Remotive', desc: 'Free · No key needed', color: '#06b6d4' },
            { name: 'Adzuna',   desc: 'Free tier API',        color: '#f59e0b' },
          ].map(s => (
            <div key={s.name} style={{
              display: 'flex', alignItems: 'center', gap: 5,
              padding: '3px 10px', borderRadius: 999,
              background: `${s.color}10`, border: `1px solid ${s.color}25`,
              fontSize: 12,
            }}>
              <span style={{ color: s.color, fontWeight: 600 }}>{s.name}</span>
              <span style={{ color: 'var(--text-muted)' }}>{s.desc}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Results */}
      {jobs.length > 0 && (
        <>
          <div style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 14 }}>
            {total} job{total !== 1 ? 's' : ''} found
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: selectedJob ? '1.2fr 1fr' : 'repeat(auto-fill, minmax(380px, 1fr))', gap: 14 }}>
            {/* Job cards */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10, overflow: 'auto', maxHeight: selectedJob ? 680 : 'none' }}>
              {jobs.map((job, i) => (
                <div
                  key={i}
                  className="glass-card"
                  style={{
                    padding: '14px 16px', cursor: 'pointer',
                    border: selectedJob?.url === job.url && selectedJob?.title === job.title
                      ? '1px solid var(--accent-violet)'
                      : '1px solid var(--border)',
                    background: selectedJob?.url === job.url && selectedJob?.title === job.title
                      ? 'var(--accent-violet-dim)' : 'var(--bg-card)',
                  }}
                  onClick={() => setSelectedJob(job === selectedJob ? null : job)}
                >
                  <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10 }}>
                    {/* Source icon */}
                    <div style={{
                      width: 36, height: 36, borderRadius: 9, flexShrink: 0,
                      background: `${SOURCE_COLORS[job.source] || '#8b5cf6'}15`,
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                    }}>
                      <Globe size={16} color={SOURCE_COLORS[job.source] || '#8b5cf6'} />
                    </div>

                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontWeight: 600, color: 'var(--text-primary)', fontSize: 14, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {job.title}
                      </div>
                      <div style={{ display: 'flex', gap: 10, marginTop: 3, flexWrap: 'wrap' }}>
                        {job.company && (
                          <span style={{ fontSize: 12, color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: 3 }}>
                            <Briefcase size={11} /> {job.company}
                          </span>
                        )}
                        {job.location && (
                          <span style={{ fontSize: 12, color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: 3 }}>
                            <MapPin size={11} /> {job.location}
                          </span>
                        )}
                      </div>
                      {/* Skills preview */}
                      {job.skills && job.skills.length > 0 && (
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, marginTop: 8 }}>
                          {job.skills.slice(0, 4).map((s, idx) => (
                            <span key={idx} className="skill-chip" style={{ fontSize: 11 }}>{s}</span>
                          ))}
                          {job.skills.length > 4 && (
                            <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>+{job.skills.length - 4}</span>
                          )}
                        </div>
                      )}
                    </div>

                    <span style={{
                      fontSize: 10, fontWeight: 600, padding: '2px 7px', borderRadius: 5, flexShrink: 0,
                      background: `${SOURCE_COLORS[job.source] || '#8b5cf6'}20`,
                      color: SOURCE_COLORS[job.source] || '#8b5cf6',
                    }}>
                      {job.source}
                    </span>
                  </div>
                </div>
              ))}
            </div>

            {/* Detail panel */}
            {selectedJob && (
              <div className="glass-card fade-in" style={{ padding: 20, alignSelf: 'flex-start', position: 'sticky', top: 0 }}>
                <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 16 }}>
                  <div>
                    <h3 style={{ fontWeight: 700, color: 'var(--text-primary)', margin: 0, fontSize: 16 }}>
                      {selectedJob.title}
                    </h3>
                    {selectedJob.company && (
                      <p style={{ color: 'var(--text-secondary)', margin: '4px 0 0', fontSize: 13 }}>
                        {selectedJob.company} · {selectedJob.location}
                      </p>
                    )}
                  </div>
                  <button
                    style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', padding: 4 }}
                    onClick={() => setSelectedJob(null)}
                  >
                    ✕
                  </button>
                </div>

                {selectedJob.salary_range && selectedJob.salary_range.trim() !== '-' && (
                  <div style={{ fontSize: 13, color: '#10b981', marginBottom: 12, fontWeight: 500 }}>
                    💰 {selectedJob.salary_range}
                  </div>
                )}

                <div style={{ maxHeight: 280, overflowY: 'auto', marginBottom: 16 }}>
                  <div style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.7 }}
                    dangerouslySetInnerHTML={{
                      __html: selectedJob.description?.slice(0, 1500).replace(/<[^>]+>/g, '') + (selectedJob.description?.length > 1500 ? '…' : '')
                    }}
                  />
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  <button
                    className="btn-primary"
                    style={{ width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8 }}
                    onClick={() => handleMatchJob(selectedJob)}
                    disabled={matchingId === (selectedJob.url || selectedJob.title)}
                  >
                    {matchingId === (selectedJob.url || selectedJob.title)
                      ? <div className="spinner" style={{ borderColor: 'rgba(255,255,255,0.3)', borderTopColor: 'white' }} />
                      : <Zap size={15} />}
                    Match with My Resume
                  </button>

                  {selectedJob.url && (
                    <a
                      href={selectedJob.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="btn-ghost"
                      style={{ textAlign: 'center', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6, textDecoration: 'none' }}
                    >
                      <ExternalLink size={14} /> View Original
                    </a>
                  )}
                </div>
              </div>
            )}
          </div>
        </>
      )}

      {/* Empty state */}
      {!loading && jobs.length === 0 && (
        <div className="glass-card" style={{ padding: 60, textAlign: 'center' }}>
          <Search size={48} color="var(--text-muted)" style={{ margin: '0 auto 16px' }} />
          <h3 style={{ color: 'var(--text-primary)', margin: '0 0 8px' }}>Find Your Next Role</h3>
          <p style={{ color: 'var(--text-muted)', margin: 0, fontSize: 14 }}>
            Search jobs from Remotive (remote roles, free) and Adzuna (requires free API key).<br />
            Results are saved to your database for tracking.
          </p>
        </div>
      )}
    </div>
  );
}
