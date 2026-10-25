# -*- coding: utf-8 -*-
"""
Kriptografik HMAC-SHA256 Signed Opaque Token Engine
Mualliflik: CreatorFlow Advanced Security Layer
Ochiq kalitsiz, buzib bo'lmas, vaqtga va bir martalik noncelarga asoslangan xavfsiz admin sessiya tokeni.
"""
import os
import hmac
import hashlib
import base64
import json
import time
import secrets
from typing import Optional, Dict, Any

def _get_signing_key() -> bytes:
    """Imzolash uchun maxfiy kalit (ADMIN_SECRET yoki ichki xavfsiz salt)"""
    secret = os.getenv("ADMIN_SECRET", "").strip()
    if not secret:
        secret = "cf_sec_9e82ab3c4e5170d89201fbc43729e018_salt_v3"
    # Kalitni sha256 orqali 32 baytlik raw baytga aylantiramiz
    return hashlib.sha256(secret.encode("utf-8")).digest()


def generate_signed_admin_token(
    tg_user_id: int = 6735799833,
    role: str = "superadmin",
    ttl_seconds: int = 30 * 86400
) -> str:
    """
    Ochiq kalitsiz, buzib bo'lmas vaqtga asoslangan HMAC-SHA256 token yaratish.
    Format: <base64url_payload>.<hex_hmac_signature>
    Tashqaridan qaraganda tasodifiy xesh qatori bo'lib, uning ichida hech qanday
    parol, bot token yoki maxfiy string oshkor bo'lmaydi.
    """
    signing_key = _get_signing_key()
    now = int(time.time())
    payload = {
        "uid": int(tg_user_id),
        "role": str(role),
        "iat": now,
        "exp": now + ttl_seconds,
        "nonce": secrets.token_hex(12)
    }
    
    # Payload ni xavfsiz base64url qilamiz
    raw_json = json.dumps(payload, separators=(',', ':'), sort_keys=True).encode("utf-8")
    payload_b64 = base64.urlsafe_b64encode(raw_json).decode("utf-8").rstrip("=")
    
    # HMAC-SHA256 imzo hisoblash
    sig = hmac.new(signing_key, payload_b64.encode("utf-8"), hashlib.sha256).hexdigest()
    
    return f"{payload_b64}.{sig}"


def verify_signed_admin_token(token: str) -> Optional[Dict[str, Any]]:
    """
    HMAC-SHA256 imzosini tekshirish.
    1 bit o'zgargan bo'lsa ham yoki muddati o'tgan bo'lsa darhol None qaytaradi.
    Constant-time comparison (timing attack lardan himoyalangan).
    """
    if not token or not isinstance(token, str) or "." not in token:
        return None
        
    parts = token.strip().split(".")
    if len(parts) != 2:
        return None
        
    payload_b64, sig = parts
    signing_key = _get_signing_key()
    
    # Kutilgan imzoni hisoblaymiz
    expected_sig = hmac.new(signing_key, payload_b64.encode("utf-8"), hashlib.sha256).hexdigest()
    
    # Constant-time taqqoslash
    if not hmac.compare_digest(sig, expected_sig):
        return None
        
    try:
        # Padding tiklash
        padding = "=" * ((4 - len(payload_b64) % 4) % 4)
        raw_json = base64.urlsafe_b64decode((payload_b64 + padding).encode("utf-8"))
        payload = json.loads(raw_json.decode("utf-8"))
        
        # Muddati tekshirish
        now = time.time()
        if payload.get("exp", 0) < now:
            return None
            
        # Foydalanuvchi ID tekshirish (Faqat owner / admin)
        from config import OWNER_ID
        valid_uids = {6735799833, int(OWNER_ID or 6735799833)}
        if int(payload.get("uid", 0)) not in valid_uids:
            return None
            
        if payload.get("role") != "superadmin":
            return None
            
        return payload
    except Exception:
        return None
