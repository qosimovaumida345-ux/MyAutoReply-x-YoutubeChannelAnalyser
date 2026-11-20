import React, { useEffect } from 'react';
import { IconClose } from './Icons.jsx';

export function Modal({ open, onClose, title, children, maxWidth = 560 }) {
  useEffect(() => {
    if (!open) return undefined;
    const onKey = (e) => {
      if (e.key === 'Escape') onClose?.();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div
      className="md-modal-backdrop"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose?.();
      }}
      role="presentation"
    >
      <div
        className="md-modal"
        style={{ maxWidth }}
        role="dialog"
        aria-modal="true"
        aria-label={title || 'Dialog'}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16, gap: 12 }}>
          <h3 style={{ fontFamily: 'var(--font-display)', fontSize: 18, fontWeight: 600 }}>{title}</h3>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="md-btn md-btn-sm"
            style={{ padding: '6px', borderRadius: 8 }}
          >
            <IconClose size={16} />
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}
