import React, { useEffect, useRef, useState } from 'react';
import {
  BrandMark,
  IconBox,
  IconChart,
  IconChevronDown,
  IconDiamond,
  IconDownload,
  IconExternal,
  IconShield,
} from './Icons.jsx';

export function Navbar({
  route,
  navigate,
  user,
  userStats,
  lang,
  setLang,
  onSyncProfile,
  syncLoading,
  onLogout,
  t,
}) {
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef(null);
  const isAuthed = Boolean(user && user.id > 0);

  useEffect(() => {
    if (!menuOpen) return undefined;
    const onDocClick = (e) => {
      if (menuRef.current && !menuRef.current.contains(e.target)) {
        setMenuOpen(false);
      }
    };
    const onKeyDown = (e) => {
      if (e.key === 'Escape') setMenuOpen(false);
    };
    document.addEventListener('mousedown', onDocClick);
    window.addEventListener('keydown', onKeyDown);
    return () => {
      document.removeEventListener('mousedown', onDocClick);
      window.removeEventListener('keydown', onKeyDown);
    };
  }, [menuOpen]);

  const navItems = [
    { path: '/studio', label: t('navStudio') },
    { path: '/downloader', label: t('navDownloader') },
    { path: '/cases', label: t('navCases') },
    { path: '/nfts', label: t('navNfts') },
  ];

  const handleNav = (e, to) => {
    e.preventDefault();
    setMenuOpen(false);
    navigate(to);
  };

  return (
    <>
      <header className="md-nav">
        <div className="md-nav-inner">
          <a href="/" onClick={(e) => handleNav(e, '/')} className="md-brand">
            <BrandMark size={24} />
            <span>{t('brand')}</span>
          </a>

          <nav className="md-nav-pills" aria-label="Primary">
            {navItems.map((item) => (
              <a
                key={item.path}
                href={item.path}
                onClick={(e) => handleNav(e, item.path)}
                className={`md-nav-link${route === item.path ? ' active' : ''}`}
              >
                {item.label}
              </a>
            ))}
          </nav>

          <div className="md-nav-right" ref={menuRef}>
            {!isAuthed ? (
              <>
                <div
                  style={{
                    display: 'inline-flex',
                    border: '1px solid var(--border)',
                    background: 'var(--surface)',
                    borderRadius: 999,
                    padding: 2,
                  }}
                  role="group"
                  aria-label="Language"
                >
                  {['en', 'uz', 'ru'].map((code) => (
                    <button
                      key={code}
                      type="button"
                      onClick={() => setLang(code)}
                      style={{
                        border: 'none',
                        background: lang === code ? 'var(--ink)' : 'transparent',
                        color: lang === code ? '#FFFFFF' : 'var(--muted)',
                        borderRadius: 999,
                        padding: '3px 8px',
                        fontSize: 11,
                        fontWeight: 600,
                        textTransform: 'uppercase',
                        cursor: 'pointer',
                      }}
                    >
                      {code}
                    </button>
                  ))}
                </div>
                <a
                  href="/login"
                  onClick={(e) => handleNav(e, '/login')}
                  className="md-btn md-btn-primary md-btn-sm"
                >
                  {t('signIn')}
                </a>
              </>
            ) : (
              <div className="md-account-wrap">
                <button
                  type="button"
                  onClick={() => setMenuOpen((prev) => !prev)}
                  className="md-btn md-btn-sm"
                  aria-expanded={menuOpen}
                  aria-haspopup="menu"
                  style={{ paddingRight: 10 }}
                >
                  <span
                    className="md-mono"
                    style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      width: 20,
                      height: 20,
                      borderRadius: 999,
                      background: 'var(--ink)',
                      color: '#FFFFFF',
                      fontSize: 11,
                      fontWeight: 600,
                    }}
                  >
                    {(user.first_name || 'M').slice(0, 1).toUpperCase()}
                  </span>
                  <span style={{ maxWidth: 110, overflow: 'hidden', textOverflow: 'ellipsis' }}>
                    {user.first_name || `#${user.id}`}
                  </span>
                  <span
                    className="md-mono"
                    style={{
                      fontSize: 11,
                      color: 'var(--accent)',
                      fontWeight: 600,
                    }}
                  >
                    {Number(userStats?.balance_uzs || 0).toLocaleString()}
                  </span>
                  <IconChevronDown size={13} />
                </button>

                {menuOpen && (
                  <div className="md-dropdown" role="menu">
                    <div
                      style={{
                        padding: '8px 10px',
                        borderBottom: '1px solid var(--border)',
                        marginBottom: 4,
                      }}
                    >
                      <div style={{ fontSize: 13, fontWeight: 600 }}>
                        {user.first_name || `Creator #${user.id}`}
                      </div>
                      <div className="md-mono" style={{ fontSize: 11, color: 'var(--muted)' }}>
                        ID {user.id} &middot; {Number(userStats?.balance_uzs || 0).toLocaleString()} UZS
                      </div>
                    </div>

                    <button
                      type="button"
                      role="menuitem"
                      className="md-dropdown-item"
                      disabled={syncLoading}
                      onClick={() => {
                        onSyncProfile();
                        setMenuOpen(false);
                      }}
                    >
                      <span>{syncLoading ? t('loading') : t('syncProfile')}</span>
                    </button>

                    <a href="/docs" className="md-dropdown-item" role="menuitem">
                      <span>API Docs</span>
                      <IconExternal size={13} color="var(--muted)" />
                    </a>

                    <a href="/captcha" className="md-dropdown-item" role="menuitem">
                      <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
                        <IconShield size={13} />
                        <span>Shield Captcha</span>
                      </span>
                      <IconExternal size={13} color="var(--muted)" />
                    </a>

                    <div
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        padding: '6px 10px',
                        borderTop: '1px solid var(--border)',
                        borderBottom: '1px solid var(--border)',
                        margin: '4px 0',
                      }}
                    >
                      <span style={{ fontSize: 12, color: 'var(--muted)' }}>Lang</span>
                      <div style={{ display: 'flex', gap: 4 }}>
                        {['en', 'uz', 'ru'].map((code) => (
                          <button
                            key={code}
                            type="button"
                            onClick={() => setLang(code)}
                            style={{
                              border: '1px solid var(--border)',
                              background: lang === code ? 'var(--ink)' : 'transparent',
                              color: lang === code ? '#FFFFFF' : 'var(--ink)',
                              borderRadius: 6,
                              padding: '2px 7px',
                              fontSize: 11,
                              fontWeight: 600,
                              textTransform: 'uppercase',
                              cursor: 'pointer',
                            }}
                          >
                            {code}
                          </button>
                        ))}
                      </div>
                    </div>

                    <button
                      type="button"
                      role="menuitem"
                      className="md-dropdown-item"
                      style={{ color: 'var(--err)' }}
                      onClick={() => {
                        setMenuOpen(false);
                        onLogout();
                      }}
                    >
                      <span>{t('signOut')}</span>
                    </button>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </header>

      <nav className="md-mobile-bar" aria-label="Mobile navigation">
        <a
          href="/studio"
          onClick={(e) => handleNav(e, '/studio')}
          className={`md-mobile-tab${route === '/studio' ? ' active' : ''}`}
        >
          <IconChart size={18} />
          <span>{t('navStudio')}</span>
        </a>
        <a
          href="/downloader"
          onClick={(e) => handleNav(e, '/downloader')}
          className={`md-mobile-tab${route === '/downloader' ? ' active' : ''}`}
        >
          <IconDownload size={18} />
          <span>{t('navDownloader')}</span>
        </a>
        <a
          href="/cases"
          onClick={(e) => handleNav(e, '/cases')}
          className={`md-mobile-tab${route === '/cases' ? ' active' : ''}`}
        >
          <IconBox size={18} />
          <span>{t('navCases')}</span>
        </a>
        <a
          href="/nfts"
          onClick={(e) => handleNav(e, '/nfts')}
          className={`md-mobile-tab${route === '/nfts' ? ' active' : ''}`}
        >
          <IconDiamond size={18} />
          <span>{t('navNfts')}</span>
        </a>
      </nav>
    </>
  );
}
