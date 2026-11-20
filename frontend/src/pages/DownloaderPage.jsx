import React, { useCallback, useEffect, useRef, useState } from 'react';
import { IconDownload, IconSearch, IconVideo } from '../components/Icons.jsx';
import { Modal } from '../components/Modal.jsx';
import { apiFetchJson, getAuthHeaders, sanitizeYoutubeId } from '../lib/auth.js';

export function DownloaderPage({ user, navigate, t }) {
  const uid = user?.id || 0;
  const [query, setQuery] = useState('');
  const [videos, setVideos] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [selectedIds, setSelectedIds] = useState([]);
  const [tasks, setTasks] = useState([]);
  const [submitting, setSubmitting] = useState(false);

  const [formatModal, setFormatModal] = useState(null);
  const [formatsLoading, setFormatsLoading] = useState(false);
  const [downloadingFmt, setDownloadingFmt] = useState('');

  const [previewModal, setPreviewModal] = useState(null);
  const [holdingVideoId, setHoldingVideoId] = useState('');
  const holdTimerRef = useRef(null);

  const loadTasks = useCallback(async () => {
    if (!uid) return;
    const { data } = await apiFetchJson(`/api/autopost-tasks?tg_user_id=${encodeURIComponent(uid)}`).catch(() => ({}));
    if (Array.isArray(data?.tasks)) setTasks(data.tasks);
  }, [uid]);

  useEffect(() => {
    loadTasks();
    return () => {
      if (holdTimerRef.current) clearTimeout(holdTimerRef.current);
    };
  }, [loadTasks]);

  const handleInspectOrSearch = async (e) => {
    e.preventDefault();
    const raw = query.trim();
    if (!raw) return;

    const directId = sanitizeYoutubeId(raw);
    if (directId) {
      openFormatModal({ id: directId, title: `YouTube Video (${directId})` });
      return;
    }

    setLoading(true);
    setError('');
    try {
      const { ok, data } = await apiFetchJson(
        `/api/videos?q=${encodeURIComponent(raw)}&type=&maxResults=16`
      );
      if (!ok) throw new Error(data?.error || 'Search failed');
      setVideos(Array.isArray(data?.videos) ? data.videos : []);
      if (data?.error) setError(data.error);
    } catch (err) {
      setError(err.message || 'Could not search videos.');
    } finally {
      setLoading(false);
    }
  };

  const handleTrending = async (region) => {
    setLoading(true);
    setError('');
    try {
      const { ok, data } = await apiFetchJson(`/api/trending?region=${encodeURIComponent(region)}`);
      if (!ok) throw new Error(data?.error || 'Failed to load trending');
      setVideos(Array.isArray(data?.videos) ? data.videos : []);
    } catch (err) {
      setError(err.message || 'Could not fetch trending list.');
    } finally {
      setLoading(false);
    }
  };

  const openFormatModal = async (vid) => {
    const vId = sanitizeYoutubeId(vid?.id || vid);
    if (!vId) return;
    const title = vid?.title || `Video ${vId}`;
    setFormatModal({ id: vId, title, formats: [], error: '' });
    setFormatsLoading(true);
    try {
      const { data } = await apiFetchJson(
        `/api/video-formats?video_id=${encodeURIComponent(vId)}&tg_user_id=${encodeURIComponent(uid)}`
      );
      setFormatModal({
        id: vId,
        title: data?.title || title,
        formats: Array.isArray(data?.formats) ? data.formats : [],
        error: data?.error || '',
      });
    } catch {
      setFormatModal({ id: vId, title, formats: [], error: 'Failed to inspect formats.' });
    } finally {
      setFormatsLoading(false);
    }
  };

  const startDownload = async (videoId, fmtVal) => {
    if (!uid) {
      navigate('/login');
      return;
    }
    const vId = sanitizeYoutubeId(videoId);
    if (!vId) return;
    const resVal = String(fmtVal || 'best').trim();
    setDownloadingFmt(resVal);
    try {
      const url = `/api/download-file?video_id=${encodeURIComponent(vId)}&resolution=${encodeURIComponent(
        resVal
      )}&tg_user_id=${encodeURIComponent(uid)}`;
      const response = await fetch(url, {
        method: 'GET',
        headers: getAuthHeaders({}, false),
        credentials: 'same-origin',
      });
      const ct = response.headers.get('content-type') || '';
      if (!response.ok || ct.includes('application/json')) {
        const err = await response.json().catch(() => null);
        if (response.status === 401 || response.status === 403) {
          navigate('/login');
          return;
        }
        setFormatModal((prev) => (prev ? { ...prev, error: err?.error || 'Download failed.' } : prev));
        return;
      }
      const blob = await response.blob();
      const blobUrl = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = blobUrl;
      a.download = `monodeck_${vId}.${resVal === 'mp3' ? 'mp3' : 'mp4'}`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      setTimeout(() => URL.revokeObjectURL(blobUrl), 60000);
    } catch {
      setFormatModal((prev) => (prev ? { ...prev, error: 'Network error during download.' } : prev));
    } finally {
      setDownloadingFmt('');
    }
  };

  const queueAutoPost = async (videoIds) => {
    if (!uid) {
      navigate('/login');
      return;
    }
    if (!Array.isArray(videoIds) || videoIds.length === 0) return;
    setSubmitting(true);
    setNotice('');
    try {
      const { data } = await apiFetchJson('/api/autopost-create', {
        method: 'POST',
        body: JSON.stringify({ tg_user_id: uid, video_type: 'shorts', video_ids: videoIds }),
      });
      if (data?.ok || data?.success) {
        setNotice(`Auto-Post task (#${data.task_id || ''}) queued for ${videoIds.length} video(s).`);
        setSelectedIds([]);
        loadTasks();
      } else {
        setNotice(data?.error || 'Auto-Post failed. Connect your YouTube channel first via /ytlogin.');
      }
    } catch {
      setNotice('Network error while queueing Auto-Post.');
    } finally {
      setSubmitting(false);
    }
  };

  const startHoldPreview = (vidId) => {
    if (!vidId) return;
    if (holdTimerRef.current) clearTimeout(holdTimerRef.current);
    holdTimerRef.current = setTimeout(() => setHoldingVideoId(vidId), 180);
  };

  const stopHoldPreview = () => {
    if (holdTimerRef.current) {
      clearTimeout(holdTimerRef.current);
      holdTimerRef.current = null;
    }
    setHoldingVideoId('');
  };

  return (
    <main className="md-container md-page">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', flexWrap: 'wrap', gap: 14, marginBottom: 24 }}>
        <div>
          <div className="md-eyebrow" style={{ marginBottom: 10 }}>
            <span className="md-dot" />
            <span>MEDIA FETCHER &amp; BATCH AUTOPOST</span>
          </div>
          <h1 className="md-h2" style={{ marginBottom: 6 }}>{t('dlTitle')}</h1>
          <p style={{ color: 'var(--muted)', fontSize: 14 }}>{t('dlSub')}</p>
        </div>

        {selectedIds.length > 0 && (
          <button
            type="button"
            disabled={submitting}
            className="md-btn md-btn-accent"
            onClick={() => queueAutoPost(selectedIds)}
          >
            {submitting ? t('loading') : `Queue ${selectedIds.length} Selected for Auto-Post`}
          </button>
        )}
      </div>

      <section className="md-card" style={{ marginBottom: 24 }}>
        <form onSubmit={handleInspectOrSearch} style={{ display: 'flex', flexWrap: 'wrap', gap: 10 }}>
          <input
            type="text"
            className="md-input"
            style={{ flex: '1 1 280px' }}
            placeholder={t('dlPlaceholder')}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          <button type="submit" disabled={loading} className="md-btn md-btn-primary md-btn-rect">
            <IconSearch size={14} />
            <span>{loading ? t('loading') : t('dlInspect')}</span>
          </button>
        </form>

        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginTop: 12 }}>
          <span className="md-mono" style={{ fontSize: 11, color: 'var(--muted)', alignSelf: 'center' }}>
            TRENDING REGIONS:
          </span>
          {['UZ', 'US', 'RU', 'GB', 'TR', 'KR'].map((reg) => (
            <button
              key={reg}
              type="button"
              className="md-btn md-btn-sm"
              onClick={() => handleTrending(reg)}
            >
              {reg}
            </button>
          ))}
        </div>

        {error && <p style={{ marginTop: 12, color: 'var(--err)', fontSize: 13, fontWeight: 500 }}>{error}</p>}
        {notice && <p style={{ marginTop: 12, color: 'var(--ok)', fontSize: 13, fontWeight: 500 }}>{notice}</p>}
      </section>

      {videos.length > 0 ? (
        <section className="md-grid-cards" style={{ marginBottom: 28 }}>
          {videos.map((vid, idx) => {
            const safeId = sanitizeYoutubeId(vid.id || '');
            const isHolding = Boolean(safeId && holdingVideoId === safeId);
            const isChecked = safeId ? selectedIds.includes(safeId) : false;
            return (
              <article
                key={safeId || idx}
                className="md-card md-card-interactive"
                style={{
                  padding: 16,
                  borderColor: isHolding ? 'var(--accent)' : undefined,
                  display: 'flex',
                  flexDirection: 'column',
                  justifyContent: 'space-between',
                  gap: 12,
                }}
              >
                <div>
                  <div
                    style={{ position: 'relative', aspectRatio: '16 / 9', borderRadius: 10, overflow: 'hidden', background: '#0A0A0A', marginBottom: 12, cursor: safeId ? 'pointer' : 'default' }}
                    onMouseDown={() => safeId && startHoldPreview(safeId)}
                    onMouseUp={stopHoldPreview}
                    onMouseLeave={stopHoldPreview}
                    onTouchStart={() => safeId && startHoldPreview(safeId)}
                    onTouchEnd={stopHoldPreview}
                  >
                    {isHolding && safeId ? (
                      <iframe
                        title={vid.title || 'Preview'}
                        src={`https://www.youtube-nocookie.com/embed/${encodeURIComponent(safeId)}?autoplay=1&mute=1`}
                        style={{ width: '100%', height: '100%', border: 'none' }}
                        allow="autoplay; encrypted-media"
                      />
                    ) : (
                      vid.thumbnail && (
                        <img
                          src={vid.thumbnail}
                          alt={vid.title || 'Video'}
                          loading="lazy"
                          style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }}
                        />
                      )
                    )}
                    {safeId && (
                      <input
                        type="checkbox"
                        checked={isChecked}
                        aria-label={`Select ${vid.title || 'video'}`}
                        onMouseDown={(e) => e.stopPropagation()}
                        onChange={() =>
                          setSelectedIds((prev) =>
                            prev.includes(safeId) ? prev.filter((x) => x !== safeId) : [...prev, safeId]
                          )
                        }
                        style={{ position: 'absolute', top: 8, left: 8, width: 18, height: 18, accentColor: '#FF5A1F' }}
                      />
                    )}
                  </div>
                  <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 4, lineHeight: 1.4 }}>
                    {vid.title || 'YouTube Video'}
                  </h3>
                  <p className="md-mono" style={{ fontSize: 11, color: 'var(--muted)' }}>
                    {vid.channel || 'YouTube'} &middot; Hold cover to preview
                  </p>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <button
                    type="button"
                    className="md-btn md-btn-sm"
                    onClick={() => safeId && setPreviewModal({ id: safeId, title: vid.title || 'Preview' })}
                  >
                    <IconVideo size={13} />
                    <span>{t('preview')}</span>
                  </button>
                  <button
                    type="button"
                    className="md-btn md-btn-sm md-btn-primary"
                    onClick={() => openFormatModal(vid)}
                  >
                    <IconDownload size={13} />
                    <span>Formats</span>
                  </button>
                  <button
                    type="button"
                    disabled={submitting || !safeId}
                    className="md-btn md-btn-sm md-btn-accent"
                    style={{ gridColumn: '1 / -1' }}
                    onClick={() => safeId && queueAutoPost([safeId])}
                  >
                    1-Click Auto-Post to Channel
                  </button>
                </div>
              </article>
            );
          })}
        </section>
      ) : (
        <div className="md-card" style={{ textAlign: 'center', color: 'var(--muted)', padding: '36px 20px', marginBottom: 28 }}>
          Enter a YouTube URL, 11-character ID, keyword, or choose a Trending region above.
        </div>
      )}

      {tasks.length > 0 && (
        <section className="md-card">
          <h2 style={{ fontFamily: 'var(--font-display)', fontSize: 17, fontWeight: 600, marginBottom: 12 }}>
            Recent Auto-Post Jobs ({tasks.length})
          </h2>
          <div className="md-table-wrap">
            <table className="md-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Topic / Video</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {tasks.slice(0, 6).map((tk) => (
                  <tr key={tk.id || `${tk.topic}-${tk.created_at}`}>
                    <td className="md-mono">#{tk.id || '-'}</td>
                    <td>{tk.topic || tk.search_query || tk.title || 'Video task'}</td>
                    <td className="md-mono" style={{ fontSize: 11, fontWeight: 600 }}>
                      {String(tk.status || 'pending').toUpperCase()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      <Modal
        open={Boolean(formatModal)}
        onClose={() => setFormatModal(null)}
        title={formatModal?.title || 'Formats'}
      >
        {formatsLoading ? (
          <div style={{ padding: '24px 0', textAlign: 'center', color: 'var(--muted)' }}>
            {t('loading')}
          </div>
        ) : (
          <div style={{ display: 'grid', gap: 10 }}>
            {formatModal?.error && (
              <div style={{ padding: 10, borderRadius: 8, background: 'var(--err-soft)', color: 'var(--err)', fontSize: 13 }}>
                {formatModal.error}
              </div>
            )}

            {(formatModal?.formats || []).map((fmt, i) => {
              const fmtVal = fmt.value || fmt.format_id || fmt.resolution || '720';
              const busy = downloadingFmt === fmtVal;
              return (
                <div
                  key={i}
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    padding: '10px 14px',
                    borderRadius: 10,
                    border: '1px solid var(--border)',
                    background: 'var(--bg)',
                    gap: 10,
                  }}
                >
                  <div>
                    <div style={{ fontSize: 13, fontWeight: 600 }}>
                      {fmt.label || fmt.resolution || fmt.quality || 'Stream'} &middot;{' '}
                      {String(fmt.ext || 'MP4').toUpperCase()}
                    </div>
                    <div className="md-mono" style={{ fontSize: 11, color: 'var(--muted)' }}>
                      {fmt.filesize_str ||
                        (fmt.filesize ? `${(fmt.filesize / 1048576).toFixed(1)} MB` : 'Ready')}
                    </div>
                  </div>
                  <button
                    type="button"
                    disabled={busy}
                    className="md-btn md-btn-primary md-btn-sm"
                    onClick={() => startDownload(formatModal.id, fmtVal)}
                  >
                    {busy ? t('loading') : t('dlDownload')}
                  </button>
                </div>
              );
            })}

            {(!formatModal?.formats || formatModal.formats.length === 0) && (
              <button
                type="button"
                disabled={downloadingFmt === 'best'}
                className="md-btn md-btn-accent"
                onClick={() => startDownload(formatModal?.id, 'best')}
              >
                {downloadingFmt === 'best' ? t('loading') : `${t('dlDownload')} (Best)`}
              </button>
            )}
          </div>
        )}
      </Modal>

      <Modal
        open={Boolean(previewModal)}
        onClose={() => setPreviewModal(null)}
        title={previewModal?.title || 'Preview'}
        maxWidth={720}
      >
        {previewModal?.id && (
          <div style={{ aspectRatio: '16 / 9', background: '#000', borderRadius: 10, overflow: 'hidden' }}>
            <iframe
              title={previewModal.title}
              src={`https://www.youtube-nocookie.com/embed/${encodeURIComponent(previewModal.id)}?autoplay=1`}
              style={{ width: '100%', height: '100%', border: 'none' }}
              allow="autoplay; encrypted-media; picture-in-picture"
              allowFullScreen
            />
          </div>
        )}
      </Modal>
    </main>
  );
}
export default DownloaderPage;
