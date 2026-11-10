# -*- coding: utf-8 -*-
"""
Unit Tests for Security Hardening and Google AdSense Verification Integration
"""
import pytest
import os
import re
from aiohttp import web
from aiohttp.test_utils import make_mocked_request
from main import (
    handle_ads_txt,
    handle_robots,
    handle_google_verification,
    handle_api_reseller_my_orders,
    handle_api_reseller_admin_wallet,
    _add_security_headers
)
import legal_templates

@pytest.mark.asyncio
async def test_ads_txt_endpoint():
    """Verify /ads.txt serves Google AdSense publisher ID with 200 OK and correct headers"""
    req = make_mocked_request("GET", "/ads.txt")
    resp = await handle_ads_txt(req)
    assert resp.status == 200
    assert "google.com, pub-4094396006908725, DIRECT, f08c47fec0942fa0" in resp.text
    assert "text/plain" in resp.content_type


@pytest.mark.asyncio
async def test_robots_txt_allows_adsense():
    """Verify robots.txt explicitly allows Mediapartners-Google and /ads.txt"""
    req = make_mocked_request("GET", "/robots.txt")
    resp = await handle_robots(req)
    assert resp.status == 200
    assert "User-agent: Mediapartners-Google" in resp.text
    assert "Allow: /ads.txt" in resp.text


@pytest.mark.asyncio
async def test_google_verification_path_traversal_protection():
    """Verify handle_google_verification blocks path traversal attempts"""
    # 1. Traversal attempt with ../
    req_bad1 = make_mocked_request("GET", "/google..html", match_info={"filename": "../secret.txt"})
    resp_bad1 = await handle_google_verification(req_bad1)
    assert resp_bad1.status == 404

    # 2. Legitimate verification file pattern
    req_good = make_mocked_request("GET", "/google024111ea2452e08e.html", match_info={"filename": "google024111ea2452e08e.html"})
    resp_good = await handle_google_verification(req_good)
    assert resp_good.status == 200
    assert "google-site-verification" in resp_good.text


@pytest.mark.asyncio
async def test_idor_protection_reseller_orders():
    """Verify handle_api_reseller_my_orders rejects unauthenticated access to victim orders"""
    # Unauthenticated request trying to read orders for user 999999999
    req_unauth = make_mocked_request("GET", "/api/reseller/my-orders?user_id=999999999")
    resp_unauth = await handle_api_reseller_my_orders(req_unauth)
    assert resp_unauth.status == 401


@pytest.mark.asyncio
async def test_admin_wallet_access_control():
    """Verify handle_api_reseller_admin_wallet blocks unauthorized access"""
    req_unauth = make_mocked_request("GET", "/api/reseller/admin/wallet")
    resp_unauth = await handle_api_reseller_admin_wallet(req_unauth)
    assert resp_unauth.status == 403


def test_index_html_adsense_tags():
    """Verify index.html contains AdSense script and meta tag with exact publisher ID"""
    with open("index.html", "r", encoding="utf-8") as f:
        html = f.read()
    assert "ca-pub-4094396006908725" in html
    assert '<meta name="google-adsense-account" content="ca-pub-4094396006908725">' in html
    assert 'src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-4094396006908725"' in html


def test_legal_templates_adsense_tags():
    """Verify Privacy Policy and Terms of Service templates include AdSense tags"""
    priv_html = legal_templates.get_privacy_html()
    assert "ca-pub-4094396006908725" in priv_html
    assert '<meta name="google-adsense-account" content="ca-pub-4094396006908725">' in priv_html

    terms_html = legal_templates.get_terms_html()
    assert "ca-pub-4094396006908725" in terms_html
    assert '<meta name="google-adsense-account" content="ca-pub-4094396006908725">' in terms_html


def test_ads_txt_file_exists_and_valid():
    """Verify physical ads.txt exists and matches Google AdSense spec"""
    assert os.path.isfile("ads.txt")
    with open("ads.txt", "r", encoding="utf-8") as f:
        content = f.read().strip()
    assert content == "google.com, pub-4094396006908725, DIRECT, f08c47fec0942fa0"


def test_security_headers_and_csp():
    """Verify security headers and frame-ancestors support AdSense and Telegram"""
    raw_resp = web.Response(text="<html></html>", content_type="text/html")
    secured = _add_security_headers(raw_resp)
    assert secured.headers.get("X-Content-Type-Options") == "nosniff"
    csp = secured.headers.get("Content-Security-Policy", "")
    assert "frame-ancestors" in csp
    assert "https://web.telegram.org" in csp
    assert "https://*.google.com" in csp
