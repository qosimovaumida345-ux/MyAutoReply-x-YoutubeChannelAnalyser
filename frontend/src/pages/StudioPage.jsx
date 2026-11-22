import React, { useCallback, useEffect, useRef, useState } from 'react';
import { IconChart, IconRefresh, IconVideo } from '../components/Icons.jsx';
import { Modal } from '../components/Modal.jsx';
import { apiFetchJson, sanitizeYoutubeId } from '../lib/auth.js';

function SegmentedMeter({ fillRatio = 0.35 }) {
  const cells = 32;
  const filled = Math.max(1, Math.min(cells, Math.round(fillRatio * cells)));
  return (
    <div className="md-meter" aria-hidden="true">
      {Array.from({ length: cells }, (_, i) => (
        <span
          key={i}
          className={`md-meter-cell${i < filled ? (i >= cells - 5 ? ' hot' : ' filled') : ''}`}
        />
      ))}
    </div>
  );
}

export function StudioPage({ user, navigate, t }) {
  const uid = user?.id || 0;
  const [stats, setStats] = useState({
    channel_title: '',
    channel_id: '',
    channel_thumbnail: '',
    subscribers: 0,
    total_subscribers: 0,
    total_views: 0,
    total_videos: 0,
    avg_views: 0,
    avg_likes: 0,
    avg_comments: 0,
    engagement_rate: 0,
    autopost: { total: 0, success: 0, failed: 0, active_task: null },
    recent_videos: [],
    stale: false,
  });
  const [channels, setChannels] = useState([]);
  const [selectedChannel, setSelectedChannel] = useState('');
  const [tasks, setTasks] = useState([]);
  const [topic, setTopic] = useState('');
  const [count, setCount] = useState(1);
  const [selectedIds, setSelectedIds] = useState([]);
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [notice, setNotice] = useState('');
  const [previewVideo, setPreviewVideo] = useState(null);
  const [holdingVideoId, setHoldingVideoId] = useState('');
  const holdTimerRef = useRef(null);
  const [candidates, setCandidates] = useState([]);
  const [candidatesLoading, setCandidatesLoading] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [inspectedTask, setInspectedTask] = useState(null);
  const [taskHistory, setTaskHistory] = useState([]);
  const [taskActionBusy, setTaskActionBusy] = useState(false);

  const loadAll = useCallback(
    async (forceRefresh = false, chOverride = null) => {
      if (!uid) return;
      setLoading(true);
      const ch = chOverride ?? selectedChannel;
      const chParam = ch ? `&channel_id=${encodeURIComponent(ch)}` : '';
      const refreshParam = forceRefresh ? '&refresh=1' : '';
      try {
        const [stRes, chRes, taskRes] = await Promise.all([
          apiFetchJson(`/api/stats?tg_user_id=${encodeURIComponent(uid)}${chParam}${refreshParam}`),
          apiFetchJson(`/api/channels?tg_user_id=${encodeURIComponent(uid)}`),
          apiFetchJson(`/api/autopost-tasks?tg_user_id=${encodeURIComponent(uid)}`),
        ]);
        if (stRes.data && (stRes.data.ok || stRes.data.channel_title || stRes.data.total_videos !== undefined)) {
          setStats(stRes.data);
          if (stRes.data.channel_id && !ch) setSelectedChannel(stRes.data.channel_id);
        }
        if (chRes.data?.channels) {
          setChannels(chRes.data.channels);
          if (!ch) {
            setSelectedChannel(
              chRes.data.default_channel_id || chRes.data.channels[0]?.channel_id || ''
            );
          }
        }
        if (Array.isArray(taskRes.data?.tasks)) {
          setTasks(taskRes.data.tasks);
        }
      } catch {
        // Keep partial state without breaking render
      } finally {
        setLoading(false);
      }
    },
    [uid, selectedChannel]
  );

  useEffect(() => {
    if (uid > 0) loadAll(false);
    return () => {
      if (holdTimerRef.current) clearTimeout(holdTimerRef.current);
    };
  }, [uid]);

  useEffect(() => {
    if (!uid || !stats.stale) return undefined;
    const timer = setTimeout(() => {
      loadAll(false);
    }, 2600);
    return () => clearTimeout(timer);
  }, [uid, stats.stale, loadAll]);

  const handleSelectChannel = async (channelId) => {
    if (!channelId) return;
    const prevChannel = selectedChannel;
    setSelectedChannel(channelId);
    if (!uid) return;
    try {
      const res = await apiFetchJson('/api/channels/select', {
        method: 'POST',
        body: JSON.stringify({ tg_user_id: uid, channel_id: channelId }),
      });
      if (res.data?.ok === false) {
        setSelectedChannel(prevChannel);
        setNotice(res.data?.error || 'Kanalni tanlab bo\'lmadi.');
        return;
      }
      loadAll(true, channelId);
    } catch {
      setSelectedChannel(prevChannel);
      setNotice('Tarmoq xatosi: kanal tanlanmadi.');
    }
  };

  const handleQueueAutopost = async (e) => {
    e.preventDefault();
    if (!uid) {
      navigate('/login');
      return;
    }
    if (!topic.trim() && selectedIds.length === 0) {
      setNotice('Enter a topic or check at least one video for Auto-Post.');
      return;
    }
    const cleanTopic = topic.trim();
    const taskCount = selectedIds.length > 0 ? selectedIds.length : Math.max(1, Math.min(10, Number(count || 1)));
    const tempTask = {
      id: `tmp_${Date.now()}`,
      topic: selectedIds.length > 0 ? `${selectedIds.length} ta tanlangan video` : cleanTopic,
      search_query: cleanTopic,
      completed_count: 0,
      total_count: taskCount,
      status: 'pending',
      created_at: new Date().toISOString(),
    };
    const prevTasks = tasks;
    const prevTopic = topic;
    const prevSel = selectedIds;

    // Optimistic UI: show queued task immediately without blocking
    setTasks((prev) => [tempTask, ...prev]);
    setTopic('');
    setSelectedIds([]);
    setNotice('Auto-Post navbatga qo\'shildi...');
    setSubmitting(true);

    try {
      const payload = {
        tg_user_id: uid,
        channel_id: selectedChannel || undefined,
        video_type: 'shorts',
      };
      if (prevSel.length > 0) {
        payload.video_ids = prevSel;
      } else {
        payload.topic = cleanTopic;
        payload.count = taskCount;
      }
      const { data } = await apiFetchJson('/api/autopost-create', {
        method: 'POST',
        body: JSON.stringify(payload),
      });
      if (data?.ok || data?.success) {
        setNotice(`Auto-Post task (#${data.task_id || ''}) navbatga qo'shildi.`);
        loadAll(false);
      } else {
        setTasks(prevTasks);
        setTopic(prevTopic);
        setSelectedIds(prevSel);
        setNotice(data?.error || 'Could not queue task. Check channel connection.');
      }
    } catch {
      setTasks(prevTasks);
      setTopic(prevTopic);
      setSelectedIds(prevSel);
      setNotice('Network error while creating task.');
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

  if (!uid) {
    return (
      <main className="md-container md-page">
        <div className="md-card" style={{ maxWidth: 560, margin: '24px auto', textAlign: 'center' }}>
          <div className="md-eyebrow" style={{ marginBottom: 12 }}>
            <span className="md-dot" />
            <span>AUTHENTICATION REQUIRED</span>
          </div>
          <h1 className="md-h2" style={{ marginBottom: 8 }}>{t('studioTitle')}</h1>
          <p style={{ color: 'var(--muted)', fontSize: 14, marginBottom: 20 }}>
            {t('connectChannelHint')}
          </p>
          <div style={{ display: 'flex', gap: 10, justifyContent: 'center', flexWrap: 'wrap' }}>
            <button type="button" className="md-btn md-btn-primary" onClick={() => navigate('/login')}>
              {t('signIn')}
            </button>
            <a className="md-btn" href="/oauth/youtube/start">
              Connect YouTube (Google OAuth)
            </a>
          </div>
        </div>
      </main>
    );
  }

  const totalSubs = Number(stats.total_subscribers ?? stats.subscribers ?? 0);
  const totalViews = Number(stats.total_views || 0);
  const totalVideos = Number(stats.total_videos || 0);
  const recentVideos = Array.isArray(stats.recent_videos) ? stats.recent_videos : [];
  const channelList =
    channels.length > 0
      ? channels
      : stats.channel_title
      ? [
          {
            channel_id: stats.channel_id || 'default',
            channel_title: stats.channel_title,
            thumbnail_url: stats.channel_thumbnail,
            subscriber_count: totalSubs,
          },
        ]
      : [];

  const handleSearchCandidates = async (overrideQuery = '') => {
    const q = (overrideQuery || topic || '').trim();
    if (!q) {
      setNotice('Avval mavzu yoki kalit so\'z kiriting.');
      return;
    }
    setDrawerOpen(true);
    setInspectedTask(null);
    setTaskHistory([]);
    setCandidatesLoading(true);
    setNotice('');
    try {
      const res = await apiFetchJson(`/api/videos?q=${encodeURIComponent(q)}&type=short&maxResults=8`);
      const list = Array.isArray(res.data?.videos) ? res.data.videos : [];
      setCandidates(list);
      if (list.length === 0) {
        setNotice(res.data?.warning || 'Namuna videolar topilmadi.');
      }
    } catch {
      setNotice('Namunalarni yuklashda xatolik yuz berdi.');
    } finally {
      setCandidatesLoading(false);
    }
  };

  const handleInspectTask = async (task) => {
    if (!task?.id) return;
    setDrawerOpen(true);
    setInspectedTask(task);
    setCandidatesLoading(true);
    setNotice('');
    try {
      const res = await apiFetchJson(`/api/autopost-tasks/${task.id}/details`);
      if (res.data?.ok) {
        setInspectedTask(res.data.task || task);
        setTaskHistory(Array.isArray(res.data.history) ? res.data.history : []);
        setCandidates(Array.isArray(res.data.candidates) ? res.data.candidates : []);
        setSelectedIds([]);
      } else {
        setNotice(res.data?.error || 'Vazifa ma\'lumotini yuklab bo\'lmadi.');
      }
    } catch {
      setNotice('Tarmoq xatosi.');
    } finally {
      setCandidatesLoading(false);
    }
  };

  const handleTaskAction = async (taskId, action, useGithub = false) => {
    if (!taskId) return;
    const prevTasks = tasks;
    setTaskActionBusy(true);

    // Optimistic UI update immediately
    if (action === 'delete') {
      setTasks((prev) => prev.filter((item) => item.id !== taskId));
      if (inspectedTask?.id === taskId) {
        setDrawerOpen(false);
        setInspectedTask(null);
      }
      setNotice(`Task #${taskId} o'chirildi.`);
    } else {
      setTasks((prev) =>
        prev.map((item) => (item.id === taskId ? { ...item, status: 'running' } : item))
      );
      setNotice(
        useGithub
          ? `Task #${taskId} 7 GB GitHub Actions worker'ga yuborildi (avto watermark tozalash yoqilgan).`
          : `Task #${taskId} ishga tushirildi (avto watermark tozalash yoqilgan).`
      );
    }

    try {
      const res = await apiFetchJson('/api/autopost-tasks/action', {
        method: 'POST',
        body: JSON.stringify({
          task_id: taskId,
          action,
          selected_video_ids: selectedIds,
          use_github: useGithub,
        }),
      });
      if (res.data?.ok) {
        await loadAll(false);
      } else {
        setTasks(prevTasks);
        setNotice(`Bajarilmadi: ${res.data?.error || 'Amalni bajarib bo\'lmadi.'}`);
      }
    } catch {
      setTasks(prevTasks);
      setNotice('Tarmoq xatosi: amal bekor qilindi.');
    } finally {
      setTaskActionBusy(false);
    }
  };

  const formatDuration = (sec) => {
    const n = Number(sec);
    if (!n || Number.isNaN(n)) return '';
    const m = Math.floor(n / 60);
    const s = Math.floor(n % 60);
    return `${m}:${String(s).padStart(2, '0')}`;
  };

  return (
    <main className="md-container md-page">
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-end',
          flexWrap: 'wrap',
          gap: 14,
          marginBottom: 24,
        }}
      >
        <div>
          <div className="md-eyebrow" style={{ marginBottom: 10 }}>
            <span className="md-dot" />
            <span>YOUTUBE ANALYTICS</span>
          </div>
          <h1 className="md-h2">{stats.channel_title || t('studioTitle')}</h1>
          {stats.stale && (
            <p className="md-mono" style={{ fontSize: 12, color: 'var(--accent)', marginTop: 4 }}>
              {t('syncingBg')}
            </p>
          )}
        </div>

        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <a className="md-btn md-btn-primary md-btn-sm" href="/oauth/youtube/start">
            + Connect YouTube (Google OAuth)
          </a>
          <button
            type="button"
            className="md-btn md-btn-sm"
            disabled={loading}
            onClick={() => loadAll(true)}
          >
            <IconRefresh size={14} />
            <span>{loading ? t('loading') : t('refresh')}</span>
          </button>
        </div>
      </div>

      {/* Primary 4 Channel KPIs */}
      <section className="md-grid-4" style={{ marginBottom: 16 }}>
        {[
          { label: t('totalVideos'), val: totalVideos.toLocaleString(), fill: Math.min(1, totalVideos / 100) },
          { label: t('totalViews'), val: totalViews.toLocaleString(), fill: Math.min(1, totalViews / 100000) },
          { label: t('subscribers'), val: totalSubs.toLocaleString(), fill: Math.min(1, totalSubs / 10000) },
          { label: t('connectedChannels'), val: String(channelList.length), fill: Math.min(1, channelList.length / 4) },
        ].map((metric) => (
          <div key={metric.label} className="md-card" style={{ padding: 18 }}>
            <div style={{ fontSize: 12, color: 'var(--muted)', fontWeight: 500, marginBottom: 6 }}>
              {metric.label}
            </div>
            <div className="md-mono" style={{ fontSize: 24, fontWeight: 600, marginBottom: 12 }}>
              {metric.val}
            </div>
            <SegmentedMeter fillRatio={metric.fill} />
          </div>
        ))}
      </section>

      {/* Secondary Velocity, Engagement & Autopost Summary Telemetry Strip */}
      <section className="md-grid-4" style={{ marginBottom: 28 }}>
        <div className="md-card" style={{ padding: 14 }}>
          <div className="md-mono" style={{ fontSize: 11, color: 'var(--muted)' }}>AVG VIEWS / VIDEO</div>
          <div className="md-mono" style={{ fontSize: 18, fontWeight: 600, marginTop: 4 }}>
            {Number(stats.avg_views || 0).toLocaleString()}
          </div>
        </div>
        <div className="md-card" style={{ padding: 14 }}>
          <div className="md-mono" style={{ fontSize: 11, color: 'var(--muted)' }}>AVG LIKES &amp; COMMENTS</div>
          <div className="md-mono" style={{ fontSize: 18, fontWeight: 600, marginTop: 4 }}>
            {Number(stats.avg_likes || 0).toLocaleString()} / {Number(stats.avg_comments || 0).toLocaleString()}
          </div>
        </div>
        <div className="md-card" style={{ padding: 14 }}>
          <div className="md-mono" style={{ fontSize: 11, color: 'var(--muted)' }}>ENGAGEMENT RATE</div>
          <div className="md-mono" style={{ fontSize: 18, fontWeight: 600, color: 'var(--accent)', marginTop: 4 }}>
            {Number(stats.engagement_rate || 0)}%
          </div>
        </div>
        <div className="md-card" style={{ padding: 14 }}>
          <div className="md-mono" style={{ fontSize: 11, color: 'var(--muted)' }}>AUTOPOST UPLOADED / TOTAL</div>
          <div className="md-mono" style={{ fontSize: 18, fontWeight: 600, marginTop: 4 }}>
            {Number(stats.autopost?.success || 0)} / {Number(stats.autopost?.total || 0)}
          </div>
        </div>
      </section>

      {/* Visual Multi-Channel Switcher Grid */}
      {channelList.length > 0 && (
        <section className="md-card" style={{ marginBottom: 28 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14, flexWrap: 'wrap', gap: 8 }}>
            <h2 style={{ fontFamily: 'var(--font-display)', fontSize: 17, fontWeight: 600 }}>
              Connected YouTube Channels ({channelList.length})
            </h2>
            <span className="md-mono" style={{ fontSize: 11.5, color: 'var(--muted)' }}>
              Active channel scopes analytics &amp; Autopost uploads
            </span>
          </div>
          <div className="md-grid-cards">
            {channelList.map((ch, idx) => {
              const chId = ch.channel_id || '';
              const isSelected = chId ? (selectedChannel ? chId === selectedChannel : idx === 0) : true;
              const thumb = ch.thumbnail_url || stats.channel_thumbnail;
              return (
                <div
                  key={chId || idx}
                  onClick={() => chId && !isSelected && handleSelectChannel(chId)}
                  className="md-card md-card-interactive"
                  style={{
                    padding: 16,
                    cursor: chId && !isSelected ? 'pointer' : 'default',
                    borderColor: isSelected ? 'var(--ink)' : 'var(--border)',
                    background: isSelected ? 'var(--surface)' : 'var(--bg)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    gap: 12,
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: 12, minWidth: 0 }}>
                    {thumb ? (
                      <img
                        src={thumb}
                        alt={ch.channel_title || 'Channel'}
                        width={44}
                        height={44}
                        style={{ borderRadius: 999, objectFit: 'cover', flexShrink: 0, border: '1px solid var(--border)' }}
                      />
                    ) : (
                      <div
                        style={{
                          width: 44,
                          height: 44,
                          borderRadius: 999,
                          background: 'var(--ink)',
                          color: '#FFF',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          fontWeight: 700,
                          flexShrink: 0,
                        }}
                      >
                        {(ch.channel_title || 'Y').slice(0, 1).toUpperCase()}
                      </div>
                    )}
                    <div style={{ minWidth: 0 }}>
                      <div style={{ fontWeight: 600, fontSize: 14, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {ch.channel_title || 'YouTube Channel'}
                      </div>
                      <div className="md-mono" style={{ fontSize: 11.5, color: 'var(--muted)' }}>
                        {Number(ch.subscriber_count ?? totalSubs).toLocaleString()} subs
                      </div>
                    </div>
                  </div>

                  {isSelected ? (
                    <span className="md-mono" style={{ fontSize: 10.5, fontWeight: 600, color: 'var(--accent)', flexShrink: 0 }}>
                      ACTIVE
                    </span>
                  ) : (
                    <button
                      type="button"
                      className="md-btn md-btn-sm"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleSelectChannel(chId);
                      }}
                    >
                      Select
                    </button>
                  )}
                </div>
              );
            })}
          </div>
        </section>
      )}

      {/* Autopost Queue & Active Task */}
      <section className="md-card" style={{ marginBottom: 28 }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14, flexWrap: 'wrap', gap: 8 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
            <IconChart size={16} color="var(--accent)" />
            <h2 style={{ fontFamily: 'var(--font-display)', fontSize: 17, fontWeight: 600 }}>
              {t('autopostTitle')}
            </h2>
            <span
              className="md-mono"
              style={{
                fontSize: 10.5,
                padding: '2px 8px',
                borderRadius: 999,
                background: 'rgba(16, 185, 129, 0.12)',
                color: '#10b981',
                fontWeight: 600,
              }}
            >
              AUTO WATERMARK CLEAN: ON
            </span>
          </div>
          {stats.autopost?.active_task && (
            <span className="md-mono" style={{ fontSize: 11.5, color: 'var(--accent)' }}>
              Active Task #{stats.autopost.active_task.id}: {stats.autopost.active_task.completed}/{stats.autopost.active_task.total} ({stats.autopost.active_task.status})
            </span>
          )}
        </div>

        <form
          onSubmit={handleQueueAutopost}
          style={{ display: 'flex', flexWrap: 'wrap', gap: 10, alignItems: 'center' }}
        >
          <input
            type="text"
            className="md-input"
            style={{ flex: '1 1 240px' }}
            placeholder={
              selectedIds.length > 0
                ? `${selectedIds.length} ta tanlangan video postga tayyor`
                : t('autopostTopicPlaceholder')
            }
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            disabled={selectedIds.length > 0}
          />
          <button
            type="button"
            disabled={candidatesLoading}
            onClick={() => handleSearchCandidates()}
            className="md-btn md-btn-rect"
            style={{ whiteSpace: 'nowrap' }}
          >
            {candidatesLoading && !inspectedTask ? 'Qidirilmoqda...' : 'Namunalarni ko\'rish'}
          </button>
          <input
            type="number"
            min={1}
            max={10}
            aria-label={t('autopostCount')}
            className="md-input md-mono"
            style={{ width: 82 }}
            value={count}
            onChange={(e) => setCount(Number(e.target.value))}
          />
          <button type="submit" disabled={submitting} className="md-btn md-btn-accent md-btn-rect">
            {submitting ? t('loading') : selectedIds.length > 0 ? `Tanlanganini Post Qilish (${selectedIds.length})` : t('autopostLaunch')}
          </button>
          {selectedIds.length > 0 && (
            <button
              type="button"
              className="md-btn md-btn-sm"
              onClick={() => setSelectedIds([])}
            >
              Tozalash
            </button>
          )}
        </form>

        {notice && (
          <p className="md-mono" style={{ fontSize: 12, color: 'var(--ink-2)', marginTop: 10 }}>
            {notice}
          </p>
        )}

        {tasks.length > 0 && (
          <div className="md-table-wrap" style={{ marginTop: 16 }}>
            <table className="md-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Topic / Query</th>
                  <th>Progress</th>
                  <th>Status</th>
                  <th style={{ textAlign: 'right' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {tasks.slice(0, 8).map((task) => {
                  const isActiveRow = inspectedTask?.id === task.id && drawerOpen;
                  return (
                    <tr
                      key={task.id || `${task.topic}-${task.created_at}`}
                      onClick={() => handleInspectTask(task)}
                      style={{
                        cursor: 'pointer',
                        background: isActiveRow ? 'rgba(255, 79, 24, 0.06)' : undefined,
                      }}
                    >
                      <td className="md-mono">#{task.id || '-'}</td>
                      <td>
                        <div style={{ fontWeight: 500 }}>{task.topic || task.search_query || task.title || 'Scheduled Shorts'}</div>
                        <div className="md-mono" style={{ fontSize: 10.5, color: 'var(--muted)' }}>
                          Bosib namunalarni ko&apos;ring
                        </div>
                      </td>
                      <td className="md-mono">
                        {task.completed_count !== undefined
                          ? `${task.completed_count}/${task.total_count || 1}`
                          : '-'}
                      </td>
                      <td>
                        <span
                          className="md-mono"
                          style={{
                            fontSize: 11,
                            fontWeight: 600,
                            color: task.status === 'done' || task.status === 'completed' ? 'var(--ok)' : 'var(--accent)',
                          }}
                        >
                          {String(task.status || 'pending').toUpperCase()}
                        </span>
                      </td>
                      <td style={{ textAlign: 'right' }} onClick={(e) => e.stopPropagation()}>
                        <div style={{ display: 'inline-flex', gap: 6 }}>
                          <button
                            type="button"
                            className="md-btn md-btn-sm"
                            onClick={() => handleInspectTask(task)}
                          >
                            Preview
                          </button>
                          <button
                            type="button"
                            disabled={taskActionBusy}
                            className="md-btn md-btn-sm md-btn-accent"
                            onClick={() => handleTaskAction(task.id, 'run_now', false)}
                          >
                            Run
                          </button>
                          <button
                            type="button"
                            disabled={taskActionBusy}
                            className="md-btn md-btn-sm"
                            onClick={() => handleTaskAction(task.id, 'delete', false)}
                          >
                            Del
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        {/* Candidate Videos & Task Inspector Drawer */}
        {drawerOpen && (
          <div
            style={{
              marginTop: 18,
              padding: 16,
              borderRadius: 12,
              border: '1px solid var(--border-strong)',
              background: 'var(--bg)',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12, flexWrap: 'wrap', gap: 8 }}>
              <div>
                <div style={{ fontFamily: 'var(--font-display)', fontSize: 15, fontWeight: 600 }}>
                  {inspectedTask
                    ? `Task #${inspectedTask.id}: ${inspectedTask.search_query || inspectedTask.topic}`
                    : `Qidiruv namunalari: "${topic}"`}
                </div>
                <div className="md-mono" style={{ fontSize: 11, color: 'var(--muted)' }}>
                  Post qilishdan oldin videoni ko&apos;rib chiqing &middot; Watermark avtomatik o&apos;chiriladi
                </div>
              </div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                {inspectedTask && (
                  <>
                    <button
                      type="button"
                      disabled={taskActionBusy}
                      className="md-btn md-btn-sm md-btn-accent"
                      onClick={() => handleTaskAction(inspectedTask.id, 'run_now', false)}
                    >
                      {selectedIds.length > 0 ? `Tanlanganini Run (${selectedIds.length})` : 'Hozir Run Qilish'}
                    </button>
                    <button
                      type="button"
                      disabled={taskActionBusy}
                      className="md-btn md-btn-sm"
                      onClick={() => handleTaskAction(inspectedTask.id, 'run_now', true)}
                    >
                      GitHub Actions (7GB)
                    </button>
                  </>
                )}
                <button
                  type="button"
                  className="md-btn md-btn-sm"
                  onClick={() => setDrawerOpen(false)}
                >
                  Yopish
                </button>
              </div>
            </div>

            {taskHistory.length > 0 && (
              <div style={{ marginBottom: 14, padding: 10, borderRadius: 8, border: '1px solid var(--border)', background: 'var(--surface)' }}>
                <div className="md-mono" style={{ fontSize: 11, fontWeight: 600, marginBottom: 6 }}>
                  TASK HISTORY ({taskHistory.length})
                </div>
                {taskHistory.map((h) => (
                  <div key={h.id} className="md-mono" style={{ fontSize: 11.5, display: 'flex', justifyContent: 'space-between', gap: 8, padding: '4px 0' }}>
                    <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {h.source_title || h.source_video_id}
                    </span>
                    <span style={{ color: h.status === 'uploaded' ? 'var(--ok)' : 'var(--accent)' }}>
                      {String(h.status || '').toUpperCase()} {h.error_msg ? `(${String(h.error_msg).slice(0, 48)})` : ''}
                    </span>
                  </div>
                ))}
              </div>
            )}

            {candidatesLoading ? (
              <div className="md-mono" style={{ fontSize: 12, color: 'var(--muted)', padding: '14px 0' }}>
                Namuna videolar yuklanmoqda...
              </div>
            ) : candidates.length === 0 ? (
              <div className="md-mono" style={{ fontSize: 12, color: 'var(--muted)', padding: '14px 0' }}>
                Namuna videolar topilmadi.
              </div>
            ) : (
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))',
                  gap: 12,
                }}
              >
                {candidates.map((cand) => {
                  const vid = sanitizeYoutubeId(cand.id);
                  const checked = vid && selectedIds.includes(vid);
                  return (
                    <div
                      key={cand.id}
                      style={{
                        border: checked ? '1.5px solid var(--accent)' : '1px solid var(--border)',
                        borderRadius: 10,
                        background: 'var(--surface)',
                        overflow: 'hidden',
                        display: 'flex',
                        flexDirection: 'column',
                      }}
                    >
                      <div style={{ position: 'relative', aspectRatio: '16 / 9', background: '#111' }}>
                        <img
                          src={cand.thumbnail || `https://i.ytimg.com/vi/${vid}/hqdefault.jpg`}
                          alt={cand.title}
                          loading="lazy"
                          decoding="async"
                          style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                        />
                        {cand.duration ? (
                          <span
                            className="md-mono"
                            style={{
                              position: 'absolute',
                              right: 6,
                              bottom: 6,
                              fontSize: 10,
                              padding: '2px 5px',
                              borderRadius: 4,
                              background: 'rgba(0,0,0,0.78)',
                              color: '#fff',
                            }}
                          >
                            {formatDuration(cand.duration)}
                          </span>
                        ) : null}
                      </div>
                      <div style={{ padding: 10, display: 'flex', flexDirection: 'column', gap: 8, flex: 1 }}>
                        <div style={{ fontSize: 12.5, fontWeight: 600, lineHeight: 1.3, display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
                          {cand.title}
                        </div>
                        <div className="md-mono" style={{ fontSize: 10.5, color: 'var(--muted)' }}>
                          {cand.channel || 'YouTube'} {cand.views ? `· ${Number(cand.views).toLocaleString()} views` : ''}
                        </div>
                        <div style={{ display: 'flex', gap: 6, marginTop: 'auto' }}>
                          <button
                            type="button"
                            className="md-btn md-btn-sm"
                            style={{ flex: 1 }}
                            onClick={() => setPreviewVideo({ id: vid, title: cand.title, views: cand.views })}
                          >
                            Ko&apos;rish
                          </button>
                          <button
                            type="button"
                            className={`md-btn md-btn-sm${checked ? ' md-btn-accent' : ''}`}
                            onClick={() => vid && toggleSelectVideo(vid)}
                          >
                            {checked ? 'Tanlandi' : 'Tanlash'}
                          </button>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}
      </section>

      {/* Hold-to-Preview Overlay Bar (when pressing & holding any row/card) */}
      {holdingVideoId && (
        <div className="md-card" style={{ marginBottom: 20, padding: 14, borderColor: 'var(--accent)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
            <span className="md-mono" style={{ fontSize: 11.5, color: 'var(--accent)', fontWeight: 600 }}>
              HOLD-TO-PREVIEW &middot; {holdingVideoId}
            </span>
            <button type="button" className="md-btn md-btn-sm" onClick={stopHoldPreview}>Close</button>
          </div>
          <div style={{ aspectRatio: '16 / 9', maxHeight: 280, background: '#000', borderRadius: 10, overflow: 'hidden' }}>
            <iframe
              title="Hold Preview"
              src={`https://www.youtube-nocookie.com/embed/${encodeURIComponent(holdingVideoId)}?autoplay=1&mute=1`}
              style={{ width: '100%', height: '100%', border: 'none' }}
              allow="autoplay; encrypted-media"
            />
          </div>
        </div>
      )}

      {/* Recent Videos Table */}
      <section className="md-card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
          <h2 style={{ fontFamily: 'var(--font-display)', fontSize: 17, fontWeight: 600 }}>
            {t('recentVideos')}
          </h2>
          <span className="md-mono" style={{ fontSize: 12, color: 'var(--muted)' }}>
            {recentVideos.length} ITEMS
          </span>
        </div>

        {recentVideos.length === 0 ? (
          <div style={{ padding: '32px 0', textAlign: 'center', color: 'var(--muted)', fontSize: 14 }}>
            <p>{t('noVideos')}</p>
            <p style={{ fontSize: 12, marginTop: 6 }}>{t('connectChannelHint')}</p>
          </div>
        ) : (
          <div className="md-table-wrap">
            <table className="md-table">
              <thead>
                <tr>
                  <th>Pick</th>
                  <th>Video (Hold for Preview)</th>
                  <th>Views</th>
                  <th>Likes</th>
                  <th>Comments</th>
                  <th>Date</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {recentVideos.map((vid, idx) => {
                  const vidId = sanitizeYoutubeId(vid.id || vid.video_id || '');
                  const isChecked = vidId ? selectedIds.includes(vidId) : false;
                  return (
                    <tr key={vidId || idx}>
                      <td>
                        <input
                          type="checkbox"
                          disabled={!vidId}
                          checked={isChecked}
                          aria-label={`Select ${vid.title || 'video'}`}
                          onChange={() =>
                            setSelectedIds((prev) =>
                              prev.includes(vidId) ? prev.filter((x) => x !== vidId) : [...prev, vidId]
                            )
                          }
                        />
                      </td>
                      <td>
                        <div
                          style={{ display: 'flex', alignItems: 'center', gap: 10, cursor: vidId ? 'pointer' : 'default' }}
                          onMouseDown={() => vidId && startHoldPreview(vidId)}
                          onMouseUp={stopHoldPreview}
                          onMouseLeave={stopHoldPreview}
                          onTouchStart={() => vidId && startHoldPreview(vidId)}
                          onTouchEnd={stopHoldPreview}
                        >
                          {vid.thumbnail && (
                            <img
                              src={vid.thumbnail}
                              alt=""
                              width={68}
                              height={40}
                              style={{ borderRadius: 6, objectFit: 'cover', flexShrink: 0 }}
                            />
                          )}
                          <div>
                            <span style={{ fontWeight: 500, maxWidth: 300, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', display: 'block' }}>
                              {vid.title || 'Video'}
                            </span>
                            {vidId && (
                              <span className="md-mono" style={{ fontSize: 10.5, color: 'var(--muted)' }}>
                                Hold to preview
                              </span>
                            )}
                          </div>
                        </div>
                      </td>
                      <td className="md-mono">{Number(vid.views || 0).toLocaleString()}</td>
                      <td className="md-mono">{Number(vid.likes || 0).toLocaleString()}</td>
                      <td className="md-mono">{Number(vid.comments || 0).toLocaleString()}</td>
                      <td className="md-mono" style={{ color: 'var(--muted)' }}>
                        {String(vid.published_at || vid.published || '').slice(0, 10)}
                      </td>
                      <td>
                        {vidId && (
                          <button
                            type="button"
                            className="md-btn md-btn-sm"
                            onClick={() => setPreviewVideo({ id: vidId, title: vid.title || 'Video' })}
                          >
                            <IconVideo size={13} />
                            <span>{t('preview')}</span>
                          </button>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <Modal
        open={Boolean(previewVideo)}
        onClose={() => setPreviewVideo(null)}
        title={previewVideo?.title || 'Preview'}
        maxWidth={720}
      >
        {previewVideo?.id && (
          <div style={{ aspectRatio: '16 / 9', background: '#000', borderRadius: 10, overflow: 'hidden' }}>
            <iframe
              title={previewVideo.title}
              src={`https://www.youtube-nocookie.com/embed/${encodeURIComponent(previewVideo.id)}?autoplay=1`}
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
export default StudioPage;
