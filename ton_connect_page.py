"""
TON Connect WebApp Interface & Manifest Provider.
Implements TonConnect UI SDK for Telegram Mini App with zero-friction wallet integration.
Supports: Telegram Wallet (@wallet), Tonkeeper, MyTonWallet, OpenMask.
"""

import json
import re
from urllib.parse import urlparse


_SAFE_HOST_RE = re.compile(r"^[A-Za-z0-9.\-:]+$")


def _sanitize_base_url(base_url: str, fallback: str = "") -> str:
    """Validate base_url to strictly allow safe http(s) origins (prevents XSS/Host-header injection)."""
    raw = str(base_url or "").strip().rstrip("/")
    if not raw:
        return fallback
    try:
        parsed = urlparse(raw)
        if parsed.scheme not in ("http", "https"):
            return fallback
        if parsed.path or parsed.params or parsed.query or parsed.fragment or parsed.username or parsed.password:
            return fallback
        if not parsed.netloc or not _SAFE_HOST_RE.match(parsed.netloc):
            return fallback
        return f"{parsed.scheme}://{parsed.netloc}"
    except Exception:
        return fallback


def _safe_json_for_script(obj) -> str:
    """Serialize JSON safely for embedding inside an HTML <script> block."""
    raw = json.dumps(obj, default=str, ensure_ascii=False)
    return (
        raw.replace("&", "\\u0026")
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )


def get_ton_manifest(base_url: str = "") -> dict:
    """TON Connect manifest JSON"""
    from config import APP_BASE_URL, BRAND_NAME
    clean_url = _sanitize_base_url(base_url, fallback=APP_BASE_URL)
    return {
        "url": clean_url,
        "name": f"{BRAND_NAME} Studio",
        "iconUrl": f"{clean_url}/favicon.svg",
        "termsOfServiceUrl": f"{clean_url}/terms",
        "privacyPolicyUrl": f"{clean_url}/privacy"
    }


def get_ton_connect_html(user_id: int = 0, current_wallet: dict = None, base_url: str = "") -> str:
    """
    Obsidian Monochrome Telegram Mini App for TON Connect (@tonconnect/ui).
    """
    from config import BRAND_NAME
    from ui_theme import get_obsidian_base_css
    clean_base = _sanitize_base_url(base_url, fallback="")
    manifest_url = f"{clean_base}/tonconnect-manifest.json" if clean_base else "/tonconnect-manifest.json"

    try:
        safe_uid = int(user_id or 0)
    except (TypeError, ValueError):
        safe_uid = 0

    wallet_dict = current_wallet if isinstance(current_wallet, dict) else {}
    current_addr = str(wallet_dict.get("wallet_address", "") or "").strip()
    current_name = str(wallet_dict.get("wallet_name", "") or "").strip()

    init_config_json = _safe_json_for_script({
        "userId": safe_uid,
        "currentAddr": current_addr,
        "currentName": current_name,
        "manifestUrl": manifest_url,
    })

    html = f"""<!DOCTYPE html>
<html lang="uz">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TON Connect | {BRAND_NAME}</title>
    <link rel="icon" href="/favicon.svg" type="image/svg+xml">
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <script src="https://unpkg.com/@tonconnect/ui@2.0.9/dist/tonconnect-ui.min.js" crossorigin="anonymous"></script>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=Inter+Tight:wght@600;700&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
    <style>
        {get_obsidian_base_css()}
        :root {{
            --ton-blue: #FFFFFF;
            --ton-light: #FFFFFF;
            --ton-dark: #D4D4D8;
            --bg-dark: #000000;
            --card-bg: #0E0E10;
            --card-border: rgba(255, 255, 255, 0.12);
            --text-main: #FFFFFF;
            --text-muted: #8E8E93;
            --emerald: #22C55E;
            --rose: #EF4444;
        }}
        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            -webkit-tap-highlight-color: transparent;
        }}
        body {{
            background: #000000;
            color: var(--text-main);
            font-family: var(--font-sans);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            padding: 24px 16px 40px;
            overflow-x: hidden;
        }}
        .bg-glow {{ display: none; }}
        .container {{
            width: 100%;
            max-width: 440px;
            z-index: 1;
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 20px;
        }}
        .header {{
            text-align: center;
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 8px;
        }}
        .logo-wrap {{
            width: 64px;
            height: 64px;
            border-radius: 16px;
            background: #0E0E10;
            border: 1px solid rgba(255,255,255,0.16);
            color: #FF5A1F;
            display: flex;
            align-items: center;
            justify-content: center;
            margin-bottom: 4px;
        }}
        .logo-wrap svg {{
            width: 34px;
            height: 34px;
        }}
        h1 {{
            font-family: var(--font-display);
            font-size: 24px;
            font-weight: 700;
            letter-spacing: -0.02em;
            color: #FFFFFF;
        }}
        .subtitle {{
            font-size: 13px;
            color: var(--text-muted);
            max-width: 320px;
            line-height: 1.45;
        }}
        .status-badge {{
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 6px 14px;
            border-radius: 999px;
            font-family: var(--font-mono);
            font-size: 11px;
            font-weight: 600;
            background: #0E0E10;
            border: 1px solid var(--card-border);
            margin-top: 4px;
        }}
        .status-dot {{
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: #71717A;
        }}
        .status-badge.connected {{
            background: rgba(34, 197, 94, 0.12);
            border-color: rgba(34, 197, 94, 0.35);
            color: #4ADE80;
        }}
        .status-badge.connected .status-dot {{
            background: var(--emerald);
        }}
        .card {{
            width: 100%;
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 16px;
            padding: 20px;
            display: flex;
            flex-direction: column;
            gap: 16px;
        }}
        .info-row {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 13px;
        }}
        .info-label {{ color: var(--text-muted); }}
        .info-val {{ font-weight: 600; color: var(--text-main); }}
        .address-box {{
            background: #000000;
            border: 1px solid var(--card-border);
            border-radius: 12px;
            padding: 12px;
            font-family: var(--font-mono);
            font-size: 12px;
            word-break: break-all;
            color: #FFFFFF;
            display: flex;
            flex-direction: column;
            gap: 8px;
        }}
        .address-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 11px;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.06em;
        }}
        .btn-copy {{
            background: #16161A;
            border: 1px solid var(--card-border);
            color: #FFFFFF;
            padding: 4px 8px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 11px;
        }}
        .btn-copy:active {{ background: #FF5A1F; border-color: #FF5A1F; }}
        .tc-btn-container {{
            width: 100%;
            display: flex;
            justify-content: center;
            min-height: 48px;
        }}
        .btn {{
            width: 100%;
            padding: 13px;
            border-radius: 12px;
            border: none;
            font-size: 14px;
            font-weight: 600;
            font-family: inherit;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
        }}
        .btn-primary {{
            background: #FF5A1F;
            color: #FFFFFF;
        }}
        .btn-danger {{
            background: rgba(239, 68, 68, 0.14);
            border: 1px solid rgba(239, 68, 68, 0.35);
            color: #FCA5A5;
        }}
        .btn:disabled {{ opacity: 0.55; cursor: not-allowed; }}
        .btn:focus-visible, .btn-copy:focus-visible {{ outline: 2px solid #FF5A1F; outline-offset: 2px; }}
        .features {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; width: 100%; }}
        @media (max-width: 360px) {{ .features {{ grid-template-columns: 1fr; }} }}
        .feat-item {{
            background: #0E0E10;
            border: 1px solid var(--card-border);
            border-radius: 12px;
            padding: 12px;
            font-size: 12px;
            display: flex;
            flex-direction: column;
            gap: 4px;
        }}
        .feat-title {{ font-weight: 600; color: #fff; display: flex; align-items: center; gap: 4px; }}
        .feat-desc {{ color: var(--text-muted); font-size: 11px; line-height: 1.35; }}
        .toast {{
            position: fixed; bottom: 24px; background: #16161A; color: #fff;
            padding: 12px 20px; border-radius: 12px; font-size: 13px; font-weight: 600;
            border: 1px solid var(--card-border); transform: translateY(100px); opacity: 0;
            transition: all 0.25s ease; z-index: 100; pointer-events: none;
        }}
        .toast.show {{ transform: translateY(0); opacity: 1; }}
    </style>
</head>
<body>
    <div class="bg-glow"></div>
    <div class="container">
        <div class="header">
            <div class="logo-wrap">
                <svg viewBox="0 0 24 24">
                    <path d="M12 2L2 9.5L12 22L22 9.5L12 2Z" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/>
                    <path d="M2 9.5H22M12 2V22M7 15.5L12 9.5L17 15.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
            </div>
            <h1>{BRAND_NAME} TON Connect</h1>
            <p class="subtitle">Telegram Wallet, Tonkeeper yoki MyTonWallet hamyoningizni xavfsiz ulang</p>
            <div id="statusBadge" class="status-badge">
                <div class="status-dot"></div>
                <span id="statusText">Hamyon ulanmagan</span>
            </div>
        </div>

        <div class="card">
            <!-- TON Connect UI tugmasi joylashuvi -->
            <div id="ton-connect-btn" class="tc-btn-container"></div>

            <div id="walletDetails" style="display: none; flex-direction: column; gap: 14px;">
                <div class="info-row">
                    <span class="info-label">Tarmoq</span>
                    <span class="info-val" style="color: var(--emerald);">● TON Mainnet</span>
                </div>
                <div class="info-row">
                    <span class="info-label">Ilova</span>
                    <span id="walletAppName" class="info-val">Tonkeeper</span>
                </div>

                <div class="address-box">
                    <div class="address-header">
                        <span>Hamyon Manzili</span>
                        <button type="button" class="btn-copy" onclick="copyAddress()">Nusxa olish</button>
                    </div>
                    <span id="fullAddress">UQ...</span>
                </div>

                <button type="button" id="saveWalletBtn" class="btn btn-primary" onclick="saveToBot(true)">
                    <span style="display: inline-flex; align-items: center; justify-content: center; gap: 8px;">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>
                        <span id="saveWalletBtnText">Hamyonni Botga Saqlash</span>
                    </span>
                </button>

                <button type="button" id="disconnectWalletBtn" class="btn btn-danger" onclick="disconnectWallet()">
                    <span style="display: inline-flex; align-items: center; justify-content: center; gap: 8px;">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
                        <span id="disconnectWalletBtnText">Hamyonni Uzish</span>
                    </span>
                </button>
            </div>
        </div>

        <div class="features">
            <div class="feat-item">
                <div class="feat-title" style="display: flex; align-items: center; gap: 8px;">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#FF5A1F" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="1" y="4" width="22" height="16" rx="2" ry="2"></rect><line x1="1" y1="10" x2="23" y2="10"></line></svg>
                    Tezkor Cashout
                </div>
                <div class="feat-desc">Pul yechishda manzilni qo'lda kiritish shart emas.</div>
            </div>
            <div class="feat-item">
                <div class="feat-title" style="display: flex; align-items: center; gap: 8px;">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#22C55E" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect><path d="M7 11V7a5 5 0 0 1 10 0v4"></path></svg>
                    100% Xavfsiz
                </div>
                <div class="feat-desc">Maxfiy kalitlar (seed phrase) hech qachon chiqmaydi.</div>
            </div>
            <div class="feat-item">
                <div class="feat-title" style="display: flex; align-items: center; gap: 8px;">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#FFFFFF" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect><circle cx="8.5" cy="8.5" r="1.5"></circle><polyline points="21 15 16 10 5 21"></polyline></svg>
                    3D NFT Lazy Mint
                </div>
                <div class="feat-desc">NFT laringiz bevosita o'zingizga tegishli bo'ladi.</div>
            </div>
            <div class="feat-item">
                <div class="feat-title" style="display: flex; align-items: center; gap: 8px;">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#F59E0B" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon></svg>
                    Avtomatik
                </div>
                <div class="feat-desc">Referal va YouTube daromadlarini to'g'ridan-to'g'ri qabul qiling.</div>
            </div>
        </div>
    </div>

    <div id="toast" class="toast" role="status" aria-live="polite"></div>

    <script>
        const TON_CONFIG = {init_config_json};
        const tg = window.Telegram ? window.Telegram.WebApp : null;
        if (tg) {{
            tg.ready();
            tg.expand();
            try {{
                tg.setHeaderColor('#06090e');
                tg.setBackgroundColor('#06090e');
            }} catch (e) {{}}
        }}

        const USER_ID = (tg && tg.initDataUnsafe && tg.initDataUnsafe.user && parseInt(tg.initDataUnsafe.user.id, 10)) || parseInt(TON_CONFIG.userId, 10) || 0;
        let currentConnectedAddress = String(TON_CONFIG.currentAddr || "");
        let currentConnectedName = String(TON_CONFIG.currentName || "");
        let toastTimer = null;
        let isBusy = false;

        const manifestUrl = String(TON_CONFIG.manifestUrl || "/tonconnect-manifest.json");
        let tonConnectUI = null;

        function getTonAuthHeaders() {{
            const headers = {{ 'Content-Type': 'application/json' }};
            if (tg && tg.initData) {{
                headers['X-Telegram-Init-Data'] = tg.initData;
            }}
            return headers;
        }}

        function showToast(msg, isError = false) {{
            const t = document.getElementById('toast');
            if (!t) return;
            if (toastTimer) clearTimeout(toastTimer);
            t.innerText = String(msg || "");
            t.style.borderColor = isError ? 'var(--rose)' : 'var(--emerald)';
            t.classList.add('show');
            toastTimer = setTimeout(() => t.classList.remove('show'), 3500);
        }}

        function setButtonsDisabled(disabled) {{
            isBusy = disabled;
            const saveBtn = document.getElementById('saveWalletBtn');
            const discBtn = document.getElementById('disconnectWalletBtn');
            if (saveBtn) saveBtn.disabled = disabled;
            if (discBtn) discBtn.disabled = disabled;
        }}

        function updateUI(wallet) {{
            const badge = document.getElementById('statusBadge');
            const statusText = document.getElementById('statusText');
            const details = document.getElementById('walletDetails');
            const fullAddr = document.getElementById('fullAddress');
            const appName = document.getElementById('walletAppName');

            if (wallet) {{
                badge.classList.add('connected');
                const rawAddr = wallet.account ? wallet.account.address : (wallet.address || '');
                currentConnectedAddress = rawAddr;
                currentConnectedName = wallet.device ? wallet.device.appName : (wallet.name || 'TON Wallet');

                statusText.innerText = "Ulangan: " + currentConnectedName;
                appName.innerText = currentConnectedName;
                fullAddr.innerText = rawAddr;
                details.style.display = 'flex';
            }} else if (currentConnectedAddress) {{
                badge.classList.add('connected');
                statusText.innerText = "Ulangan: " + (currentConnectedName || 'TON Wallet');
                appName.innerText = currentConnectedName || 'TON Wallet';
                fullAddr.innerText = currentConnectedAddress;
                details.style.display = 'flex';
            }} else {{
                badge.classList.remove('connected');
                statusText.innerText = "Hamyon ulanmagan";
                details.style.display = 'none';
            }}
        }}

        if (window.TON_CONNECT_UI && window.TON_CONNECT_UI.TonConnectUI) {{
            tonConnectUI = new window.TON_CONNECT_UI.TonConnectUI({{
                manifestUrl: manifestUrl,
                buttonRootId: 'ton-connect-btn'
            }});

            // Subscribe to wallet changes
            tonConnectUI.onStatusChange(async (wallet) => {{
                if (wallet) {{
                    updateUI(wallet);
                    await saveToBot(false);
                }} else {{
                    updateUI(null);
                }}
            }});
        }} else {{
            const btnRoot = document.getElementById('ton-connect-btn');
            if (btnRoot) {{
                const errEl = document.createElement('div');
                errEl.style.cssText = 'color: var(--rose); font-size: 13px; text-align: center; padding: 10px;';
                errEl.textContent = "TON Connect SDK yuklanmadi. Internet aloqasini tekshirib sahifani yangilang.";
                btnRoot.appendChild(errEl);
            }}
        }}

        // If backend already had wallet saved, show it initially
        if (currentConnectedAddress) {{
            updateUI({{ address: currentConnectedAddress, name: currentConnectedName }});
        }}

        async function saveToBot(manual = false) {{
            if (isBusy) return;
            if (!currentConnectedAddress) {{
                showToast("Avval hamyonni ulang!", true);
                return;
            }}

            setButtonsDisabled(true);
            const saveTxt = document.getElementById('saveWalletBtnText');
            if (saveTxt) saveTxt.textContent = "Saqlanmoqda...";

            try {{
                const bodyPayload = {{
                    user_id: USER_ID,
                    address: currentConnectedAddress,
                    wallet_name: currentConnectedName,
                    chain: 'mainnet'
                }};
                if (tg && tg.initData) {{
                    bodyPayload.initData = tg.initData;
                }}

                const res = await fetch('/api/tonconnect/save', {{
                    method: 'POST',
                    headers: getTonAuthHeaders(),
                    credentials: 'same-origin',
                    body: JSON.stringify(bodyPayload)
                }});
                let data = {{ ok: false, message: `Server xatosi (HTTP ${{res.status}})` }};
                try {{
                    data = await res.json();
                }} catch (parseErr) {{}}

                if (res.ok && data.ok) {{
                    showToast(manual ? "Hamyon botga saqlandi!" : "Hamyon muvaffaqiyatli ulandi va saqlandi!");
                    if (tg) {{
                        try {{
                            tg.sendData(JSON.stringify({{
                                action: "ton_connected",
                                address: currentConnectedAddress,
                                wallet: currentConnectedName
                            }}));
                        }} catch (e) {{
                            console.log("sendData ignored for inline webapp");
                        }}
                        if (manual) {{
                            setTimeout(() => tg.close(), 1200);
                        }}
                    }}
                }} else {{
                    showToast(data.message || data.error || "Saqlashda xatolik", true);
                }}
            }} catch (err) {{
                console.error("Save error:", err);
                showToast("Aloqa xatosi: " + (err?.message || "Tarmoq xatosi"), true);
            }} finally {{
                setButtonsDisabled(false);
                if (saveTxt) saveTxt.textContent = "Hamyonni Botga Saqlash";
            }}
        }}

        async function disconnectWallet() {{
            if (isBusy) return;
            setButtonsDisabled(true);
            const discTxt = document.getElementById('disconnectWalletBtnText');
            if (discTxt) discTxt.textContent = "Uzilmoqda...";

            try {{
                if (tonConnectUI && tonConnectUI.connected) {{
                    try {{
                        await tonConnectUI.disconnect();
                    }} catch (sdkErr) {{
                        console.warn("TON Connect SDK disconnect warning:", sdkErr);
                    }}
                }}
                if (USER_ID) {{
                    const bodyPayload = {{ user_id: USER_ID }};
                    if (tg && tg.initData) {{
                        bodyPayload.initData = tg.initData;
                    }}
                    const res = await fetch('/api/tonconnect/disconnect', {{
                        method: 'POST',
                        headers: getTonAuthHeaders(),
                        credentials: 'same-origin',
                        body: JSON.stringify(bodyPayload)
                    }});
                    let data = {{ ok: false, message: `Server xatosi (HTTP ${{res.status}})` }};
                    try {{
                        data = await res.json();
                    }} catch (parseErr) {{}}
                    if (!res.ok || !data.ok) {{
                        showToast(data.message || data.error || "Serverdan uzishda xatolik", true);
                        return;
                    }}
                }}
                currentConnectedAddress = "";
                currentConnectedName = "";
                updateUI(null);
                showToast("Hamyon uzildi");
            }} catch (e) {{
                console.error(e);
                showToast("Uzishda xatolik", true);
            }} finally {{
                setButtonsDisabled(false);
                if (discTxt) discTxt.textContent = "Hamyonni Uzish";
            }}
        }}

        function copyAddress() {{
            if (!currentConnectedAddress) return;
            if (navigator.clipboard && navigator.clipboard.writeText) {{
                navigator.clipboard.writeText(currentConnectedAddress).then(() => {{
                    showToast("Manzil nusxalandi!");
                }}).catch(() => {{
                    fallbackCopy(currentConnectedAddress);
                }});
            }} else {{
                fallbackCopy(currentConnectedAddress);
            }}
        }}

        function fallbackCopy(text) {{
            try {{
                const ta = document.createElement('textarea');
                ta.value = text;
                ta.style.position = 'fixed';
                ta.style.opacity = '0';
                document.body.appendChild(ta);
                ta.focus();
                ta.select();
                const ok = document.execCommand('copy');
                document.body.removeChild(ta);
                showToast(ok ? "Manzil nusxalandi!" : "Nusxalab bo'lmadi", !ok);
            }} catch (e) {{
                showToast("Nusxalab bo'lmadi", true);
            }}
        }}
    </script>
</body>
</html>
"""
    return html
