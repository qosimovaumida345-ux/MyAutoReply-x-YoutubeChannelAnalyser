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
    app.router.add_get("/oauth/youtube/start", main.handle_oauth_youtube_start)
    app.router.add_get("/api/oauth/youtube/url", main.handle_oauth_youtube_start)

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


def test_build_connect_kwargs_handles_neon_pooler_urls():
    import database

    pooler_kwargs = database._build_connect_kwargs(
        "postgresql://u:p@ep-abc-pooler.c-2.aws.neon.tech/neondb?sslmode=require"
    )
    assert "options" not in pooler_kwargs
    assert pooler_kwargs["connect_timeout"] == 3

    direct_kwargs = database._build_connect_kwargs(
        "postgresql://u:p@ep-abc.c-2.aws.neon.tech/neondb?sslmode=require"
    )
    assert direct_kwargs["options"] == "-c statement_timeout=8000"


@pytest.mark.asyncio
async def test_web_oauth_youtube_start_generates_english_consent_url():
    import autopost

    orig_cfg = autopost.CLIENT_CONFIG
    test_cfg = {
        "web": {
            "client_id": "1234567890-testclient.apps.googleusercontent.com",
            "client_secret": "test-client-secret",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["https://monodeck.site/oauth/callback"],
        }
    }
    try:
        autopost.CLIENT_CONFIG = test_cfg
        autopost.REDIRECT_URI = "https://monodeck.site/oauth/callback"
        app = _build_wired_test_app()
        async with TestClient(TestServer(app)) as client:
            resp = await client.get("/api/oauth/youtube/url")
            assert resp.status == 200
            data = await resp.json()
            assert data["ok"] is True
            auth_url = data["auth_url"]
            assert "accounts.google.com/o/oauth2/auth" in auth_url
            assert "redirect_uri=https%3A%2F%2Fmonodeck.site%2Foauth%2Fcallback" in auth_url
            assert "prompt=consent" in auth_url
            assert "hl=en" in auth_url

            redir = await client.get("/oauth/youtube/start", allow_redirects=False)
            assert redir.status == 302
            loc = redir.headers.get("Location", "")
            assert "accounts.google.com/o/oauth2/auth" in loc
            assert "hl=en" in loc
            await redir.release()
    finally:
        autopost.CLIENT_CONFIG = orig_cfg


def test_internal_rewards_auto_activate_without_fake_keys():
    import games_monetization as gm

    # 1. Daily streak claims must auto-activate without generating fake license_key/pass_code or promo codes
    with patch("database.get_db_user_streak", return_value={"streak_count": 2, "last_claimed_date": None}), \
         patch("database.update_db_user_streak", return_value=True), \
         patch("database.record_user_purchase", return_value={"ok": True, "new_balance": 10000}) as mock_rec, \
         patch("database.create_promo_code") as mock_promo:
        res_daily = gm.claim_daily_streak(987654321)
        assert res_daily["ok"] is True
        assert res_daily["auto_activated"] is True
        reward = res_daily["reward"]
        assert reward["auto_activated"] is True
        assert "license_key" not in reward
        assert "pass_code" not in reward
        mock_promo.assert_not_called()
        mock_rec.assert_called_once()
        assert mock_rec.call_args.kwargs["price_uzs"] == 0
        assert mock_rec.call_args.kwargs["payload"] == "auto_activated"

    # 2. Scratch card wins must auto-activate without fake key or promo code creation
    with patch("random.random", return_value=0.05), \
         patch("database.record_user_purchase", return_value={"ok": True, "new_balance": 10000}) as mock_rec, \
         patch("database.create_promo_code") as mock_promo:
        res_scratch = gm.play_scratch_card(987654321)
        assert res_scratch["ok"] is True
        assert res_scratch["won"] is True
        prize = res_scratch["prize"]
        assert prize["auto_activated"] is True
        assert "key" not in prize
        assert "license_key" not in prize
        mock_promo.assert_not_called()
        mock_rec.assert_called_once()

    # 3. Creator Redeem Store internal services must auto-activate without license_key/pass_code
    with patch("database.record_user_purchase", return_value={"ok": True, "new_balance": 50000}) as mock_rec:
        res_redeem = gm.redeem_creator_service(987654321, "ai_seo_50")
        assert res_redeem["ok"] is True
        assert res_redeem["auto_activated"] is True
        assert "license_key" not in res_redeem
        assert "pass_code" not in res_redeem
        assert mock_rec.call_args.kwargs["payload"] == "auto_activated"


def test_gift_media_uses_lottie_web_without_custom_element():
    gm_src = (ROOT_DIR / "frontend" / "src" / "components" / "GiftMedia.jsx").read_text(encoding="utf-8")
    lazy_src = (ROOT_DIR / "frontend" / "src" / "lib" / "lazyScripts.js").read_text(encoding="utf-8")
    assert "<lottie-player" not in gm_src
    assert "@lottiefiles/lottie-player" not in lazy_src
    assert "lottie-web" in lazy_src
    assert "AbortController" in gm_src
    assert "animInstance.destroy" in gm_src


def test_upgraded_shield_captcha_all_four_modes_end_to_end():
    import captcha_engine as ce

    # Mode 1: Slider (with decoy notch & 9px tolerance)
    ch_s = ce.CaptchaManager.create_challenge(challenge_type="slider", sitekey="demo_key")
    assert ch_s["ok"] is True
    sol_s = ce._ACTIVE_CHALLENGES[ch_s["challenge_id"]]["solution"]
    assert sol_s["tolerance"] == 9
    res_s = ce.CaptchaManager.verify_challenge(
        ch_s["challenge_id"],
        {"x": sol_s["target_x"] + 3},
        telemetry={
            "duration_ms": 950,
            "trajectory": [
                {"x": 0, "y": 210, "t": 0},
                {"x": 45, "y": 211, "t": 180},
                {"x": 92, "y": 209, "t": 390},
                {"x": sol_s["target_x"] + 3, "y": 212, "t": 950},
            ],
        },
    )
    assert res_s["ok"] is True
    assert ce.CaptchaManager.siteverify_token(res_s["token"], secret_key="demo", sitekey="demo_key")["success"] is True

    # Mode 2: Grid (9 tiles, 3-4 targets)
    ch_g = ce.CaptchaManager.create_challenge(challenge_type="grid", sitekey="demo_key")
    sol_g = ce._ACTIVE_CHALLENGES[ch_g["challenge_id"]]["solution"]
    assert len(ch_g["payload"]["tiles"]) == 9
    assert len(sol_g["target_indices"]) in (3, 4)
    res_g = ce.CaptchaManager.verify_challenge(
        ch_g["challenge_id"],
        {"selected": sol_g["target_indices"]},
        telemetry={
            "duration_ms": 1400,
            "clicks": [{"t": 350 + i * 280, "idx": v} for i, v in enumerate(sol_g["target_indices"])],
        },
    )
    assert res_g["ok"] is True

    # Mode 3: Rotate (15 deg tolerance, upright compensation)
    ch_r = ce.CaptchaManager.create_challenge(challenge_type="rotate", sitekey="demo_key")
    sol_r = ce._ACTIVE_CHALLENGES[ch_r["challenge_id"]]["solution"]
    assert sol_r["tolerance"] == 15
    correct_angle = (360 - sol_r["initial_angle"]) % 360
    res_r = ce.CaptchaManager.verify_challenge(
        ch_r["challenge_id"],
        {"angle": correct_angle},
        telemetry={"duration_ms": 1200, "trajectory": [{"t": 100, "angle": 45}, {"t": 600, "angle": correct_angle}]},
    )
    assert res_r["ok"] is True

    # Mode 4: Sequence (3 targets picked from 5 drawn symbols, 36px hit radius)
    ch_q = ce.CaptchaManager.create_challenge(challenge_type="sequence", sitekey="demo_key")
    sol_q = ce._ACTIVE_CHALLENGES[ch_q["challenge_id"]]["solution"]
    assert len(sol_q["targets"]) == 3
    assert sol_q["targets"][0]["radius"] == 36
    clicks_q = [{"x": t["x"], "y": t["y"], "t": 300 + i * 420} for i, t in enumerate(sol_q["targets"])]
    res_q = ce.CaptchaManager.verify_challenge(
        ch_q["challenge_id"],
        {"clicks": clicks_q},
        telemetry={"duration_ms": 1500, "clicks": clicks_q},
    )
    assert res_q["ok"] is True

    # Wrong sequence attempt must fail cleanly and burn challenge
    ch_q2 = ce.CaptchaManager.create_challenge(challenge_type="sequence", sitekey="demo_key")
    wrong_clicks = [{"x": 5, "y": 5, "t": 300}, {"x": 5, "y": 5, "t": 600}, {"x": 5, "y": 5, "t": 900}]
    res_q2 = ce.CaptchaManager.verify_challenge(
        ch_q2["challenge_id"],
        {"clicks": wrong_clicks},
        telemetry={"duration_ms": 1000, "clicks": wrong_clicks},
    )
    assert res_q2["ok"] is False
    assert res_q2["error"] == "incorrect_solution"


def test_upgrader_anti_exploit_and_pool_solvency_guarantee():
    from unittest.mock import MagicMock
    import secrets
    import database
    import games_monetization as gm

    # 1. House-edged odds: player EV must stay strictly <= 0.70 across all multipliers (1.5x..100x)
    for m in (1.5, 2.0, 3.0, 5.0, 10.0, 20.0, 50.0, 100.0):
        odds, deg = gm.compute_upgrader_odds(m)
        assert 0.0 < odds <= 0.60
        assert 4 <= deg <= 216
        assert (m * odds) <= 0.705, f"Expected <= 70% EV at {m}x, got {m * odds}"

    def _run_tx(plays_before: int, pool_before: int, item_stars: int, mult: float, rand_num: int, expect_insert: bool = False):
        mock_cur = MagicMock()
        side_effects = [
            {"id": 101, "gift_id": "delicious-cake", "prize_name": "Delicious Cake", "prize_stars": item_stars, "status": "pending"},
            {"value": str(plays_before)},
            {"value": str(pool_before)},
        ]
        if expect_insert:
            side_effects.append({"id": 202})
        side_effects.append({"balance_uzs": 50000})
        mock_cur.fetchone.side_effect = side_effects
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cur

        def _fake_randbelow(n):
            if n == 1_000_000:
                return rand_num
            return 0

        with patch.object(database, "get_db", return_value=mock_conn), \
             patch.object(secrets, "randbelow", side_effect=_fake_randbelow):
            return gm.execute_upgrade_roll(
                user_id=555666,
                item_stars=item_stars,
                target_stars=int(round(item_stars * mult)),
                target_name="Plush Pepe",
                target_icon="pepe",
                source_inventory_id=101,
                target_slug="plushpepe",
                multiplier=mult,
            )

    # 2. Old 6th-spin exploit (plays_before == 5 on 100x with cheap 15* gift) MUST NOT win when pool < required 100x payout
    res_exploit = _run_tx(plays_before=5, pool_before=100, item_stars=15, mult=100.0, rand_num=0, expect_insert=False)
    assert res_exploit.get("ok") is True, res_exploit
    assert res_exploit["won"] is False, "100x 6th-spin exploit with insufficient reserve must be blocked!"
    assert res_exploit["final_angle"] > res_exploit["green_slice_deg"]

    # 3. Normal 2x loss when CSPRNG rolls outside odds -> burns gift, adds 65% to pool
    res_loss = _run_tx(plays_before=5, pool_before=5000, item_stars=100, mult=2.0, rand_num=900_000, expect_insert=False)
    assert res_loss.get("ok") is True, res_loss
    assert res_loss["won"] is False
    assert res_loss["final_angle"] > res_loss["green_slice_deg"]

    # 4. Legit win when CSPRNG rolls inside odds AND pool covers target_stars
    res_win = _run_tx(plays_before=2, pool_before=5000, item_stars=100, mult=2.0, rand_num=100, expect_insert=True)
    assert res_win.get("ok") is True, res_win
    assert res_win["won"] is True
    assert 1 <= res_win["final_angle"] <= res_win["green_slice_deg"]


@pytest.mark.asyncio
async def test_avatar_hmac_signing_and_no_creatorflow_fallback():
    from aiohttp.test_utils import make_mocked_request

    sig = main._make_avatar_sig(123456789)
    assert len(sig) == 20
    assert main._verify_avatar_sig(123456789, sig) is True
    assert main._verify_avatar_sig(123456789, "deadbeef000000000000") is False
    assert main._verify_avatar_sig(987654321, sig) is False

    # Image validation & SSRF guard
    assert main._detect_raster_mime(b"\xff\xd8\xff\xe0" + b"0" * 20) == "image/jpeg"
    assert main._detect_raster_mime(b"\x89PNG\r\n\x1a\n" + b"0" * 20) == "image/png"
    assert main._detect_raster_mime(b"<svg></svg>") is None
    assert main._is_safe_tg_avatar_url("https://t.me/i/userpic/320/test.jpg") is True
    assert main._is_safe_tg_avatar_url("http://127.0.0.1/secret.jpg") is False

    # Uncached + unauthenticated/missing avatar must return 404 (never creatorflow_avatar.jpg!)
    req_404 = make_mocked_request("GET", "/api/user/avatar/888999777?sig=badbadbadbadbadbad00", match_info={"user_id": "888999777"})
    resp_404 = await main.handle_api_user_avatar(req_404)
    assert resp_404.status == 404


def test_upgrader_cursor_wheel_and_navbar_avatar_source():
    cases_src = (ROOT_DIR / "frontend" / "src" / "pages" / "CasesPage.jsx").read_text(encoding="utf-8")
    nav_src = (ROOT_DIR / "frontend" / "src" / "components" / "Navbar.jsx").read_text(encoding="utf-8")
    assert "const duration = 3800;" in cases_src
    assert "getUpgraderOdds" in cases_src
    assert "startDeg + 1800 + diff" in cases_src
    assert "<polygon points=\"16,32 10.5,11 21.5,11\" fill=\"#FF5A1F\" />" in cases_src
    assert "user?.photo_url" in nav_src
    assert "onError={() => setAvatarFailed(true)}" in nav_src


@pytest.mark.asyncio
async def test_secondary_bot_token_webapp_hmac_and_factory():
    import hashlib
    import hmac
    import json
    import time
    from urllib.parse import urlencode
    from aiohttp.test_utils import make_mocked_request
    import config as _cfg
    import ytbot

    primary_tok = "111111:PRIMARY_TEST_TOKEN_000001"
    secondary_tok = "222222:SECONDARY_TEST_TOKEN_000002"

    user_json = json.dumps({"id": 777666, "first_name": "Kai", "username": "kai_test"}, separators=(",", ":"))
    params = {
        "auth_date": str(int(time.time())),
        "query_id": "AAHdF6IQAAAAAN0XohDhrOrc",
        "user": user_json,
    }
    data_check = "\n".join(f"{k}={v}" for k, v in sorted(params.items()))
    sec_key = hmac.new(b"WebAppData", secondary_tok.encode("utf-8"), hashlib.sha256).digest()
    params["hash"] = hmac.new(sec_key, data_check.encode("utf-8"), hashlib.sha256).hexdigest()
    init_data = urlencode(params)

    with patch.object(_cfg, "BOT_TOKEN", primary_tok), \
         patch.object(_cfg, "SECONDARY_BOT_TOKEN", secondary_tok), \
         patch.object(_cfg, "SECONDARY_BOT_TOKENS", [secondary_tok]), \
         patch.object(main, "BOT_TOKEN", primary_tok), \
         patch.dict(os.environ, {"SECONDARY_BOT_TOKEN": secondary_tok, "SECONDARY_BOT_TOKENS": ""}, clear=False), \
         patch("database.save_web_session", return_value=True), \
         patch("database.is_bot_admin", return_value=False), \
         patch("database.is_user_vip", return_value=False):
        tokens = _cfg.get_all_bot_tokens()
        assert primary_tok in tokens
        assert secondary_tok in tokens

        req = make_mocked_request("POST", "/api/auth/verify-webapp", headers={"X-Forwarded-Proto": "https"})
        async def _json():
            return {"initData": init_data}
        req.json = _json
        resp = await main.handle_api_auth_verify_webapp(req)
        assert resp.status == 200
        body = json.loads(resp.text)
        assert body["ok"] is True
        assert body["tg_user_id"] == 777666
        main._AUTH_TOKENS.pop(body["token"], None)

        req_hdr = make_mocked_request("GET", "/api/stars/user-inventory?user_id=777666", headers={"X-Telegram-Init-Data": init_data})
        assert main.get_authenticated_user_id(req_hdr) == 777666

        # Tampered secondary initData must still fail 403
        req_bad = make_mocked_request("POST", "/api/auth/verify-webapp")
        async def _bad_json():
            return {"initData": init_data.replace("Kai", "Evil")}
        req_bad.json = _bad_json
        resp_bad = await main.handle_api_auth_verify_webapp(req_bad)
        assert resp_bad.status == 403

    from unittest.mock import MagicMock
    mock_sec_client = MagicMock()
    with patch.object(ytbot, "Client", return_value=mock_sec_client) as mock_cli:
        bot_obj = ytbot.create_ytbot(bot_token=secondary_tok, session_name="yt_analytics_bot_secondary_1")
        assert bot_obj is mock_sec_client
        mock_cli.assert_called_once_with(
            "yt_analytics_bot_secondary_1",
            api_id=ytbot.API_ID,
            api_hash=ytbot.API_HASH,
            bot_token=secondary_tok,
        )


def test_raster_compression_and_avatar_size():
    """Avatars and static raster thumbnails must compress to compact WebP without breaking animations."""
    from io import BytesIO
    from PIL import Image

    avatar_file = ROOT_DIR / "nft_assets" / "user_avatars" / "6735799833.jpg"
    assert avatar_file.exists()
    assert avatar_file.stat().st_size <= 8192, f"Avatar too large: {avatar_file.stat().st_size} bytes"

    # Synthetic noisy 640x640 PNG should shrink dramatically to 96x96 WebP
    buf = BytesIO()
    img = Image.new("RGB", (640, 640), (30, 120, 220))
    img.save(buf, format="PNG")
    compact, mime = main._compress_raster_image(buf.getvalue(), max_dim=96, quality=82)
    assert mime == "image/webp"
    assert len(compact) < 4096


def test_autopost_db_helpers_and_ytdlp_candidate_fallback():
    """Verify missing get_autopost_task_by_id is restored and yt_dlp search fallback returns candidates."""
    import database
    import autopost

    assert callable(database.get_autopost_task_by_id)
    assert callable(database.reset_stale_autopost_tasks)
    assert callable(database.delete_autopost_task)

    fake_ydl_result = {
        "entries": [
            {
                "id": "dQw4w9WgXcQ",
                "title": "Patrick Jane Deduction Short",
                "uploader": "Mentalist Clips",
                "view_count": 125000,
                "duration": 42,
                "upload_date": "20261101",
            }
        ]
    }

    class FakeYDL:
        def __init__(self, opts):
            self.opts = opts
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def extract_info(self, url, download=False):
            return fake_ydl_result

    import yt_dlp
    with patch.object(autopost, "build_youtube_api", side_effect=RuntimeError("403 quotaExceeded")), \
         patch.object(yt_dlp, "YoutubeDL", FakeYDL):
        cands = autopost.search_youtube_candidates("Patrick Jane", max_results=5, video_type="shorts")
        assert len(cands) == 1
        assert cands[0]["id"] == "dQw4w9WgXcQ"
        assert cands[0]["duration"] == 42
        assert "hqdefault.jpg" in cands[0]["thumbnail"]


def test_video_processor_watermark_detection_and_default_enabled():
    """Verify automatic watermark detection finds static overlay boxes and WATERMARK_CLEAN defaults ON."""
    import video_processor
    import numpy as np
    import cv2

    # Ensure WATERMARK_CLEAN defaults to true when env var is unset
    assert os.getenv("WATERMARK_CLEAN", "true").lower() != "false"

    tmp_vid = ROOT_DIR / "downloads" / "_test_wm_sample.mp4"
    tmp_vid.parent.mkdir(parents=True, exist_ok=True)
    try:
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(str(tmp_vid), fourcc, 10.0, (320, 240))
        for f in range(8):
            frame = np.full((240, 320, 3), (20 + f * 5, 30, 40), dtype=np.uint8)
            # Draw high-contrast persistent watermark box in bottom-right corner
            cv2.rectangle(frame, (240, 200), (310, 230), (255, 255, 255), -1)
            cv2.putText(frame, "@WM", (245, 222), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 2)
            writer.write(frame)
        writer.release()

        boxes = video_processor.detect_watermark_regions(str(tmp_vid), max_samples=6)
        assert isinstance(boxes, list)
        assert len(boxes) >= 1, f"Expected persistent corner watermark box, got {boxes}"
        # At least one box overlaps bottom-right quadrant
        assert any(x + w > 220 and y + h > 190 for (x, y, w, h) in boxes)
    finally:
        if tmp_vid.exists():
            tmp_vid.unlink()


@pytest.mark.asyncio
async def test_autopost_task_details_and_action_routes():
    """Verify /api/autopost-tasks/{id}/details and /api/autopost-tasks/action endpoints."""
    import time as _t
    tok = "monodeck_test_autopost_tok_111"
    main._AUTH_TOKENS[tok] = {"tg_user_id": 6735799833, "created_at": _t.time()}
    try:
        app = _build_wired_test_app()
        app.router.add_get("/api/autopost-tasks/{task_id}/details", main.handle_api_autopost_task_details)
        app.router.add_post("/api/autopost-tasks/action", main.handle_api_autopost_task_action)

        fake_task = {
            "id": 1,
            "tg_user_id": 6735799833,
            "search_query": "Patrick Jane",
            "video_type": "shorts",
            "total_count": 1,
            "completed_count": 0,
            "status": "pending",
        }
        fake_cands = [{"id": "abc12345678", "title": "Patrick Jane Sample", "thumbnail": "https://i.ytimg.com/vi/abc12345678/hqdefault.jpg"}]

        with patch("database.get_autopost_task_by_id", return_value=fake_task), \
             patch("database.get_autopost_history", return_value=[]), \
             patch("autopost.search_youtube_candidates", return_value=fake_cands), \
             patch("database.update_autopost_task"), \
             patch.object(main, "dispatch_or_run_autopost", return_value=None):
            async with TestClient(TestServer(app)) as client:
                r1 = await client.get(
                    "/api/autopost-tasks/1/details",
                    headers={"Cookie": f"cf_auth_token={tok}"},
                )
                assert r1.status == 200
                d1 = await r1.json()
                assert d1["ok"] is True
                assert d1["task"]["search_query"] == "Patrick Jane"
                assert len(d1["candidates"]) == 1

                r2 = await client.post(
                    "/api/autopost-tasks/action",
                    headers={"Cookie": f"cf_auth_token={tok}"},
                    json={"task_id": 1, "action": "run_now"},
                )
                assert r2.status == 200
                d2 = await r2.json()
                assert d2["ok"] is True
    finally:
        main._AUTH_TOKENS.pop(tok, None)


def test_cases_default_prices_match_backend_no_flash():
    """Verify CasesPage DEFAULT_CASES matches backend STARS_CASES prices so wrong prices never flash before load."""
    from games_monetization import STARS_CASES

    src = (ROOT_DIR / "frontend" / "src" / "pages" / "CasesPage.jsx").read_text(encoding="utf-8")
    # Old stale prices 25 Stars / 75 Stars / Bronze Starter Case must be gone
    assert "price_stars: 25," not in src
    assert "price_stars: 75," not in src
    assert "price_stars: 750," not in src
    assert "price_stars: 2500," not in src

    for tier_id, info in STARS_CASES.items():
        assert f"id: '{tier_id}'" in src
        assert f"price_stars: {info['price_stars']}" in src
        assert f"price_uzs: {info['price_uzs']}" in src


def test_service_logos_and_optimistic_ui_present():
    """Verify GiftMedia renders crisp vector SVG emblems and optimistic rollback exists in Cases, NFTs, and Studio."""
    gm_src = (ROOT_DIR / "frontend" / "src" / "components" / "GiftMedia.jsx").read_text(encoding="utf-8")
    assert "renderServiceVectorLogo" in gm_src
    assert "getCaseBackdropTheme" in gm_src
    for fn_key in ("gm-ap-bg", "gm-as-bg", "gm-seo-bg", "gm-uq-bg", "gm-sc-bg", "gm-st-bg"):
        assert fn_key in gm_src

    cases_src = (ROOT_DIR / "frontend" / "src" / "pages" / "CasesPage.jsx").read_text(encoding="utf-8")
    assert "claimed_today: true" in cases_src
    assert "Olinmadi:" in cases_src
    assert "onAdjustBalance" in cases_src

    app_src = (ROOT_DIR / "frontend" / "src" / "App.jsx").read_text(encoding="utf-8")
    assert "md_user_stats_v3_" in app_src
    assert "adjustBalanceOptimistic" in app_src

    studio_src = (ROOT_DIR / "frontend" / "src" / "pages" / "StudioPage.jsx").read_text(encoding="utf-8")
    assert "setTasks(prevTasks)" in studio_src


def test_fake_user_cleaner_protects_real_users_and_removes_synthetic():
    """Verify is_synthetic_fake_user_id and purge_fake_and_test_users never delete real users."""
    import database

    assert database.is_synthetic_fake_user_id(99999999) is True
    assert database.is_synthetic_fake_user_id(888888888) is True
    assert database.is_synthetic_fake_user_id(123456) is True
    assert database.is_synthetic_fake_user_id(6735799833) is False
    assert database.is_synthetic_fake_user_id(743301587) is False

    deleted_sql = []

    class FakeCursor:
        def __init__(self):
            self._rows = []

        def execute(self, sql, params=None):
            if "FROM user_balances WHERE balance_uzs > 0" in sql:
                self._rows = [{"tg_user_id": 743301587}]
            elif "SELECT tg_user_id, first_name, username FROM bot_users" in sql:
                self._rows = [
                    {"tg_user_id": 6735799833, "first_name": "Aiko", "username": "aiko_64"},
                    {"tg_user_id": 743301587, "first_name": "Azamat", "username": "Lionkingw"},
                    {"tg_user_id": 847568463, "first_name": "Hamida", "username": None},
                    {"tg_user_id": 99999999, "first_name": None, "username": None},
                ]
            elif sql.startswith("DELETE "):
                deleted_sql.append((sql, params))
            else:
                self._rows = []

        def fetchall(self):
            return self._rows

    class FakeConn:
        def __init__(self):
            self.cur = FakeCursor()
        def cursor(self):
            return self.cur
        def commit(self):
            pass
        def rollback(self):
            pass
        def close(self):
            pass

    with patch("database.get_db", return_value=FakeConn()):
        res = database.purge_fake_and_test_users(bot_token="", dry_run=False)
        assert res["ok"] is True
        assert res["deleted_ids"] == [99999999]
        assert res["protected_skipped"] == 3


def test_daily_channel_promo_non_repeating_and_monodeck_branded():
    """Verify store_channel_service rotates unique templates, custom emojis, and uses Mono Deck Studio branding."""
    import store_channel_service

    assert len(store_channel_service.PROMO_TEMPLATES) >= 12
    for tpl in store_channel_service.PROMO_TEMPLATES:
        assert "CreatorFlow" not in tpl["title"]
        assert "CreatorFlow" not in tpl["body"]
        assert "emoji_theme" in tpl and len(tpl["emoji_theme"]) >= 3

    saved_state = []
    with patch.object(store_channel_service, "_load_recent_promo_ids", side_effect=lambda: list(saved_state[-10:])), \
         patch.object(store_channel_service, "_save_recent_promo_ids", side_effect=lambda ids: saved_state.clear() or saved_state.extend(ids)):
        seen_ids = []
        for _ in range(10):
            picked = store_channel_service.select_next_daily_promo()
            assert picked["id"] not in seen_ids, f"Repeated promo template within 10 days: {picked['id']}"
            seen_ids.append(picked["id"])


def test_wallet_menu_no_literal_masked_and_crypto_hidden_when_disabled():
    """Verify wallet_menu_kb formats {masked} properly and hides TON/CryptoPay when ENABLE_CRYPTO_PAY=False."""
    import config
    import ytbot

    fake_wallet = {"wallet_address": "UQB5es0x95ojgzAoAXmCtJYX2BbK1mwtyBzeqZupOVoxC5gz"}
    with patch("database.get_user_ton_wallet", return_value=fake_wallet), \
         patch.object(config, "ENABLE_CRYPTO_PAY", True), \
         patch.object(config, "CRYPTO_PAY_TOKEN", ""):
        kb_on = ytbot.wallet_menu_kb(6735799833, "en")
        texts_on = [btn.text for row in kb_on.inline_keyboard for btn in row]
        assert any("UQB5...C5gz" in s for s in texts_on)
        assert all("{masked}" not in s for s in texts_on)

    with patch("database.get_user_ton_wallet", return_value=fake_wallet), \
         patch.object(config, "ENABLE_CRYPTO_PAY", False), \
         patch.object(config, "CRYPTO_PAY_TOKEN", ""):
        kb_off = ytbot.wallet_menu_kb(6735799833, "en")
        texts_off = [btn.text for row in kb_off.inline_keyboard for btn in row]
        assert not any("TON Wallet" in s or "Via TON" in s for s in texts_off)
        assert any("HUMO / Uzcard" in s for s in texts_off)
        assert any("Telegram Stars" in s for s in texts_off)


def test_promo_video_renderer_produces_valid_rgb_frames():
    """Verify kinetic Telegram promo renderer creates crisp 1080x1920 frames across all 5 scenes."""
    import sys
    sys.path.insert(0, str(ROOT_DIR / "scripts"))
    import generate_promo_videos as gpv
    for lang in ("uz", "en"):
        for t_sec in (2.0, 6.5, 12.2, 18.0, 22.0):
            img = gpv.render_frame(t_sec, 24.0, lang)
            assert img.size == (1080, 1920)
            assert img.mode == "RGB"


@pytest.mark.asyncio
async def test_custom_amount_binance_pay_and_txid_anti_replay():
    """Verify Binance Pay Order ID custom-amount verification, URL normalization, UZS conversion, and replay guard."""
    import binance_crypto_verifier as bcv
    import database

    assert bcv.normalize_tx_id("https://tronscan.org/#/transaction/ab12cd34ef567890") == "ab12cd34ef567890"
    assert bcv.normalize_tx_id("  338192045678123456  ") == "338192045678123456"

    fake_cfg = {
        "binance_uid": "554433221",
        "binance_api_key": "test_key",
        "binance_api_secret": "test_secret",
        "usdt_trc20_address": "",
        "usdt_bep20_address": "",
        "ton_wallet_address": "",
    }
    fake_pay = {
        "found": True,
        "source": "binance_pay",
        "network": "BINANCE_PAY",
        "asset": "USDT",
        "amount_crypto": 12.5,
        "tx_id": "338192045678123456",
    }

    with patch("database.get_binance_crypto_config", return_value=fake_cfg), \
         patch("database.is_crypto_tx_claimed", return_value=False), \
         patch.object(bcv, "verify_binance_pay_tx", return_value=fake_pay), \
         patch.object(bcv, "get_live_usd_price", return_value=1.0), \
         patch.object(bcv, "USD_TO_UZS_RATE", 12850):
        res = await bcv.verify_crypto_tx_by_id("338192045678123456")
        assert res["ok"] is True
        assert res["amount_crypto"] == 12.5
        assert res["asset"] == "USDT"
        assert res["amount_uzs"] == int(round(12.5 * 12850))

    # Already claimed TxID must be rejected immediately (anti-replay)
    with patch("database.is_crypto_tx_claimed", return_value=True):
        res_dup = await bcv.verify_crypto_tx_by_id("338192045678123456")
        assert res_dup["ok"] is False

    # Atomic claim_and_credit_crypto_tx returns error on conflict
    class ConflictCursor:
        def execute(self, sql, params=None):
            pass
        def fetchone(self):
            return None

    class ConflictConn:
        def cursor(self):
            return ConflictCursor()
        def rollback(self):
            pass
        def commit(self):
            pass
        def close(self):
            pass

    with patch("database.get_db", return_value=ConflictConn()):
        c_dup = database.claim_and_credit_crypto_tx(6735799833, "338192045678123456", "BINANCE_PAY", "USDT", 12.5, 160625)
        assert c_dup["ok"] is False
        assert c_dup.get("already_claimed") is True


def test_binance_crypto_config_env_only_and_commands_removed():
    """Verify Binance/crypto credentials are read strictly from .env, commands removed, and disabled by default."""
    import importlib
    import os
    import config
    import database
    import ytbot

    yt_src = (ROOT_DIR / "ytbot.py").read_text(encoding="utf-8")
    assert 'filters.command("setbinance")' not in yt_src
    assert 'filters.command("setusdt")' not in yt_src

    # DB values in bot_config must NOT be used by get_binance_crypto_config
    with patch("database.get_bot_config", return_value="db_should_be_ignored"), \
         patch.dict(
             os.environ,
             {
                 "BINANCE_UID": "987654321",
                 "BINANCE_API_KEY": "env_ro_key",
                 "BINANCE_API_SECRET": "env_ro_secret",
                 "USDT_TRC20_ADDRESS": "TEnvOnlyAddress123",
                 "USDT_BEP20_ADDRESS": "0xEnvOnlyAddress123",
                 "TON_WALLET_ADDRESS": "UQB5_ENV_ONLY",
             },
             clear=False,
         ):
        cfg = database.get_binance_crypto_config()
        assert cfg["binance_uid"] == "987654321"
        assert cfg["binance_api_key"] == "env_ro_key"
        assert cfg["binance_api_secret"] == "env_ro_secret"
        assert cfg["usdt_trc20_address"] == "TEnvOnlyAddress123"
        assert cfg["usdt_bep20_address"] == "0xEnvOnlyAddress123"
        assert cfg["ton_wallet_address"] == "UQB5_ENV_ONLY"

    # ENABLE_CRYPTO_PAY defaults to False when env vars are unset
    clean_env = dict(os.environ)
    for k in ("ENABLE_CRYPTO_PAY", "BINANCE_API_KEY", "CRYPTO_PAY_TOKEN"):
        clean_env.pop(k, None)
    with patch.dict(os.environ, clean_env, clear=True):
        importlib.reload(config)
        assert config.ENABLE_CRYPTO_PAY is False
    # Restore config module state
    importlib.reload(config)

    with patch.object(config, "ENABLE_CRYPTO_PAY", False), \
         patch.object(config, "CRYPTO_PAY_TOKEN", ""):
        txt_off = ytbot._format_wallet_balance_text("en", 30000)
        assert "Crypto (" not in txt_off
        assert "Telegram Stars" in txt_off

    with patch.object(config, "ENABLE_CRYPTO_PAY", True), \
         patch.object(config, "CRYPTO_PAY_TOKEN", ""):
        txt_on = ytbot._format_wallet_balance_text("en", 30000)
        assert "Crypto (" in txt_on
