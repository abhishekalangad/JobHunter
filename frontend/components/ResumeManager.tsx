'use client';

import { useCallback, useEffect, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import toast from 'react-hot-toast';
import { resumeApi } from '@/lib/api';
import {
  Upload, FileText, Trash2, RefreshCw, CheckCircle,
  Clock, ChevronDown, ChevronUp, X
} from 'lucide-react';

interface Resume {
  id: string;
  filename: string;
  name: string;
  email: string;
  skills: string[];
  is_embedded: boolean;
  file_type: string;
  file_size: number;
  created_at: string;
}

export default function ResumeManager() {
  const [resumes, setResumes] = useState<Resume[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [detailData, setDetailData] = useState<Record<string, any>>({});

  const loadResumes = async () => {
    try {
      const res = await resumeApi.list();
      setResumes(res.data);
    } catch {
      toast.error('Failed to load resumes');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadResumes(); }, []);

  const onDrop = useCallback(async (files: File[]) => {
    for (const file of files) {
      setUploading(true);
      const tid = toast.loading(`Uploading ${file.name}…`);
      try {
        await resumeApi.upload(file);
        toast.success(`${file.name} uploaded! Parsing in background…`, { id: tid });
        await loadResumes();
      } catch (err: any) {
        toast.error(err?.response?.data?.detail || 'Upload failed', { id: tid });
      } finally {
        setUploading(false);
      }
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'application/pdf': ['.pdf'], 'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'] },
    multiple: true,
    maxSize: 10 * 1024 * 1024,
  });

  const handleDelete = async (id: string, name: string) => {
    if (!confirm(`Delete "${name}"?`)) return;
    try {
      await resumeApi.delete(id);
      toast.success('Resume deleted');
      setResumes(r => r.filter(x => x.id !== id));
    } catch {
      toast.error('Delete failed');
    }
  };

  const handleReembed = async (id: string) => {
    const tid = toast.loading('Re-embedding…');
    try {
      await resumeApi.reembed(id);
      toast.success('Re-embedding started', { id: tid });
      await loadResumes();
    } catch {
      toast.error('Re-embed failed', { id: tid });
    }
  };

  const toggleExpand = async (id: string) => {
    if (expandedId === id) { setExpandedId(null); return; }
    setExpandedId(id);
    if (!detailData[id]) {
      try {
        const res = await resumeApi.get(id);
        setDetailData(d => ({ ...d, [id]: res.data }));
      } catch {}
    }
  };

  const fmtSize = (bytes: number) =>
    bytes < 1024 * 1024 ? `${(bytes / 1024).toFixed(0)} KB` : `${(bytes / (1024 * 1024)).toFixed(1)} MB`;

  return (
    <div className="fade-in" style={{ maxWidth: 900 }}>
      {/* Header */}
      <div style={{ marginBottom: 28 }}>
        <h1 style={{ fontSize: 24, fontWeight: 800, color: 'var(--text-primary)', margin: 0 }}>
          Resume Library
        </h1>
        <p style={{ color: 'var(--text-secondary)', marginTop: 4, fontSize: 14 }}>
          Upload your resumes — they'll be parsed, chunked, and embedded into ChromaDB for semantic matching.
        </p>
      </div>

      {/* Drop zone */}
      <div
        {...getRootProps()}
        className={`drop-zone ${isDragActive ? 'active' : ''}`}
        style={{ marginBottom: 28, cursor: uploading ? 'not-allowed' : 'pointer' }}
      >
        <input {...getInputProps()} disabled={uploading} />
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 10 }}>
          {uploading ? (
            <div className="spinner" style={{ width: 36, height: 36, borderWidth: 3 }} />
          ) : (
            <div style={{
              width: 52, height: 52, borderRadius: 14,
              background: 'var(--accent-violet-dim)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}>
              <Upload size={22} color="var(--accent-violet)" />
            </div>
          )}
          <div>
            <p style={{ margin: 0, fontWeight: 600, color: 'var(--text-primary)', fontSize: 15 }}>
              {isDragActive ? 'Drop your resume here' : uploading ? 'Uploading…' : 'Drag & drop resumes or click to browse'}
            </p>
            <p style={{ margin: '4px 0 0', color: 'var(--text-muted)', fontSize: 13 }}>
              Supports PDF and DOCX · Max 10MB per file · Multiple files allowed
            </p>
          </div>
        </div>
      </div>

      {/* Resume list */}
      {loading ? (
        <div style={{ textAlign: 'center', padding: 40 }}>
          <div className="spinner" style={{ margin: '0 auto', width: 32, height: 32 }} />
        </div>
      ) : resumes.length === 0 ? (
        <div className="glass-card" style={{ padding: 40, textAlign: 'center' }}>
          <FileText size={40} color="var(--text-muted)" style={{ margin: '0 auto 12px' }} />
          <p style={{ color: 'var(--text-muted)', margin: 0 }}>No resumes uploaded yet. Drop your first resume above.</p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <div style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 4 }}>
            {resumes.length} resume{resumes.length !== 1 ? 's' : ''} in library
          </div>
          {resumes.map(resume => (
            <div key={resume.id} className="glass-card" style={{ overflow: 'hidden' }}>
              {/* Card header */}
              <div style={{
                padding: '16px 20px',
                display: 'flex', alignItems: 'center', gap: 14,
              }}>
                <div style={{
                  width: 40, height: 40, borderRadius: 10, flexShrink: 0,
                  background: 'var(--accent-violet-dim)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                }}>
                  <FileText size={18} color="var(--accent-violet)" />
                </div>

                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span style={{ fontWeight: 600, color: 'var(--text-primary)', fontSize: 14, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {resume.filename}
                    </span>
                    <span style={{
                      fontSize: 11, padding: '1px 7px', borderRadius: 4, flexShrink: 0,
                      background: resume.file_type === 'pdf' ? 'rgba(244,63,94,0.1)' : 'rgba(99,102,241,0.1)',
                      color: resume.file_type === 'pdf' ? '#fb7185' : '#a5b4fc',
                      border: `1px solid ${resume.file_type === 'pdf' ? 'rgba(244,63,94,0.2)' : 'rgba(99,102,241,0.2)'}`,
                    }}>
                      {resume.file_type?.toUpperCase()}
                    </span>
                  </div>
                  <div style={{ display: 'flex', gap: 16, marginTop: 3, flexWrap: 'wrap' }}>
                    {resume.name && <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{resume.name}</span>}
                    {resume.email && <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>{resume.email}</span>}
                    <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>{fmtSize(resume.file_size)}</span>
                  </div>
                </div>

                {/* Status + actions */}
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexShrink: 0 }}>
                  {resume.is_embedded ? (
                    <div style={{ display: 'flex', alignItems: 'center', gap: 4, color: '#10b981', fontSize: 12 }}>
                      <CheckCircle size={13} /> Embedded
                    </div>
                  ) : (
                    <div className="processing" style={{ display: 'flex', alignItems: 'center', gap: 4, color: '#f59e0b', fontSize: 12, borderRadius: 6, padding: '2px 6px' }}>
                      <Clock size={13} /> Processing…
                    </div>
                  )}
                  <button
                    className="btn-ghost"
                    style={{ padding: '6px 8px' }}
                    onClick={() => handleReembed(resume.id)}
                    title="Re-embed"
                  >
                    <RefreshCw size={14} />
                  </button>
                  <button
                    style={{ padding: '6px 8px', background: 'rgba(244,63,94,0.1)', border: '1px solid rgba(244,63,94,0.2)', borderRadius: 8, cursor: 'pointer', color: '#fb7185', transition: 'all 0.15s' }}
                    onClick={() => handleDelete(resume.id, resume.filename)}
                    title="Delete"
                  >
                    <Trash2 size={14} />
                  </button>
                  <button
                    className="btn-ghost"
                    style={{ padding: '6px 8px' }}
                    onClick={() => toggleExpand(resume.id)}
                  >
                    {expandedId === resume.id ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                  </button>
                </div>
              </div>

              {/* Expanded detail */}
              {expandedId === resume.id && (
                <div style={{
                  borderTop: '1px solid var(--border)',
                  padding: '16px 20px',
                  background: 'var(--bg-secondary)',
                }}>
                  {!detailData[resume.id] ? (
                    <div className="spinner" />
                  ) : (
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
                      {/* Skills */}
                      <div>
                        <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-muted)', marginBottom: 8, textTransform: 'uppercase', letterSpacing: '0.06em' }}>Skills</div>
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                          {(detailData[resume.id]?.skills || []).slice(0, 20).map((s: string) => (
                            <span key={s} className="skill-chip">{s}</span>
                          ))}
                          {(detailData[resume.id]?.skills || []).length === 0 && (
                            <span style={{ color: 'var(--text-muted)', fontSize: 13 }}>None detected</span>
                          )}
                        </div>
                      </div>
                      {/* Education */}
                      <div>
                        <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-muted)', marginBottom: 8, textTransform: 'uppercase', letterSpacing: '0.06em' }}>Education</div>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                          {(detailData[resume.id]?.education || []).slice(0, 3).map((e: string, i: number) => (
                            <span key={i} style={{ fontSize: 13, color: 'var(--text-secondary)' }}>{e}</span>
                          ))}
                          {(detailData[resume.id]?.education || []).length === 0 && (
                            <span style={{ color: 'var(--text-muted)', fontSize: 13 }}>Not detected</span>
                          )}
                        </div>
                      </div>
                      {/* Summary */}
                      {detailData[resume.id]?.summary && (
                        <div style={{ gridColumn: '1/-1' }}>
                          <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-muted)', marginBottom: 8, textTransform: 'uppercase', letterSpacing: '0.06em' }}>Summary</div>
                          <p style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.6, margin: 0 }}>
                            {detailData[resume.id].summary}
                          </p>
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
