import React from 'react';

export function Footer({ publicConfig, t }) {
  const botUsername = publicConfig?.bot_username || 'monodeck_bot';
  const supportUsername = publicConfig?.support_username || 'monodeck_support';
  const rawBase = String(publicConfig?.app_base_url || 'monodeck.site');
  const domain = rawBase.replace(/^https?:\/\//, '').split('/')[0] || 'monodeck.site';

  return (
    <footer className="md-footer">
      <div className="md-footer-inner">
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span>&copy; 2026 {t('brand')}</span>
          <span style={{ color: 'var(--border-strong)' }}>/</span>
          <code className="md-mono" style={{ fontSize: 12, color: 'var(--ink-2)' }}>{domain}</code>
        </div>
        <div className="md-footer-links">
          <a href="/privacy">{t('privacyPolicy')}</a>
          <a href="/terms">{t('termsOfService')}</a>
          <a href="/docs">{t('exploreApi')}</a>
          <a href="/captcha">{t('tryCaptcha')}</a>
          <a href={`https://t.me/${encodeURIComponent(botUsername)}`} target="_blank" rel="noopener noreferrer">
            @{botUsername}
          </a>
          <a href={`https://t.me/${encodeURIComponent(supportUsername)}`} target="_blank" rel="noopener noreferrer">
            Support
          </a>
        </div>
      </div>
    </footer>
  );
}
