"""
TON Connect WebApp Interface & Manifest Provider.
Implements TonConnect UI SDK for Telegram Mini App with zero-friction wallet integration.
Supports: Telegram Wallet (@wallet), Tonkeeper, MyTonWallet, OpenMask.
"""

import json


def get_ton_manifest(base_url: str = "https://t.me") -> dict:
    """TON Connect manifest JSON"""
    clean_url = base_url.rstrip("/")
    return {
        "url": clean_url,
        "name": "AutoReply & YouTube Studio",
        "iconUrl": "https://cdn-icons-png.flaticon.com/512/2111/2111646.png",
        "termsOfServiceUrl": f"{clean_url}/terms",
        "privacyPolicyUrl": f"{clean_url}/privacy"
    }


def get_ton_connect_html(user_id: int = 0, current_wallet: dict = None, base_url: str = "") -> str:
    """
    Stunning, ultra-modern Cyberpunk / Web3 Telegram Mini App for TON Connect.
    Uses @tonconnect/ui CDN and Telegram WebApp SDK.
    """
    clean_base = base_url.rstrip("/") if base_url else ""
    manifest_url = f"{clean_base}/tonconnect-manifest.json" if clean_base else "/tonconnect-manifest.json"
    
    current_addr = current_wallet.get("wallet_address", "") if current_wallet else ""
    current_name = current_wallet.get("wallet_name", "") if current_wallet else ""

    html = f"""<!DOCTYPE html>
<html lang="uz">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>TON Connect | AutoReply</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <script src="https://unpkg.com/@tonconnect/ui@latest/dist/tonconnect-ui.min.js"></script>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
    <style>
        :root {{
            --ton-blue: #0098EA;
            --ton-light: #45B6F7;
            --ton-dark: #0077B5;
            --bg-dark: #06090e;
            --card-bg: rgba(13, 20, 32, 0.75);
            --card-border: rgba(0, 152, 234, 0.25);
            --text-main: #f1f5f9;
            --text-muted: #94a3b8;
            --emerald: #10b981;
            --rose: #f43f5e;
        }}
        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            -webkit-tap-highlight-color: transparent;
        }}
        body {{
            background: radial-gradient(circle at 50% 0%, #0d2238 0%, var(--bg-dark) 70%);
            color: var(--text-main);
            font-family: 'Outfit', -apple-system, sans-serif;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            padding: 24px 16px 40px;
            overflow-x: hidden;
        }}
        .bg-glow {{
            position: fixed;
            top: -100px;
            left: 50%;
            transform: translateX(-50%);
            width: 320px;
            height: 320px;
            background: radial-gradient(circle, rgba(0,152,234,0.3) 0%, transparent 70%);
            pointer-events: none;
            z-index: 0;
        }}
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
            width: 72px;
            height: 72px;
            border-radius: 22px;
            background: linear-gradient(135deg, rgba(0,152,234,0.2) 0%, rgba(69,182,247,0.05) 100%);
            border: 1px solid rgba(0,152,234,0.4);
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 0 25px rgba(0,152,234,0.3);
            margin-bottom: 4px;
            animation: pulse-glow 3s infinite alternate;
        }}
        @keyframes pulse-glow {{
            0% {{ box-shadow: 0 0 15px rgba(0,152,234,0.2); transform: scale(1); }}
            100% {{ box-shadow: 0 0 35px rgba(0,152,234,0.5); transform: scale(1.03); }}
        }}
        .logo-wrap svg {{
            width: 42px;
            height: 42px;
            fill: var(--ton-blue);
        }}
        h1 {{
            font-size: 24px;
            font-weight: 800;
            letter-spacing: -0.5px;
            background: linear-gradient(135deg, #ffffff 40%, var(--ton-light) 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        .subtitle {{
            font-size: 13px;
            color: var(--text-muted);
            max-width: 300px;
            line-height: 1.4;
        }}
        .status-badge {{
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 6px 14px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
            background: rgba(255, 255, 255, 0.04);
            border: 1px solid rgba(255, 255, 255, 0.08);
            margin-top: 4px;
        }}
        .status-dot {{
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: #64748b;
        }}
        .status-badge.connected {{
            background: rgba(16, 185, 129, 0.12);
            border-color: rgba(16, 185, 129, 0.3);
            color: #34d399;
        }}
        .status-badge.connected .status-dot {{
            background: var(--emerald);
            box-shadow: 0 0 8px var(--emerald);
        }}
        .card {{
            width: 100%;
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 20px;
            padding: 20px;
            backdrop-filter: blur(16px);
            -webkit-backdrop-filter: blur(16px);
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
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
        .info-label {{
            color: var(--text-muted);
        }}
        .info-val {{
            font-weight: 600;
            color: var(--text-main);
        }}
        .address-box {{
            background: rgba(0, 0, 0, 0.4);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 12px;
            padding: 12px;
            font-family: 'JetBrains Mono', monospace;
            font-size: 12px;
            word-break: break-all;
            color: var(--ton-light);
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
            font-family: 'Outfit', sans-serif;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        .btn-copy {{
            background: rgba(255, 255, 255, 0.08);
            border: none;
            color: var(--text-main);
            padding: 4px 8px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 11px;
            transition: all 0.2s;
        }}
        .btn-copy:active {{
            transform: scale(0.95);
            background: var(--ton-blue);
        }}
        .tc-btn-container {{
            width: 100%;
            display: flex;
            justify-content: center;
            min-height: 48px;
        }}
        .btn {{
            width: 100%;
            padding: 14px;
            border-radius: 14px;
            border: none;
            font-size: 14px;
            font-weight: 700;
            font-family: inherit;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            transition: all 0.2s;
        }}
        .btn-primary {{
            background: linear-gradient(135deg, var(--ton-blue) 0%, var(--ton-dark) 100%);
            color: #fff;
            box-shadow: 0 4px 20px rgba(0, 152, 234, 0.4);
        }}
        .btn-primary:active {{
            transform: scale(0.98);
        }}
        .btn-danger {{
            background: rgba(244, 63, 94, 0.12);
            border: 1px solid rgba(244, 63, 94, 0.3);
            color: var(--rose);
        }}
        .btn-danger:active {{
            background: rgba(244, 63, 94, 0.2);
            transform: scale(0.98);
        }}
        .features {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
            width: 100%;
        }}
        .feat-item {{
            background: rgba(255, 255, 255, 0.02);
            border: 1px solid rgba(255, 255, 255, 0.05);
            border-radius: 14px;
            padding: 12px;
            font-size: 12px;
            display: flex;
            flex-direction: column;
            gap: 4px;
        }}
        .feat-title {{
            font-weight: 700;
            color: #fff;
            display: flex;
            align-items: center;
            gap: 4px;
        }}
        .feat-desc {{
            color: var(--text-muted);
            font-size: 11px;
            line-height: 1.3;
        }}
        .toast {{
            position: fixed;
            bottom: 24px;
            background: #1e293b;
            color: #fff;
            padding: 12px 20px;
            border-radius: 12px;
            font-size: 13px;
            font-weight: 600;
            box-shadow: 0 10px 30px rgba(0,0,0,0.5);
            border: 1px solid rgba(255,255,255,0.1);
            transform: translateY(100px);
            opacity: 0;
            transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
            z-index: 100;
            pointer-events: none;
        }}
        .toast.show {{
            transform: translateY(0);
            opacity: 1;
        }}
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
            <h1>TON Connect Studio</h1>
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
                        <button class="btn-copy" onclick="copyAddress()">Nusxa olish</button>
                    </div>
                    <span id="fullAddress">UQ...</span>
                </div>

                <button class="btn btn-primary" onclick="saveToBot(true)">
                    <span>✅ Hamyonni Botga Saqlash</span>
                </button>

                <button class="btn btn-danger" onclick="disconnectWallet()">
                    <span>❌ Hamyonni Uzish</span>
                </button>
            </div>
        </div>

        <div class="features">
            <div class="feat-item">
                <div class="feat-title">💸 Tezkor Cashout</div>
                <div class="feat-desc">Pul yechishda manzilni qo'lda kiritish shart emas.</div>
            </div>
            <div class="feat-item">
                <div class="feat-title">🔒 100% Xavfsiz</div>
                <div class="feat-desc">Maxfiy kalitlar (seed phrase) hech qachon chiqmaydi.</div>
            </div>
            <div class="feat-item">
                <div class="feat-title">🖼️ 3D NFT Lazy Mint</div>
                <div class="feat-desc">NFT laringiz bevosita o'zingizga tegishli bo'ladi.</div>
            </div>
            <div class="feat-item">
                <div class="feat-title">⚡ Avtomatik</div>
                <div class="feat-desc">Referal va YouTube daromadlarini to'g'ridan-to'g'ri qabul qiling.</div>
            </div>
        </div>
    </div>

    <div id="toast" class="toast"></div>

    <script>
        const tg = window.Telegram ? window.Telegram.WebApp : null;
        if (tg) {{
            tg.ready();
            tg.expand();
            tg.setHeaderColor('#06090e');
            tg.setBackgroundColor('#06090e');
        }}

        const USER_ID = parseInt("{user_id}") || (tg && tg.initDataUnsafe && tg.initDataUnsafe.user ? tg.initDataUnsafe.user.id : 0);
        let currentConnectedAddress = "{current_addr}";
        let currentConnectedName = "{current_name}";

        const manifestUrl = "{manifest_url}";
        const tonConnectUI = new TON_CONNECT_UI.TonConnectUI({{
            manifestUrl: manifestUrl,
            buttonRootId: 'ton-connect-btn'
        }});

        function showToast(msg, isError = false) {{
            const t = document.getElementById('toast');
            t.innerText = msg;
            t.style.borderColor = isError ? 'var(--rose)' : 'var(--emerald)';
            t.classList.add('show');
            setTimeout(() => t.classList.remove('show'), 3500);
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

        // Subscribe to wallet changes
        tonConnectUI.onStatusChange(async (wallet) => {{
            if (wallet) {{
                updateUI(wallet);
                await saveToBot(false);
            }} else {{
                updateUI(null);
            }}
        }});

        // If backend already had wallet saved, show it initially
        if (currentConnectedAddress) {{
            updateUI({{ address: currentConnectedAddress, name: currentConnectedName }});
        }}

        async function saveToBot(manual = false) {{
            if (!currentConnectedAddress) {{
                showToast("Avval hamyonni ulang!", true);
                return;
            }}

            try {{
                const res = await fetch('/api/tonconnect/save', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{
                        user_id: USER_ID,
                        address: currentConnectedAddress,
                        wallet_name: currentConnectedName,
                        chain: 'mainnet'
                    }})
                }});
                const data = await res.json();
                if (data.ok) {{
                    showToast(manual ? "✅ Hamyon botga saqlandi!" : "💎 Hamyon ulandi va saqlandi!");
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
                    showToast(data.message || "Saqlashda xatolik", true);
                }}
            }} catch (err) {{
                console.error("Save error:", err);
                showToast("Aloqa xatosi: " + err.message, true);
            }}
        }}

        async function disconnectWallet() {{
            try {{
                await tonConnectUI.disconnect();
                if (USER_ID) {{
                    await fetch('/api/tonconnect/disconnect', {{
                        method: 'POST',
                        headers: {{ 'Content-Type': 'application/json' }},
                        body: JSON.stringify({{ user_id: USER_ID }})
                    }});
                }}
                currentConnectedAddress = "";
                updateUI(null);
                showToast("Hamyon uzildi");
            }} catch (e) {{
                console.error(e);
                showToast("Uzishda xatolik", true);
            }}
        }}

        function copyAddress() {{
            if (!currentConnectedAddress) return;
            navigator.clipboard.writeText(currentConnectedAddress).then(() => {{
                showToast("Manzil nusxalandi! 📋");
            }}).catch(() => {{
                showToast("Nusxalab bo'lmadi", true);
            }});
        }}
    </script>
</body>
</html>
"""
    return html
