"""
CreatorFlow Studio - Multilingual Legal & Compliance Templates
Google OAuth 2.0 & YouTube Data API Compliant Privacy Policy and Terms of Service.
Supports English (Default), Russian, and Uzbek with instant client-side switching.
"""

def get_privacy_html():
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Privacy Policy | Bot Client</title>
    <meta name="description" content="Privacy Policy for Bot Client (CreatorFlow Studio), detailing Google OAuth 2.0, YouTube Data API usage, data protection, and Google API Services User Data Policy compliance.">
    <meta name="google-site-verification" content="EW0VY9fhYQ7yzwrd8oqani_iNoDbRELBOsbpy4c2xUU">
    <meta name="google-site-verification" content="XSrhQq7tmTEbP4JLXAoPNIHfK3gZkuoZWCQi-_51dYk">
    <script async src="https://www.googletagmanager.com/gtag/js"></script>
    <!-- Google AdSense -->
    <meta name="google-adsense-account" content="ca-pub-4094396006908725">
    <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-4094396006908725" crossorigin="anonymous"></script>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        :root {
            --bg: #090A0F;
            --card-bg: rgba(18, 22, 34, 0.85);
            --card-border: rgba(255, 255, 255, 0.08);
            --accent: #7342E2;
            --accent-glow: rgba(115, 66, 226, 0.35);
            --cyan: #00F0FF;
            --emerald: #10B981;
            --text-main: #F3F4F6;
            --text-muted: #9CA3AF;
            --font: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        }
        body {
            font-family: var(--font);
            background: var(--bg);
            color: var(--text-main);
            min-height: 100vh;
            line-height: 1.65;
            padding: 0 16px 80px;
            overflow-x: hidden;
        }
        .container {
            max-width: 920px;
            margin: 0 auto;
        }
        /* Top Navigation Header */
        header {
            padding: 24px 0 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid var(--card-border);
            margin-bottom: 36px;
        }
        .brand {
            display: flex;
            align-items: center;
            gap: 12px;
            text-decoration: none;
            color: #ffffff;
        }
        .brand-icon {
            width: 38px;
            height: 38px;
            border-radius: 12px;
            background: linear-gradient(135deg, #7342E2, #00F0FF);
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 0 18px var(--accent-glow);
        }
        .brand-text {
            font-size: 20px;
            font-weight: 800;
            letter-spacing: -0.03em;
        }
        .brand-tag {
            font-size: 11px;
            font-weight: 700;
            color: var(--cyan);
            background: rgba(0, 240, 255, 0.12);
            border: 1px solid rgba(0, 240, 255, 0.25);
            padding: 2px 8px;
            border-radius: 999px;
        }
        /* Language Switcher */
        .lang-switch {
            display: flex;
            align-items: center;
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid var(--card-border);
            border-radius: 999px;
            padding: 3px 4px;
            gap: 2px;
        }
        .lang-btn {
            background: transparent;
            border: none;
            color: var(--text-muted);
            padding: 6px 12px;
            border-radius: 999px;
            font-size: 12px;
            font-weight: 700;
            cursor: pointer;
            transition: all 0.2s ease;
        }
        .lang-btn:hover {
            color: #ffffff;
        }
        .lang-btn.active {
            background: var(--accent);
            color: #ffffff;
            box-shadow: 0 2px 8px var(--accent-glow);
        }
        /* Breadcrumb */
        .breadcrumb {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 13px;
            color: var(--text-muted);
            margin-bottom: 24px;
        }
        .breadcrumb a {
            color: var(--cyan);
            text-decoration: none;
        }
        .breadcrumb a:hover {
            text-decoration: underline;
        }
        /* Hero Banner */
        .hero {
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 24px;
            padding: 36px 32px;
            backdrop-filter: blur(20px);
            margin-bottom: 32px;
            position: relative;
            overflow: hidden;
        }
        .hero::before {
            content: '';
            position: absolute;
            top: -40px;
            right: -40px;
            width: 220px;
            height: 220px;
            background: radial-gradient(circle, rgba(115, 66, 226, 0.25) 0%, transparent 70%);
            filter: blur(40px);
            pointer-events: none;
        }
        .badge {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            font-size: 12px;
            font-weight: 700;
            color: var(--emerald);
            background: rgba(16, 185, 129, 0.12);
            border: 1px solid rgba(16, 185, 129, 0.25);
            padding: 4px 12px;
            border-radius: 999px;
            margin-bottom: 16px;
        }
        h1 {
            font-size: clamp(28px, 4vw, 36px);
            font-weight: 800;
            letter-spacing: -0.03em;
            color: #ffffff;
            margin-bottom: 12px;
        }
        .meta-info {
            display: flex;
            gap: 20px;
            font-size: 13px;
            color: var(--text-muted);
            flex-wrap: wrap;
        }
        .meta-info span strong {
            color: #ffffff;
        }
        /* Highlight Box: Limited Use Clause */
        .limited-use-box {
            background: rgba(115, 66, 226, 0.1);
            border: 1px solid rgba(115, 66, 226, 0.35);
            border-left: 4px solid var(--accent);
            border-radius: 14px;
            padding: 20px 24px;
            margin: 28px 0;
        }
        .limited-use-box h4 {
            font-size: 15px;
            font-weight: 700;
            color: #c084fc;
            margin-bottom: 8px;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .limited-use-box p {
            font-size: 14px;
            color: #e5e7eb;
            line-height: 1.6;
        }
        /* Content Sections */
        .section-card {
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 18px;
            padding: 28px 30px;
            margin-bottom: 24px;
            backdrop-filter: blur(16px);
        }
        .section-card h2 {
            font-size: 20px;
            font-weight: 700;
            color: #ffffff;
            margin-bottom: 16px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .section-card p, .section-card li {
            font-size: 14.5px;
            color: #D1D5DB;
            margin-bottom: 12px;
        }
        .section-card ul {
            padding-left: 20px;
            margin-bottom: 16px;
        }
        .scope-badge {
            display: inline-block;
            font-family: 'JetBrains Mono', monospace;
            font-size: 12px;
            background: rgba(0, 240, 255, 0.08);
            border: 1px solid rgba(0, 240, 255, 0.25);
            color: var(--cyan);
            padding: 2px 8px;
            border-radius: 6px;
            margin: 2px 0;
        }
        .footer-nav {
            margin-top: 48px;
            padding-top: 24px;
            border-top: 1px solid var(--card-border);
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 16px;
            font-size: 13px;
            color: var(--text-muted);
        }
        .footer-nav a {
            color: var(--cyan);
            text-decoration: none;
        }
        .footer-nav a:hover {
            text-decoration: underline;
        }
        .lang-content {
            display: none;
        }
        .lang-content.active {
            display: block;
        }
    </style>
</head>
<body>
    <div class="container">
        <!-- Top Nav -->
        <header>
            <a href="/" class="brand">
                <div class="brand-icon">
                    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#ffffff" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                        <polygon points="12 2 2 7 12 12 22 7 12 2"></polygon>
                        <polyline points="2 17 12 22 22 17"></polyline>
                        <polyline points="2 12 12 17 22 12"></polyline>
                    </svg>
                </div>
                <div>
                    <span class="brand-text">Bot Client</span>
                    <span class="brand-tag">CreatorFlow Studio</span>
                </div>
            </a>
            
            <div class="lang-switch">
                <button class="lang-btn active" data-lang="en" onclick="setLang('en')">EN</button>
                <button class="lang-btn" data-lang="ru" onclick="setLang('ru')">RU</button>
                <button class="lang-btn" data-lang="uz" onclick="setLang('uz')">UZ</button>
            </div>
        </header>

        <!-- Breadcrumb -->
        <div class="breadcrumb">
            <a href="/">Home</a>
            <span>/</span>
            <span id="bc-title">Privacy Policy</span>
        </div>

        <!-- =============================================================
             ENGLISH CONTENT (DEFAULT)
             ============================================================= -->
        <div id="content-en" class="lang-content active">
            <div class="hero">
                <div class="badge">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path>
                    </svg>
                    Official Privacy & Security Disclosures
                </div>
                <h1>Privacy Policy</h1>
                <div class="meta-info">
                    <span>Application: <strong>Bot Client (CreatorFlow Studio)</strong></span>
                    <span>Last Updated: <strong>October 18, 2026</strong></span>
                    <span>Domain: <strong>botclient-d1jn.onrender.com</strong></span>
                </div>
            </div>

            <!-- Mandatory Google Limited Use Statement -->
            <div class="limited-use-box">
                <h4>
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <circle cx="12" cy="12" r="10"></circle>
                        <line x1="12" y1="16" x2="12" y2="12"></line>
                        <line x1="12" y1="8" x2="12.01" y2="8"></line>
                    </svg>
                    Google API Services User Data Policy Compliance
                </h4>
                <p>
                    <strong>Bot Client's (operating as CreatorFlow Studio) use and transfer to any other app of information received from Google APIs will adhere to the <a href="https://developers.google.com/terms/api-services-user-data-policy" target="_blank" rel="noopener" style="color:#00F0FF;text-decoration:underline;">Google API Services User Data Policy</a>, including the Limited Use requirements.</strong>
                </p>
            </div>

            <div class="section-card">
                <h2>1. Introduction & Overview</h2>
                <p>
                    Bot Client ("CreatorFlow Studio", "we", "us", or "our") operates the web application and automation services accessible at <strong>https://botclient-d1jn.onrender.com</strong> and the associated Telegram user automation studio. This Privacy Policy outlines our commitment to protecting your personal information and explains how we access, collect, process, and safeguard data when you use our services.
                </p>
                <p>
                    By connecting your Google Account or utilizing Bot Client, you consent to the data practices described in this document. If you do not agree with any part of this policy, please do not authorize the application or immediately revoke access via your Google Security settings.
                </p>
            </div>

            <div class="section-card">
                <h2>2. Google User Data & YouTube API Scopes Accessed</h2>
                <p>
                    CreatorFlow Studio integrates with the <strong>YouTube Data API v3</strong> to provide creators with real-time analytics, automated publishing workflows, and video performance monitoring. When you authorize CreatorFlow Studio via Google OAuth 2.0, we request access only to the following specific scopes:
                </p>
                <ul>
                    <li>
                        <span class="scope-badge">https://www.googleapis.com/auth/youtube.readonly</span>
                        <br>
                        <strong>Purpose:</strong> Used exclusively to retrieve and display your YouTube channel profile, channel ID, subscriber count, total views, video count, and public performance metrics in your personal CreatorFlow Studio dashboard.
                    </li>
                    <li style="margin-top:12px;">
                        <span class="scope-badge">https://www.googleapis.com/auth/youtube.upload</span>
                        <br>
                        <strong>Purpose:</strong> Used solely when you explicitly schedule or initiate a video or short upload to your YouTube channel through our automated queue.
                    </li>
                    <li style="margin-top:12px;">
                        <span class="scope-badge">https://www.googleapis.com/auth/youtube.force-ssl</span>
                        <br>
                        <strong>Purpose:</strong> Used only to update titles, descriptions, tags, and thumbnails for videos uploaded through the studio upon your explicit command.
                    </li>
                </ul>
            </div>

            <div class="section-card">
                <h2>3. How We Use and Protect Google User Data</h2>
                <p>We handle Google user data with strict safeguards:</p>
                <ul>
                    <li><strong>No Sale or Third-Party Monetization:</strong> We do not sell, rent, lease, or transfer your Google user data or YouTube data to any third parties, advertisers, data brokers, or external entities.</li>
                    <li><strong>No AI Model Training:</strong> Your Google user data and private video data are never used to train, retrain, or fine-tune generalized machine learning or artificial intelligence models.</li>
                    <li><strong>Limited Purpose Access:</strong> Google API data is used solely to provide user-facing channel analytics and creator automation features directly requested by you.</li>
                    <li><strong>Industry-Grade Encryption:</strong> OAuth 2.0 access and refresh tokens are encrypted at rest using AES-256 standards in our secure database, and all network communication occurs strictly over HTTPS/TLS 1.3.</li>
                </ul>
            </div>

            <div class="section-card">
                <h2>4. Data Retention, Deletion & Revoking Access</h2>
                <p>
                    You maintain complete sovereignty over your Google Account and YouTube data at all times:
                </p>
                <ul>
                    <li>
                        <strong>Instant Access Revocation:</strong> You can revoke CreatorFlow Studio's access to your Google Account at any time directly through Google Account Security Settings at <a href="https://myaccount.google.com/permissions" target="_blank" rel="noopener" style="color:#00F0FF;text-decoration:underline;">https://myaccount.google.com/permissions</a>. Once revoked, our application can no longer access your YouTube channel or data.
                    </li>
                    <li>
                        <strong>Account & Token Deletion:</strong> You can disconnect your channel inside the dashboard or send the <code>/disconnect</code> command to our bot, which instantly purges all stored OAuth tokens from our database.
                    </li>
                    <li>
                        <strong>Full Data Erasure Request:</strong> To request complete erasure of all associated data, contact our support team at <a href="mailto:support@creatorflow.app" style="color:#00F0FF;">support@creatorflow.app</a> or via Telegram at <a href="https://t.me/CreatorFlow_Store" target="_blank" rel="noopener" style="color:#00F0FF;">@CreatorFlow_Store</a>. We process all erasure requests within 48 hours.
                    </li>
                </ul>
            </div>

            <div class="section-card">
                <h2>5. Cookies & Technical Telemetry</h2>
                <p>
                    We use strictly essential local storage and session cookies to maintain your authentication state and preferred language settings (EN / RU / UZ). We do not deploy third-party advertising tracking cookies or invasive cross-site tracking scripts.
                </p>
            </div>

            <div class="section-card">
                <h2>6. Developer Contact Information</h2>
                <p>
                    If you have questions, feedback, or data privacy inquiries regarding this Privacy Policy or our Google OAuth integration, please contact our Data Protection Officer:
                </p>
                <ul>
                    <li><strong>Email:</strong> <a href="mailto:support@creatorflow.app" style="color:#00F0FF;">support@creatorflow.app</a></li>
                    <li><strong>Telegram Support:</strong> <a href="https://t.me/CreatorFlow_Store" target="_blank" rel="noopener" style="color:#00F0FF;">@CreatorFlow_Store</a></li>
                    <li><strong>Authorized Web Domain:</strong> https://botclient-d1jn.onrender.com</li>
                </ul>
            </div>
        </div>

        <!-- =============================================================
             RUSSIAN CONTENT (RU)
             ============================================================= -->
        <div id="content-ru" class="lang-content">
            <div class="hero">
                <div class="badge">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path>
                    </svg>
                    Официальное раскрытие политики конфиденциальности
                </div>
                <h1>Политика конфиденциальности</h1>
                <div class="meta-info">
                    <span>Приложение: <strong>CreatorFlow Studio</strong></span>
                    <span>Дата обновления: <strong>18 октября 2026 г.</strong></span>
                    <span>Домен: <strong>botclient-d1jn.onrender.com</strong></span>
                </div>
            </div>

            <div class="limited-use-box">
                <h4>
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <circle cx="12" cy="12" r="10"></circle>
                        <line x1="12" y1="16" x2="12" y2="12"></line>
                        <line x1="12" y1="8" x2="12.01" y2="8"></line>
                    </svg>
                    Соответствие Политике данных пользователей Google API
                </h4>
                <p>
                    <strong>Использование и передача CreatorFlow Studio любой информации, полученной из API Google, в любое другое приложение соответствуют <a href="https://developers.google.com/terms/api-services-user-data-policy" target="_blank" rel="noopener" style="color:#00F0FF;text-decoration:underline;">Политике в отношении данных пользователей Google API Services</a>, включая требования ограниченного использования (Limited Use).</strong>
                </p>
            </div>

            <div class="section-card">
                <h2>1. Введение и обзор</h2>
                <p>
                    CreatorFlow Studio («мы», «нас» или «наш») предоставляет веб-приложение и сервисы автоматизации, доступные по адресу <strong>https://botclient-d1jn.onrender.com</strong> и через Telegram-студию. Настоящая Политика конфиденциальности описывает, как мы обрабатываем, защищаем и храним ваши данные при авторизации через Google OAuth 2.0.
                </p>
            </div>

            <div class="section-card">
                <h2>2. Данные Google и запрашиваемые разрешения YouTube API</h2>
                <p>
                    CreatorFlow Studio интегрируется с <strong>YouTube Data API v3</strong> для предоставления аналитики канала в реальном времени и автоматизации загрузки видео по вашему запросу. Мы запрашиваем только минимально необходимые области доступа:
                </p>
                <ul>
                    <li>
                        <span class="scope-badge">https://www.googleapis.com/auth/youtube.readonly</span>
                        <br>
                        <strong>Назначение:</strong> Используется исключительно для отображения профиля канала, количества подписчиков, общих просмотров и статистики видео в вашей панели управления.
                    </li>
                    <li style="margin-top:12px;">
                        <span class="scope-badge">https://www.googleapis.com/auth/youtube.upload</span>
                        <br>
                        <strong>Назначение:</strong> Используется исключительно при явной команде пользователя на публикацию или загрузку видео/shorts.
                    </li>
                    <li style="margin-top:12px;">
                        <span class="scope-badge">https://www.googleapis.com/auth/youtube.force-ssl</span>
                        <br>
                        <strong>Назначение:</strong> Используется для обновления метаданных (заголовки, описания, теги) загружаемых видео.
                    </li>
                </ul>
            </div>

            <div class="section-card">
                <h2>3. Защита данных и ограничение использования</h2>
                <ul>
                    <li><strong>Никакой продажи данных:</strong> Мы никогда не продаем, не сдаем в аренду и не передаем ваши данные третьим лицам или брокерам данных.</li>
                    <li><strong>Никакого обучения AI моделей:</strong> Ваши личные данные Google не используются для обучения публичных моделей искусственного интеллекта.</li>
                    <li><strong>Шифрование:</strong> Токены доступа сохраняются в зашифрованном виде (AES-256) в защищенной базе данных. Все соединения защищены TLS 1.3/HTTPS.</li>
                </ul>
            </div>

            <div class="section-card">
                <h2>4. Отзыв доступа и удаление данных</h2>
                <ul>
                    <li>
                        <strong>Отзыв доступа Google:</strong> Вы можете отозвать доступ CreatorFlow Studio в любой момент на странице безопасности Google: <a href="https://myaccount.google.com/permissions" target="_blank" rel="noopener" style="color:#00F0FF;text-decoration:underline;">https://myaccount.google.com/permissions</a>.
                    </li>
                    <li>
                        <strong>Полное удаление:</strong> Отправьте запрос на удаление на <a href="mailto:support@creatorflow.app" style="color:#00F0FF;">support@creatorflow.app</a> или в Telegram <a href="https://t.me/CreatorFlow_Store" target="_blank" rel="noopener" style="color:#00F0FF;">@CreatorFlow_Store</a>. Данные удаляются в течение 48 часов.
                    </li>
                </ul>
            </div>

            <div class="section-card">
                <h2>5. Контакты службы поддержки</h2>
                <p>По любым вопросам конфиденциальности обращайтесь к нам:</p>
                <ul>
                    <li><strong>Email:</strong> support@creatorflow.app</li>
                    <li><strong>Telegram:</strong> @CreatorFlow_Store</li>
                    <li><strong>Сайт:</strong> https://botclient-d1jn.onrender.com</li>
                </ul>
            </div>
        </div>

        <!-- =============================================================
             UZBEK CONTENT (UZ)
             ============================================================= -->
        <div id="content-uz" class="lang-content">
            <div class="hero">
                <div class="badge">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path>
                    </svg>
                    Rasmiy Maxfiylik va Xavfsizlik Siyosati
                </div>
                <h1>Maxfiylik Siyosati</h1>
                <div class="meta-info">
                    <span>Ilova: <strong>CreatorFlow Studio</strong></span>
                    <span>Yangilangan sana: <strong>18-oktyabr, 2026-yil</strong></span>
                    <span>Domen: <strong>botclient-d1jn.onrender.com</strong></span>
                </div>
            </div>

            <div class="limited-use-box">
                <h4>
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <circle cx="12" cy="12" r="10"></circle>
                        <line x1="12" y1="16" x2="12" y2="12"></line>
                        <line x1="12" y1="8" x2="12.01" y2="8"></line>
                    </svg>
                    Google API Services Foydalanuvchi Ma'lumotlari Siyosatiga Muvofiqlik
                </h4>
                <p>
                    <strong>CreatorFlow Studio ilovasining Google API orqali olingan har qanday axborotdan foydalanishi va uni boshqa ilovalarga uzatishi <a href="https://developers.google.com/terms/api-services-user-data-policy" target="_blank" rel="noopener" style="color:#00F0FF;text-decoration:underline;">Google API Services User Data Policy</a>, jumladan Cheklangan Foydalanish (Limited Use) talablariga qat'iy javob beradi.</strong>
                </p>
            </div>

            <div class="section-card">
                <h2>1. Kirish va Umumiy Ma'lumot</h2>
                <p>
                    CreatorFlow Studio ("biz", "bizning") <strong>https://botclient-d1jn.onrender.com</strong> veb-manzilida va Telegram boti orqali professional mualliflar va kanallar uchun avtomatlashtirish, tahlil va video xizmatlarini taqdim etadi. Ushbu Maxfiylik Siyosati foydalanuvchilarimizning ma'lumotlarini qanday himoyalashimiz va Google OAuth 2.0 orqali qanday ma'lumotlar bilan ishlashimizni belgilaydi.
                </p>
            </div>

            <div class="section-card">
                <h2>2. YouTube API orqali olinadigan Ma'lumotlar va Vakolatlar</h2>
                <p>
                    CreatorFlow Studio foydalanuvchining YouTube kanalini tahlil qilish uchun <strong>YouTube Data API v3</strong> bilan integratsiya qilingan:
                </p>
                <ul>
                    <li>
                        <span class="scope-badge">https://www.googleapis.com/auth/youtube.readonly</span>
                        <br>
                        <strong>Maqsad:</strong> Faqatgina kanal profili, obunachilar soni, umumiy ko'rishlar va oxirgi videolarning ommaviy statistikasini sizning shaxsiy panellaringizda ko'rsatish uchun.
                    </li>
                    <li style="margin-top:12px;">
                        <span class="scope-badge">https://www.googleapis.com/auth/youtube.upload</span>
                        <br>
                        <strong>Maqsad:</strong> Faqat sizning bevosita buyrug'ingiz bilan kanalingizga video yoki Shorts yuklash uchun.
                    </li>
                    <li style="margin-top:12px;">
                        <span class="scope-badge">https://www.googleapis.com/auth/youtube.force-ssl</span>
                        <br>
                        <strong>Maqsad:</strong> Yuklangan videolarning sarlavha, tavsif va teglarini tahrirlash uchun.
                    </li>
                </ul>
            </div>

            <div class="section-card">
                <h2>3. Ma'lumotlar Xavfsizligi va Kafolatlar</h2>
                <ul>
                    <li><strong>Sotilmaydi va tarqatilmaydi:</strong> Biz sizning ma'lumotlaringizni hech qachon uchinchi shaxslarga, reklama agentliklariga yoki ma'lumot brokerlariga sotmaymiz.</li>
                    <li><strong>AI modellarini o'qitish uchun ishlatilmaydi:</strong> Google orqali olingan ma'lumotlar sun'iy intellekt modellarini o'qitishda qo'llanilmaydi.</li>
                    <li><strong>Shifrlangan saqlash:</strong> Tokenlar xavfsiz ma'lumotlar bazasida AES-256 shifrlash bilan saqlanadi.</li>
                </ul>
            </div>

            <div class="section-card">
                <h2>4. Ruxsatni Bekor Qilish va Ma'lumotlarni O'chirish</h2>
                <ul>
                    <li>
                        <strong>Google orqali bekor qilish:</strong> Istalgan vaqtda Google Xavfsizlik sahifasi orqali ilovaga berilgan ruxsatni bekor qilishingiz mumkin: <a href="https://myaccount.google.com/permissions" target="_blank" rel="noopener" style="color:#00F0FF;text-decoration:underline;">https://myaccount.google.com/permissions</a>.
                    </li>
                    <li>
                        <strong>To'liq o'chirish talabi:</strong> Ma'lumotlaringizni to'liq o'chirish uchun <a href="mailto:support@creatorflow.app" style="color:#00F0FF;">support@creatorflow.app</a> manziliga yoki Telegramdagi <a href="https://t.me/CreatorFlow_Store" target="_blank" rel="noopener" style="color:#00F0FF;">@CreatorFlow_Store</a> qo'llab-quvvatlash xizmatiga murojaat qiling.
                    </li>
                </ul>
            </div>

            <div class="section-card">
                <h2>5. Bog'lanish Ma'lumotlari</h2>
                <ul>
                    <li><strong>Elektron pochta:</strong> support@creatorflow.app</li>
                    <li><strong>Telegram Support:</strong> @CreatorFlow_Store</li>
                    <li><strong>Rasmiy Domen:</strong> https://botclient-d1jn.onrender.com</li>
                </ul>
            </div>
        </div>

        <!-- Footer -->
        <div class="footer-nav">
            <div>
                &copy; 2026 CreatorFlow Studio. All rights reserved.
            </div>
            <div style="display:flex;gap:18px;">
                <a href="/">Home</a>
                <a href="/terms">Terms of Service</a>
                <a href="https://myaccount.google.com/permissions" target="_blank" rel="noopener">Google Permissions</a>
            </div>
        </div>
    </div>

    <script>
        function setLang(lang) {
            try {
                localStorage.setItem('cf_lang', lang);
            } catch(e) {}
            document.querySelectorAll('.lang-btn').forEach(btn => {
                if (btn.getAttribute('data-lang') === lang) {
                    btn.classList.add('active');
                } else {
                    btn.classList.remove('active');
                }
            });
            document.querySelectorAll('.lang-content').forEach(c => {
                c.classList.remove('active');
            });
            const target = document.getElementById('content-' + lang);
            if (target) {
                target.classList.add('active');
            }
            const bc = document.getElementById('bc-title');
            if (bc) {
                bc.innerText = lang === 'uz' ? 'Maxfiylik Siyosati' : (lang === 'ru' ? 'Политика конфиденциальности' : 'Privacy Policy');
            }
        }

        // Initialize from URL param, localStorage, or default to EN
        (function() {
            const params = new URLSearchParams(window.location.search);
            const urlLang = params.get('lang');
            let savedLang = 'en';
            try {
                savedLang = localStorage.getItem('cf_lang') || 'en';
            } catch(e) {}
            const active = (urlLang && ['en','ru','uz'].includes(urlLang)) ? urlLang : (['en','ru','uz'].includes(savedLang) ? savedLang : 'en');
            setLang(active);
        })();
    </script>
</body>
</html>"""


def get_terms_html():
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Terms of Service | Bot Client</title>
    <meta name="description" content="Terms of Service for Bot Client (CreatorFlow Studio), governing platform usage, YouTube API compliance, and creator automation tools.">
    <meta name="google-site-verification" content="EW0VY9fhYQ7yzwrd8oqani_iNoDbRELBOsbpy4c2xUU">
    <meta name="google-site-verification" content="XSrhQq7tmTEbP4JLXAoPNIHfK3gZkuoZWCQi-_51dYk">
    <script async src="https://www.googletagmanager.com/gtag/js"></script>
    <!-- Google AdSense -->
    <meta name="google-adsense-account" content="ca-pub-4094396006908725">
    <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-4094396006908725" crossorigin="anonymous"></script>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        :root {
            --bg: #090A0F;
            --card-bg: rgba(18, 22, 34, 0.85);
            --card-border: rgba(255, 255, 255, 0.08);
            --accent: #7342E2;
            --accent-glow: rgba(115, 66, 226, 0.35);
            --cyan: #00F0FF;
            --emerald: #10B981;
            --text-main: #F3F4F6;
            --text-muted: #9CA3AF;
            --font: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        }
        body {
            font-family: var(--font);
            background: var(--bg);
            color: var(--text-main);
            min-height: 100vh;
            line-height: 1.65;
            padding: 0 16px 80px;
            overflow-x: hidden;
        }
        .container {
            max-width: 920px;
            margin: 0 auto;
        }
        header {
            padding: 24px 0 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid var(--card-border);
            margin-bottom: 36px;
        }
        .brand {
            display: flex;
            align-items: center;
            gap: 12px;
            text-decoration: none;
            color: #ffffff;
        }
        .brand-icon {
            width: 38px;
            height: 38px;
            border-radius: 12px;
            background: linear-gradient(135deg, #7342E2, #00F0FF);
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 0 18px var(--accent-glow);
        }
        .brand-text {
            font-size: 20px;
            font-weight: 800;
            letter-spacing: -0.03em;
        }
        .brand-tag {
            font-size: 11px;
            font-weight: 700;
            color: var(--cyan);
            background: rgba(0, 240, 255, 0.12);
            border: 1px solid rgba(0, 240, 255, 0.25);
            padding: 2px 8px;
            border-radius: 999px;
        }
        .lang-switch {
            display: flex;
            align-items: center;
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid var(--card-border);
            border-radius: 999px;
            padding: 3px 4px;
            gap: 2px;
        }
        .lang-btn {
            background: transparent;
            border: none;
            color: var(--text-muted);
            padding: 6px 12px;
            border-radius: 999px;
            font-size: 12px;
            font-weight: 700;
            cursor: pointer;
            transition: all 0.2s ease;
        }
        .lang-btn:hover {
            color: #ffffff;
        }
        .lang-btn.active {
            background: var(--accent);
            color: #ffffff;
            box-shadow: 0 2px 8px var(--accent-glow);
        }
        .breadcrumb {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 13px;
            color: var(--text-muted);
            margin-bottom: 24px;
        }
        .breadcrumb a {
            color: var(--cyan);
            text-decoration: none;
        }
        .breadcrumb a:hover {
            text-decoration: underline;
        }
        .hero {
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 24px;
            padding: 36px 32px;
            backdrop-filter: blur(20px);
            margin-bottom: 32px;
            position: relative;
            overflow: hidden;
        }
        .hero::before {
            content: '';
            position: absolute;
            top: -40px;
            right: -40px;
            width: 220px;
            height: 220px;
            background: radial-gradient(circle, rgba(0, 240, 255, 0.15) 0%, transparent 70%);
            filter: blur(40px);
            pointer-events: none;
        }
        .badge {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            font-size: 12px;
            font-weight: 700;
            color: var(--cyan);
            background: rgba(0, 240, 255, 0.12);
            border: 1px solid rgba(0, 240, 255, 0.25);
            padding: 4px 12px;
            border-radius: 999px;
            margin-bottom: 16px;
        }
        h1 {
            font-size: clamp(28px, 4vw, 36px);
            font-weight: 800;
            letter-spacing: -0.03em;
            color: #ffffff;
            margin-bottom: 12px;
        }
        .meta-info {
            display: flex;
            gap: 20px;
            font-size: 13px;
            color: var(--text-muted);
            flex-wrap: wrap;
        }
        .meta-info span strong {
            color: #ffffff;
        }
        .highlight-box {
            background: rgba(0, 240, 255, 0.08);
            border: 1px solid rgba(0, 240, 255, 0.25);
            border-left: 4px solid var(--cyan);
            border-radius: 14px;
            padding: 20px 24px;
            margin: 28px 0;
        }
        .highlight-box h4 {
            font-size: 15px;
            font-weight: 700;
            color: #67e8f9;
            margin-bottom: 8px;
        }
        .highlight-box p {
            font-size: 14px;
            color: #e5e7eb;
            line-height: 1.6;
        }
        .section-card {
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 18px;
            padding: 28px 30px;
            margin-bottom: 24px;
            backdrop-filter: blur(16px);
        }
        .section-card h2 {
            font-size: 20px;
            font-weight: 700;
            color: #ffffff;
            margin-bottom: 16px;
        }
        .section-card p, .section-card li {
            font-size: 14.5px;
            color: #D1D5DB;
            margin-bottom: 12px;
        }
        .section-card ul {
            padding-left: 20px;
            margin-bottom: 16px;
        }
        .footer-nav {
            margin-top: 48px;
            padding-top: 24px;
            border-top: 1px solid var(--card-border);
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 16px;
            font-size: 13px;
            color: var(--text-muted);
        }
        .footer-nav a {
            color: var(--cyan);
            text-decoration: none;
        }
        .footer-nav a:hover {
            text-decoration: underline;
        }
        .lang-content {
            display: none;
        }
        .lang-content.active {
            display: block;
        }
    </style>
</head>
<body>
    <div class="container">
        <!-- Top Nav -->
        <header>
            <a href="/" class="brand">
                <div class="brand-icon">
                    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#ffffff" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                        <polygon points="12 2 2 7 12 12 22 7 12 2"></polygon>
                        <polyline points="2 17 12 22 22 17"></polyline>
                        <polyline points="2 12 12 17 22 12"></polyline>
                    </svg>
                </div>
                <div>
                    <span class="brand-text">Bot Client</span>
                    <span class="brand-tag">CreatorFlow Studio</span>
                </div>
            </a>
            
            <div class="lang-switch">
                <button class="lang-btn active" data-lang="en" onclick="setLang('en')">EN</button>
                <button class="lang-btn" data-lang="ru" onclick="setLang('ru')">RU</button>
                <button class="lang-btn" data-lang="uz" onclick="setLang('uz')">UZ</button>
            </div>
        </header>

        <!-- Breadcrumb -->
        <div class="breadcrumb">
            <a href="/">Home</a>
            <span>/</span>
            <span id="bc-title">Terms of Service</span>
        </div>

        <!-- =============================================================
             ENGLISH CONTENT (DEFAULT)
             ============================================================= -->
        <div id="content-en" class="lang-content active">
            <div class="hero">
                <div class="badge">Legal Agreement & Service Terms</div>
                <h1>Terms of Service</h1>
                <div class="meta-info">
                    <span>Application: <strong>Bot Client (CreatorFlow Studio)</strong></span>
                    <span>Last Updated: <strong>October 18, 2026</strong></span>
                    <span>Domain: <strong>botclient-d1jn.onrender.com</strong></span>
                </div>
            </div>

            <!-- YouTube Terms of Service Reference -->
            <div class="highlight-box">
                <h4>YouTube API Services Terms of Service Agreement</h4>
                <p>
                    Bot Client (CreatorFlow Studio) utilizes YouTube API Services to provide analytics and automation tools. By utilizing YouTube features within Bot Client, users agree to be bound by the <a href="https://www.youtube.com/t/terms" target="_blank" rel="noopener" style="color:#00F0FF;text-decoration:underline;">YouTube Terms of Service</a> and the <a href="https://policies.google.com/privacy" target="_blank" rel="noopener" style="color:#00F0FF;text-decoration:underline;">Google Privacy Policy</a>.
                </p>
            </div>

            <div class="section-card">
                <h2>1. Acceptance of Terms</h2>
                <p>
                    By accessing or using Bot Client ("CreatorFlow Studio", the "Service") hosted at <strong>https://botclient-d1jn.onrender.com</strong>, you agree to comply with and be legally bound by these Terms of Service ("Terms"). If you do not agree to these terms, you may not access or use the Service.
                </p>
            </div>

            <div class="section-card">
                <h2>2. Description of Services</h2>
                <p>
                    CreatorFlow Studio provides digital creators with suite-level productivity tools, including:
                </p>
                <ul>
                    <li>Real-time YouTube channel analytics, view counts, and subscriber tracking via YouTube Data API v3.</li>
                    <li>Automated video uploading, queue scheduling, and metadata management.</li>
                    <li>High-definition video processing and format transcoding.</li>
                    <li>Gamified Telegram Stars rewards, mystery cases, and digital collectibles.</li>
                </ul>
            </div>

            <div class="section-card">
                <h2>3. User Account & Security</h2>
                <p>
                    You are solely responsible for maintaining the confidentiality of your authentication tokens, Telegram User ID, and Google account credentials. You agree to notify us immediately of any unauthorized use of your account or security breach. CreatorFlow Studio is not liable for any losses caused by unauthorized use of your credentials.
                </p>
            </div>

            <div class="section-card">
                <h2>4. Prohibited Conduct</h2>
                <p>When using CreatorFlow Studio, you agree NOT to:</p>
                <ul>
                    <li>Violate the YouTube Community Guidelines, Copyright policies, or Terms of Service.</li>
                    <li>Attempt to reverse-engineer, decompile, or disrupt the operation of the application or its API endpoints.</li>
                    <li>Use automated scripts or scrapers to overwhelm our servers or circumvent YouTube API quota limitations.</li>
                    <li>Upload or schedule content that is illegal, defamatory, abusive, or infringes upon third-party intellectual property rights.</li>
                </ul>
            </div>

            <div class="section-card">
                <h2>5. Intellectual Property & Ownership</h2>
                <p>
                    You retain full intellectual property ownership of all videos, audio files, titles, descriptions, and media you produce and upload via CreatorFlow Studio. CreatorFlow Studio and its visual designs, logos, trademarks, and code are the exclusive property of CreatorFlow Studio and its licensors.
                </p>
            </div>

            <div class="section-card">
                <h2>6. Disclaimers & Limitation of Liability</h2>
                <p>
                    The Service is provided on an "AS IS" and "AS AVAILABLE" basis without warranties of any kind, whether express or implied. We do not warrant that the service will be uninterrupted, error-free, or completely secure. In no event shall CreatorFlow Studio be liable for any indirect, incidental, special, consequential, or punitive damages arising from your use of the service.
                </p>
            </div>

            <div class="section-card">
                <h2>7. Contact Information</h2>
                <p>
                    For inquiries regarding these Terms of Service, please reach out to:
                </p>
                <ul>
                    <li><strong>Email:</strong> <a href="mailto:support@creatorflow.app" style="color:#00F0FF;">support@creatorflow.app</a></li>
                    <li><strong>Telegram Support:</strong> <a href="https://t.me/CreatorFlow_Store" target="_blank" rel="noopener" style="color:#00F0FF;">@CreatorFlow_Store</a></li>
                </ul>
            </div>
        </div>

        <!-- =============================================================
             RUSSIAN CONTENT (RU)
             ============================================================= -->
        <div id="content-ru" class="lang-content">
            <div class="hero">
                <div class="badge">Юридическое соглашение и условия</div>
                <h1>Условия использования</h1>
                <div class="meta-info">
                    <span>Приложение: <strong>CreatorFlow Studio</strong></span>
                    <span>Дата обновления: <strong>18 октября 2026 г.</strong></span>
                    <span>Домен: <strong>botclient-d1jn.onrender.com</strong></span>
                </div>
            </div>

            <div class="highlight-box">
                <h4>Согласие с Условиями использования YouTube API</h4>
                <p>
                    CreatorFlow Studio использует сервисы YouTube API. Используя функции YouTube в CreatorFlow Studio, вы соглашаетесь соблюдать <a href="https://www.youtube.com/t/terms" target="_blank" rel="noopener" style="color:#00F0FF;text-decoration:underline;">Условия использования YouTube</a> и <a href="https://policies.google.com/privacy" target="_blank" rel="noopener" style="color:#00F0FF;text-decoration:underline;">Политику конфиденциальности Google</a>.
                </p>
            </div>

            <div class="section-card">
                <h2>1. Принятие условий</h2>
                <p>
                    Получая доступ к CreatorFlow Studio по адресу <strong>https://botclient-d1jn.onrender.com</strong>, вы соглашаетесь соблюдать настоящие Условия использования.
                </p>
            </div>

            <div class="section-card">
                <h2>2. Описание сервиса</h2>
                <p>
                    CreatorFlow Studio предоставляет инструменты аналитики каналов YouTube в реальном времени, автоматизацию отложенной публикации видео и экосистему вознаграждений Telegram Stars.
                </p>
            </div>

            <div class="section-card">
                <h2>3. Ограничения и правила</h2>
                <ul>
                    <li>Соблюдайте правила сообщества YouTube и авторские права.</li>
                    <li>Запрещены попытки взлома, сканирования уязвимостей или искусственной перегрузки API.</li>
                </ul>
            </div>

            <div class="section-card">
                <h2>4. Контактные данные</h2>
                <p>
                    По любым вопросам пишите нам на <strong>support@creatorflow.app</strong> или в Telegram <strong>@CreatorFlow_Store</strong>.
                </p>
            </div>
        </div>

        <!-- =============================================================
             UZBEK CONTENT (UZ)
             ============================================================= -->
        <div id="content-uz" class="lang-content">
            <div class="hero">
                <div class="badge">Foydalanish Shartlari & Qoidalari</div>
                <h1>Foydalanish Shartlari</h1>
                <div class="meta-info">
                    <span>Ilova: <strong>CreatorFlow Studio</strong></span>
                    <span>Yangilangan sana: <strong>18-oktyabr, 2026-yil</strong></span>
                    <span>Domen: <strong>botclient-d1jn.onrender.com</strong></span>
                </div>
            </div>

            <div class="highlight-box">
                <h4>YouTube API Foydalanish Shartlari bilan Rozilik</h4>
                <p>
                    CreatorFlow Studio YouTube API xizmatlaridan foydalanadi. Ilovamizdagi YouTube funksiyalaridan foydalanish orqali siz <a href="https://www.youtube.com/t/terms" target="_blank" rel="noopener" style="color:#00F0FF;text-decoration:underline;">YouTube Foydalanish Shartlari</a> va <a href="https://policies.google.com/privacy" target="_blank" rel="noopener" style="color:#00F0FF;text-decoration:underline;">Google Maxfiylik Siyosati</a> ga rozilik bildirasiz.
                </p>
            </div>

            <div class="section-card">
                <h2>1. Shartlarni Qabul Qilish</h2>
                <p>
                    <strong>https://botclient-d1jn.onrender.com</strong> manzilidagi CreatorFlow Studio platformasidan foydalanish orqali siz ushbu Foydalanish Shartlariga to'liq rozilik bildirasiz.
                </p>
            </div>

            <div class="section-card">
                <h2>2. Xizmatlar Tavsifi</h2>
                <p>
                    CreatorFlow Studio mualliflarga YouTube kanallari tahlili, videolarni rejalashtirish, formatlarni konvertatsiya qilish va Telegram Stars mukofot tizimlarini taqdim etadi.
                </p>
            </div>

            <div class="section-card">
                <h2>3. Foydalanuvchi Majburiyatlari</h2>
                <ul>
                    <li>Mualliflik huquqlari va YouTube hamjamiyat qoidalariga rioya qilish.</li>
                    <li>Tizimga zarar yetkazuvchi dasturlar yoki ortiqcha yuklama hosil qiluvchi skriptlardan foydalanmaslik.</li>
                </ul>
            </div>

            <div class="section-card">
                <h2>4. Bog'lanish</h2>
                <p>
                    Savollar bo'yicha biz bilan bog'laning: <strong>support@creatorflow.app</strong> yoki Telegram: <strong>@CreatorFlow_Store</strong>.
                </p>
            </div>
        </div>

        <!-- Footer -->
        <div class="footer-nav">
            <div>
                &copy; 2026 CreatorFlow Studio. All rights reserved.
            </div>
            <div style="display:flex;gap:18px;">
                <a href="/">Home</a>
                <a href="/privacy">Privacy Policy</a>
                <a href="https://www.youtube.com/t/terms" target="_blank" rel="noopener">YouTube Terms</a>
            </div>
        </div>
    </div>

    <script>
        function setLang(lang) {
            try {
                localStorage.setItem('cf_lang', lang);
            } catch(e) {}
            document.querySelectorAll('.lang-btn').forEach(btn => {
                if (btn.getAttribute('data-lang') === lang) {
                    btn.classList.add('active');
                } else {
                    btn.classList.remove('active');
                }
            });
            document.querySelectorAll('.lang-content').forEach(c => {
                c.classList.remove('active');
            });
            const target = document.getElementById('content-' + lang);
            if (target) {
                target.classList.add('active');
            }
            const bc = document.getElementById('bc-title');
            if (bc) {
                bc.innerText = lang === 'uz' ? 'Foydalanish Shartlari' : (lang === 'ru' ? 'Условия использования' : 'Terms of Service');
            }
        }

        (function() {
            const params = new URLSearchParams(window.location.search);
            const urlLang = params.get('lang');
            let savedLang = 'en';
            try {
                savedLang = localStorage.getItem('cf_lang') || 'en';
            } catch(e) {}
            const active = (urlLang && ['en','ru','uz'].includes(urlLang)) ? urlLang : (['en','ru','uz'].includes(savedLang) ? savedLang : 'en');
            setLang(active);
        })();
    </script>
</body>
</html>"""
