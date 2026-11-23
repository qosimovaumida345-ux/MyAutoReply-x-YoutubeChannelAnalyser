import React, { useEffect, useState } from 'react';
import { IconExternal, IconShield } from '../components/Icons.jsx';
import { apiFetchJson, getBrowserFingerprint, saveAuthSession } from '../lib/auth.js';

export function LoginPage({ user, onAuthSuccess, publicConfig, navigate, t }) {
  const [step, setStep] = useState(1);
  const [tgIdInput, setTgIdInput] = useState('');
  const [otpInput, setOtpInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [cooldown, setCooldown] = useState(0);
  const [error, setError] = useState('');
  const [statusMsg, setStatusMsg] = useState('');

  const botUsername = publicConfig?.bot_username || 'monodeck_app';

  useEffect(() => {
    if (cooldown <= 0) return undefined;
    const id = setTimeout(() => setCooldown((c) => c - 1), 1000);
    return () => clearTimeout(id);
  }, [cooldown]);

  if (user && user.id > 0) {
    return (
      <main className="md-container md-page">
        <div className="md-card" style={{ maxWidth: 480, margin: '24px auto' }}>
          <div className="md-eyebrow" style={{ marginBottom: 14 }}>
            <span className="md-dot" />
            <span>ACTIVE SESSION</span>
          </div>
          <h1 className="md-h2" style={{ marginBottom: 8 }}>
            {user.first_name || `Creator #${user.id}`}
          </h1>
          <p className="md-mono" style={{ fontSize: 13, color: 'var(--muted)', marginBottom: 20 }}>
            Telegram ID: {user.id}
          </p>
          <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
            <button type="button" className="md-btn md-btn-primary" onClick={() => navigate('/studio')}>
              {t('openStudio')}
            </button>
            <button type="button" className="md-btn" onClick={() => navigate('/cases')}>
              {t('navCases')}
            </button>
          </div>
        </div>
      </main>
    );
  }

  const handleRequestOtp = async (e) => {
    e.preventDefault();
    const uid = parseInt(tgIdInput.trim(), 10);
    if (!uid || uid <= 0) {
      setError('Enter a valid numeric Telegram User ID.');
      return;
    }
    setLoading(true);
    setError('');
    setStatusMsg('');
    try {
      const { data } = await apiFetchJson('/api/auth/request-otp', {
        method: 'POST',
        body: JSON.stringify({ tg_user_id: uid }),
      });
      if (data?.ok) {
        setStep(2);
        setCooldown(30);
        setStatusMsg(`Verification code sent via @${botUsername}.`);
      } else {
        setError(data?.error || 'Could not send verification code.');
      }
    } catch {
      setError('Network error while requesting code.');
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyOtp = async (e) => {
    e.preventDefault();
    const uid = parseInt(tgIdInput.trim(), 10);
    const code = otpInput.trim();
    if (!uid || code.length < 6) {
      setError('Enter the full 6-digit code sent by the bot.');
      return;
    }
    setLoading(true);
    setError('');
    try {
      const { data } = await apiFetchJson('/api/auth/verify-otp', {
        method: 'POST',
        body: JSON.stringify({
          tg_user_id: uid,
          otp: code,
          fingerprint: getBrowserFingerprint(),
        }),
      });
      if (data?.ok && data?.token) {
        saveAuthSession({
          token: data.token,
          tgUserId: uid,
          firstName: `Creator #${uid}`,
        });
        onAuthSuccess({
          id: uid,
          first_name: `Creator #${uid}`,
          is_vip: Boolean(data.is_vip),
          is_owner: Boolean(data.is_owner),
        });
        navigate('/studio');
      } else {
        setError(data?.error || 'Invalid or expired verification code.');
      }
    } catch {
      setError('Network error while verifying code.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="md-container md-page">
      <div className="md-card" style={{ maxWidth: 480, margin: '16px auto' }}>
        <div className="md-eyebrow" style={{ marginBottom: 14 }}>
          <span className="md-dot" />
          <span>TELEGRAM AUTH GATEWAY</span>
        </div>

        <h1 className="md-h2" style={{ marginBottom: 8 }}>{t('loginTitle')}</h1>
        <p style={{ fontSize: 14, color: 'var(--muted)', marginBottom: 22 }}>{t('loginSub')}</p>

        {error && (
          <div
            role="alert"
            style={{
              background: 'var(--err-soft)',
              color: 'var(--err)',
              border: '1px solid #FECACA',
              borderRadius: 10,
              padding: '10px 12px',
              fontSize: 13,
              fontWeight: 500,
              marginBottom: 16,
            }}
          >
            {error}
          </div>
        )}

        {statusMsg && (
          <div
            style={{
              background: 'var(--ok-soft)',
              color: 'var(--ok)',
              border: '1px solid #BBF7D0',
              borderRadius: 10,
              padding: '10px 12px',
              fontSize: 13,
              fontWeight: 500,
              marginBottom: 16,
            }}
          >
            {statusMsg}
          </div>
        )}

        {step === 1 ? (
          <form onSubmit={handleRequestOtp} style={{ display: 'grid', gap: 14 }}>
            <div>
              <label
                htmlFor="md-tg-id"
                style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 6 }}
              >
                {t('tgIdLabel')}
              </label>
              <input
                id="md-tg-id"
                type="text"
                inputMode="numeric"
                className="md-input md-mono"
                placeholder={t('tgIdPlaceholder')}
                value={tgIdInput}
                onChange={(e) => setTgIdInput(e.target.value)}
                required
              />
            </div>

            <button type="submit" disabled={loading} className="md-btn md-btn-primary md-btn-rect">
              {loading ? t('sendingCode') : t('sendCode')}
            </button>
          </form>
        ) : (
          <form onSubmit={handleVerifyOtp} style={{ display: 'grid', gap: 14 }}>
            <div>
              <label
                htmlFor="md-otp-code"
                style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 6 }}
              >
                {t('otpLabel')}
              </label>
              <input
                id="md-otp-code"
                type="text"
                inputMode="numeric"
                maxLength={8}
                className="md-input md-mono"
                placeholder="123456"
                value={otpInput}
                onChange={(e) => setOtpInput(e.target.value)}
                required
              />
            </div>

            <button type="submit" disabled={loading} className="md-btn md-btn-accent md-btn-rect">
              {loading ? t('verifying') : t('verifyCode')}
            </button>

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 8 }}>
              <button
                type="button"
                className="md-btn md-btn-sm"
                onClick={() => {
                  setStep(1);
                  setOtpInput('');
                  setError('');
                }}
              >
                Change ID
              </button>
              <button
                type="button"
                className="md-btn md-btn-sm"
                disabled={cooldown > 0 || loading}
                onClick={handleRequestOtp}
              >
                {cooldown > 0 ? `Resend (${cooldown}s)` : 'Resend code'}
              </button>
            </div>
          </form>
        )}

        <div
          style={{
            marginTop: 22,
            paddingTop: 16,
            borderTop: '1px solid var(--border)',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            flexWrap: 'wrap',
            gap: 10,
            fontSize: 12,
            color: 'var(--muted)',
          }}
        >
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
            <IconShield size={13} />
            <span>Need your ID? Run /start in Telegram.</span>
          </span>
          <a
            href={`https://t.me/${encodeURIComponent(botUsername)}`}
            target="_blank"
            rel="noopener noreferrer"
            className="md-btn md-btn-sm"
          >
            <span>{t('openBot')}</span>
            <IconExternal size={12} />
          </a>
        </div>
      </div>
    </main>
  );
}
