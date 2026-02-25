'use client';

import { useEffect, useState } from 'react';
import { Upload, RefreshCw, Trash2, FileText } from 'lucide-react';
import { api, type KbChunk, type KbDocument } from '@/lib/api-client';

type SourceType = 'conversation' | 'site' | 'architecture' | 'general';

export default function TrainingPage() {
  const [documents, setDocuments] = useState<KbDocument[]>([]);
  const [chunks, setChunks] = useState<KbChunk[]>([]);
  const [selectedDoc, setSelectedDoc] = useState<KbDocument | null>(null);
  const [title, setTitle] = useState('');
  const [sourceType, setSourceType] = useState<SourceType>('general');
  const [tags, setTags] = useState('');
  const [content, setContent] = useState('');
  const [maxDocumentBytes, setMaxDocumentBytes] = useState(512 * 1024);
  const [stats, setStats] = useState({ total_documents: 0, active_documents: 0, total_chunks: 0 });
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  async function loadDocuments(manual = false) {
    if (manual) setRefreshing(true);
    try {
      const response = await api.getTrainingDocuments();
      setDocuments(response.documents || []);
      setStats(response.stats || stats);
      setMaxDocumentBytes(response.limits?.maxDocumentBytes || 512 * 1024);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load training documents.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }

  useEffect(() => {
    loadDocuments();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function loadChunks(document: KbDocument) {
    setSelectedDoc(document);
    try {
      const response = await api.getTrainingChunks(document.id, 300, 0);
      setChunks(response.chunks || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load chunks.');
    }
  }

  async function handleCreateDocument(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    setNotice(null);
    try {
      await api.createTrainingDocument({
        title: title.trim(),
        source_type: sourceType,
        content: content.trim(),
        tags: tags.trim()
      });
      setTitle('');
      setTags('');
      setContent('');
      setNotice('Document ingested and chunked successfully.');
      await loadDocuments();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to ingest document.');
    } finally {
      setSaving(false);
    }
  }

  async function handleDeleteDocument(document: KbDocument) {
    const confirmed = window.confirm(`Delete "${document.title}" and all chunks?`);
    if (!confirmed) return;
    setError(null);
    setNotice(null);
    try {
      await api.deleteTrainingDocument(document.id);
      if (selectedDoc?.id === document.id) {
        setSelectedDoc(null);
        setChunks([]);
      }
      setNotice('Document deleted.');
      await loadDocuments();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete document.');
    }
  }

  async function handleFileChange(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    try {
      const text = await file.text();
      setTitle((prev) => prev || file.name.replace(/\.[^.]+$/, ''));
      setContent(text);
      setNotice(`Loaded ${file.name} (${Math.round(file.size / 1024)} KB)`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to read file.');
    }
  }

  return (
    <div className="space-y-5">
      <section className="panel p-5 md:p-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 className="section-title">Training / Knowledge Base</h1>
            <p className="mt-2 text-sm text-slate-400">
              Upload curated knowledge docs for deterministic KB retrieval.
            </p>
          </div>
          <button
            type="button"
            onClick={() => loadDocuments(true)}
            disabled={refreshing}
            className="inline-flex items-center gap-2 rounded-lg border border-[rgba(255,255,255,0.2)] bg-[rgba(7,19,32,0.9)] px-3 py-2 text-xs font-medium text-slate-200 transition hover:border-[rgba(32,197,165,0.5)] hover:text-white disabled:opacity-65"
          >
            <RefreshCw size={13} className={refreshing ? 'animate-spin' : ''} />
            Refresh
          </button>
        </div>

        <div className="mt-4 grid gap-3 sm:grid-cols-3">
          <div className="panel-soft p-3">
            <p className="text-xs uppercase tracking-[0.16em] text-slate-500">Documents</p>
            <p className="mt-2 text-xl font-semibold text-white">{stats.total_documents}</p>
          </div>
          <div className="panel-soft p-3">
            <p className="text-xs uppercase tracking-[0.16em] text-slate-500">Active</p>
            <p className="mt-2 text-xl font-semibold text-white">{stats.active_documents}</p>
          </div>
          <div className="panel-soft p-3">
            <p className="text-xs uppercase tracking-[0.16em] text-slate-500">Chunks</p>
            <p className="mt-2 text-xl font-semibold text-white">{stats.total_chunks}</p>
          </div>
        </div>

        {notice && (
          <p className="mt-4 rounded-lg border border-emerald-400/35 bg-emerald-500/10 px-3 py-2 text-sm text-emerald-100">
            {notice}
          </p>
        )}
        {error && (
          <p className="mt-4 rounded-lg border border-red-400/35 bg-red-500/10 px-3 py-2 text-sm text-red-200">
            {error}
          </p>
        )}
      </section>

      <section className="grid gap-4 xl:grid-cols-[1fr_1.2fr]">
        <form onSubmit={handleCreateDocument} className="panel space-y-3 p-4">
          <h2 className="text-base font-semibold text-white">Ingest Document</h2>

          <label className="block text-sm">
            <span className="text-slate-300">Title</span>
            <input
              required
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              className="mt-1 w-full rounded-lg border border-[rgba(255,255,255,0.14)] bg-[rgba(9,23,38,0.85)] px-3 py-2 text-sm text-white outline-none"
              placeholder="Datacube architecture guide"
            />
          </label>

          <label className="block text-sm">
            <span className="text-slate-300">Source Type</span>
            <select
              value={sourceType}
              onChange={(event) => setSourceType(event.target.value as SourceType)}
              className="mt-1 w-full rounded-lg border border-[rgba(255,255,255,0.14)] bg-[rgba(9,23,38,0.85)] px-3 py-2 text-sm text-white outline-none"
            >
              <option value="general">general</option>
              <option value="conversation">conversation</option>
              <option value="site">site</option>
              <option value="architecture">architecture</option>
            </select>
          </label>

          <label className="block text-sm">
            <span className="text-slate-300">Tags</span>
            <input
              value={tags}
              onChange={(event) => setTags(event.target.value)}
              className="mt-1 w-full rounded-lg border border-[rgba(255,255,255,0.14)] bg-[rgba(9,23,38,0.85)] px-3 py-2 text-sm text-white outline-none"
              placeholder="vps, deployment, auth"
            />
          </label>

          <label className="block text-sm">
            <span className="text-slate-300">Load from File</span>
            <input
              type="file"
              accept=".txt,.md,.json,.csv"
              onChange={handleFileChange}
              className="mt-1 w-full text-sm text-slate-300"
            />
          </label>

          <label className="block text-sm">
            <span className="text-slate-300">Content</span>
            <textarea
              required
              rows={12}
              value={content}
              onChange={(event) => setContent(event.target.value)}
              className="mt-1 w-full rounded-lg border border-[rgba(255,255,255,0.14)] bg-[rgba(9,23,38,0.85)] px-3 py-2 text-sm text-white outline-none"
              placeholder="Paste source material to ingest..."
            />
          </label>

          <p className="text-xs text-slate-500">
            Limit: {Math.round(maxDocumentBytes / 1024)} KB. Private user chats are never auto-ingested.
          </p>

          <button
            type="submit"
            disabled={saving || !content.trim() || !title.trim()}
            className="inline-flex items-center gap-2 rounded-lg bg-gradient-to-r from-[var(--brand-1)] to-[var(--brand-2)] px-3 py-2 text-sm font-semibold text-slate-950 disabled:opacity-60"
          >
            <Upload size={14} />
            {saving ? 'Ingesting...' : 'Ingest Document'}
          </button>
        </form>

        <section className="space-y-4">
          <div className="panel p-0">
            {loading ? (
              <div className="p-4 text-sm text-slate-400">Loading documents...</div>
            ) : (
              <div className="space-y-2 p-3">
                {documents.map((document) => (
                  <div key={document.id} className="panel-soft flex items-start justify-between gap-3 p-3">
                    <div>
                      <p className="font-medium text-white">{document.title}</p>
                      <p className="mt-1 text-xs text-slate-400">
                        {document.source_type} • {document.tags || 'no tags'}
                      </p>
                      <p className="mt-1 text-xs text-slate-500">
                        Updated {new Date(document.updated_at).toLocaleString()}
                      </p>
                    </div>
                    <div className="flex gap-2">
                      <button
                        type="button"
                        onClick={() => loadChunks(document)}
                        className="inline-flex items-center gap-1 rounded-lg border border-[rgba(255,255,255,0.16)] px-2 py-1 text-xs text-slate-200"
                      >
                        <FileText size={12} />
                        Chunks
                      </button>
                      <button
                        type="button"
                        onClick={() => handleDeleteDocument(document)}
                        className="inline-flex items-center gap-1 rounded-lg border border-red-400/35 px-2 py-1 text-xs text-red-200"
                      >
                        <Trash2 size={12} />
                        Delete
                      </button>
                    </div>
                  </div>
                ))}
                {documents.length === 0 && (
                  <p className="p-2 text-sm text-slate-500">No training documents uploaded yet.</p>
                )}
              </div>
            )}
          </div>

          <div className="panel p-4">
            <h2 className="text-base font-semibold text-white">
              {selectedDoc ? `Chunks: ${selectedDoc.title}` : 'Chunk Viewer'}
            </h2>
            {!selectedDoc ? (
              <p className="mt-2 text-sm text-slate-400">Choose a document to inspect generated chunks.</p>
            ) : chunks.length === 0 ? (
              <p className="mt-2 text-sm text-slate-400">No chunks available.</p>
            ) : (
              <div className="mt-3 max-h-[380px] space-y-2 overflow-y-auto pr-1">
                {chunks.map((chunk) => (
                  <div key={chunk.id} className="panel-soft p-3 text-xs">
                    <p className="text-slate-500">Chunk #{chunk.chunk_index + 1}</p>
                    <p className="mt-1 whitespace-pre-wrap text-slate-200">{chunk.chunk_text}</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        </section>
      </section>
    </div>
  );
}

