# -*- coding: utf-8 -*-
"""
Red Team Defensive Security Audit Test Suite for UI-Facing Backend APIs
Covers: main.py, crypto_auth.py, captcha_engine.py, reseller_api.py
"""
import asyncio
import hashlib
import hmac
import json
import os
import time
from urllib.parse import urlencode
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiohttp import web
from aiohttp.test_utils import make_mocked_request

import main
import crypto_auth
import captcha_engine
import reseller_api


# ==================== HELPERS ====================

def _make_json_request(method: str, path: str, body: dict = None, headers: dict = None, cookies: dict = None, match_info: dict = None, scheme: str = "http"):
    hdrs = dict(headers or {})
    if cookies:
        hdrs["Cookie"] = "; ".join(f"{k}={v}" for k, v in cookies.items())
    if scheme == "https":
        hdrs["X-Forwarded-Proto"] = "https"
    req = make_mocked_request(
        method,
        path,
        headers=hdrs,
        match_info=match_info or {},
    )
    if body is not None:
        raw = json.dumps(body).encode("utf-8")
        req.json = AsyncMock(return_value=body)
        req.read = AsyncMock(return_value=raw)
    return req


def _make_valid_webapp_init_data(user_id: int, bot_token: str, auth_date: int = None) -> str:
    if auth_date is None:
        auth_date = int(time.time())
    user_json = json.dumps({"id": user_id, "first_name": "Kai", "username": "kai_test"}, separators=(",", ":"))
    params = {
        "auth_date": str(auth_date),
        "query_id": "AAHdF6IQAAAAAN0XohDhrOrc",
        "user": user_json,
    }
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(params.items()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode("utf-8"), hashlib.sha256).digest()
    sig = hmac.new(secret_key, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()
    params["hash"] = sig
    return urlencode(params)


def _register_test_session(user_id: int, token: str = None) -> str:
    tok = token or f"test_session_tok_{user_id}_{int(time.time())}_abcdef0123456789"
    main._AUTH_TOKENS[tok] = {"tg_user_id": user_id, "created_at": time.time()}
    return tok


# ==================== 1. AUTHENTICATION, SESSIONS & COOKIES ====================

@pytest.mark.asyncio
async def test_verify_token_blocks_unauthenticated_uid_takeover():
    """CRITICAL: /api/auth/verify-token must NEVER mint or recover sessions from tg_user_id alone."""
    with patch("database.get_web_session", return_value=None):
        # No token, only victim tg_user_id (including OWNER_ID)
        req1 = _make_json_request("POST", "/api/auth/verify-token", body={"tg_user_id": 6735799833, "fingerprint": "fp_attacker_12345"})
        resp1 = await main.handle_api_auth_verify_token(req1)
        assert resp1.status == 401

        # Fake token with victim tg_user_id
        req2 = _make_json_request("POST", "/api/auth/verify-token", body={"token": "fake_token_1234567890", "tg_user_id": 6735799833})
        resp2 = await main.handle_api_auth_verify_token(req2)
        assert resp2.status == 401


@pytest.mark.asyncio
async def test_verify_token_rejects_cross_user_mismatch_and_sets_secure_httponly_cookie():
    tok_a = _register_test_session(111111)
    try:
        # Cross-user mismatch -> 403
        req_cross = _make_json_request("POST", "/api/auth/verify-token", body={"token": tok_a, "tg_user_id": 222222})
        resp_cross = await main.handle_api_auth_verify_token(req_cross)
        assert resp_cross.status == 403

        # Legitimate token over HTTPS -> 200 + HttpOnly + Secure + SameSite=Lax cookie
        with patch("database.is_user_banned", return_value=False), \
             patch("database.is_bot_admin", return_value=False), \
             patch("database.is_user_vip", return_value=False), \
             patch("database.get_user_balance", return_value=50000), \
             patch("database.is_user_kyc_verified", return_value=False):
            req_ok = _make_json_request(
                "POST",
                "/api/auth/verify-token",
                body={"token": tok_a, "tg_user_id": 111111},
                scheme="https",
            )
            resp_ok = await main.handle_api_auth_verify_token(req_ok)
            assert resp_ok.status == 200
            cookie = resp_ok.cookies.get("cf_auth_token")
            assert cookie is not None
            assert cookie["httponly"] is True
            assert cookie["secure"] is True
            assert cookie["samesite"] == "Lax"
    finally:
        main._AUTH_TOKENS.pop(tok_a, None)


@pytest.mark.asyncio
async def test_otp_bruteforce_lockout_and_persistence():
    """OTP must lock out on 5th failed attempt and persist attempts even when loaded from DB."""
    uid = 555666777
    main._LOGIN_OTPS.pop(uid, None)
    db_store = {
        f"otp_{uid}": json.dumps({
            "otp": "654321",
            "expires_at": time.time() + 300,
            "cooldown_until": time.time() + 30,
            "attempts": 0,
        })
    }

    def _mock_get_cfg(k):
        return db_store.get(k, "")

    def _mock_set_cfg(k, v):
        db_store[k] = v

    with patch("database.get_bot_config", side_effect=_mock_get_cfg), \
         patch("database.set_bot_config", side_effect=_mock_set_cfg):
        for attempt in range(1, 5):
            # Simulate cold memory each attempt to verify DB persistence of attempt counter
            main._LOGIN_OTPS.pop(uid, None)
            req = _make_json_request("POST", "/api/auth/verify-otp", body={"tg_user_id": uid, "otp": "000000"})
            resp = await main.handle_api_auth_verify_otp(req)
            assert resp.status == 400
            persisted = json.loads(db_store[f"otp_{uid}"])
            assert persisted["attempts"] == attempt

        # 5th failed attempt -> 403 lockout and OTP cleared
        main._LOGIN_OTPS.pop(uid, None)
        req5 = _make_json_request("POST", "/api/auth/verify-otp", body={"tg_user_id": uid, "otp": "000000"})
        resp5 = await main.handle_api_auth_verify_otp(req5)
        assert resp5.status == 403
        assert db_store[f"otp_{uid}"] == ""
        assert uid not in main._LOGIN_OTPS


@pytest.mark.asyncio
async def test_webapp_hmac_validation_and_cookie_flags():
    test_bot_token = "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
    valid_init = _make_valid_webapp_init_data(888999, test_bot_token)
    tampered_init = valid_init.replace("Kai", "Evil")
    expired_init = _make_valid_webapp_init_data(888999, test_bot_token, auth_date=int(time.time()) - 100000)
    future_init = _make_valid_webapp_init_data(888999, test_bot_token, auth_date=int(time.time()) + 3600)

    with patch("config.BOT_TOKEN", test_bot_token), \
         patch.object(main, "BOT_TOKEN", test_bot_token), \
         patch("database.save_web_session", return_value=True), \
         patch("database.is_bot_admin", return_value=False), \
         patch("database.is_user_vip", return_value=False):
        # Tampered hash -> 403
        r_bad = await main.handle_api_auth_verify_webapp(_make_json_request("POST", "/api/auth/verify-webapp", {"initData": tampered_init}))
        assert r_bad.status == 403

        # Expired -> 401
        r_exp = await main.handle_api_auth_verify_webapp(_make_json_request("POST", "/api/auth/verify-webapp", {"initData": expired_init}))
        assert r_exp.status == 401

        # Future clock skew -> 401
        r_fut = await main.handle_api_auth_verify_webapp(_make_json_request("POST", "/api/auth/verify-webapp", {"initData": future_init}))
        assert r_fut.status == 401

        # Valid -> 200 + HttpOnly Secure cookie
        r_ok = await main.handle_api_auth_verify_webapp(_make_json_request("POST", "/api/auth/verify-webapp", {"initData": valid_init}, scheme="https"))
        assert r_ok.status == 200
        data = json.loads(r_ok.text)
        assert data["ok"] is True
        assert data["tg_user_id"] == 888999
        cookie = r_ok.cookies.get("cf_auth_token")
        assert cookie["httponly"] is True
        assert cookie["secure"] is True
        main._AUTH_TOKENS.pop(data["token"], None)


@pytest.mark.asyncio
async def test_logout_revokes_cookie_and_session():
    tok = _register_test_session(123456)
    with patch("database.delete_web_session", return_value=True) as mock_del:
        req = _make_json_request("POST", "/api/auth/logout", body={}, cookies={"cf_auth_token": tok})
        resp = await main.handle_api_auth_logout(req)
        assert resp.status == 200
        assert tok not in main._AUTH_TOKENS
        mock_del.assert_called_once_with(tok)
        assert resp.cookies["cf_auth_token"]["max-age"] == "0"


# ==================== 2. IDOR & BROKEN ACCESS CONTROL ====================

@pytest.mark.asyncio
async def test_idor_protection_on_all_user_endpoints():
    """Verify unauthenticated (401) and cross-user (403) blocking across all UI-facing user endpoints."""
    tok_attacker = _register_test_session(100001)
    victim_id = 200002
    attacker_headers = {"Authorization": f"Bearer {tok_attacker}"}

    try:
        # GET endpoints
        get_cases = [
            (main.handle_api_stats, f"/api/stats?tg_user_id={victim_id}"),
            (main.handle_api_bot_user, f"/api/bot_user?tg_user_id={victim_id}"),
            (main.handle_api_channels, f"/api/channels?tg_user_id={victim_id}"),
            (main.handle_api_autopost_tasks, f"/api/autopost-tasks?tg_user_id={victim_id}"),
            (main.handle_api_health_score, f"/api/health-score?tg_user_id={victim_id}"),
            (main.handle_api_best_time, f"/api/best-time?tg_user_id={victim_id}"),
            (main.handle_kyc_status, f"/kyc/status?user_id={victim_id}"),
            (main.handle_api_stars_user_inventory, f"/api/stars/user-inventory?user_id={victim_id}"),
            (main.handle_api_stars_daily_streak, f"/api/stars/daily-streak?user_id={victim_id}"),
            (main.handle_api_download_file, f"/api/download-file?video_id=dQw4w9WgXcQ&resolution=720&tg_user_id={victim_id}"),
        ]
        for handler, path in get_cases:
            r_unauth = await handler(make_mocked_request("GET", path))
            assert r_unauth.status == 401, f"Unauth GET {path} expected 401, got {r_unauth.status}"
            r_cross = await handler(make_mocked_request("GET", path, headers=attacker_headers))
            assert r_cross.status == 403, f"Cross-user GET {path} expected 403, got {r_cross.status}"

        # POST state-changing endpoints
        post_cases = [
            (main.handle_api_sync_profile, "/api/user/sync-profile", {"tg_user_id": victim_id, "first_name": "Hacked"}),
            (main.handle_api_channel_select, "/api/channels/select", {"tg_user_id": victim_id, "channel_id": "UC123"}),
            (main.handle_api_autopost_create, "/api/autopost-create", {"tg_user_id": victim_id, "topic": "spam"}),
            (main.handle_kyc_submit, "/kyc/submit", {"user_id": victim_id, "phone": "+998901234567", "face_hash": "abc123"}),
            (main.handle_api_tonconnect_save, "/api/tonconnect/save", {"user_id": victim_id, "address": "UQ" + "A" * 46}),
            (main.handle_api_tonconnect_disconnect, "/api/tonconnect/disconnect", {"user_id": victim_id}),
            (main.handle_api_stars_open_case, "/api/stars/open-case", {"user_id": 6735799833, "tier_id": "tier_5"}),
            (main.handle_api_stars_create_invoice, "/api/stars/create-invoice", {"user_id": victim_id, "tier_id": "tier_1"}),
            (main.handle_api_stars_marketplace_buy_invoice, "/api/stars/marketplace/buy-invoice", {"user_id": victim_id, "slug": "toybear-7605"}),
            (main.handle_api_stars_open_case_uzs, "/api/stars/open-case-uzs", {"user_id": victim_id, "tier_id": "tier_1"}),
            (main.handle_api_stars_pvp_create, "/api/stars/pvp/create", {"user_id": victim_id, "tier_id": "tier_1"}),
            (main.handle_api_stars_pvp_join, "/api/stars/pvp/join", {"user_id": victim_id, "battle_id": "b1"}),
            (main.handle_api_stars_pvp_cancel, "/api/stars/pvp/cancel", {"user_id": victim_id, "battle_id": "b1"}),
            (main.handle_api_stars_upgrader, "/api/stars/upgrader", {"user_id": victim_id, "item_stars": 15, "target_stars": 50}),
            (main.handle_api_stars_withdraw_gift, "/api/stars/withdraw-gift", {"user_id": victim_id, "record_id": 1}),
            (main.handle_api_stars_recycle_gift, "/api/stars/recycle-gift", {"user_id": victim_id, "record_id": 1}),
            (main.handle_api_stars_daily_claim, "/api/stars/daily-streak/claim", {"user_id": victim_id}),
            (main.handle_api_stars_scratch_card, "/api/stars/scratch-card/play", {"user_id": victim_id}),
            (main.handle_api_stars_redeem, "/api/stars/redeem-service", {"user_id": victim_id, "service_id": "ai_seo_50"}),
            (main.handle_api_reseller_buy, "/api/reseller/buy", {"user_id": victim_id, "product_id": 1, "quantity": 1}),
        ]
        for handler, path, payload in post_cases:
            r_unauth = await handler(_make_json_request("POST", path, body=payload))
            assert r_unauth.status == 401, f"Unauth POST {path} expected 401, got {r_unauth.status}"
            r_cross = await handler(_make_json_request("POST", path, body=payload, headers=attacker_headers))
            assert r_cross.status == 403, f"Cross-user POST {path} expected 403, got {r_cross.status}"
    finally:
        main._AUTH_TOKENS.pop(tok_attacker, None)


@pytest.mark.asyncio
async def test_daily_streak_guest_compatibility_and_webapp_header_auth():
    """Ensure initial guest mount (/api/stars/daily-streak?user_id=0) still returns 200 and WebApp HMAC works on KYC/TON Connect."""
    r_guest = await main.handle_api_stars_daily_streak(make_mocked_request("GET", "/api/stars/daily-streak?user_id=0"))
    assert r_guest.status == 200
    assert json.loads(r_guest.text)["ok"] is True

    test_bot_token = "999999:TEST_BOT_TOKEN_XYZ1234567890"
    init_data = _make_valid_webapp_init_data(777888, test_bot_token)
    with patch.object(main, "BOT_TOKEN", test_bot_token), \
         patch("database.is_user_kyc_verified", return_value=False):
        req_kyc = make_mocked_request(
            "GET",
            "/kyc/status?user_id=777888",
            headers={"X-Telegram-Init-Data": init_data},
        )
        r_kyc = await main.handle_kyc_status(req_kyc)
        assert r_kyc.status == 200
        assert json.loads(r_kyc.text)["user_id"] == 777888


@pytest.mark.asyncio
async def test_kyc_and_tonconnect_html_do_not_leak_unauthenticated_pii():
    """Unauthenticated GET /kyc/verify?user_id=X and /tonconnect/page?user_id=X must not pre-fill victim DB PII."""
    with patch("database.is_user_kyc_verified", return_value=True) as mock_kyc_v, \
         patch("database.get_user_kyc", return_value={"phone_number": "+998909998877", "face_hash": "secret_face_hash"}) as mock_kyc_d, \
         patch("database.get_telegram_phone", return_value="+998909998877"):
        r_kyc_page = await main.handle_kyc_page(make_mocked_request("GET", "/kyc/verify?user_id=999111"))
        assert r_kyc_page.status == 200
        assert "+998909998877" not in r_kyc_page.text
        assert "secret_face_hash" not in r_kyc_page.text
        mock_kyc_v.assert_not_called()
        mock_kyc_d.assert_not_called()

    with patch("database.get_user_ton_wallet", return_value={"wallet_address": "UQSecretVictimWalletAddress1234567890", "wallet_name": "Tonkeeper"}) as mock_w:
        r_ton_page = await main.handle_tonconnect_page(make_mocked_request("GET", "/tonconnect/page?user_id=999111"))
        assert r_ton_page.status == 200
        assert "UQSecretVictimWalletAddress1234567890" not in r_ton_page.text
        mock_w.assert_not_called()


# ==================== 3. FINANCIAL & BUSINESS LOGIC INTEGRITY ====================

@pytest.mark.asyncio
async def test_recycle_gift_ignores_client_supplied_prize_stars():
    """CRITICAL: recycle-gift must use authoritative DB prize_stars, never client-supplied value."""
    tok = _register_test_session(303030)
    mock_cur = MagicMock()
    mock_cur.fetchone.return_value = {"prize_stars": 15, "status": "pending"}
    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cur

    try:
        with patch("database.get_db", return_value=mock_conn), \
             patch("games_monetization.recycle_pending_gift", return_value={"ok": True, "refund_uzs": 4500}) as mock_recycle:
            req = _make_json_request(
                "POST",
                "/api/stars/recycle-gift",
                body={"user_id": 303030, "record_id": 42, "prize_stars": 9999999},
                headers={"Authorization": f"Bearer {tok}"},
            )
            resp = await main.handle_api_stars_recycle_gift(req)
            assert resp.status == 200
            # Must pass DB value (15), NOT attacker's 9999999
            mock_recycle.assert_called_once_with(42, 303030, 15)
    finally:
        main._AUTH_TOKENS.pop(tok, None)


@pytest.mark.asyncio
async def test_scratch_card_checks_atomic_deduct_return_value():
    """Scratch card must not play if deduct_user_balance returns False (prevents TOCTOU double-spend)."""
    tok = _register_test_session(404040)
    main._SCRATCH_COOLDOWN.pop(404040, None)
    try:
        with patch("database.is_user_banned", return_value=False), \
             patch("database.get_user_balance", return_value=1000), \
             patch("database.deduct_user_balance", return_value=False), \
             patch("games_monetization.play_scratch_card") as mock_play:
            req = _make_json_request(
                "POST",
                "/api/stars/scratch-card/play",
                body={"user_id": 404040},
                headers={"Authorization": f"Bearer {tok}"},
            )
            resp = await main.handle_api_stars_scratch_card(req)
            assert resp.status == 400
            mock_play.assert_not_called()
    finally:
        main._AUTH_TOKENS.pop(tok, None)


@pytest.mark.asyncio
async def test_reseller_gifts_send_blocks_negative_and_zero_price():
    """CRITICAL: /api/v1/gifts/send must reject negative/zero gift_stars."""
    fake_user = {"tg_user_id": 12345, "is_active": True, "balance_uzs": 100000}
    with patch("reseller_api.authenticate_request", return_value=(fake_user, None)), \
         patch("reseller_api.fetch_telegram_server_gifts", new=AsyncMock(return_value=[])), \
         patch("reseller_api.build_cases_from_gifts", return_value={}):
        for bad_stars in (-1000, 0, 5):
            req = _make_json_request(
                "POST",
                "/api/v1/gifts/send",
                body={"recipient_user_id": 99999, "gift_id": "custom_gift_1", "gift_stars": bad_stars},
            )
            resp = await reseller_api.handle_api_gifts_send(req)
            assert resp.status == 400


# ==================== 4. CRYPTO, ADMIN AUTH & CAPTCHA ENGINE ====================

def test_crypto_auth_no_hardcoded_secret_forgery_and_strict_claims():
    """Verify crypto_auth rejects tokens forged with the old hardcoded repository salt and enforces iat/exp."""
    with patch.dict(os.environ, {"ADMIN_SECRET": ""}, clear=False):
        # Attempt to forge using the legacy hardcoded secret string
        import base64
        legacy_key = hashlib.sha256(b"cf_sec_9e82ab3c4e5170d89201fbc43729e018_salt_v3").digest()
        payload = {"uid": 6735799833, "role": "superadmin", "iat": int(time.time()), "exp": int(time.time()) + 3600, "nonce": "abc"}
        p_b64 = base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()).decode().rstrip("=")
        forged_sig = hmac.new(legacy_key, p_b64.encode(), hashlib.sha256).hexdigest()
        assert crypto_auth.verify_signed_admin_token(f"{p_b64}.{forged_sig}") is None

        # Valid token in same process works
        good_tok = crypto_auth.generate_signed_admin_token(6735799833, ttl_seconds=600)
        assert crypto_auth.verify_signed_admin_token(good_tok) is not None


def test_admin_auth_rejects_query_param_admin_sig():
    """Admin token in URL query string (?admin_sig=...) must be rejected."""
    tok = crypto_auth.generate_signed_admin_token(6735799833, ttl_seconds=600)
    req_query = make_mocked_request("GET", f"/api/admin/telemetry/stream?admin_sig={tok}")
    assert main.is_admin_request(req_query) is False

    # Valid cookie / header works
    req_hdr = make_mocked_request("GET", "/api/admin/telemetry/stream", headers={"X-Admin-Signature": tok})
    assert main.is_admin_request(req_hdr) is True


def test_captcha_blocks_missing_telemetry_and_bruteforce_reuse():
    """Captcha engine must reject telemetry=None on sequence challenges and burn challenge_id after 1 attempt."""
    ch = captcha_engine.CaptchaManager.create_challenge(challenge_type="sequence", sitekey="demo_key")
    cid = ch["challenge_id"]
    # Omitting telemetry must NOT auto-heal / pass
    res1 = captcha_engine.CaptchaManager.verify_challenge(cid, {"clicks": [{"x": 10, "y": 10}, {"x": 20, "y": 20}, {"x": 30, "y": 30}]}, telemetry=None)
    assert res1["ok"] is False
    assert res1["error"] == "bot_detected"
    # Second attempt on same challenge_id must be rejected (anti-bruteforce single-use)
    res2 = captcha_engine.CaptchaManager.verify_challenge(cid, {"clicks": []}, telemetry={"duration_ms": 1000, "clicks": [{"t": 100}, {"t": 300}, {"t": 500}]})
    assert res2["ok"] is False
    assert res2["error"] in ("challenge_not_found_or_expired", "challenge_already_used")


@pytest.mark.asyncio
async def test_captcha_domain_whitelist_blocks_empty_origin_and_spoofed_localhost():
    """Domain-restricted sitekey must reject missing Origin/Referer and non-whitelisted localhost."""
    restricted_key = {"site_key": "bsh_live_test", "is_active": True, "is_demo": False, "domain": "example.com"}
    with patch("reseller_api.get_captcha_key_by_sitekey", return_value=restricted_key):
        # Missing Origin & Referer -> 403
        r_empty = await reseller_api.handle_api_captcha_create(_make_json_request("POST", "/api/v1/captcha/create", {"sitekey": "bsh_live_test"}))
        assert r_empty.status == 403

        # Spoofed localhost Origin -> 403
        r_local = await reseller_api.handle_api_captcha_create(
            _make_json_request("POST", "/api/v1/captcha/create", {"sitekey": "bsh_live_test"}, headers={"Origin": "http://localhost:3000"})
        )
        assert r_local.status == 403

        # Allowed domain -> 200
        r_ok = await reseller_api.handle_api_captcha_create(
            _make_json_request("POST", "/api/v1/captcha/create", {"sitekey": "bsh_live_test"}, headers={"Origin": "https://app.example.com"})
        )
        assert r_ok.status == 200


# ==================== 5. SSRF, PATH TRAVERSAL, XSS & SECURITY HEADERS ====================

@pytest.mark.asyncio
async def test_xss_escaping_in_oauth_callback_and_dashboard_webapp():
    """Reflected XSS payloads in /oauth/callback?error=... and /dashboard?user_id=... must be neutralized."""
    xss = "<script>alert(1)</script>"
    r_oauth = await main.handle_oauth_callback(make_mocked_request("GET", f"/oauth/callback?error={xss}"))
    assert "<script>alert(1)</script>" not in r_oauth.text
    assert "&lt;script&gt;" in r_oauth.text

    r_dash = await reseller_api.handle_dashboard_webapp(make_mocked_request("GET", '/dashboard?user_id=";alert(1);//'))
    assert '";alert(1);//' not in r_dash.text
    assert '|| "0";' in r_dash.text


@pytest.mark.asyncio
async def test_path_traversal_and_ssrf_protections():
    """Verify path traversal, cookie file leak, and SSRF vectors are blocked."""
    # Fragment image proxy & NFT animation slug traversal
    r_frag = await main.handle_fragment_image_proxy(make_mocked_request("GET", "/api/nft/fragment-image/bad", match_info={"slug": "../../admin"}))
    assert r_frag.status == 400
    r_anim = await main.handle_api_nft_animation(make_mocked_request("GET", "/api/nft/animation/bad", match_info={"slug": "../../telegram_gifts_cache"}))
    assert r_anim.status == 400
    assert main._get_local_gift_lottie_bytes("../../telegram_gifts_cache") is None

    # NFT image/video must block cookie/txt files in downloads/
    r_cookie = await main.handle_nft_image(make_mocked_request("GET", "/api/nft/image/cookies_dl_6735799833.txt", match_info={"filename": "cookies_dl_6735799833.txt"}))
    assert r_cookie.status in (400, 403)
    r_txt = await main.handle_nft_image(make_mocked_request("GET", "/api/nft/image/secret.txt", match_info={"filename": "secret.txt"}))
    assert r_txt.status == 403
    r_vid_txt = await main.handle_nft_video(make_mocked_request("GET", "/api/nft/video/secret.txt", match_info={"filename": "secret.txt"}))
    assert r_vid_txt.status == 403

    # Telegram file & avatar validation
    r_tg = await main.handle_api_telegram_file(make_mocked_request("GET", "/api/telegram-file/bad", match_info={"file_id": "../secret&x=1"}))
    assert r_tg.status == 400
    r_av = await main.handle_api_user_avatar(make_mocked_request("GET", "/api/user/avatar/notanid", match_info={"user_id": "notanid"}))
    assert r_av.status == 400

    # Video formats & download-file invalid video_id
    r_vf = await main.handle_api_video_formats(make_mocked_request("GET", "/api/video-formats?video_id=../../etc/passwd"))
    assert r_vf.status == 400
    r_dl = await main.handle_api_download_file(make_mocked_request("GET", "/api/download-file?video_id=../../etc/passwd"))
    assert r_dl.status == 400

    # SSRF validator in reseller_api.py
    for evil_url in [
        "http://127.0.0.1/admin",
        "http://localhost:8080/internal",
        "http://169.254.169.254/latest/meta-data/",
        "http://10.0.0.1/secret",
        "http://[::1]/secret",
        "file:///etc/passwd",
        "https://user:pass@example.com/hook",
    ]:
        assert reseller_api.is_safe_public_webhook_url(evil_url) is False, f"SSRF URL not blocked: {evil_url}"

    # YouTube target validator blocks SSRF
    assert reseller_api.extract_safe_youtube_target("http://169.254.169.254/latest/meta-data/") == (None, None)
    assert reseller_api.extract_safe_youtube_target("file:///etc/passwd") == (None, None)
    assert reseller_api.extract_safe_youtube_target("dQw4w9WgXcQ") == ("dQw4w9WgXcQ", "https://www.youtube.com/watch?v=dQw4w9WgXcQ")


def test_download_signature_and_security_headers():
    """Verify HMAC download signature & HSTS/CSP security headers."""
    exp, sig = crypto_auth.generate_download_signature("dQw4w9WgXcQ", "720", 123456)
    assert crypto_auth.verify_download_signature("dQw4w9WgXcQ", "720", 123456, exp, sig) is True
    assert crypto_auth.verify_download_signature("dQw4w9WgXcQ", "1080", 123456, exp, sig) is False
    assert crypto_auth.verify_download_signature("dQw4w9WgXcQ", "720", 999999, exp, sig) is False

    https_req = make_mocked_request("GET", "/", headers={"X-Forwarded-Proto": "https"})
    resp = main._add_security_headers(web.Response(text="<html></html>", content_type="text/html"), https_req)
    assert "max-age=31536000" in resp.headers.get("Strict-Transport-Security", "")
    assert "object-src 'none'" in resp.headers.get("Content-Security-Policy", "")
    assert resp.headers.get("X-Content-Type-Options") == "nosniff"
