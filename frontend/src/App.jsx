import React, { Suspense, lazy, useCallback, useEffect, useState } from 'react';
import { ErrorBoundary } from './components/ErrorBoundary.jsx';
import { Footer } from './components/Footer.jsx';
import { Navbar } from './components/Navbar.jsx';
import {
  apiFetchJson,
  clearAuthSession,
  getBrowserFingerprint,
  getSavedLang,
  getStoredToken,
  getStoredUid,
  saveAuthSession,
  setSavedLang,
} from './lib/auth.js';
import { createTranslator } from './lib/i18n.js';
import { useRoute } from './lib/router.js';
import { DownloaderPage } from './pages/DownloaderPage.jsx';
import { LandingPage } from './pages/LandingPage.jsx';
import { LoginPage } from './pages/LoginPage.jsx';
import { StudioPage } from './pages/StudioPage.jsx';

const CasesPage = lazy(() => import('./pages/CasesPage.jsx'));
const NftsPage = lazy(() => import('./pages/NftsPage.jsx'));

function ChunkFallback() {
  return (
    <main className="md-container md-page">
      <div className="md-card" style={{ display: 'grid', gap: 14 }}>
        <div className="md-skeleton" style={{ height: 26, width: 220 }} />
        <div className="md-skeleton" style={{ height: 14, width: 340 }} />
        <div className="md-grid-3" style={{ marginTop: 8 }}>
          <div className="md-skeleton" style={{ height: 140 }} />
          <div className="md-skeleton" style={{ height: 140 }} />
          <div className="md-skeleton" style={{ height: 140 }} />
        </div>
      </div>
    </main>
  );
}

export function App() {
  const [route, navigate] = useRoute();
  const [lang, setLangState] = useState(getSavedLang);
  const t = createTranslator(lang);

  const [publicConfig, setPublicConfig] = useState({
    brand: 'MonoDeck',
    app_base_url: 'https://monodeck.site',
    bot_username: 'monodeck_bot',
    support_username: 'monodeck_support',
  });

  const [user, setUser] = useState(() => {
    const uid = getStoredUid();
    const tok = getStoredToken();
    if (uid > 0 && tok) {
      try {
        const cached = JSON.parse(localStorage.getItem(`md_user_profile_v3_${uid}`) || 'null');
        if (cached && cached.id === uid) return cached;
      } catch {}
      return { id: uid, first_name: `Creator #${uid}`, is_vip: false, is_owner: false };
    }
    return { id: 0, first_name: '', is_vip: false, is_owner: false };
  });

  const [userStats, setUserStats] = useState(() => {
    const uid = getStoredUid();
    if (uid > 0) {
      try {
        const cached = JSON.parse(localStorage.getItem(`md_user_stats_v3_${uid}`) || 'null');
        if (cached && typeof cached.balance_uzs === 'number') return cached;
      } catch {}
    }
    return { balance_uzs: 0, ton_balance: 0 };
  });
  const [syncLoading, setSyncLoading] = useState(false);

  const adjustBalanceOptimistic = useCallback((deltaUzs) => {
    setUserStats((prev) => {
      const next = {
        ...prev,
        balance_uzs: Math.max(0, Number(prev?.balance_uzs || 0) + Number(deltaUzs || 0)),
      };
      const uid = getStoredUid();
      if (uid > 0) {
        try {
          localStorage.setItem(`md_user_stats_v3_${uid}`, JSON.stringify(next));
        } catch {}
      }
      return next;
    });
  }, []);

  const setLang = (next) => {
    setLangState(next);
    setSavedLang(next);
  };

  const refreshUser = useCallback(async (force = false) => {
    const uid = getStoredUid();
    if (!uid) return;
    if (force) setSyncLoading(true);
    try {
      if (force) {
        const waUser = window.Telegram?.WebApp?.initDataUnsafe?.user;
        if (waUser && waUser.id === uid) {
          await apiFetchJson('/api/user/sync-profile', {
            method: 'POST',
            body: JSON.stringify({
              tg_user_id: uid,
              first_name: waUser.first_name || undefined,
              last_name: waUser.last_name || undefined,
              username: waUser.username || undefined,
              photo_url: waUser.photo_url || undefined,
            }),
          }).catch(() => {});
        }
      }
      const { ok, data } = await apiFetchJson(
        `/api/bot_user?tg_user_id=${encodeURIComponent(uid)}${force ? '&refresh=1' : ''}`
      );
      if (ok && data && (data.ok || data.balance_uzs !== undefined)) {
        const nextStats = {
          balance_uzs: Number(data.balance_uzs || 0),
          ton_balance: Number(data.ton_balance || 0),
        };
        setUserStats(nextStats);
        try {
          localStorage.setItem(`md_user_stats_v3_${uid}`, JSON.stringify(nextStats));
        } catch {}
        setUser((prev) => {
          const nextUser = {
            ...prev,
            id: uid,
            first_name: data.first_name || prev.first_name || `Creator #${uid}`,
            username: data.username || '',
            photo_url: data.photo_url || prev.photo_url || '',
            is_vip: Boolean(data.is_vip),
            is_owner: Boolean(data.is_owner),
          };
          try {
            localStorage.setItem(`md_user_profile_v3_${uid}`, JSON.stringify(nextUser));
          } catch {}
          return nextUser;
        });
      }
    } finally {
      if (force) setSyncLoading(false);
    }
  }, []);

  useEffect(() => {
    apiFetchJson('/api/public-config')
      .then(({ data }) => {
        if (data?.ok) setPublicConfig(data);
      })
      .catch(() => {});

    let handled = false;
    try {
      const params = new URLSearchParams(window.location.search);
      const qUid = parseInt(params.get('tg_user_id') || params.get('user_id') || '0', 10);
      const qOtp = params.get('otp');
      if (qOtp) {
        params.delete('otp');
        params.delete('tg_user_id');
        params.delete('user_id');
        const nextQs = params.toString();
        window.history.replaceState(
          {},
          document.title,
          window.location.pathname + (nextQs ? `?${nextQs}` : '') + (window.location.hash || '')
        );
      }
      if (qUid > 0 && qOtp) {
        handled = true;
        apiFetchJson('/api/auth/verify-otp', {
          method: 'POST',
          body: JSON.stringify({ tg_user_id: qUid, otp: qOtp, fingerprint: getBrowserFingerprint() }),
        }).then(({ data }) => {
          if (data?.ok && data?.token) {
            saveAuthSession({ token: data.token, tgUserId: qUid, firstName: `Creator #${qUid}` });
            setUser({
              id: qUid,
              first_name: `Creator #${qUid}`,
              photo_url: data.photo_url || '',
              is_vip: Boolean(data.is_vip),
              is_owner: Boolean(data.is_owner),
            });
            refreshUser(false);
            if (window.location.pathname === '/' || window.location.pathname === '/login') {
              navigate('/studio');
            }
          }
        });
      }
    } catch {}

    if (!handled && window.Telegram?.WebApp) {
      const tg = window.Telegram.WebApp;
      tg.ready();
      tg.expand();
      if (tg.initData) {
        handled = true;
        apiFetchJson('/api/auth/verify-webapp', {
          method: 'POST',
          body: JSON.stringify({ initData: tg.initData, fingerprint: getBrowserFingerprint() }),
        }).then(({ data }) => {
          if (data?.ok && data?.tg_user_id && data?.token) {
            const u = data.user || {};
            const fn = u.first_name || `Creator #${data.tg_user_id}`;
            saveAuthSession({ token: data.token, tgUserId: data.tg_user_id, firstName: fn });
            setUser({
              id: data.tg_user_id,
              first_name: fn,
              username: u.username || '',
              photo_url: data.photo_url || u.photo_url || '',
              is_vip: Boolean(data.is_vip),
              is_owner: Boolean(data.is_owner),
            });
            if (u.photo_url || u.first_name) {
              apiFetchJson('/api/user/sync-profile', {
                method: 'POST',
                body: JSON.stringify({
                  tg_user_id: data.tg_user_id,
                  first_name: u.first_name || undefined,
                  last_name: u.last_name || undefined,
                  username: u.username || undefined,
                  photo_url: u.photo_url || undefined,
                }),
              }).catch(() => {});
            }
            refreshUser(false);
          }
        });
      }
    }

    if (!handled) {
      const tok = getStoredToken();
      const uid = getStoredUid();
      if (tok && uid > 0) {
        apiFetchJson('/api/auth/verify-token', {
          method: 'POST',
          body: JSON.stringify({ token: tok, tg_user_id: uid, fingerprint: getBrowserFingerprint() }),
        }).then(({ ok, data }) => {
          if (ok && data?.ok) {
            const vUid = Number(data.tg_user_id || uid);
            if (data.token) saveAuthSession({ token: data.token, tgUserId: vUid });
            setUser({
              id: vUid,
              first_name: data.user?.first_name || `Creator #${vUid}`,
              photo_url: data.photo_url || data.user?.photo_url || '',
              is_vip: Boolean(data.is_vip),
              is_owner: Boolean(data.is_owner),
            });
            refreshUser(false);
          } else {
            clearAuthSession();
            setUser({ id: 0, first_name: '', photo_url: '', is_vip: false, is_owner: false });
          }
        });
      }
    }
  }, [refreshUser, navigate]);

  const handleLogout = () => {
    const token = getStoredToken();
    clearAuthSession();
    setUser({ id: 0, first_name: '', is_vip: false, is_owner: false });
    setUserStats({ balance_uzs: 0, ton_balance: 0 });
    apiFetchJson('/api/auth/logout', {
      method: 'POST',
      body: JSON.stringify({ token }),
    }).catch(() => {});
    navigate('/');
  };

  return (
    <ErrorBoundary>
      <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
        <div>
          <Navbar
            route={route}
            navigate={navigate}
            user={user}
            userStats={userStats}
            lang={lang}
            setLang={setLang}
            onSyncProfile={() => refreshUser(true)}
            syncLoading={syncLoading}
            onLogout={handleLogout}
            t={t}
          />

          {route === '/' && <LandingPage user={user} navigate={navigate} publicConfig={publicConfig} t={t} />}
          {route === '/login' && (
            <LoginPage
              user={user}
              onAuthSuccess={(u) => {
                setUser(u);
                refreshUser(false);
              }}
              publicConfig={publicConfig}
              navigate={navigate}
              t={t}
            />
          )}
          {route === '/studio' && <StudioPage user={user} navigate={navigate} t={t} />}
          {route === '/downloader' && <DownloaderPage user={user} navigate={navigate} t={t} />}
          {route === '/cases' && (
            <Suspense fallback={<ChunkFallback />}>
              <CasesPage user={user} userStats={userStats} onRefreshUser={refreshUser} onAdjustBalance={adjustBalanceOptimistic} navigate={navigate} t={t} />
            </Suspense>
          )}
          {route === '/nfts' && (
            <Suspense fallback={<ChunkFallback />}>
              <NftsPage user={user} onRefreshUser={refreshUser} onAdjustBalance={adjustBalanceOptimistic} navigate={navigate} t={t} />
            </Suspense>
          )}
        </div>

        <Footer publicConfig={publicConfig} t={t} />
      </div>
    </ErrorBoundary>
  );
}
export default App;
