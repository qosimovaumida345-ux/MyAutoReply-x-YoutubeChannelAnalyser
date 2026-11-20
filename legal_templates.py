# -*- coding: utf-8 -*-
"""
MonoDeck - Multilingual Legal & Compliance Templates
Google OAuth 2.0 & YouTube Data API Compliant Privacy Policy and Terms of Service.
Supports English (Default), Russian, and Uzbek with instant client-side switching.
Styled cleanly with the MonoDeck Editorial Paper design system (Black / White / #FF5A1F).
"""

import html as _html
from config import APP_BASE_URL, BRAND_NAME, SUPPORT_USERNAME
from ui_theme import (
    get_adsense_head_html,
    get_editorial_base_css,
    get_fonts_head_html,
    get_verification_head_html,
    render_editorial_footer,
    render_editorial_navbar,
)


def _legal_page_css() -> str:
    return get_editorial_base_css() + """
.md-legal-wrap { max-width: 920px; margin: 0 auto; padding: 32px 24px 72px; }
.md-legal-top {
    display: flex; justify-content: space-between; align-items: center;
    flex-wrap: wrap; gap: 12px; margin-bottom: 24px;
}
.md-breadcrumb {
    font-family: var(--font-mono); font-size: 12px; color: var(--muted);
    display: flex; align-items: center; gap: 8px;
}
.md-breadcrumb a { text-decoration: none; color: var(--ink); font-weight: 500; }
.md-breadcrumb a:hover { text-decoration: underline; }
.md-lang-switch {
    display: inline-flex; align-items: center; gap: 4px;
    background: var(--surface); border: 1px solid var(--border);
    border-radius: 999px; padding: 3px;
}
.lang-btn {
    border: none; background: transparent; color: var(--muted);
    font-family: var(--font-mono); font-size: 11px; font-weight: 600;
    padding: 5px 11px; border-radius: 999px; cursor: pointer;
    transition: background-color 0.15s ease, color 0.15s ease;
}
.lang-btn:hover { color: var(--ink); }
.lang-btn.active { background: var(--ink); color: #FFFFFF; }
.md-legal-hero {
    background: var(--surface); border: 1px solid var(--border);
    border-radius: 14px; padding: 28px; margin-bottom: 20px;
}
.md-legal-hero h1 {
    font-family: var(--font-display); font-size: clamp(28px, 4vw, 38px);
    font-weight: 600; letter-spacing: -0.025em; margin: 12px 0;
}
.md-legal-meta {
    display: flex; flex-wrap: wrap; gap: 18px;
    font-family: var(--font-mono); font-size: 12px; color: var(--muted);
}
.md-legal-meta strong { color: var(--ink); }
.md-notice-box {
    background: var(--accent-soft); border: 1px solid #FDBA9A;
    border-left: 4px solid var(--accent); border-radius: 12px;
    padding: 18px 22px; margin-bottom: 20px;
}
.md-notice-box h4 {
    font-family: var(--font-display); font-size: 15px; font-weight: 600;
    margin-bottom: 6px; color: var(--ink); display: flex; align-items: center; gap: 8px;
}
.md-notice-box p { font-size: 14px; color: var(--ink-2); }
.md-notice-box a, .section-card a {
    color: var(--ink); text-decoration: underline; text-decoration-color: var(--accent);
    text-underline-offset: 3px; font-weight: 500;
}
.section-card {
    background: var(--surface); border: 1px solid var(--border);
    border-radius: 14px; padding: 24px; margin-bottom: 16px;
}
.section-card h2 {
    font-family: var(--font-display); font-size: 19px; font-weight: 600;
    margin-bottom: 12px; color: var(--ink);
}
.section-card p, .section-card li {
    font-size: 14.5px; color: var(--ink-2); margin-bottom: 10px; line-height: 1.65;
}
.section-card ul { padding-left: 20px; margin-bottom: 6px; }
.scope-badge {
    display: inline-block; font-family: var(--font-mono); font-size: 12px;
    background: var(--bg); border: 1px solid var(--border);
    padding: 2px 8px; border-radius: 6px; color: var(--ink);
    word-break: break-all; margin-bottom: 4px;
}
.section-card code {
    font-family: var(--font-mono); font-size: 12.5px;
    background: var(--bg); border: 1px solid var(--border);
    padding: 1px 6px; border-radius: 5px;
}
.lang-content { display: none; }
.lang-content.active { display: block; }
@media (max-width: 600px) {
    .md-legal-wrap { padding: 20px 16px 56px; }
    .md-legal-hero, .section-card, .md-notice-box { padding: 18px; }
}
"""


def _lang_script(default_label_en: str, label_ru: str, label_uz: str) -> str:
    brand = _html.escape(BRAND_NAME)
    return f"""
    <script>
        function setLang(lang) {{
            var safeLang = ['en', 'ru', 'uz'].indexOf(lang) !== -1 ? lang : 'en';
            document.documentElement.lang = safeLang;
            try {{ localStorage.setItem('monodeck_lang', safeLang); }} catch(e) {{}}
            document.querySelectorAll('.lang-btn').forEach(function(btn) {{
                var active = btn.getAttribute('data-lang') === safeLang;
                btn.classList.toggle('active', active);
                btn.setAttribute('aria-pressed', active ? 'true' : 'false');
            }});
            document.querySelectorAll('.lang-content').forEach(function(el) {{
                el.classList.remove('active');
            }});
            var target = document.getElementById('content-' + safeLang);
            if (target) target.classList.add('active');
            var label = safeLang === 'uz' ? '{label_uz}' : (safeLang === 'ru' ? '{label_ru}' : '{default_label_en}');
            var bc = document.getElementById('bc-title');
            if (bc) bc.innerText = label;
            document.title = label + ' | {brand}';
        }}
        (function() {{
            var params = new URLSearchParams(window.location.search);
            var urlLang = params.get('lang');
            var savedLang = 'en';
            try {{ savedLang = localStorage.getItem('monodeck_lang') || 'en'; }} catch(e) {{}}
            var active = ['en','ru','uz'].indexOf(urlLang) !== -1 ? urlLang : (['en','ru','uz'].indexOf(savedLang) !== -1 ? savedLang : 'en');
            setLang(active);
        }})();
    </script>
"""


def get_privacy_html():
    brand = _html.escape(BRAND_NAME)
    base_url = _html.escape(APP_BASE_URL)
    domain = _html.escape(APP_BASE_URL.split("://", 1)[-1].split("/", 1)[0])
    sup_u = _html.escape(SUPPORT_USERNAME)
    sup_email = _html.escape(f"support@{domain}")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Privacy Policy | {brand}</title>
    <meta name="description" content="Privacy Policy for {brand} ({domain}), detailing Google OAuth 2.0, YouTube Data API v3 usage, data protection, and Google API Services User Data Policy compliance.">
    <link rel="icon" href="/favicon.svg" type="image/svg+xml">
    {get_verification_head_html()}
    <script async src="https://www.googletagmanager.com/gtag/js"></script>
    {get_adsense_head_html()}
    {get_fonts_head_html()}
    <style>{_legal_page_css()}</style>
</head>
<body>
    {render_editorial_navbar(active="home")}

    <main class="md-legal-wrap">
        <div class="md-legal-top">
            <div class="md-breadcrumb">
                <a href="/">Home</a>
                <span>/</span>
                <span id="bc-title">Privacy Policy</span>
            </div>
            <div class="md-lang-switch" role="group" aria-label="Language switcher">
                <button type="button" class="lang-btn active" data-lang="en" aria-pressed="true" onclick="setLang('en')">EN</button>
                <button type="button" class="lang-btn" data-lang="ru" aria-pressed="false" onclick="setLang('ru')">RU</button>
                <button type="button" class="lang-btn" data-lang="uz" aria-pressed="false" onclick="setLang('uz')">UZ</button>
            </div>
        </div>

        <!-- =============================================================
             ENGLISH CONTENT (DEFAULT)
             ============================================================= -->
        <div id="content-en" class="lang-content active">
            <div class="md-legal-hero">
                <div class="md-eyebrow"><span class="md-eyebrow-dot"></span><span>Official Privacy &amp; Security Disclosures</span></div>
                <h1>Privacy <span class="md-serif-em">Policy</span></h1>
                <div class="md-legal-meta">
                    <span>Application: <strong>{brand}</strong></span>
                    <span>Last Updated: <strong>November 20, 2026</strong></span>
                    <span>Domain: <strong>{domain}</strong></span>
                </div>
            </div>

            <div class="md-notice-box">
                <h4>
                    <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                        <circle cx="12" cy="12" r="10"></circle>
                        <line x1="12" y1="16" x2="12" y2="12"></line>
                        <line x1="12" y1="8" x2="12.01" y2="8"></line>
                    </svg>
                    Google API Services User Data Policy Compliance
                </h4>
                <p>
                    <strong>{brand}&apos;s use and transfer to any other app of information received from Google APIs will adhere to the
                    <a href="https://developers.google.com/terms/api-services-user-data-policy" target="_blank" rel="noopener noreferrer">Google API Services User Data Policy</a>,
                    including the Limited Use requirements.</strong>
                </p>
            </div>

            <div class="section-card">
                <h2>1. Introduction &amp; Overview</h2>
                <p>
                    {brand} (&ldquo;we&rdquo;, &ldquo;us&rdquo;, or &ldquo;our&rdquo;) operates the web application and automation services accessible at <strong>{base_url}</strong> and the associated Telegram user automation studio. This Privacy Policy outlines our commitment to protecting your personal information and explains how we access, collect, process, and safeguard data when you use our services.
                </p>
                <p>
                    By connecting your Google Account or utilizing {brand}, you consent to the data practices described in this document. If you do not agree with any part of this policy, please do not authorize the application or immediately revoke access via your Google Security settings.
                </p>
            </div>

            <div class="section-card">
                <h2>2. Google User Data &amp; YouTube API Scopes Accessed</h2>
                <p>
                    {brand} integrates with the <strong>YouTube Data API v3</strong> to provide creators with real-time analytics, automated publishing workflows, and video performance monitoring. When you authorize {brand} via Google OAuth 2.0, we request access only to the following specific scopes:
                </p>
                <ul>
                    <li>
                        <span class="scope-badge">https://www.googleapis.com/auth/youtube.readonly</span>
                        <br>
                        <strong>Purpose:</strong> Used exclusively to retrieve and display your YouTube channel profile, channel ID, subscriber count, total views, video count, and public performance metrics in your personal {brand} Studio dashboard.
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
                <h2>4. Data Retention, Deletion &amp; Revoking Access</h2>
                <p>
                    You maintain complete sovereignty over your Google Account and YouTube data at all times:
                </p>
                <ul>
                    <li>
                        <strong>Instant Access Revocation:</strong> You can revoke {brand}&apos;s access to your Google Account at any time directly through Google Account Security Settings at
                        <a href="https://myaccount.google.com/permissions" target="_blank" rel="noopener noreferrer">https://myaccount.google.com/permissions</a>.
                        Once revoked, our application can no longer access your YouTube channel or data.
                    </li>
                    <li>
                        <strong>Account &amp; Token Deletion:</strong> You can disconnect your channel inside the dashboard or send the <code>/delaccount</code> or <code>/disconnect</code> command to our bot, which instantly purges all stored OAuth tokens from our database.
                    </li>
                    <li>
                        <strong>Full Data Erasure Request:</strong> To request complete erasure of all associated data, contact our support team at <a href="mailto:{sup_email}">{sup_email}</a> or via Telegram at <a href="https://t.me/{sup_u}" target="_blank" rel="noopener noreferrer">@{sup_u}</a>. We process all erasure requests within 48 hours.
                    </li>
                </ul>
            </div>

            <div class="section-card">
                <h2>5. Cookies &amp; Technical Telemetry</h2>
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
                    <li><strong>Email:</strong> <a href="mailto:{sup_email}">{sup_email}</a></li>
                    <li><strong>Telegram Support:</strong> <a href="https://t.me/{sup_u}" target="_blank" rel="noopener noreferrer">@{sup_u}</a></li>
                    <li><strong>Authorized Web Domain:</strong> {base_url}</li>
                </ul>
            </div>
        </div>

        <!-- =============================================================
             RUSSIAN CONTENT (RU)
             ============================================================= -->
        <div id="content-ru" class="lang-content">
            <div class="md-legal-hero">
                <div class="md-eyebrow"><span class="md-eyebrow-dot"></span><span>Официальное раскрытие политики конфиденциальности</span></div>
                <h1>Политика конфиденциальности</h1>
                <div class="md-legal-meta">
                    <span>Приложение: <strong>{brand}</strong></span>
                    <span>Дата обновления: <strong>20 ноября 2026 г.</strong></span>
                    <span>Домен: <strong>{domain}</strong></span>
                </div>
            </div>

            <div class="md-notice-box">
                <h4>
                    <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                        <circle cx="12" cy="12" r="10"></circle>
                        <line x1="12" y1="16" x2="12" y2="12"></line>
                        <line x1="12" y1="8" x2="12.01" y2="8"></line>
                    </svg>
                    Соответствие Политике данных пользователей Google API
                </h4>
                <p>
                    <strong>Использование и передача {brand} любой информации, полученной из API Google, в любое другое приложение соответствуют
                    <a href="https://developers.google.com/terms/api-services-user-data-policy" target="_blank" rel="noopener noreferrer">Политике в отношении данных пользователей Google API Services</a>,
                    включая требования ограниченного использования (Limited Use).</strong>
                </p>
            </div>

            <div class="section-card">
                <h2>1. Введение и обзор</h2>
                <p>
                    {brand} (&laquo;мы&raquo;, &laquo;нас&raquo; или &laquo;наш&raquo;) предоставляет веб-приложение и сервисы автоматизации, доступные по адресу <strong>{base_url}</strong> и через Telegram-студию. Настоящая Политика конфиденциальности описывает, как мы обрабатываем, защищаем и храним ваши данные при авторизации через Google OAuth 2.0.
                </p>
            </div>

            <div class="section-card">
                <h2>2. Данные Google и запрашиваемые разрешения YouTube API</h2>
                <p>
                    {brand} интегрируется с <strong>YouTube Data API v3</strong> для предоставления аналитики канала в реальном времени и автоматизации загрузки видео по вашему запросу. Мы запрашиваем только минимально необходимые области доступа:
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
                        <strong>Отзыв доступа Google:</strong> Вы можете отозвать доступ {brand} в любой момент на странице безопасности Google:
                        <a href="https://myaccount.google.com/permissions" target="_blank" rel="noopener noreferrer">https://myaccount.google.com/permissions</a>.
                    </li>
                    <li>
                        <strong>Полное удаление:</strong> Отправьте запрос на удаление на <a href="mailto:{sup_email}">{sup_email}</a> или в Telegram <a href="https://t.me/{sup_u}" target="_blank" rel="noopener noreferrer">@{sup_u}</a>. Данные удаляются в течение 48 часов.
                    </li>
                </ul>
            </div>

            <div class="section-card">
                <h2>5. Контакты службы поддержки</h2>
                <p>По любым вопросам конфиденциальности обращайтесь к нам:</p>
                <ul>
                    <li><strong>Email:</strong> <a href="mailto:{sup_email}">{sup_email}</a></li>
                    <li><strong>Telegram:</strong> <a href="https://t.me/{sup_u}" target="_blank" rel="noopener noreferrer">@{sup_u}</a></li>
                    <li><strong>Сайт:</strong> {base_url}</li>
                </ul>
            </div>
        </div>

        <!-- =============================================================
             UZBEK CONTENT (UZ)
             ============================================================= -->
        <div id="content-uz" class="lang-content">
            <div class="md-legal-hero">
                <div class="md-eyebrow"><span class="md-eyebrow-dot"></span><span>Rasmiy Maxfiylik va Xavfsizlik Siyosati</span></div>
                <h1>Maxfiylik Siyosati</h1>
                <div class="md-legal-meta">
                    <span>Ilova: <strong>{brand}</strong></span>
                    <span>Yangilangan sana: <strong>20-noyabr, 2026-yil</strong></span>
                    <span>Domen: <strong>{domain}</strong></span>
                </div>
            </div>

            <div class="md-notice-box">
                <h4>
                    <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                        <circle cx="12" cy="12" r="10"></circle>
                        <line x1="12" y1="16" x2="12" y2="12"></line>
                        <line x1="12" y1="8" x2="12.01" y2="8"></line>
                    </svg>
                    Google API Services Foydalanuvchi Ma&apos;lumotlari Siyosatiga Muvofiqlik
                </h4>
                <p>
                    <strong>{brand} ilovasining Google API orqali olingan har qanday axborotdan foydalanishi va uni boshqa ilovalarga uzatishi
                    <a href="https://developers.google.com/terms/api-services-user-data-policy" target="_blank" rel="noopener noreferrer">Google API Services User Data Policy</a>,
                    jumladan Cheklangan Foydalanish (Limited Use) talablariga qat&apos;iy javob beradi.</strong>
                </p>
            </div>

            <div class="section-card">
                <h2>1. Kirish va Umumiy Ma&apos;lumot</h2>
                <p>
                    {brand} (&ldquo;biz&rdquo;, &ldquo;bizning&rdquo;) <strong>{base_url}</strong> veb-manzilida va Telegram boti orqali professional mualliflar va kanallar uchun avtomatlashtirish, tahlil va video xizmatlarini taqdim etadi. Ushbu Maxfiylik Siyosati foydalanuvchilarimizning ma&apos;lumotlarini qanday himoyalashimiz va Google OAuth 2.0 orqali qanday ma&apos;lumotlar bilan ishlashimizni belgilaydi.
                </p>
            </div>

            <div class="section-card">
                <h2>2. YouTube API orqali olinadigan Ma&apos;lumotlar va Vakolatlar</h2>
                <p>
                    {brand} foydalanuvchining YouTube kanalini tahlil qilish uchun <strong>YouTube Data API v3</strong> bilan integratsiya qilingan:
                </p>
                <ul>
                    <li>
                        <span class="scope-badge">https://www.googleapis.com/auth/youtube.readonly</span>
                        <br>
                        <strong>Maqsad:</strong> Faqatgina kanal profili, obunachilar soni, umumiy ko&apos;rishlar va oxirgi videolarning ommaviy statistikasini sizning shaxsiy panellaringizda ko&apos;rsatish uchun.
                    </li>
                    <li style="margin-top:12px;">
                        <span class="scope-badge">https://www.googleapis.com/auth/youtube.upload</span>
                        <br>
                        <strong>Maqsad:</strong> Faqat sizning bevosita buyrug&apos;ingiz bilan kanalingizga video yoki Shorts yuklash uchun.
                    </li>
                    <li style="margin-top:12px;">
                        <span class="scope-badge">https://www.googleapis.com/auth/youtube.force-ssl</span>
                        <br>
                        <strong>Maqsad:</strong> Yuklangan videolarning sarlavha, tavsif va teglarini tahrirlash uchun.
                    </li>
                </ul>
            </div>

            <div class="section-card">
                <h2>3. Ma&apos;lumotlar Xavfsizligi va Kafolatlar</h2>
                <ul>
                    <li><strong>Sotilmaydi va tarqatilmaydi:</strong> Biz sizning ma&apos;lumotlaringizni hech qachon uchinchi shaxslarga, reklama agentliklariga yoki ma&apos;lumot brokerlariga sotmaymiz.</li>
                    <li><strong>AI modellarini o&apos;qitish uchun ishlatilmaydi:</strong> Google orqali olingan ma&apos;lumotlar sun&apos;iy intellekt modellarini o&apos;qitishda qo&apos;llanilmaydi.</li>
                    <li><strong>Shifrlangan saqlash:</strong> Tokenlar xavfsiz ma&apos;lumotlar bazasida AES-256 shifrlash bilan saqlanadi.</li>
                </ul>
            </div>

            <div class="section-card">
                <h2>4. Ruxsatni Bekor Qilish va Ma&apos;lumotlarni O&apos;chirish</h2>
                <ul>
                    <li>
                        <strong>Google orqali bekor qilish:</strong> Istalgan vaqtda Google Xavfsizlik sahifasi orqali ilovaga berilgan ruxsatni bekor qilishingiz mumkin:
                        <a href="https://myaccount.google.com/permissions" target="_blank" rel="noopener noreferrer">https://myaccount.google.com/permissions</a>.
                    </li>
                    <li>
                        <strong>To&apos;liq o&apos;chirish talabi:</strong> Ma&apos;lumotlaringizni to&apos;liq o&apos;chirish uchun <a href="mailto:{sup_email}">{sup_email}</a> manziliga yoki Telegramdagi <a href="https://t.me/{sup_u}" target="_blank" rel="noopener noreferrer">@{sup_u}</a> qo&apos;llab-quvvatlash xizmatiga murojaat qiling.
                    </li>
                </ul>
            </div>

            <div class="section-card">
                <h2>5. Bog&apos;lanish Ma&apos;lumotlari</h2>
                <ul>
                    <li><strong>Elektron pochta:</strong> <a href="mailto:{sup_email}">{sup_email}</a></li>
                    <li><strong>Telegram Support:</strong> <a href="https://t.me/{sup_u}" target="_blank" rel="noopener noreferrer">@{sup_u}</a></li>
                    <li><strong>Rasmiy Domen:</strong> {base_url}</li>
                </ul>
            </div>
        </div>
    </main>

    {render_editorial_footer()}
    {_lang_script("Privacy Policy", "Политика конфиденциальности", "Maxfiylik Siyosati")}
</body>
</html>"""


def get_terms_html():
    brand = _html.escape(BRAND_NAME)
    base_url = _html.escape(APP_BASE_URL)
    domain = _html.escape(APP_BASE_URL.split("://", 1)[-1].split("/", 1)[0])
    sup_u = _html.escape(SUPPORT_USERNAME)
    sup_email = _html.escape(f"support@{domain}")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Terms of Service | {brand}</title>
    <meta name="description" content="Terms of Service for {brand} ({domain}), governing platform usage, YouTube API compliance, and creator automation tools.">
    <link rel="icon" href="/favicon.svg" type="image/svg+xml">
    {get_verification_head_html()}
    <script async src="https://www.googletagmanager.com/gtag/js"></script>
    {get_adsense_head_html()}
    {get_fonts_head_html()}
    <style>{_legal_page_css()}</style>
</head>
<body>
    {render_editorial_navbar(active="home")}

    <main class="md-legal-wrap">
        <div class="md-legal-top">
            <div class="md-breadcrumb">
                <a href="/">Home</a>
                <span>/</span>
                <span id="bc-title">Terms of Service</span>
            </div>
            <div class="md-lang-switch" role="group" aria-label="Language switcher">
                <button type="button" class="lang-btn active" data-lang="en" aria-pressed="true" onclick="setLang('en')">EN</button>
                <button type="button" class="lang-btn" data-lang="ru" aria-pressed="false" onclick="setLang('ru')">RU</button>
                <button type="button" class="lang-btn" data-lang="uz" aria-pressed="false" onclick="setLang('uz')">UZ</button>
            </div>
        </div>

        <!-- =============================================================
             ENGLISH CONTENT (DEFAULT)
             ============================================================= -->
        <div id="content-en" class="lang-content active">
            <div class="md-legal-hero">
                <div class="md-eyebrow"><span class="md-eyebrow-dot"></span><span>Legal Agreement &amp; Service Terms</span></div>
                <h1>Terms of <span class="md-serif-em">Service</span></h1>
                <div class="md-legal-meta">
                    <span>Application: <strong>{brand}</strong></span>
                    <span>Last Updated: <strong>November 20, 2026</strong></span>
                    <span>Domain: <strong>{domain}</strong></span>
                </div>
            </div>

            <div class="md-notice-box">
                <h4>YouTube API Services Terms of Service Agreement</h4>
                <p>
                    {brand} utilizes YouTube API Services to provide analytics and automation tools. By utilizing YouTube features within {brand}, users agree to be bound by the
                    <a href="https://www.youtube.com/t/terms" target="_blank" rel="noopener noreferrer">YouTube Terms of Service</a> and the
                    <a href="https://policies.google.com/privacy" target="_blank" rel="noopener noreferrer">Google Privacy Policy</a>.
                </p>
            </div>

            <div class="section-card">
                <h2>1. Acceptance of Terms</h2>
                <p>
                    By accessing or using {brand} (the &ldquo;Service&rdquo;) hosted at <strong>{base_url}</strong>, you agree to comply with and be legally bound by these Terms of Service (&ldquo;Terms&rdquo;). If you do not agree to these terms, you may not access or use the Service.
                </p>
            </div>

            <div class="section-card">
                <h2>2. Description of Services</h2>
                <p>
                    {brand} provides digital creators with suite-level productivity tools, including:
                </p>
                <ul>
                    <li>Real-time YouTube channel analytics, view counts, and subscriber tracking via YouTube Data API v3.</li>
                    <li>Automated video uploading, queue scheduling, and metadata management.</li>
                    <li>High-definition video processing and format transcoding.</li>
                    <li>Gamified Telegram Stars rewards, mystery cases, and digital collectibles.</li>
                </ul>
            </div>

            <div class="section-card">
                <h2>3. User Account &amp; Security</h2>
                <p>
                    You are solely responsible for maintaining the confidentiality of your authentication tokens, Telegram User ID, and Google account credentials. You agree to notify us immediately of any unauthorized use of your account or security breach. {brand} is not liable for any losses caused by unauthorized use of your credentials.
                </p>
            </div>

            <div class="section-card">
                <h2>4. Prohibited Conduct</h2>
                <p>When using {brand}, you agree NOT to:</p>
                <ul>
                    <li>Violate the YouTube Community Guidelines, Copyright policies, or Terms of Service.</li>
                    <li>Attempt to reverse-engineer, decompile, or disrupt the operation of the application or its API endpoints.</li>
                    <li>Use automated scripts or scrapers to overwhelm our servers or circumvent YouTube API quota limitations.</li>
                    <li>Upload or schedule content that is illegal, defamatory, abusive, or infringes upon third-party intellectual property rights.</li>
                </ul>
            </div>

            <div class="section-card">
                <h2>5. Intellectual Property &amp; Ownership</h2>
                <p>
                    You retain full intellectual property ownership of all videos, audio files, titles, descriptions, and media you produce and upload via {brand}. {brand} and its visual designs, logos, trademarks, and code are the exclusive property of {brand} and its licensors.
                </p>
            </div>

            <div class="section-card">
                <h2>6. Disclaimers &amp; Limitation of Liability</h2>
                <p>
                    The Service is provided on an &ldquo;AS IS&rdquo; and &ldquo;AS AVAILABLE&rdquo; basis without warranties of any kind, whether express or implied. We do not warrant that the service will be uninterrupted, error-free, or completely secure. In no event shall {brand} be liable for any indirect, incidental, special, consequential, or punitive damages arising from your use of the service.
                </p>
            </div>

            <div class="section-card">
                <h2>7. Contact Information</h2>
                <p>
                    For inquiries regarding these Terms of Service, please reach out to:
                </p>
                <ul>
                    <li><strong>Email:</strong> <a href="mailto:{sup_email}">{sup_email}</a></li>
                    <li><strong>Telegram Support:</strong> <a href="https://t.me/{sup_u}" target="_blank" rel="noopener noreferrer">@{sup_u}</a></li>
                </ul>
            </div>
        </div>

        <!-- =============================================================
             RUSSIAN CONTENT (RU)
             ============================================================= -->
        <div id="content-ru" class="lang-content">
            <div class="md-legal-hero">
                <div class="md-eyebrow"><span class="md-eyebrow-dot"></span><span>Юридическое соглашение и условия</span></div>
                <h1>Условия использования</h1>
                <div class="md-legal-meta">
                    <span>Приложение: <strong>{brand}</strong></span>
                    <span>Дата обновления: <strong>20 ноября 2026 г.</strong></span>
                    <span>Домен: <strong>{domain}</strong></span>
                </div>
            </div>

            <div class="md-notice-box">
                <h4>Согласие с Условиями использования YouTube API</h4>
                <p>
                    {brand} использует сервисы YouTube API. Используя функции YouTube в {brand}, вы соглашаетесь соблюдать
                    <a href="https://www.youtube.com/t/terms" target="_blank" rel="noopener noreferrer">Условия использования YouTube</a> и
                    <a href="https://policies.google.com/privacy" target="_blank" rel="noopener noreferrer">Политику конфиденциальности Google</a>.
                </p>
            </div>

            <div class="section-card">
                <h2>1. Принятие условий</h2>
                <p>
                    Получая доступ к {brand} по адресу <strong>{base_url}</strong>, вы соглашаетесь соблюдать настоящие Условия использования.
                </p>
            </div>

            <div class="section-card">
                <h2>2. Описание сервиса</h2>
                <p>
                    {brand} предоставляет инструменты аналитики каналов YouTube в реальном времени, автоматизацию отложенной публикации видео и экосистему вознаграждений Telegram Stars.
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
                    По любым вопросам пишите нам на <a href="mailto:{sup_email}">{sup_email}</a> или в Telegram <a href="https://t.me/{sup_u}" target="_blank" rel="noopener noreferrer">@{sup_u}</a>.
                </p>
            </div>
        </div>

        <!-- =============================================================
             UZBEK CONTENT (UZ)
             ============================================================= -->
        <div id="content-uz" class="lang-content">
            <div class="md-legal-hero">
                <div class="md-eyebrow"><span class="md-eyebrow-dot"></span><span>Foydalanish Shartlari &amp; Qoidalari</span></div>
                <h1>Foydalanish Shartlari</h1>
                <div class="md-legal-meta">
                    <span>Ilova: <strong>{brand}</strong></span>
                    <span>Yangilangan sana: <strong>20-noyabr, 2026-yil</strong></span>
                    <span>Domen: <strong>{domain}</strong></span>
                </div>
            </div>

            <div class="md-notice-box">
                <h4>YouTube API Foydalanish Shartlari bilan Rozilik</h4>
                <p>
                    {brand} YouTube API xizmatlaridan foydalanadi. Ilovamizdagi YouTube funksiyalaridan foydalanish orqali siz
                    <a href="https://www.youtube.com/t/terms" target="_blank" rel="noopener noreferrer">YouTube Foydalanish Shartlari</a> va
                    <a href="https://policies.google.com/privacy" target="_blank" rel="noopener noreferrer">Google Maxfiylik Siyosati</a> ga rozilik bildirasiz.
                </p>
            </div>

            <div class="section-card">
                <h2>1. Shartlarni Qabul Qilish</h2>
                <p>
                    <strong>{base_url}</strong> manzilidagi {brand} platformasidan foydalanish orqali siz ushbu Foydalanish Shartlariga to&apos;liq rozilik bildirasiz.
                </p>
            </div>

            <div class="section-card">
                <h2>2. Xizmatlar Tavsifi</h2>
                <p>
                    {brand} mualliflarga YouTube kanallari tahlili, videolarni rejalashtirish, formatlarni konvertatsiya qilish va Telegram Stars mukofot tizimlarini taqdim etadi.
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
                <h2>4. Bog&apos;lanish</h2>
                <p>
                    Savollar bo&apos;yicha biz bilan bog&apos;laning: <a href="mailto:{sup_email}">{sup_email}</a> yoki Telegram: <a href="https://t.me/{sup_u}" target="_blank" rel="noopener noreferrer">@{sup_u}</a>.
                </p>
            </div>
        </div>
    </main>

    {render_editorial_footer()}
    {_lang_script("Terms of Service", "Условия использования", "Foydalanish Shartlari")}
</body>
</html>"""
