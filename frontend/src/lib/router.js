import { useEffect, useState, useCallback } from 'react';

export function normalizeRoute(pathname) {
  const p = String(pathname || '/').toLowerCase().replace(/\/+$/, '') || '/';
  if (p === '/login' || p === '/signin') return '/login';
  if (p === '/studio' || p === '/analytics' || p === '/goal' || p === '/boost' || p === '/teamwork' || p === '/teamwork-preview' || p === '/teamwork_preview') {
    return '/studio';
  }
  if (p === '/downloader' || p === '/videos') return '/downloader';
  if (p === '/cases') return '/cases';
  if (p === '/nfts') return '/nfts';
  return '/';
}

export function useRoute() {
  const [route, setRoute] = useState(() => normalizeRoute(window.location.pathname));

  useEffect(() => {
    const onPop = () => setRoute(normalizeRoute(window.location.pathname));
    window.addEventListener('popstate', onPop);
    return () => window.removeEventListener('popstate', onPop);
  }, []);

  const navigate = useCallback((to) => {
    const next = normalizeRoute(to);
    if (window.location.pathname !== next) {
      window.history.pushState({}, '', next);
    }
    setRoute(next);
    window.scrollTo({ top: 0, behavior: 'auto' });
  }, []);

  return [route, navigate];
}
