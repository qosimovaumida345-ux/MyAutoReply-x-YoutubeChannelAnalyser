import React from 'react';
import { IconBox, IconChart, IconDownload, IconExternal, IconShield } from '../components/Icons.jsx';

export function LandingPage({ user, navigate, publicConfig, t }) {
  const isAuthed = Boolean(user && user.id > 0);
  const botUsername = publicConfig?.bot_username || 'monodeck_app';

  const modules = [
    {
      num: '01',
      title: 'YouTube Studio & Autopost',
      desc: 'Inspect live channel subscriber & view velocity, preview uploads, and queue automated Shorts workflows.',
      to: '/studio',
      cta: 'Open Studio',
      Icon: IconChart,
    },
    {
      num: '02',
      title: 'Media Format Downloader',
      desc: 'Resolve available MP4 and MP3 stream formats for authorized downloads without stalling the UI thread.',
      to: '/downloader',
      cta: 'Open Downloader',
      Icon: IconDownload,
    },
    {
      num: '03',
      title: 'Stars Cases & Collectibles',
      desc: 'Provably weighted digital gift unboxings, 1v1 duels, Gift Upgrader wheel, and Fragment NFTs.',
      to: '/cases',
      cta: 'Explore Cases',
      Icon: IconBox,
    },
    {
      num: '04',
      title: 'REST v1 & Shield Captcha',
      desc: 'Embeddable human-verification widget and reseller automation endpoints with transparent API docs.',
      href: '/docs',
      cta: 'Read API Docs',
      Icon: IconShield,
    },
  ];

  return (
    <main className="md-container md-page">
      <section style={{ paddingTop: 20, paddingBottom: 48, borderBottom: '1px solid var(--border)' }}>
        <div className="md-eyebrow" style={{ marginBottom: 20 }}>
          <span className="md-dot" />
          <span>{t('heroEyebrow')}</span>
        </div>

        <h1 className="md-h1" style={{ maxWidth: 820, marginBottom: 20 }}>
          {t('heroTitleBefore')}
          <span className="md-serif-em">{t('heroTitleEm')}</span>
          {t('heroTitleAfter')}
        </h1>

        <p style={{ maxWidth: 640, fontSize: 16, color: 'var(--ink-2)', lineHeight: 1.65, marginBottom: 28 }}>
          {t('heroSub')}
        </p>

        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10, alignItems: 'center' }}>
          <button
            type="button"
            className="md-btn md-btn-primary"
            onClick={() => navigate(isAuthed ? '/studio' : '/login')}
          >
            <span>{isAuthed ? t('openStudio') : t('signIn')}</span>
          </button>
          <a href="/docs" className="md-btn">
            <span>{t('exploreApi')}</span>
          </a>
          <a href="/captcha" className="md-btn">
            <IconShield size={14} />
            <span>{t('tryCaptcha')}</span>
          </a>
          <a
            href={`https://t.me/${encodeURIComponent(botUsername)}`}
            target="_blank"
            rel="noopener noreferrer"
            className="md-mono"
            style={{
              fontSize: 12,
              color: 'var(--muted)',
              textDecoration: 'none',
              padding: '0 8px',
              display: 'inline-flex',
              alignItems: 'center',
              gap: 5,
            }}
          >
            <span>@{botUsername}</span>
            <IconExternal size={12} />
          </a>
        </div>
      </section>

      <section style={{ padding: '44px 0', borderBottom: '1px solid var(--border)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 20, flexWrap: 'wrap', gap: 8 }}>
          <h2 className="md-h2">Core Modules</h2>
          <span className="md-mono" style={{ fontSize: 12, color: 'var(--muted)' }}>
            4 DEDICATED ROUTES &middot; ZERO BLOCKING
          </span>
        </div>

        <div className="md-grid-4">
          {modules.map((mod) => {
            const Icon = mod.Icon;
            return (
              <div
                key={mod.num}
                className="md-card md-card-interactive"
                style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between', gap: 18 }}
              >
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
                    <span className="md-mono" style={{ fontSize: 12, color: 'var(--accent)', fontWeight: 600 }}>
                      {mod.num}
                    </span>
                    <Icon size={17} color="var(--ink)" />
                  </div>
                  <h3 style={{ fontFamily: 'var(--font-display)', fontSize: 17, fontWeight: 600, marginBottom: 8 }}>
                    {mod.title}
                  </h3>
                  <p style={{ fontSize: 13.5, color: 'var(--muted)', lineHeight: 1.55 }}>{mod.desc}</p>
                </div>

                {mod.to ? (
                  <button
                    type="button"
                    className="md-btn md-btn-sm"
                    style={{ width: '100%' }}
                    onClick={() => navigate(mod.to)}
                  >
                    {mod.cta}
                  </button>
                ) : (
                  <a href={mod.href} className="md-btn md-btn-sm" style={{ width: '100%' }}>
                    {mod.cta}
                  </a>
                )}
              </div>
            );
          })}
        </div>
      </section>

      <section style={{ paddingTop: 40 }}>
        <div className="md-card" style={{ display: 'grid', gap: 16 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 10 }}>
            <div className="md-eyebrow">
              <span className="md-dot" />
              <span>GOOGLE API SERVICES COMPLIANCE</span>
            </div>
            <span className="md-mono" style={{ fontSize: 11, color: 'var(--ok)', fontWeight: 600 }}>
              OAUTH 2.0 LIMITED USE
            </span>
          </div>

          <h2 className="md-h2">{t('oauthTitle')}</h2>
          <p style={{ color: 'var(--ink-2)', fontSize: 14.5, maxWidth: 820, lineHeight: 1.65 }}>
            {t('oauthDesc')}
          </p>

          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10, paddingTop: 4 }}>
            <a href="/privacy" className="md-btn md-btn-sm">
              {t('privacyPolicy')}
            </a>
            <a href="/terms" className="md-btn md-btn-sm">
              {t('termsOfService')}
            </a>
            <a
              href="https://www.youtube.com/t/terms"
              target="_blank"
              rel="noopener noreferrer"
              className="md-btn md-btn-sm"
            >
              <span>YouTube Terms of Service</span>
              <IconExternal size={12} />
            </a>
            <a
              href="https://policies.google.com/privacy"
              target="_blank"
              rel="noopener noreferrer"
              className="md-btn md-btn-sm"
            >
              <span>Google Privacy Policy</span>
              <IconExternal size={12} />
            </a>
            <a
              href="https://myaccount.google.com/permissions"
              target="_blank"
              rel="noopener noreferrer"
              className="md-btn md-btn-accent md-btn-sm"
            >
              <span>{t('revokeAccess')}</span>
              <IconExternal size={12} />
            </a>
          </div>
        </div>
      </section>
    </main>
  );
}
