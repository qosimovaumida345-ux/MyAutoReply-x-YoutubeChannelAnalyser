# -*- coding: utf-8 -*-
"""
MonoDeck Unified Design System (MotionSites.ai Editorial Paper & Pure Obsidian)
Strict Black, White & International Vermilion (#FF5A1F) visual grammar.
Zero cyan/purple neon gradients, zero AI slop, zero cluttered navbars.
"""

import html as _html
from config import BRAND_NAME, APP_BASE_URL, ADSENSE_CLIENT_ID, get_bot_username, SUPPORT_USERNAME, get_store_channel


BRAND_MARK_SVG = (
    '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" aria-hidden="true">'
    '<rect x="2" y="2" width="20" height="20" rx="5" fill="#0A0A0A"/>'
    '<rect x="5.5" y="6" width="5" height="12" rx="1.2" fill="#FFFFFF"/>'
    '<rect x="13" y="6" width="5.5" height="5.2" rx="1.2" fill="#FF5A1F"/>'
    '<rect x="13" y="12.8" width="5.5" height="5.2" rx="1.2" fill="#FFFFFF"/>'
    '</svg>'
)

BRAND_MARK_LIGHT_SVG = (
    '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" aria-hidden="true">'
    '<rect x="2" y="2" width="20" height="20" rx="5" fill="#FFFFFF"/>'
    '<rect x="5.5" y="6" width="5" height="12" rx="1.2" fill="#0A0A0A"/>'
    '<rect x="13" y="6" width="5.5" height="5.2" rx="1.2" fill="#FF5A1F"/>'
    '<rect x="13" y="12.8" width="5.5" height="5.2" rx="1.2" fill="#0A0A0A"/>'
    '</svg>'
)

FAVICON_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">'
    '<rect width="64" height="64" rx="14" fill="#0A0A0A"/>'
    '<rect x="15" y="16" width="13" height="32" rx="3" fill="#FFFFFF"/>'
    '<rect x="34" y="16" width="15" height="14" rx="3" fill="#FF5A1F"/>'
    '<rect x="34" y="34" width="15" height="14" rx="3" fill="#FFFFFF"/>'
    '</svg>'
)


def get_fonts_head_html() -> str:
    return (
        '<link rel="preconnect" href="https://fonts.googleapis.com">\n'
        '    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
        '    <link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=Instrument+Serif:ital@0;1&family=Inter+Tight:wght@500;600;700&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">'
    )


def get_verification_head_html() -> str:
    return (
        '<meta name="google-site-verification" content="EW0VY9fhYQ7yzwrd8oqani_iNoDbRELBOsbpy4c2xUU">\n'
        '    <meta name="google-site-verification" content="XSrhQq7tmTEbP4JLXAoPNIHfK3gZkuoZWCQi-_51dYk">'
    )


def get_adsense_head_html() -> str:
    cid = _html.escape(ADSENSE_CLIENT_ID)
    return (
        f'<meta name="google-adsense-account" content="{cid}">\n'
        f'    <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={cid}" crossorigin="anonymous"></script>'
    )


def get_editorial_base_css() -> str:
    return """
:root {
    --bg: #F5F5F4;
    --surface: #FFFFFF;
    --surface-subtle: #FAFAF9;
    --ink: #0A0A0A;
    --ink-2: #404040;
    --muted: #737373;
    --border: #E5E5E5;
    --border-strong: #D4D4D4;
    --accent: #FF5A1F;
    --accent-hover: #E04812;
    --accent-soft: #FFF1EB;
    --ok: #15803D;
    --ok-soft: #DCFCE7;
    --warn: #B45309;
    --warn-soft: #FEF3C7;
    --err: #DC2626;
    --err-soft: #FEE2E2;
    --code-bg: #0E0E10;
    --code-ink: #F4F4F5;
    --font-sans: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    --font-display: 'Inter Tight', 'Inter', -apple-system, sans-serif;
    --font-serif: 'Instrument Serif', Georgia, serif;
    --font-mono: 'IBM Plex Mono', ui-monospace, monospace;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
html { scroll-behavior: smooth; }
body {
    background: var(--bg);
    color: var(--ink);
    font-family: var(--font-sans);
    font-size: 15px;
    line-height: 1.6;
    min-height: 100vh;
    -webkit-font-smoothing: antialiased;
    overflow-x: hidden;
}
a { color: inherit; }
button, input, select, textarea { font: inherit; }
:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
.md-container { max-width: 1120px; margin: 0 auto; padding: 0 24px; }
.md-nav {
    position: sticky; top: 0; z-index: 40;
    height: 56px;
    background: rgba(245, 245, 244, 0.9);
    backdrop-filter: blur(10px);
    border-bottom: 1px solid var(--border);
}
.md-nav-inner {
    max-width: 1120px; margin: 0 auto; padding: 0 24px; height: 100%;
    display: grid; grid-template-columns: 1fr auto 1fr; align-items: center; gap: 12px;
}
.md-brand {
    display: inline-flex; align-items: center; gap: 10px;
    text-decoration: none; font-family: var(--font-display);
    font-weight: 700; font-size: 16px; letter-spacing: -0.02em; color: var(--ink);
}
.md-nav-links {
    display: inline-flex; align-items: center; gap: 6px;
    background: var(--surface); border: 1px solid var(--border);
    padding: 3px; border-radius: 999px;
}
.md-nav-link {
    text-decoration: none; font-size: 13px; font-weight: 500;
    color: var(--muted); padding: 5px 12px; border-radius: 999px;
    transition: background-color 0.15s ease, color 0.15s ease;
    white-space: nowrap;
}
.md-nav-link:hover { color: var(--ink); }
.md-nav-link.active { background: var(--ink); color: #FFFFFF; }
.md-nav-right { display: flex; align-items: center; justify-content: flex-end; gap: 8px; }
.md-btn {
    display: inline-flex; align-items: center; justify-content: center; gap: 8px;
    padding: 8px 16px; border-radius: 999px; font-size: 13px; font-weight: 600;
    text-decoration: none; border: 1px solid var(--border-strong);
    background: var(--surface); color: var(--ink); cursor: pointer;
    transition: transform 0.2s cubic-bezier(0.2, 0.8, 0.2, 1), background-color 0.15s ease, border-color 0.15s ease;
}
.md-btn:hover { transform: translateY(-1px); border-color: var(--ink); }
.md-btn-primary {
    background: var(--ink); color: #FFFFFF; border-color: var(--ink);
}
.md-btn-primary:hover { background: #262626; border-color: #262626; }
.md-btn-accent {
    background: var(--accent); color: #FFFFFF; border-color: var(--accent);
}
.md-btn-accent:hover { background: var(--accent-hover); border-color: var(--accent-hover); }
.md-eyebrow {
    display: inline-flex; align-items: center; gap: 8px;
    font-family: var(--font-mono); font-size: 11px; font-weight: 500;
    text-transform: uppercase; letter-spacing: 0.08em;
    color: var(--ink-2); background: var(--surface);
    border: 1px solid var(--border); border-radius: 4px; padding: 4px 10px;
}
.md-eyebrow-dot { width: 6px; height: 6px; border-radius: 999px; background: var(--accent); }
.md-card {
    background: var(--surface); border: 1px solid var(--border);
    border-radius: 14px; padding: 24px;
}
.md-serif-em { font-family: var(--font-serif); font-style: italic; font-weight: 400; }
.md-footer {
    border-top: 1px solid var(--border); margin-top: 72px; padding: 28px 0 40px;
    font-size: 13px; color: var(--muted);
}
.md-footer-inner {
    max-width: 1120px; margin: 0 auto; padding: 0 24px;
    display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; gap: 16px;
}
.md-footer-links { display: flex; flex-wrap: wrap; gap: 18px; }
.md-footer-links a { text-decoration: none; color: var(--muted); }
.md-footer-links a:hover { color: var(--ink); }
@media (max-width: 780px) {
    .md-nav-inner { grid-template-columns: auto 1fr; }
    .md-nav-links { display: none; }
}
@media (prefers-reduced-motion: reduce) {
    *, *::before, *::after { animation-duration: 0.01ms !important; transition-duration: 0.01ms !important; }
}
"""


def get_obsidian_base_css() -> str:
    return """
:root {
    --bg: #000000;
    --surface: #0E0E10;
    --surface-2: #16161A;
    --ink: #FFFFFF;
    --ink-2: #D4D4D8;
    --muted: #8E8E93;
    --border: rgba(255, 255, 255, 0.12);
    --border-strong: rgba(255, 255, 255, 0.24);
    --accent: #FF5A1F;
    --accent-soft: rgba(255, 90, 31, 0.14);
    --ok: #22C55E;
    --warn: #F59E0B;
    --err: #EF4444;
    --font-sans: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    --font-display: 'Inter Tight', 'Inter', -apple-system, sans-serif;
    --font-serif: 'Instrument Serif', Georgia, serif;
    --font-mono: 'IBM Plex Mono', ui-monospace, monospace;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
    background: var(--bg);
    color: var(--ink);
    font-family: var(--font-sans);
    font-size: 14px;
    line-height: 1.55;
    min-height: 100vh;
    -webkit-font-smoothing: antialiased;
    overflow-x: hidden;
}
a { color: inherit; }
button, input, select, textarea { font: inherit; }
:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
@media (prefers-reduced-motion: reduce) {
    *, *::before, *::after { animation-duration: 0.01ms !important; transition-duration: 0.01ms !important; }
}
"""


def render_editorial_navbar(active: str = "", right_html: str = "") -> str:
    brand = _html.escape(BRAND_NAME)
    nav_items = [
        ("/", "Home", "home"),
        ("/studio", "Studio", "studio"),
        ("/docs", "API", "docs"),
        ("/captcha", "Captcha", "captcha"),
    ]
    links_html = "".join(
        f'<a class="md-nav-link{" active" if active == key else ""}" href="{href}">{label}</a>'
        for href, label, key in nav_items
    )
    if not right_html:
        right_html = '<a class="md-btn md-btn-primary" href="/studio">Open Studio</a>'
    return (
        '<header class="md-nav">'
        '<div class="md-nav-inner">'
        f'<a class="md-brand" href="/">{BRAND_MARK_SVG}<span>{brand}</span></a>'
        f'<nav class="md-nav-links" aria-label="Primary">{links_html}</nav>'
        f'<div class="md-nav-right">{right_html}</div>'
        '</div>'
        '</header>'
    )


def render_editorial_footer() -> str:
    brand = _html.escape(BRAND_NAME)
    domain = _html.escape(APP_BASE_URL.split("://", 1)[-1].split("/", 1)[0])
    bot_u = _html.escape(get_bot_username())
    sup_u = _html.escape(SUPPORT_USERNAME)
    ch_clean = get_store_channel().lstrip("@").strip()
    ch_link = ""
    if ch_clean and not ch_clean.lstrip("-").isdigit():
        ch_esc = _html.escape(ch_clean)
        ch_link = f'<a href="https://t.me/{ch_esc}" target="_blank" rel="noopener noreferrer">@{ch_esc}</a>'
    return (
        '<footer class="md-footer">'
        '<div class="md-footer-inner">'
        f'<div>&copy; 2026 {brand} &middot; <code>{domain}</code></div>'
        '<div class="md-footer-links">'
        '<a href="/privacy">Privacy Policy</a>'
        '<a href="/terms">Terms of Service</a>'
        '<a href="/docs">API Docs</a>'
        '<a href="/captcha">Shield Captcha</a>'
        f'<a href="https://t.me/{bot_u}" target="_blank" rel="noopener noreferrer">@{bot_u}</a>'
        f'{ch_link}'
        f'<a href="https://t.me/{sup_u}" target="_blank" rel="noopener noreferrer">Support</a>'
        '</div>'
        '</div>'
        '</footer>'
    )
