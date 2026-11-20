const TOKEN_KEY = 'monodeck_auth_token';
const UID_KEY = 'monodeck_tg_user_id';
const NAME_KEY = 'monodeck_user_name';
const LANG_KEY = 'monodeck_lang';

export function getSavedLang() {
  try {
    const val = localStorage.getItem(LANG_KEY);
    if (val === 'en' || val === 'uz' || val === 'ru') return val;
  } catch {}
  return 'en';
}

export function setSavedLang(lang) {
  try {
    localStorage.setItem(LANG_KEY, lang);
  } catch {}
}

export function getBrowserFingerprint() {
  try {
    const raw = [
      navigator.userAgent || '',
      navigator.language || '',
      screen?.width || 0,
      screen?.height || 0,
      Intl.DateTimeFormat().resolvedOptions().timeZone || '',
    ].join('|');
    let h = 0;
    for (let i = 0; i < raw.length; i += 1) {
      h = (h * 31 + raw.charCodeAt(i)) | 0;
    }
    return 'md_' + Math.abs(h).toString(16);
  } catch {
    return 'md_web';
  }
}

export function getStoredToken() {
  try {
    return (localStorage.getItem(TOKEN_KEY) || '').trim();
  } catch {
    return '';
  }
}

export function getStoredUid() {
  try {
    const n = parseInt(localStorage.getItem(UID_KEY) || '0', 10);
    return Number.isFinite(n) && n > 0 ? n : 0;
  } catch {
    return 0;
  }
}

export function saveAuthSession({ token, tgUserId, firstName }) {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, String(token));
    if (tgUserId) localStorage.setItem(UID_KEY, String(tgUserId));
    if (firstName) localStorage.setItem(NAME_KEY, String(firstName));
  } catch {}
}

export function clearClientCookie(name) {
  try {
    const secureFlag = window.location.protocol === 'https:' ? '; Secure' : '';
    document.cookie = `${name}=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT; SameSite=Lax${secureFlag}`;
  } catch {}
}

export function clearAuthSession() {
  try {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(UID_KEY);
    localStorage.removeItem(NAME_KEY);
  } catch {}
  clearClientCookie('cf_adm_sig');
  clearClientCookie('cf_auth_token');
}

export function getAuthHeaders(extraHeaders = {}, includeContentType = true) {
  const headers = { ...extraHeaders };
  if (includeContentType && !headers['Content-Type']) {
    headers['Content-Type'] = 'application/json';
  }
  const token = getStoredToken();
  if (token) {
    headers.Authorization = `Bearer ${token}`;
    headers['X-Auth-Token'] = token;
  }
  const initData = window.Telegram?.WebApp?.initData;
  if (initData) {
    headers['X-Telegram-Init-Data'] = initData;
  }
  return headers;
}

export function sanitizeYoutubeId(rawId) {
  const raw = String(rawId || '').trim();
  if (/^[A-Za-z0-9_-]{11}$/.test(raw)) return raw;
  try {
    const u = new URL(raw);
    const vParam = u.searchParams.get('v');
    if (vParam && /^[A-Za-z0-9_-]{11}$/.test(vParam)) return vParam;
    const parts = u.pathname.split('/').filter(Boolean);
    for (let i = parts.length - 1; i >= 0; i -= 1) {
      if (/^[A-Za-z0-9_-]{11}$/.test(parts[i])) return parts[i];
    }
  } catch {}
  return '';
}

export function safeOpenExternal(rawUrl) {
  try {
    const u = new URL(String(rawUrl || ''), window.location.origin);
    if (u.protocol !== 'https:' && u.protocol !== 'http:') return false;
    if (window.location.protocol === 'https:' && u.protocol === 'http:') return false;
    if (u.hostname === 't.me' && window.Telegram?.WebApp?.openTelegramLink) {
      window.Telegram.WebApp.openTelegramLink(u.toString());
      return true;
    }
    const opened = window.open(u.toString(), '_blank', 'noopener,noreferrer');
    if (opened) opened.opener = null;
    return true;
  } catch {
    return false;
  }
}

export async function apiFetchJson(url, options = {}) {
  const isGet = !options.method || options.method.toUpperCase() === 'GET';
  const res = await fetch(url, {
    ...options,
    headers: getAuthHeaders(options.headers || {}, !isGet),
    credentials: 'same-origin',
  });
  let data = null;
  try {
    data = await res.json();
  } catch {
    data = { ok: false, error: `HTTP ${res.status}` };
  }
  return { status: res.status, ok: res.ok, data };
}
