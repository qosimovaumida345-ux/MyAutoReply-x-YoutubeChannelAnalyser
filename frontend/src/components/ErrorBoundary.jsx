import React from 'react';

export class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(err) {
    console.error('[MonoDeck UI]', err?.name || 'Error');
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="md-container md-page">
          <div className="md-card" style={{ maxWidth: 520, margin: '40px auto', textAlign: 'center' }}>
            <div className="md-eyebrow" style={{ marginBottom: 12 }}>
              <span className="md-dot" />
              <span>RECOVERY</span>
            </div>
            <h2 className="md-h2" style={{ marginBottom: 8 }}>Something failed to render</h2>
            <p style={{ color: 'var(--muted)', fontSize: 14, marginBottom: 18 }}>
              Reload the page to restore a clean workspace state.
            </p>
            <button
              type="button"
              className="md-btn md-btn-primary"
              onClick={() => window.location.reload()}
            >
              Reload Workspace
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
