# -*- coding: utf-8 -*-
"""
Regression tests for MonoDeck rebrand, fast precompiled SPA serving,
AdSense/robots/legal parity, gzip compression middleware, and zero legacy leaks.
"""
from __future__ import annotations

import gzip
import os
from pathlib import Path
from unittest.mock import patch

import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

import legal_templates
import main
import reseller_api


ROOT_DIR = Path(__file__).resolve().parent.parent
DIST_DIR = ROOT_DIR / "static" / "dist"
LEGACY_STRINGS = (
    "CreatorFlow",
    "Bot Client",
    "botclient-d1jn.onrender.com",
    "AutoReply",
)
NEON_COLORS = (
    "#00F0FF",
    "#00f0ff",
    "#7342E2",
    "#7342e2",
    "#00f2fe",
    "#00F2FE",
    "#7928ca",
    "#7928CA",
)


def _build_wired_test_app() -> web.Application:
    """Wire public, SPA, legal, captcha, reseller docs, and static asset routes like start_web_server."""
    app = web.Application(
        client_max_size=2097152,
        middlewares=[main.security_and_rate_limit_middleware],
    )
    app.router.add_get("/", main.handle_health)
    app.router.add_get("/api/public-config", main.handle_api_public_config)
    app.router.add_get("/privacy", main.handle_privacy_page)
    app.router.add_get("/privacy-policy", main.handle_privacy_page)
    app.router.add_get("/privacy.html", main.handle_privacy_page)
    app.router.add_get("/terms", main.handle_terms_page)
    app.router.add_get("/terms-of-service", main.handle_terms_page)
    app.router.add_get("/terms.html", main.handle_terms_page)
    app.router.add_get("/robots.txt", main.handle_robots)
    app.router.add_get("/ads.txt", main.handle_ads_txt)
    for spa_path in (
        "/login",
        "/signin",
        "/studio",
        "/analytics",
        "/downloader",
        "/videos",
        "/cases",
        "/nfts",
    ):
        app.router.add_get(spa_path, main.handle_health)

    assets_dir = DIST_DIR / "assets"
    if assets_dir.is_dir():
        app.router.add_static("/assets", str(assets_dir), append_version=False)

    app.router.add_get("/favicon.ico", main.handle_favicon)
    app.router.add_get("/favicon.svg", main.handle_favicon)

    # Register reseller routes AFTER /robots.txt to verify reseller_api never shadows robots.txt
    reseller_api.setup_reseller_api_routes(app)
    app.router.add_get("/docs", reseller_api.handle_api_docs_html)
    app.router.add_get("/captcha", reseller_api.handle_captcha_demo_page)
    return app


@pytest.mark.asyncio
async def test_public_routes_head_and_get_return_200():
    app = _build_wired_test_app()
    routes = [
        "/",
        "/login",
        "/studio",
        "/downloader",
        "/cases",
        "/nfts",
        "/privacy",
        "/terms",
        "/docs",
        "/api/v1/docs",
        "/captcha",
        "/captcha/demo",
        "/robots.txt",
        "/ads.txt",
        "/favicon.svg",
        "/api/public-config",
    ]
    async with TestClient(TestServer(app)) as client:
        for path in routes:
            get_resp = await client.get(path)
            assert get_resp.status == 200, f"GET {path} returned {get_resp.status}"
            await get_resp.release()

            head_resp = await client.head(path)
            assert head_resp.status == 200, f"HEAD {path} returned {head_resp.status}"
            await head_resp.release()

        cfg_resp = await client.get("/api/public-config")
        cfg_data = await cfg_resp.json()
        assert cfg_data["brand"] == "MonoDeck"
        assert cfg_data["app_base_url"] == "https://monodeck.site"

        fav_resp = await client.get("/favicon.svg")
        assert "svg" in fav_resp.headers.get("Content-Type", "").lower()
        fav_body = await fav_resp.text()
        assert "#FF5A1F" in fav_body

        ads_resp = await client.get("/ads.txt")
        ads_body = await ads_resp.text()
        assert "4094396006908725" in ads_body


@pytest.mark.asyncio
async def test_robots_txt_not_overwritten_by_reseller_api():
    app = _build_wired_test_app()
    async with TestClient(TestServer(app)) as client:
        resp = await client.get("/robots.txt")
        assert resp.status == 200
        text = await resp.text()
        assert "User-agent: Mediapartners-Google" in text
        assert "Allow: /ads.txt" in text
        assert "MonoDeck" in text


@pytest.mark.asyncio
async def test_gzip_compression_enabled_for_html():
    app = _build_wired_test_app()
    async with TestClient(TestServer(app)) as client:
        for path in ("/", "/privacy"):
            resp = await client.get(
                path,
                headers={"Accept-Encoding": "gzip"},
                auto_decompress=False,
            )
            assert resp.status == 200
            assert resp.headers.get("Content-Encoding", "").lower() == "gzip"
            raw = await resp.read()
            decompressed = gzip.decompress(raw).decode("utf-8")
            assert "<html" in decompressed.lower()
            assert "MonoDeck" in decompressed


def test_legal_templates_preserve_all_trilingual_sections_and_google_links():
    privacy_html = legal_templates.get_privacy_html()
    terms_html = legal_templates.get_terms_html()

    # Google AdSense tags present on both legal pages
    for doc in (privacy_html, terms_html):
        assert "ca-pub-4094396006908725" in doc
        assert 'name="google-adsense-account"' in doc
        assert "MonoDeck" in doc
        for legacy in LEGACY_STRINGS:
            assert legacy not in doc
        for neon in NEON_COLORS:
            assert neon not in doc

    # Privacy Policy sections: EN (6), RU (5), UZ (5) + Limited Use + Instant Revocation
    for expected in (
        "1. Introduction &amp; Overview",
        "2. Google User Data &amp; YouTube API Scopes Accessed",
        "3. How We Use and Protect Google User Data",
        "4. Data Retention, Deletion &amp; Revoking Access",
        "5. Cookies &amp; Technical Telemetry",
        "6. Developer Contact Information",
        "1. Введение и обзор",
        "2. Данные Google и запрашиваемые разрешения YouTube API",
        "3. Защита данных и ограничение использования",
        "4. Отзыв доступа и удаление данных",
        "5. Контакты службы поддержки",
        "1. Kirish va Umumiy Ma&apos;lumot",
        "2. YouTube API orqali olinadigan Ma&apos;lumotlar va Vakolatlar",
        "3. Ma&apos;lumotlar Xavfsizligi va Kafolatlar",
        "4. Ruxsatni Bekor Qilish va Ma&apos;lumotlarni O&apos;chirish",
        "5. Bog&apos;lanish Ma&apos;lumotlari",
        "https://developers.google.com/terms/api-services-user-data-policy",
        "https://myaccount.google.com/permissions",
    ):
        assert expected in privacy_html

    # Terms of Service sections: EN (7), RU (4), UZ (4) + YouTube ToS + Google Privacy
    for expected in (
        "1. Acceptance of Terms",
        "2. Description of Services",
        "3. User Account &amp; Security",
        "4. Prohibited Conduct",
        "5. Intellectual Property &amp; Ownership",
        "6. Disclaimers &amp; Limitation of Liability",
        "7. Contact Information",
        "1. Принятие условий",
        "2. Описание сервиса",
        "3. Ограничения и правила",
        "4. Контактные данные",
        "1. Shartlarni Qabul Qilish",
        "2. Xizmatlar Tavsifi",
        "3. Foydalanuvchi Majburiyatlari",
        "4. Bog&apos;lanish",
        "https://www.youtube.com/t/terms",
        "https://policies.google.com/privacy",
    ):
        assert expected in terms_html


def test_precompiled_dist_no_babel_and_zero_legacy_or_neon_leaks():
    root_index = (ROOT_DIR / "index.html").read_text(encoding="utf-8")
    dist_index = (DIST_DIR / "index.html").read_text(encoding="utf-8")
    assert root_index == dist_index, "Root index.html must stay synced with static/dist/index.html"
    assert "babel.min.js" not in root_index
    assert "@babel/standalone" not in root_index
    assert "ca-pub-4094396006908725" in root_index

    public_files = [
        ROOT_DIR / "index.html",
        ROOT_DIR / "captcha_demo.html",
        ROOT_DIR / "captcha_widget.js",
        ROOT_DIR / "favicon.svg",
    ]
    assets_dir = DIST_DIR / "assets"
    assert assets_dir.is_dir(), "Built frontend bundle directory static/dist/assets is missing"
    bundle_files = [
        p for p in assets_dir.iterdir()
        if p.is_file() and p.suffix in (".js", ".css")
    ]
    assert len(bundle_files) >= 2, "Expected built JS and CSS assets in static/dist/assets"
    public_files.extend(bundle_files)

    for file_path in public_files:
        text = file_path.read_text(encoding="utf-8")
        assert "babel.min.js" not in text, f"Found babel.min.js in {file_path}"
        for legacy in LEGACY_STRINGS:
            assert legacy not in text, f"Found legacy string {legacy!r} in {file_path}"
        for neon in NEON_COLORS:
            assert neon not in text, f"Found neon color {neon!r} in {file_path}"


@pytest.mark.asyncio
async def test_public_ssr_html_pages_clean_brand_and_no_neon():
    app = _build_wired_test_app()
    ssr_paths = ("/", "/privacy", "/terms", "/docs", "/captcha")
    async with TestClient(TestServer(app)) as client:
        for path in ssr_paths:
            resp = await client.get(path)
            assert resp.status == 200
            html_text = await resp.text()
            for legacy in LEGACY_STRINGS:
                assert legacy not in html_text, f"{legacy!r} leaked on {path}"
            for neon in NEON_COLORS:
                assert neon not in html_text, f"{neon!r} leaked on {path}"
            assert "babel.min.js" not in html_text, f"babel.min.js leaked on {path}"


@pytest.mark.asyncio
async def test_api_stats_fast_nonblocking_with_mock_db():
    import time as _t
    tok = "monodeck_test_stats_token_999111"
    main._AUTH_TOKENS[tok] = {"tg_user_id": 999111, "created_at": _t.time()}
    main._stats_cache.pop("999111_default", None)
    mock_conn = {
        "access_token": "tok",
        "yt_channel_id": "UC_TEST_123",
        "yt_channel_title": "MonoDeck QA",
        "yt_channel_username": "@monodeck_qa",
        "channel_thumbnail_url": "",
        "subscriber_count": 4200,
    }
    try:
        with patch("database.get_yt_connection", return_value=mock_conn), \
             patch.object(main, "_refresh_stats_bg"):
            app = _build_wired_test_app()
            app.router.add_get("/api/stats", main.handle_api_stats)
            async with TestClient(TestServer(app)) as client:
                t0 = _t.monotonic()
                resp = await client.get(
                    "/api/stats",
                    headers={"Cookie": f"cf_auth_token={tok}"},
                )
                elapsed = _t.monotonic() - t0
                assert resp.status == 200
                assert elapsed < 1.0
                data = await resp.json()
                assert data["stale"] is True
                assert data["channel_title"] == "MonoDeck QA"
                assert data["subscribers"] == 4200
    finally:
        main._AUTH_TOKENS.pop(tok, None)
        main._stats_cache.pop("999111_default", None)


@pytest.mark.asyncio
async def test_database_quota_circuit_breaker_fails_fast_without_blocking():
    import time as _t
    import database
    import config as _cfg

    orig_pool = database._DB_POOL
    database._DB_POOL = None
    database.reset_db_cooldown()
    quota_err = RuntimeError("ERROR: Your account or project has exceeded the quota. Upgrade your plan to increase limits.")

    try:
        with patch.object(database, "DATABASE_URL", "postgresql://user:pass@localhost:5432/testdb"), \
             patch.object(_cfg, "DATABASE_URL", "postgresql://user:pass@localhost:5432/testdb"), \
             patch.object(database, "ThreadedConnectionPool", side_effect=quota_err) as pool_mock, \
             patch.object(database.psycopg2, "connect", side_effect=quota_err) as conn_mock:
            t0 = _t.monotonic()
            results = [database.get_db() for _ in range(25)]
            elapsed = _t.monotonic() - t0

            assert all(r is None for r in results)
            assert elapsed < 0.3
            assert database.is_db_in_cooldown() is True
            assert pool_mock.call_count <= 1
            assert conn_mock.call_count <= 1

            app = _build_wired_test_app()
            async with TestClient(TestServer(app)) as client:
                t_web = _t.monotonic()
                for path in ("/", "/privacy"):
                    resp = await client.get(path)
                    assert resp.status == 200
                    await resp.release()
                assert (_t.monotonic() - t_web) < 0.5
    finally:
        database.reset_db_cooldown()
        database._DB_POOL = orig_pool
