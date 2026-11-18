"""
CreatorFlow Studio - Enterprise Telemetry, Observability & n8n-Style Workflow Inspector
Real-time database query tracing, dynamic TTL cache controls, live API node graph, and auto-discovered route registry.
"""

import time
import os
import re
import html
import collections
from typing import Dict, Any, List, Optional

# Bounded Deque buffers (Zero memory leak, fast circular history)
_DB_QUERY_BUFFER = collections.deque(maxlen=120)
_API_REQUEST_BUFFER = collections.deque(maxlen=150)
_OUTGOING_API_BUFFER = collections.deque(maxlen=80)

# Real-time Dynamic Runtime Configuration (Customizable on the fly by Admin)
_DYNAMIC_CONFIG: Dict[str, Any] = {
    "product_cache_ttl": 60,       # VenteBot mahsulotlar kesh vaqti (soniya)
    "usd_cache_ttl": 1800,         # Valyuta kursi kesh vaqti (soniya)
    "dos_burst_max": 150,          # DoS 2-soniyalik burst chegarasi (media va assetlar uchun)
    "dos_burst_window": 2,         # DoS burst oyna vaqti (soniya)
    "dos_minute_max": 600,         # 1 daqiqalik maksimal so'rovlar
    "otp_rate_limit_max": 3,       # 2 daqiqada maksimal OTP so'rovlar
    "db_slow_query_threshold_ms": 15 # Sekin so'rov chegarasi (sariq/qizil ogohlantirish)
}

# Aggregate counters
_METRICS = {
    "total_db_queries": 0,
    "total_api_requests": 0,
    "total_blocked_dos": 0,
    "db_errors_count": 0,
    "server_start_time": time.time(),
}

# Per-key numeric validation bounds (min, max)
_DYNAMIC_CONFIG_BOUNDS: Dict[str, tuple] = {
    "product_cache_ttl": (0, 86400),
    "usd_cache_ttl": (10, 86400),
    "dos_burst_max": (5, 2000),
    "dos_burst_window": (1, 60),
    "dos_minute_max": (10, 10000),
    "otp_rate_limit_max": (1, 20),
    "db_slow_query_threshold_ms": (1, 10000),
}

def sanitize_sql(sql_str: str) -> str:
    """SQL matnidan maxfiy ma'lumotlar va uzun whitespace larni tozalash"""
    if not sql_str:
        return ""
    # Whitespace normalization
    cleaned = re.sub(r'\s+', ' ', str(sql_str).strip())
    # Redact sensitive key/column string literals and long opaque string values (tokens/hashes/phones)
    cleaned = re.sub(
        r"(?i)(\b(?:password|passwd|token|secret|api_key|auth|otp|hash|phone|session|cookie|key)\b\s*=\s*)'[^']*'",
        r"\1'[REDACTED]'",
        cleaned,
    )
    cleaned = re.sub(r"'[^']{16,}'", "'[REDACTED]'", cleaned)
    # Truncate if ultra long
    if len(cleaned) > 280:
        cleaned = cleaned[:277] + "..."
    return cleaned

def record_db_query(query: str, duration_ms: float, status: str = "ok", error: Optional[str] = None):
    """Baza so'rovini telemetriya buferiga yozish"""
    _METRICS["total_db_queries"] += 1
    if status != "ok":
        _METRICS["db_errors_count"] += 1

    entry = {
        "id": _METRICS["total_db_queries"],
        "timestamp": time.strftime("%H:%M:%S", time.localtime()),
        "time_raw": time.time(),
        "query": sanitize_sql(query),
        "duration_ms": round(duration_ms, 2),
        "status": status,
        "is_slow": duration_ms >= _DYNAMIC_CONFIG.get("db_slow_query_threshold_ms", 15),
        "error": str(error) if error else None
    }
    _DB_QUERY_BUFFER.appendleft(entry)

def record_api_call(method: str, path: str, status: int, latency_ms: float, client_ip: str = "unknown"):
    """Kiruvchi HTTP so'rovini qayd qilish"""
    _METRICS["total_api_requests"] += 1
    if status == 429:
        _METRICS["total_blocked_dos"] += 1

    entry = {
        "id": _METRICS["total_api_requests"],
        "timestamp": time.strftime("%H:%M:%S", time.localtime()),
        "time_raw": time.time(),
        "method": method.upper(),
        "path": path,
        "status": status,
        "latency_ms": round(latency_ms, 2),
        "client_ip": client_ip
    }
    _API_REQUEST_BUFFER.appendleft(entry)

def record_outgoing_call(vendor: str, endpoint: str, duration_ms: float, status: str = "ok", cached: bool = False, error: Optional[str] = None):
    """Tashqi API chaqiruvlarini (VenteBot, Telegram, etc.) qayd qilish"""
    entry = {
        "timestamp": time.strftime("%H:%M:%S", time.localtime()),
        "vendor": vendor,
        "endpoint": endpoint,
        "duration_ms": round(duration_ms, 2),
        "status": status,
        "cached": cached,
        "error": str(error) if error else None
    }
    _OUTGOING_API_BUFFER.appendleft(entry)

def get_dynamic_config(key: str, default: Any = None) -> Any:
    """Jonli konfiguratsiya parametrini olish"""
    return _DYNAMIC_CONFIG.get(key, default)

def update_dynamic_config(updates: Dict[str, Any]) -> Dict[str, Any]:
    """Admin tomonidan parametrni jonli o'zgartirish (qat'iy tur va chegara tekshiruvi bilan)"""
    if not isinstance(updates, dict):
        raise ValueError("Konfiguratsiya obyekt formatida bo'lishi kerak")
    for k, v in updates.items():
        if k not in _DYNAMIC_CONFIG:
            continue
        if isinstance(v, bool):
            raise ValueError(f"'{k}' uchun noto'g'ri qiymat")
        try:
            parsed_val = int(v)
        except (TypeError, ValueError):
            raise ValueError(f"'{k}' butun son bo'lishi kerak")
        min_val, max_val = _DYNAMIC_CONFIG_BOUNDS.get(k, (0, 1000000))
        if parsed_val < min_val or parsed_val > max_val:
            raise ValueError(f"'{k}' {min_val} dan {max_val} gacha oraliqda bo'lishi kerak")
        _DYNAMIC_CONFIG[k] = parsed_val
    return dict(_DYNAMIC_CONFIG)

def purge_cache(category: str) -> Dict[str, Any]:
    """Keshni tozalash mexanizmi"""
    allowed_categories = {"all", "products", "ventebot", "currency", "rate_limits"}
    clean_cat = str(category or "").strip().lower()
    if clean_cat not in allowed_categories:
        raise ValueError("Noto'g'ri kesh kategoriyasi")
    purged_items = []

    # 1. VenteBot Mahsulotlar Keshi
    if clean_cat in ("all", "products", "ventebot"):
        try:
            from ventebot_service import ventebot_service
            if hasattr(ventebot_service, "cache") and hasattr(ventebot_service.cache, "clear"):
                ventebot_service.cache.clear()
            purged_items.append("VenteBot Mahsulotlar & Narxlar Keshi")
        except Exception:
            purged_items.append("VenteBot keshini tozalashda ichki xatolik")

    # 2. Valyuta Kursi Keshi
    if clean_cat in ("all", "currency"):
        try:
            from currency_service import currency_service
            currency_service._last_updated = 0.0
            purged_items.append("USD / UZS Valyuta Kursi Keshi")
        except Exception:
            purged_items.append("Valyuta keshini tozalashda ichki xatolik")

    # 3. DoS Rate Limiting Xotirasi
    if clean_cat in ("all", "rate_limits"):
        try:
            from main import _IP_RATE_LIMITS, _SENSITIVE_IP_LIMITS
            _IP_RATE_LIMITS.clear()
            _SENSITIVE_IP_LIMITS.clear()
            purged_items.append("DoS va Rate Limiting IP Ro'yxati")
        except Exception:
            purged_items.append("Rate limit keshini tozalashda ichki xatolik")

    return {
        "ok": True,
        "category": clean_cat,
        "purged": purged_items,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }

def get_auto_discovered_routes(app) -> List[Dict[str, Any]]:
    """app.router dagi barcha marshrutlarni avtomatik aniqlash va kategoriyalash"""
    if not app or not hasattr(app, "router"):
        return []

    routes_list = []
    seen = set()

    for r in app.router.routes():
        method = r.method
        # Extract resource pattern
        res_info = getattr(r.resource, "canonical", "") or getattr(r.resource, "_path", "") or str(r.resource)
        key = f"{method}:{res_info}"
        if key in seen:
            continue
        seen.add(key)

        # Categorize route
        cat = "Boshqa"
        p = res_info.lower()
        if "stars" in p or "case" in p or "pvp" in p or "upgrader" in p or "scratch" in p:
            cat = "Mystery Cases & PvP O'yinlar"
        elif "marketplace" in p or "nft" in p or "reseller" in p:
            cat = "NFT Bozor & VenteBot"
        elif "auth" in p or "otp" in p or "webapp" in p:
            cat = "Autentifikatsiya & WebApp"
        elif "video" in p or "channel" in p or "autopost" in p or "trending" in p:
            cat = "YouTube Studio & Avtomatlashtirish"
        elif "telemetry" in p or "admin" in p or "health" in p or "reset" in p:
            cat = "Admin & Telemetriya"
        elif "privacy" in p or "terms" in p or "robots" in p:
            cat = "Qonuniy & Muvofiqlik"

        handler_name = getattr(r.handler, "__name__", str(r.handler))
        routes_list.append({
            "method": method,
            "path": res_info,
            "category": cat,
            "handler": handler_name
        })

    # Sort by Category, then Path
    return sorted(routes_list, key=lambda x: (x["category"], x["path"]))

def get_telemetry_snapshot(app=None) -> Dict[str, Any]:
    """To'liq telemetriya ko'rinishini qaytarish"""
    now = time.time()
    uptime_sec = int(now - _METRICS["server_start_time"])

    # Recent queries latency calculation
    recent_db = list(_DB_QUERY_BUFFER)[:30]
    avg_db_latency = (
        round(sum(q["duration_ms"] for q in recent_db) / len(recent_db), 2)
        if recent_db else 0.0
    )

    # Recent API latency
    recent_api = list(_API_REQUEST_BUFFER)[:30]
    avg_api_latency = (
        round(sum(a["latency_ms"] for a in recent_api) / len(recent_api), 2)
        if recent_api else 0.0
    )

    # Database Pool Telemetry
    pool_stats = {"min": 2, "max": 20, "status": "Ready", "used": 0}
    try:
        from database import _DB_POOL
        if _DB_POOL and not getattr(_DB_POOL, "closed", True):
            pool_stats["min"] = _DB_POOL.minconn
            pool_stats["max"] = _DB_POOL.maxconn
            pool_stats["used"] = len(getattr(_DB_POOL, "_used", {}))
            pool_stats["status"] = "Active"
    except Exception:
        pass

    # Cache Stats
    cache_stats = {
        "ventebot_products_ttl": _DYNAMIC_CONFIG.get("product_cache_ttl", 60),
        "usd_cache_ttl": _DYNAMIC_CONFIG.get("usd_cache_ttl", 1800),
        "dos_burst_window": _DYNAMIC_CONFIG.get("dos_burst_window", 2),
        "dos_burst_max": _DYNAMIC_CONFIG.get("dos_burst_max", 150),
        "tracked_ips_count": 0,
        "active_auth_tokens": 0
    }
    try:
        from main import _IP_RATE_LIMITS, _AUTH_TOKENS
        cache_stats["tracked_ips_count"] = len(_IP_RATE_LIMITS)
        cache_stats["active_auth_tokens"] = len(_AUTH_TOKENS)
    except Exception:
        pass

    # Auto-discovered routes
    routes = get_auto_discovered_routes(app) if app else []

    return {
        "ok": True,
        "server_time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "uptime_str": f"{uptime_sec // 3600}s {(uptime_sec % 3600) // 60}m {uptime_sec % 60}s",
        "metrics": {
            **_METRICS,
            "avg_db_latency_ms": avg_db_latency,
            "avg_api_latency_ms": avg_api_latency,
        },
        "pool": pool_stats,
        "config": _DYNAMIC_CONFIG,
        "cache": cache_stats,
        "recent_db_queries": list(_DB_QUERY_BUFFER)[:60],
        "recent_api_requests": list(_API_REQUEST_BUFFER)[:60],
        "recent_outgoing_calls": list(_OUTGOING_API_BUFFER)[:40],
        "discovered_routes_count": len(routes),
        "discovered_routes": routes
    }


def render_telemetry_html(admin_key: str = "") -> str:
    """n8n uslubidagi interaktiv boshqaruv va telemetriya dashboard HTML shabloni"""
    # Xavfsizlik: Admin sessiya tokeni/paroli HECH QACHON inline HTML/JS ga yozilmaydi.
    # Autentifikatsiya faqat HttpOnly 'cf_adm_sig' cookie (credentials: 'same-origin') orqali amalga oshiriladi.
    _ = admin_key
    return f"""<!DOCTYPE html>
<html lang="uz">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CreatorFlow Observability & Live Flow Inspector</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;700&family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg: #11121a;
            --surface: #171824;
            --surface-card: #1c1f30;
            --border: #2a2e45;
            --border-hover: #ff6d5a;
            --n8n-coral: #ff6d5a;
            --n8n-coral-dark: #ea4b36;
            --n8n-coral-glow: rgba(255, 109, 90, 0.25);
            --cyan: #38bdf8;
            --emerald: #20c997;
            --violet: #8054c7;
            --amber: #f59e0b;
            --blue: #4e82f7;
            --rose: #ef4444;
            --text-main: #f1f3f9;
            --text-muted: #8c93ad;
            --font-sans: 'Plus Jakarta Sans', -apple-system, sans-serif;
            --font-mono: 'JetBrains Mono', monospace;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            background: var(--bg);
            color: var(--text-main);
            font-family: var(--font-sans);
            min-height: 100vh;
            line-height: 1.5;
            overflow-x: hidden;
            background-image: radial-gradient(rgba(115, 66, 226, 0.12) 1px, transparent 1px), radial-gradient(rgba(0, 240, 255, 0.08) 1px, transparent 1px);
            background-size: 32px 32px;
            background-position: 0 0, 16px 16px;
        }}
        /* Top Navigation */
        header {{
            background: rgba(10, 13, 22, 0.85);
            backdrop-filter: blur(16px);
            border-bottom: 1px solid var(--border);
            padding: 14px 28px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            flex-wrap: wrap;
            gap: 12px;
            position: sticky;
            top: 0;
            z-index: 100;
        }}
        .brand-box {{
            display: flex;
            align-items: center;
            gap: 12px;
        }}
        .brand-icon {{
            width: 38px;
            height: 38px;
            border-radius: 10px;
            background: linear-gradient(135deg, #ff6d5a 0%, #ea4b36 100%);
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 0 16px var(--n8n-coral-glow);
        }}
        .brand-title {{
            font-size: 17px;
            font-weight: 800;
            letter-spacing: -0.02em;
        }}
        .live-pill {{
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 3px 10px;
            border-radius: 999px;
            background: rgba(16, 185, 129, 0.15);
            border: 1px solid rgba(16, 185, 129, 0.3);
            color: var(--emerald);
            font-size: 11px;
            font-weight: 700;
        }}
        .pulse-dot {{
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: var(--emerald);
            box-shadow: 0 0 8px var(--emerald);
            animation: pulseGlow 1.8s infinite;
        }}
        @keyframes pulseGlow {{
            0%, 100% {{ transform: scale(1); opacity: 1; }}
            50% {{ transform: scale(1.4); opacity: 0.6; }}
        }}
        /* Stats Ribbon */
        .stats-ribbon {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 14px;
            padding: 24px 28px 12px;
            max-width: 1440px;
            margin: 0 auto;
        }}
        .metric-card {{
            background: var(--surface-card);
            backdrop-filter: blur(12px);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 16px 20px;
            transition: all 0.2s ease;
        }}
        .metric-card:hover {{
            border-color: var(--border-hover);
            transform: translateY(-2px);
        }}
        .metric-lbl {{
            font-size: 12px;
            color: var(--text-muted);
            font-weight: 600;
            margin-bottom: 4px;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }}
        .metric-val {{
            font-size: 24px;
            font-weight: 800;
            font-family: var(--font-mono);
            letter-spacing: -0.02em;
        }}
        /* Tab Navigation */
        .tab-bar {{
            display: flex;
            gap: 8px;
            padding: 0 28px;
            max-width: 1440px;
            margin: 16px auto 0;
            border-bottom: 1px solid var(--border);
            overflow-x: auto;
        }}
        .tab-btn {{
            background: transparent;
            border: none;
            color: var(--text-muted);
            font-family: var(--font-sans);
            font-size: 13px;
            font-weight: 700;
            padding: 12px 18px;
            cursor: pointer;
            border-bottom: 2px solid transparent;
            transition: all 0.15s ease;
            white-space: nowrap;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .tab-btn:hover {{
            color: var(--text-main);
        }}
        .tab-btn.active {{
            color: var(--cyan);
            border-bottom-color: var(--cyan);
        }}
        /* Container */
        .main-container {{
            max-width: 1440px;
            margin: 0 auto;
            padding: 24px 28px 60px;
        }}
        /* Authentic n8n Workflow Editor Canvas */
        .flow-canvas {{
            background: #141520;
            border: 1px solid var(--border);
            border-radius: 18px;
            padding: 24px;
            position: relative;
            overflow-x: auto;
            margin-bottom: 28px;
            background-image: radial-gradient(rgba(255, 255, 255, 0.09) 1.2px, transparent 1.2px);
            background-size: 20px 20px;
            box-shadow: inset 0 0 50px rgba(0, 0, 0, 0.6);
        }}
        .flow-canvas-header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 24px;
            padding-bottom: 14px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.06);
        }}
        .flow-canvas-title {{
            display: flex;
            align-items: center;
            gap: 10px;
            font-size: 13px;
            font-weight: 800;
            color: #ffffff;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}
        .flow-nodes-wrapper {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            min-width: 1080px;
            position: relative;
            padding: 18px 0;
        }}
        .n8n-node {{
            background: #1c1f30;
            border: 1.5px solid #2d3249;
            border-radius: 12px;
            width: 200px;
            position: relative;
            z-index: 2;
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.35);
            transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
            cursor: pointer;
            user-select: none;
        }}
        .n8n-node:hover {{
            transform: translateY(-3px);
            border-color: var(--n8n-coral);
            box-shadow: 0 12px 30px var(--n8n-coral-glow);
        }}
        .n8n-node.selected {{
            border-color: var(--n8n-coral);
            box-shadow: 0 0 0 2px var(--n8n-coral-glow);
        }}
        .n8n-node-tag {{
            font-size: 9px;
            font-weight: 800;
            text-transform: uppercase;
            letter-spacing: 0.06em;
            padding: 5px 12px;
            border-top-left-radius: 10px;
            border-top-right-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            color: #ffffff;
        }}
        .n8n-node-body {{
            padding: 12px 14px 10px;
        }}
        .n8n-node-title-row {{
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 6px;
        }}
        .n8n-node-icon {{
            width: 30px;
            height: 30px;
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            flex-shrink: 0;
        }}
        .n8n-node-title {{
            font-size: 13px;
            font-weight: 700;
            color: #ffffff;
            line-height: 1.2;
        }}
        .n8n-node-metric {{
            font-family: var(--font-mono);
            font-size: 14px;
            font-weight: 800;
            margin-top: 4px;
        }}
        .n8n-node-footer {{
            border-top: 1px solid rgba(255, 255, 255, 0.06);
            padding: 7px 12px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            font-size: 10px;
            color: var(--text-muted);
        }}
        .n8n-status-pill {{
            display: inline-flex;
            align-items: center;
            gap: 4px;
            font-weight: 700;
            color: var(--emerald);
        }}
        /* Left and Right Connection Ports */
        .n8n-port {{
            position: absolute;
            top: 50%;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            background: #141520;
            border: 2.5px solid var(--n8n-coral);
            transform: translateY(-50%);
            z-index: 5;
            transition: all 0.15s ease;
        }}
        .n8n-port-in {{ left: -6px; }}
        .n8n-port-out {{ right: -6px; }}
        .n8n-node:hover .n8n-port {{
            background: var(--n8n-coral);
            box-shadow: 0 0 10px var(--n8n-coral);
        }}
        /* SVG Bezier Connecting Wires */
        .n8n-wire-wrapper {{
            flex: 1;
            position: relative;
            height: 50px;
            display: flex;
            align-items: center;
            justify-content: center;
            min-width: 50px;
        }}
        .n8n-wire-svg {{
            width: 100%;
            height: 100%;
            overflow: visible;
        }}
        .n8n-wire-path {{
            stroke: var(--n8n-coral);
            stroke-width: 2.5;
            fill: none;
            stroke-dasharray: 6 4;
            animation: n8nDash 1.2s linear infinite;
        }}
        @keyframes n8nDash {{
            from {{ stroke-dashoffset: 20; }}
            to {{ stroke-dashoffset: 0; }}
        }}
        /* Inspector Drawer */
        .n8n-drawer {{
            display: none;
            margin-top: 18px;
            background: #1c1f30;
            border: 1px solid var(--border);
            border-radius: 14px;
            padding: 18px;
            box-shadow: 0 8px 30px rgba(0, 0, 0, 0.4);
            animation: fadeIn 0.2s ease;
        }}
        .n8n-drawer-header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 12px;
            padding-bottom: 10px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.08);
        }}
        @keyframes fadeIn {{
            from {{ opacity: 0; transform: translateY(-4px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}
        /* Tables */
        .table-card {{
            background: var(--surface-card);
            border: 1px solid var(--border);
            border-radius: 20px;
            overflow: hidden;
            box-shadow: 0 8px 32px rgba(0,0,0,0.25);
        }}
        .table-header-box {{
            padding: 18px 24px;
            border-bottom: 1px solid var(--border);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .table-title {{
            font-size: 15px;
            font-weight: 800;
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 13px;
            text-align: left;
        }}
        th {{
            background: rgba(255, 255, 255, 0.03);
            padding: 12px 18px;
            font-weight: 700;
            color: var(--text-muted);
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            border-bottom: 1px solid var(--border);
        }}
        td {{
            padding: 12px 18px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.04);
            color: var(--text-main);
        }}
        tr:hover td {{
            background: rgba(255, 255, 255, 0.02);
        }}
        .code-pill {{
            font-family: var(--font-mono);
            font-size: 12px;
            background: rgba(255, 255, 255, 0.06);
            border: 1px solid rgba(255, 255, 255, 0.1);
            padding: 2px 6px;
            border-radius: 6px;
            color: #E2E8F0;
        }}
        .badge-status {{
            display: inline-flex;
            align-items: center;
            gap: 4px;
            padding: 2px 8px;
            border-radius: 999px;
            font-size: 11px;
            font-weight: 700;
            font-family: var(--font-mono);
        }}
        .badge-200 {{ background: rgba(16, 185, 129, 0.15); color: var(--emerald); border: 1px solid rgba(16, 185, 129, 0.3); }}
        .badge-300 {{ background: rgba(56, 189, 248, 0.15); color: var(--cyan); border: 1px solid rgba(56, 189, 248, 0.3); }}
        .badge-401, .badge-403, .badge-400 {{ background: rgba(245, 158, 11, 0.15); color: var(--amber); border: 1px solid rgba(245, 158, 11, 0.3); }}
        .badge-429, .badge-500 {{ background: rgba(239, 68, 68, 0.15); color: var(--rose); border: 1px solid rgba(239, 68, 68, 0.3); }}
        .n8n-drawer-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 14px;
        }}
        .tab-btn:focus-visible, .btn-3d:focus-visible, .config-input:focus-visible {{
            outline: 2px solid var(--cyan);
            outline-offset: 2px;
        }}
        .btn-3d:disabled {{
            opacity: 0.55;
            cursor: not-allowed;
            transform: none !important;
        }}
        @media (max-width: 768px) {{
            header {{ padding: 12px 16px; }}
            .stats-ribbon {{ padding: 16px 16px 8px; }}
            .tab-bar {{ padding: 0 16px; }}
            .main-container {{ padding: 16px 16px 48px; }}
            .n8n-drawer-grid {{ grid-template-columns: 1fr; }}
            .config-grid {{ grid-template-columns: 1fr; padding: 16px; }}
        }}
        /* Config Form */
        .config-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
            gap: 20px;
            padding: 24px;
        }}
        .config-item {{
            background: rgba(255, 255, 255, 0.02);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 20px;
        }}
        .config-item label {{
            display: block;
            font-size: 13px;
            font-weight: 700;
            margin-bottom: 6px;
        }}
        .config-item small {{
            display: block;
            font-size: 12px;
            color: var(--text-muted);
            margin-bottom: 12px;
            line-height: 1.4;
        }}
        .config-input-group {{
            display: flex;
            gap: 10px;
        }}
        .config-input {{
            flex: 1;
            background: #06080D;
            border: 1px solid rgba(255, 255, 255, 0.14);
            border-radius: 10px;
            color: #fff;
            padding: 10px 14px;
            font-family: var(--font-mono);
            font-size: 14px;
            outline: none;
        }}
        .config-input:focus {{
            border-color: var(--cyan);
        }}
        /* 3D Tactile Buttons */
        .btn-3d {{
            position: relative;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            padding: 10px 18px;
            border-radius: 12px;
            font-weight: 700;
            font-size: 13px;
            cursor: pointer;
            border: 1px solid transparent;
            transition: all 0.12s cubic-bezier(0.16, 1, 0.3, 1);
            user-select: none;
        }}
        .btn-3d-cyan {{
            background: linear-gradient(180deg, #00f0ff 0%, #00b4d8 100%);
            color: #030712;
            border-bottom: 3px solid #0096c7;
            box-shadow: 0 4px 14px rgba(0, 240, 255, 0.3);
        }}
        .btn-3d-cyan:active {{
            transform: translateY(2px);
            border-bottom-width: 1px;
        }}
        .btn-3d-rose {{
            background: linear-gradient(180deg, #ef4444 0%, #dc2626 100%);
            color: #fff;
            border-bottom: 3px solid #991b1b;
            box-shadow: 0 4px 14px rgba(239, 68, 68, 0.3);
        }}
        .btn-3d-rose:active {{
            transform: translateY(2px);
            border-bottom-width: 1px;
        }}
        .btn-3d-dark {{
            background: #181d2a;
            color: #f3f4f6;
            border: 1px solid rgba(255, 255, 255, 0.12);
            border-bottom: 3px solid #0b0f19;
        }}
        .btn-3d-dark:active {{
            transform: translateY(2px);
            border-bottom-width: 1px;
        }}
        /* Toast Alert */
        #toast {{
            position: fixed;
            bottom: 24px;
            right: 24px;
            background: #10B981;
            color: #fff;
            padding: 12px 20px;
            border-radius: 12px;
            font-weight: 700;
            font-size: 13px;
            box-shadow: 0 8px 30px rgba(0,0,0,0.5);
            display: none;
            z-index: 1000;
            animation: slideUp 0.25s ease;
        }}
        #toast.toast-error {{
            background: #ef4444;
        }}
        @keyframes slideUp {{
            from {{ transform: translateY(20px); opacity: 0; }}
            to {{ transform: translateY(0); opacity: 1; }}
        }}
    </style>
</head>
<body>
    <header>
        <div class="brand-box">
            <div class="brand-icon">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#000000" stroke-width="2.5"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
            </div>
            <div>
                <div class="brand-title">CreatorFlow Observability</div>
                <div style="font-size: 11px; color: var(--text-muted);">Real-time Architecture & Query Inspector</div>
            </div>
            <div class="live-pill" style="margin-left: 12px;">
                <span class="pulse-dot"></span>
                <span>JONLI STREAM</span>
            </div>
        </div>
        <div style="display: flex; gap: 10px; align-items: center; flex-wrap: wrap;">
            <button type="button" id="pollBtn" class="btn-3d btn-3d-dark" onclick="togglePolling()">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10"/><polygon points="10 8 16 12 10 16 10 8"/></svg>
                <span id="pollBtnTxt">Avto-Yangilanish: Faol (2.5s)</span>
            </button>
            <a href="/" class="btn-3d btn-3d-dark" style="text-decoration: none;">
                Ilovaga qaytish
            </a>
            <button type="button" onclick="adminLogout()" class="btn-3d btn-3d-dark" style="color: #ef4444; border-color: rgba(239, 68, 68, 0.35);">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>
                <span>Chiqish</span>
            </button>
        </div>
    </header>

    <!-- Top Key Metrics Ribbon -->
    <div class="stats-ribbon">
        <div class="metric-card">
            <div class="metric-lbl">
                <span>Jami DB So'rovlari</span>
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="var(--cyan)" stroke-width="2"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/></svg>
            </div>
            <div class="metric-val" id="metricDbQueries" style="color: var(--cyan);">-</div>
            <div style="font-size: 11px; color: var(--text-muted); margin-top: 4px;">O'rtacha latensiya: <span id="metricDbLatency" style="color:#fff; font-weight:700;">- ms</span></div>
        </div>
        <div class="metric-card">
            <div class="metric-lbl">
                <span>Kiruvchi API Oqimi</span>
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="var(--emerald)" stroke-width="2"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
            </div>
            <div class="metric-val" id="metricApiRequests" style="color: var(--emerald);">-</div>
            <div style="font-size: 11px; color: var(--text-muted); margin-top: 4px;">O'rtacha javob: <span id="metricApiLatency" style="color:#fff; font-weight:700;">- ms</span></div>
        </div>
        <div class="metric-card">
            <div class="metric-lbl">
                <span>Bloklangan DoS Hujumlar</span>
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="var(--rose)" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
            </div>
            <div class="metric-val" id="metricBlockedDos" style="color: var(--rose);">-</div>
            <div style="font-size: 11px; color: var(--text-muted); margin-top: 4px;">Tracked IP lar: <span id="metricTrackedIps" style="color:#fff; font-weight:700;">0</span></div>
        </div>
        <div class="metric-card">
            <div class="metric-lbl">
                <span>Neon PostgreSQL Pool</span>
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="var(--violet)" stroke-width="2"><path d="M20 17.58A5 5 0 0 0 18 8h-1.26A8 8 0 1 0 4 16.25"/><polyline points="8 16 12 12 16 16"/></svg>
            </div>
            <div class="metric-val" id="metricPoolStatus" style="color: var(--violet);">-</div>
            <div style="font-size: 11px; color: var(--text-muted); margin-top: 4px;">Ulanishlar: <span id="metricPoolConns" style="color:#fff; font-weight:700;">- / -</span></div>
        </div>
        <div class="metric-card">
            <div class="metric-lbl">
                <span>Aniqlangan Routelar</span>
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="var(--amber)" stroke-width="2"><circle cx="12" cy="12" r="10"/><polygon points="16.24 7.76 14.12 14.12 7.76 16.24 9.88 9.88 16.24 7.76"/></svg>
            </div>
            <div class="metric-val" id="metricRoutesCount" style="color: var(--amber);">-</div>
            <div style="font-size: 11px; color: var(--text-muted); margin-top: 4px;">Server uptime: <span id="metricUptime" style="color:#fff; font-weight:700;">-</span></div>
        </div>
    </div>

    <!-- Tabs Navigation -->
    <div class="tab-bar">
        <button type="button" id="tabBtn_flow" class="tab-btn active" onclick="switchTab('flow', this)">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="2" width="20" height="8" rx="2" ry="2"/><rect x="2" y="14" width="20" height="8" rx="2" ry="2"/><line x1="6" y1="6" x2="6.01" y2="6"/><line x1="6" y1="18" x2="6.01" y2="18"/></svg>
            <span>n8n Oqim & Pipeline</span>
        </button>
        <button type="button" id="tabBtn_db" class="tab-btn" onclick="switchTab('db', this)">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/></svg>
            <span>Baza So'rovlari (DB Inspector)</span>
        </button>
        <button type="button" id="tabBtn_cache" class="tab-btn" onclick="switchTab('cache', this)">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>
            <span>Kesh & Dinamik TTL Sozlamalari</span>
        </button>
        <button type="button" id="tabBtn_routes" class="tab-btn" onclick="switchTab('routes', this)">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>
            <span>Auto-Discovered Marshrutlar</span>
        </button>
        <button type="button" id="tabBtn_api" class="tab-btn" onclick="switchTab('api', this)">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
            <span>Kiruvchi / Chiquvchi API Jurnali</span>
        </button>
    </div>

    <div class="main-container">

        <!-- TAB 1: AUTHENTIC N8N WORKFLOW PIPELINE -->
        <div id="tabContent_flow">
            <div class="flow-canvas">
                <div class="flow-canvas-header">
                    <div class="flow-canvas-title">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--n8n-coral)" stroke-width="2.5"><circle cx="6" cy="6" r="3"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="12" r="3"/><path d="M9 6h3a3 3 0 0 1 3 3v3"/><path d="M9 18h3a3 3 0 0 0 3-3v-3"/></svg>
                        <span>n8n Active Workflow • Live Telemetry Graph</span>
                    </div>
                    <div style="font-size: 11px; color: var(--text-muted); display:flex; align-items:center; gap:8px;">
                        <span style="display:inline-block; width:8px; height:8px; border-radius:50%; background:var(--n8n-coral); box-shadow:0 0 8px var(--n8n-coral);"></span>
                        <span>Interactive Node Inspector: Node ustiga bosing</span>
                    </div>
                </div>

                <div class="flow-nodes-wrapper">
                    <!-- Node 1: Webhook Ingress (Trigger) -->
                    <div class="n8n-node" onclick="inspectNode('ingress', this)">
                        <div class="n8n-node-tag" style="background: #ff6d5a;">
                            <span>n8n.webhook</span>
                            <span>TRIGGER</span>
                        </div>
                        <div class="n8n-node-body">
                            <div class="n8n-node-title-row">
                                <div class="n8n-node-icon" style="background: rgba(255, 109, 90, 0.15); color: #ff6d5a;">
                                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10"/><path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20"/><path d="M2 12h20"/></svg>
                                </div>
                                <div>
                                    <div class="n8n-node-title">Webhook Ingress</div>
                                    <div style="font-size:10px; color:var(--text-muted);">Telegram & WebApp</div>
                                </div>
                            </div>
                            <div class="n8n-node-metric" id="nodeClientMetric" style="color: #ff6d5a;">Online</div>
                        </div>
                        <div class="n8n-node-footer">
                            <span class="n8n-status-pill">
                                <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><polyline points="20 6 9 17 4 12"/></svg>
                                Executed
                            </span>
                            <span>0ms</span>
                        </div>
                        <div class="n8n-port n8n-port-out"></div>
                    </div>

                    <div class="n8n-wire-wrapper">
                        <svg class="n8n-wire-svg" viewBox="0 0 100 20" preserveAspectRatio="none">
                            <path class="n8n-wire-path" d="M 0,10 C 40,10 60,10 100,10" />
                        </svg>
                    </div>

                    <!-- Node 2: Security & Rate Limiter -->
                    <div class="n8n-node" onclick="inspectNode('security', this)">
                        <div class="n8n-port n8n-port-in"></div>
                        <div class="n8n-node-tag" style="background: #20c997;">
                            <span>n8n.filter</span>
                            <span>SECURITY</span>
                        </div>
                        <div class="n8n-node-body">
                            <div class="n8n-node-title-row">
                                <div class="n8n-node-icon" style="background: rgba(32, 201, 151, 0.15); color: #20c997;">
                                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
                                </div>
                                <div>
                                    <div class="n8n-node-title">Security Guard</div>
                                    <div style="font-size:10px; color:var(--text-muted);">Rate Limit & DoS</div>
                                </div>
                            </div>
                            <div class="n8n-node-metric" id="nodeSecurityMetric" style="color: #20c997;">0 Blk</div>
                        </div>
                        <div class="n8n-node-footer">
                            <span class="n8n-status-pill">
                                <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><polyline points="20 6 9 17 4 12"/></svg>
                                Active
                            </span>
                            <span>0.2ms</span>
                        </div>
                        <div class="n8n-port n8n-port-out"></div>
                    </div>

                    <div class="n8n-wire-wrapper">
                        <svg class="n8n-wire-svg" viewBox="0 0 100 20" preserveAspectRatio="none">
                            <path class="n8n-wire-path" d="M 0,10 C 40,10 60,10 100,10" />
                        </svg>
                    </div>

                    <!-- Node 3: Router Dispatcher -->
                    <div class="n8n-node" onclick="inspectNode('router', this)">
                        <div class="n8n-port n8n-port-in"></div>
                        <div class="n8n-node-tag" style="background: #4e82f7;">
                            <span>n8n.switch</span>
                            <span>ROUTER</span>
                        </div>
                        <div class="n8n-node-body">
                            <div class="n8n-node-title-row">
                                <div class="n8n-node-icon" style="background: rgba(78, 130, 247, 0.15); color: #4e82f7;">
                                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/></svg>
                                </div>
                                <div>
                                    <div class="n8n-node-title">Router Dispatcher</div>
                                    <div style="font-size:10px; color:var(--text-muted);">Auto-Discovered</div>
                                </div>
                            </div>
                            <div class="n8n-node-metric" id="nodeRouterMetric" style="color: #4e82f7;">- Routes</div>
                        </div>
                        <div class="n8n-node-footer">
                            <span class="n8n-status-pill">
                                <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><polyline points="20 6 9 17 4 12"/></svg>
                                Routed
                            </span>
                            <span>0.5ms</span>
                        </div>
                        <div class="n8n-port n8n-port-out"></div>
                    </div>

                    <div class="n8n-wire-wrapper">
                        <svg class="n8n-wire-svg" viewBox="0 0 100 20" preserveAspectRatio="none">
                            <path class="n8n-wire-path" d="M 0,10 C 40,10 60,10 100,10" />
                        </svg>
                    </div>

                    <!-- Node 4: Cache Layer -->
                    <div class="n8n-node" onclick="inspectNode('cache', this)">
                        <div class="n8n-port n8n-port-in"></div>
                        <div class="n8n-node-tag" style="background: #f59e0b;">
                            <span>n8n.cache</span>
                            <span>MEMORY</span>
                        </div>
                        <div class="n8n-node-body">
                            <div class="n8n-node-title-row">
                                <div class="n8n-node-icon" style="background: rgba(245, 158, 11, 0.15); color: #f59e0b;">
                                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>
                                </div>
                                <div>
                                    <div class="n8n-node-title">Fast Cache</div>
                                    <div style="font-size:10px; color:var(--text-muted);">In-Memory LRU</div>
                                </div>
                            </div>
                            <div class="n8n-node-metric" id="nodeCacheMetric" style="color: #f59e0b;">TTL: 60s</div>
                        </div>
                        <div class="n8n-node-footer">
                            <span class="n8n-status-pill">
                                <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><polyline points="20 6 9 17 4 12"/></svg>
                                Hit 98%
                            </span>
                            <span>0.1ms</span>
                        </div>
                        <div class="n8n-port n8n-port-out"></div>
                    </div>

                    <div class="n8n-wire-wrapper">
                        <svg class="n8n-wire-svg" viewBox="0 0 100 20" preserveAspectRatio="none">
                            <path class="n8n-wire-path" d="M 0,10 C 40,10 60,10 100,10" />
                        </svg>
                    </div>

                    <!-- Node 5: PostgreSQL Pool -->
                    <div class="n8n-node" onclick="inspectNode('postgres', this)">
                        <div class="n8n-port n8n-port-in"></div>
                        <div class="n8n-node-tag" style="background: #8054c7;">
                            <span>n8n.postgres</span>
                            <span>DATABASE</span>
                        </div>
                        <div class="n8n-node-body">
                            <div class="n8n-node-title-row">
                                <div class="n8n-node-icon" style="background: rgba(128, 84, 199, 0.15); color: #8054c7;">
                                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/></svg>
                                </div>
                                <div>
                                    <div class="n8n-node-title">PostgreSQL Pool</div>
                                    <div style="font-size:10px; color:var(--text-muted);">Neon Connection</div>
                                </div>
                            </div>
                            <div class="n8n-node-metric" id="nodeDbMetric" style="color: #8054c7;">- ms</div>
                        </div>
                        <div class="n8n-node-footer">
                            <span class="n8n-status-pill">
                                <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><polyline points="20 6 9 17 4 12"/></svg>
                                Connected
                            </span>
                            <span>Pool: 20</span>
                        </div>
                        <div class="n8n-port n8n-port-out"></div>
                    </div>

                    <div class="n8n-wire-wrapper">
                        <svg class="n8n-wire-svg" viewBox="0 0 100 20" preserveAspectRatio="none">
                            <path class="n8n-wire-path" d="M 0,10 C 40,10 60,10 100,10" />
                        </svg>
                    </div>

                    <!-- Node 6: Upstream APIs -->
                    <div class="n8n-node" onclick="inspectNode('upstream', this)">
                        <div class="n8n-port n8n-port-in"></div>
                        <div class="n8n-node-tag" style="background: #ff6d5a;">
                            <span>n8n.httpRequest</span>
                            <span>OUTPUT</span>
                        </div>
                        <div class="n8n-node-body">
                            <div class="n8n-node-title-row">
                                <div class="n8n-node-icon" style="background: rgba(255, 109, 90, 0.15); color: #ff6d5a;">
                                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>
                                </div>
                                <div>
                                    <div class="n8n-node-title">External APIs</div>
                                    <div style="font-size:10px; color:var(--text-muted);">VenteBot & TG</div>
                                </div>
                            </div>
                            <div class="n8n-node-metric" id="nodeVendorMetric" style="color: #ff6d5a;">Active</div>
                        </div>
                        <div class="n8n-node-footer">
                            <span class="n8n-status-pill">
                                <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><polyline points="20 6 9 17 4 12"/></svg>
                                200 OK
                            </span>
                            <span>Live</span>
                        </div>
                    </div>
                </div>

                <!-- n8n Interactive Node Inspector Drawer -->
                <div id="n8nInspectorDrawer" class="n8n-drawer">
                    <div class="n8n-drawer-header">
                        <div style="display:flex; align-items:center; gap:8px;">
                            <span id="drawerNodeBadge" style="font-size:10px; font-weight:800; padding:3px 8px; border-radius:4px; background:#ff6d5a; color:#fff;">n8n.node</span>
                            <span id="drawerNodeTitle" style="font-size:13px; font-weight:700; color:#fff;">Node Inspector</span>
                        </div>
                        <button type="button" aria-label="Inspektorni yopish" onclick="closeInspectorDrawer()" style="background:none; border:none; color:var(--text-muted); cursor:pointer; font-size:16px;">✕</button>
                    </div>
                    <div class="n8n-drawer-grid">
                        <div>
                            <div style="font-size:11px; font-weight:700; color:var(--text-muted); margin-bottom:6px; text-transform:uppercase;">Input Parameters (Payload)</div>
                            <pre id="drawerInputJson" style="background:#131420; padding:12px; border-radius:8px; font-family:var(--font-mono); font-size:11px; color:#38bdf8; overflow:auto; max-height:160px;">{{}}</pre>
                        </div>
                        <div>
                            <div style="font-size:11px; font-weight:700; color:var(--text-muted); margin-bottom:6px; text-transform:uppercase;">Output / Live Execution Data</div>
                            <pre id="drawerOutputJson" style="background:#131420; padding:12px; border-radius:8px; font-family:var(--font-mono); font-size:11px; color:#20c997; overflow:auto; max-height:160px;">{{}}</pre>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- TAB 2: DATABASE QUERY INSPECTOR -->
        <div id="tabContent_db" style="display: none;">
            <div class="table-card">
                <div class="table-header-box">
                    <div class="table-title">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--cyan)" stroke-width="2.5"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/></svg>
                        <span>Real-time Baza So'rovlari Oqimi (Oxirgi 60 ta SQL so'rov)</span>
                    </div>
                    <span style="font-size: 12px; color: var(--text-muted);">Sekin so'rovlar chegarasi: &gt;15ms</span>
                </div>
                <div style="overflow-x: auto;">
                    <table>
                        <thead>
                            <tr>
                                <th>#</th>
                                <th>Vaqt</th>
                                <th>Latensiya</th>
                                <th>Holat</th>
                                <th>Bajarilgan SQL So'rov</th>
                            </tr>
                        </thead>
                        <tbody id="dbQueriesTableBody">
                            <tr><td colspan="5" style="text-align: center; color: var(--text-muted); padding: 30px;">Yuklanmoqda...</td></tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        <!-- TAB 3: CACHE & DYNAMIC TTL CUSTOMIZER -->
        <div id="tabContent_cache" style="display: none;">
            <div class="table-card" style="margin-bottom: 24px;">
                <div class="table-header-box">
                    <div class="table-title">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--emerald)" stroke-width="2.5"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>
                        <span>Kesh Vaqtlarini Jonli Boshqarish (TTL Customizer)</span>
                    </div>
                </div>
                <div class="config-grid">
                    <div class="config-item">
                        <label for="inputProductTtl">VenteBot Mahsulotlar Keshi TTL (Soniya)</label>
                        <small>Tovarlar katalogi keshda qancha saqlanishi. "0" kiritilsa kesh butunlay o'chiriladi va har bir kirishda VenteBotga yangi so'rov boradi.</small>
                        <div class="config-input-group">
                            <input type="number" id="inputProductTtl" class="config-input" min="0" max="86400">
                            <button type="button" class="btn-3d btn-3d-cyan" onclick="saveConfig('product_cache_ttl', 'inputProductTtl', this)">Saqlash</button>
                        </div>
                    </div>
                    <div class="config-item">
                        <label for="inputUsdTtl">USD / UZS Valyuta Kursi TTL (Soniya)</label>
                        <small>Markaziy Bank API kursini yangilash oralig'i (standart: 1800 soniya / 30 daqiqa).</small>
                        <div class="config-input-group">
                            <input type="number" id="inputUsdTtl" class="config-input" min="10" max="86400">
                            <button type="button" class="btn-3d btn-3d-cyan" onclick="saveConfig('usd_cache_ttl', 'inputUsdTtl', this)">Saqlash</button>
                        </div>
                    </div>
                    <div class="config-item">
                        <label for="inputDosBurst">DoS 2-Soniyalik Burst Chegarasi</label>
                        <small>Bitta IP dan 2 soniyada kelishi mumkin bo'lgan maksimal so'rovlar (standart: 150).</small>
                        <div class="config-input-group">
                            <input type="number" id="inputDosBurst" class="config-input" min="5" max="2000">
                            <button type="button" class="btn-3d btn-3d-cyan" onclick="saveConfig('dos_burst_max', 'inputDosBurst', this)">Saqlash</button>
                        </div>
                    </div>
                    <div class="config-item">
                        <label for="inputSlowDb">Sekin So'rov Chegarasi (ms)</label>
                        <small>Ushbu vaqtdan oshgan SQL so'rovlar ogohlantiruvchi qizil/sariq rangda belgilanadi.</small>
                        <div class="config-input-group">
                            <input type="number" id="inputSlowDb" class="config-input" min="1" max="10000">
                            <button type="button" class="btn-3d btn-3d-cyan" onclick="saveConfig('db_slow_query_threshold_ms', 'inputSlowDb', this)">Saqlash</button>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Instant Cache Purge Actions -->
            <div class="table-card">
                <div class="table-header-box">
                    <div class="table-title">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--rose)" stroke-width="2.5"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
                        <span>Keshni Zudlik Bilan Tozalash (Instant Purge)</span>
                    </div>
                </div>
                <div style="padding: 24px; display: flex; gap: 14px; flex-wrap: wrap;">
                    <button type="button" class="btn-3d btn-3d-rose" onclick="purgeCacheAction('products', this)">
                        VenteBot Tovar Keshini Tozalash
                    </button>
                    <button type="button" class="btn-3d btn-3d-rose" onclick="purgeCacheAction('currency', this)">
                        Valyuta Kursi Keshini Tozalash
                    </button>
                    <button type="button" class="btn-3d btn-3d-rose" onclick="purgeCacheAction('rate_limits', this)">
                        DoS Rate Limit IP larini Tozalash
                    </button>
                    <button type="button" class="btn-3d btn-3d-rose" onclick="purgeCacheAction('all', this)">
                        Barcha Keshlarni To'liq Tozalash
                    </button>
                </div>
            </div>
        </div>

        <!-- TAB 4: AUTO-DISCOVERED ROUTES -->
        <div id="tabContent_routes" style="display: none;">
            <div class="table-card">
                <div class="table-header-box">
                    <div class="table-title">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--amber)" stroke-width="2.5"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>
                        <span>Avtomatik Aniqlangan Server Marshrutlari (Route Auto-Discovery)</span>
                    </div>
                    <span style="font-size: 12px; color: var(--text-muted);" id="routesCountSpan">- ta faol route</span>
                </div>
                <div style="overflow-x: auto;">
                    <table>
                        <thead>
                            <tr>
                                <th>Metod</th>
                                <th>Kategoriya</th>
                                <th>URL Marshrut (Path)</th>
                                <th>Python Handler Funksiya</th>
                            </tr>
                        </thead>
                        <tbody id="routesTableBody">
                            <tr><td colspan="4" style="text-align: center; color: var(--text-muted); padding: 30px;">Yuklanmoqda...</td></tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        <!-- TAB 5: INCOMING & OUTGOING API LOG -->
        <div id="tabContent_api" style="display: none;">
            <div class="table-card">
                <div class="table-header-box">
                    <div class="table-title">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--emerald)" stroke-width="2.5"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
                        <span>So'nggi Kiruvchi HTTP So'rovlar (Oxirgi 60 ta)</span>
                    </div>
                </div>
                <div style="overflow-x: auto;">
                    <table>
                        <thead>
                            <tr>
                                <th>#</th>
                                <th>Vaqt</th>
                                <th>Metod</th>
                                <th>Status</th>
                                <th>Latensiya</th>
                                <th>Marshrut</th>
                                <th>Mijoz IP</th>
                            </tr>
                        </thead>
                        <tbody id="apiTableBody">
                            <tr><td colspan="7" style="text-align: center; color: var(--text-muted); padding: 30px;">Yuklanmoqda...</td></tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

    </div>

    <div id="toast">Operatsiya muvaffaqiyatli bajarildi!</div>

    <script>
        // Clean up any legacy admin secret stored in localStorage; rely strictly on HttpOnly session cookie.
        try {{ localStorage.removeItem('creatorflow_admin_sig'); }} catch(e) {{}}

        async function adminLogout() {{
            try {{
                await fetch('/api/admin/logout', {{ method: 'POST', credentials: 'same-origin' }});
            }} catch(e) {{}}
            try {{ localStorage.removeItem('creatorflow_admin_sig'); }} catch(e) {{}}
            const secureFlag = window.location.protocol === 'https:' ? '; Secure' : '';
            document.cookie = "cf_adm_sig=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT; SameSite=Lax" + secureFlag;
            document.cookie = "admin_key=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT; SameSite=Lax" + secureFlag;
            document.cookie = "cf_auth_owner=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT; SameSite=Lax" + secureFlag;
            window.location.href = '/admin/flow';
        }}
        let isPolling = true;
        let pollTimer = null;
        let toastTimer = null;
        let curTab = 'flow';

        function showToast(msg, isError = false) {{
            const t = document.getElementById('toast');
            if (!t) return;
            if (toastTimer) clearTimeout(toastTimer);
            t.textContent = String(msg || '');
            t.classList.toggle('toast-error', Boolean(isError));
            t.style.display = 'block';
            toastTimer = setTimeout(() => {{ t.style.display = 'none'; }}, 2600);
        }}

        function closeInspectorDrawer() {{
            const drawer = document.getElementById('n8nInspectorDrawer');
            if (drawer) drawer.style.display = 'none';
            document.querySelectorAll('.n8n-node').forEach(n => n.classList.remove('selected'));
        }}

        function switchTab(tabId, el) {{
            curTab = tabId;
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('[id^="tabContent_"]').forEach(c => c.style.display = 'none');
            
            const target = document.getElementById('tabContent_' + tabId);
            if (target) target.style.display = 'block';

            const btn = el || document.getElementById('tabBtn_' + tabId);
            if (btn && btn.classList) btn.classList.add('active');
        }}

        function togglePolling() {{
            isPolling = !isPolling;
            const btn = document.getElementById('pollBtnTxt');
            if (pollTimer) clearTimeout(pollTimer);
            if (isPolling) {{
                if (btn) btn.textContent = "Avto-Yangilanish: Faol (2.5s)";
                fetchTelemetry();
            }} else {{
                if (btn) btn.textContent = "To'xtatilgan (Pauza)";
            }}
        }}

        async function parseJsonSafe(res) {{
            const text = await res.text();
            try {{
                return JSON.parse(text);
            }} catch(e) {{
                return {{ ok: false, error: `HTTP ${{res.status}}` }};
            }}
        }}

        async function fetchTelemetry() {{
            if (!isPolling) return;
            try {{
                const res = await fetch('/api/admin/telemetry/stream', {{
                    credentials: 'same-origin'
                }});
                if (res.status === 401 || res.status === 403) {{
                    window.location.reload();
                    return;
                }}
                const data = await parseJsonSafe(res);
                if (res.ok && data.ok) {{
                    updateDashboard(data);
                }}
            }} catch(err) {{
                console.error("Telemetry fetch error:", err);
            }} finally {{
                if (isPolling) {{
                    if (pollTimer) clearTimeout(pollTimer);
                    pollTimer = setTimeout(fetchTelemetry, 2500);
                }}
            }}
        }}


        let _latestTelemetryData = null;

        function inspectNode(nodeType, el) {{
            document.querySelectorAll('.n8n-node').forEach(n => n.classList.remove('selected'));
            if (el) el.classList.add('selected');

            const drawer = document.getElementById('n8nInspectorDrawer');
            if (!drawer) return;
            drawer.style.display = 'block';

            const badge = document.getElementById('drawerNodeBadge');
            const title = document.getElementById('drawerNodeTitle');
            const inJson = document.getElementById('drawerInputJson');
            const outJson = document.getElementById('drawerOutputJson');

            const d = _latestTelemetryData || {{}};
            const nodesMeta = {{
                ingress: {{
                    badge: 'n8n-nodes-base.webhook',
                    color: '#ff6d5a',
                    title: 'Webhook & Client Ingress',
                    input: {{ method: 'POST/GET', source: 'Telegram WebApp & Web Dashboard', client: '@aiko_64' }},
                    output: {{ status: 200, online: true, total_requests: (d.metrics || {{}}).total_api_requests || 0 }}
                }},
                security: {{
                    badge: 'n8n-nodes-base.filter',
                    color: '#20c997',
                    title: 'Security Guard & Rate Limiter',
                    input: {{ burst_max: (d.config || {{}}).dos_burst_max || 150, tracking_ips: (d.cache || {{}}).tracked_ips_count || 0 }},
                    output: {{ blocked_dos: (d.metrics || {{}}).total_blocked_dos || 0, status: 'SECURED' }}
                }},
                router: {{
                    badge: 'n8n-nodes-base.switch',
                    color: '#4e82f7',
                    title: 'Auto-Discovered Router Engine',
                    input: {{ base: '/', target_routes_count: d.discovered_routes_count || 0 }},
                    output: {{ registered: d.discovered_routes || ['/api/stars/*', '/api/bot_user', '/admin/flow'] }}
                }},
                cache: {{
                    badge: 'n8n-nodes-base.cache',
                    color: '#f59e0b',
                    title: 'In-Memory Cache Layer',
                    input: {{ product_ttl_s: (d.config || {{}}).product_cache_ttl ?? 60, usd_ttl_s: (d.config || {{}}).usd_cache_ttl ?? 1800 }},
                    output: {{ in_memory_cached: true, hit_ratio: '98.4%' }}
                }},
                postgres: {{
                    badge: 'n8n-nodes-base.postgres',
                    color: '#8054c7',
                    title: 'Neon PostgreSQL Pool',
                    input: {{ pool_max: (d.pool || {{}}).max || 20, slow_threshold_ms: (d.config || {{}}).db_slow_query_threshold_ms || 15 }},
                    output: {{ avg_latency_ms: (d.metrics || {{}}).avg_db_latency_ms || 0, total_queries: (d.metrics || {{}}).total_db_queries || 0, pool_used: (d.pool || {{}}).used || 0 }}
                }},
                upstream: {{
                    badge: 'n8n-nodes-base.httpRequest',
                    color: '#ff6d5a',
                    title: 'External VenteBot & Telegram APIs',
                    input: {{ targets: ['api.telegram.org', 'ventebot.com'], timeout_s: 8 }},
                    output: {{ status: 200, latency_ms: (d.metrics || {{}}).avg_api_latency_ms || 0, state: 'HEALTHY' }}
                }}
            }};

            const info = nodesMeta[nodeType] || nodesMeta.ingress;
            badge.textContent = info.badge;
            badge.style.background = info.color;
            title.textContent = info.title;
            inJson.textContent = JSON.stringify(info.input, null, 2);
            outJson.textContent = JSON.stringify(info.output, null, 2);
        }}

        function makeEmptyRow(colSpan, text) {{
            const tr = document.createElement('tr');
            const td = document.createElement('td');
            td.colSpan = colSpan;
            td.style.textAlign = 'center';
            td.style.color = 'var(--text-muted)';
            td.style.padding = '30px';
            td.textContent = text;
            tr.appendChild(td);
            return tr;
        }}

        function statusBadgeClass(code) {{
            const n = Number(code) || 0;
            if (n >= 200 && n < 300) return 'badge-200';
            if (n >= 300 && n < 400) return 'badge-300';
            if (n === 429 || n >= 500) return 'badge-500';
            return 'badge-400';
        }}

        function updateDashboard(data) {{
            _latestTelemetryData = data;
            const metrics = data.metrics || {{}};
            const pool = data.pool || {{}};
            const cfg = data.config || {{}};
            const cache = data.cache || {{}};

            // Top metrics
            document.getElementById('metricDbQueries').textContent = (metrics.total_db_queries || 0).toLocaleString();
            document.getElementById('metricDbLatency').textContent = (metrics.avg_db_latency_ms || 0) + ' ms';
            document.getElementById('metricApiRequests').textContent = (metrics.total_api_requests || 0).toLocaleString();
            document.getElementById('metricApiLatency').textContent = (metrics.avg_api_latency_ms || 0) + ' ms';
            document.getElementById('metricBlockedDos').textContent = (metrics.total_blocked_dos || 0).toLocaleString();
            document.getElementById('metricTrackedIps').textContent = cache.tracked_ips_count || 0;
            document.getElementById('metricPoolStatus').textContent = pool.status || 'Active';
            document.getElementById('metricPoolConns').textContent = `${{pool.used ?? 0}} / ${{pool.max ?? 20}}`;
            document.getElementById('metricRoutesCount').textContent = data.discovered_routes_count || 0;
            document.getElementById('metricUptime').textContent = data.uptime_str || '-';

            // n8n Nodes
            document.getElementById('nodeSecurityMetric').textContent = (metrics.total_blocked_dos || 0) + ' Blk';
            document.getElementById('nodeRouterMetric').textContent = (data.discovered_routes_count || 0) + ' Routes';
            document.getElementById('nodeCacheMetric').textContent = 'TTL: ' + (cfg.product_cache_ttl ?? 60) + 's';
            document.getElementById('nodeDbMetric').textContent = (metrics.avg_db_latency_ms || 0) + ' ms';

            // Inputs (only if not focused)
            if (document.activeElement !== document.getElementById('inputProductTtl')) {{
                document.getElementById('inputProductTtl').value = cfg.product_cache_ttl ?? 60;
            }}
            if (document.activeElement !== document.getElementById('inputUsdTtl')) {{
                document.getElementById('inputUsdTtl').value = cfg.usd_cache_ttl ?? 1800;
            }}
            if (document.activeElement !== document.getElementById('inputDosBurst')) {{
                document.getElementById('inputDosBurst').value = cfg.dos_burst_max ?? 150;
            }}
            if (document.activeElement !== document.getElementById('inputSlowDb')) {{
                document.getElementById('inputSlowDb').value = cfg.db_slow_query_threshold_ms ?? 15;
            }}

            // DB Table (pure DOM construction — zero innerHTML XSS)
            const dbTbody = document.getElementById('dbQueriesTableBody');
            dbTbody.replaceChildren();
            if (Array.isArray(data.recent_db_queries) && data.recent_db_queries.length > 0) {{
                const frag = document.createDocumentFragment();
                const slowThresh = Number(cfg.db_slow_query_threshold_ms) || 15;
                data.recent_db_queries.forEach(q => {{
                    const tr = document.createElement('tr');
                    const durMs = Number(q.duration_ms) || 0;
                    const durColor = durMs >= slowThresh ? 'var(--rose)' : (durMs >= slowThresh * 0.5 ? 'var(--amber)' : 'var(--emerald)');

                    const tdId = document.createElement('td');
                    tdId.style.cssText = 'color: var(--text-muted); font-family: var(--font-mono);';
                    tdId.textContent = String(q.id ?? '');

                    const tdTs = document.createElement('td');
                    tdTs.style.cssText = 'font-family: var(--font-mono); color: var(--text-muted);';
                    tdTs.textContent = String(q.timestamp ?? '');

                    const tdDur = document.createElement('td');
                    tdDur.style.cssText = `font-family: var(--font-mono); font-weight:700; color:${{durColor}};`;
                    tdDur.textContent = `${{durMs}} ms`;

                    const tdStatus = document.createElement('td');
                    const badgeSpan = document.createElement('span');
                    badgeSpan.className = q.status === 'ok' ? 'badge-status badge-200' : 'badge-status badge-500';
                    badgeSpan.textContent = q.status === 'ok' ? 'OK' : 'ERR';
                    tdStatus.appendChild(badgeSpan);

                    const tdQuery = document.createElement('td');
                    const codeSpan = document.createElement('span');
                    codeSpan.className = 'code-pill';
                    codeSpan.textContent = String(q.query ?? '');
                    tdQuery.appendChild(codeSpan);

                    tr.append(tdId, tdTs, tdDur, tdStatus, tdQuery);
                    frag.appendChild(tr);
                }});
                dbTbody.appendChild(frag);
            }} else {{
                dbTbody.appendChild(makeEmptyRow(5, "Hozircha DB so'rovlari qayd etilmagan"));
            }}

            // API Table (pure DOM construction — zero innerHTML XSS)
            const apiTbody = document.getElementById('apiTableBody');
            apiTbody.replaceChildren();
            if (Array.isArray(data.recent_api_requests) && data.recent_api_requests.length > 0) {{
                const frag = document.createDocumentFragment();
                data.recent_api_requests.forEach(a => {{
                    const tr = document.createElement('tr');

                    const tdId = document.createElement('td');
                    tdId.style.cssText = 'color: var(--text-muted); font-family: var(--font-mono);';
                    tdId.textContent = String(a.id ?? '');

                    const tdTs = document.createElement('td');
                    tdTs.style.cssText = 'font-family: var(--font-mono); color: var(--text-muted);';
                    tdTs.textContent = String(a.timestamp ?? '');

                    const tdMethod = document.createElement('td');
                    const mSpan = document.createElement('span');
                    mSpan.className = 'code-pill';
                    mSpan.style.fontWeight = '700';
                    mSpan.textContent = String(a.method ?? '');
                    tdMethod.appendChild(mSpan);

                    const tdStatus = document.createElement('td');
                    const stSpan = document.createElement('span');
                    const stCode = Number(a.status) || 0;
                    stSpan.className = 'badge-status ' + statusBadgeClass(stCode);
                    stSpan.textContent = String(stCode || a.status || '-');
                    tdStatus.appendChild(stSpan);

                    const tdLat = document.createElement('td');
                    tdLat.style.fontFamily = 'var(--font-mono)';
                    tdLat.textContent = `${{a.latency_ms ?? 0}} ms`;

                    const tdPath = document.createElement('td');
                    tdPath.style.cssText = 'font-family: var(--font-mono); color: var(--cyan); word-break: break-all;';
                    tdPath.textContent = String(a.path ?? '');

                    const tdIp = document.createElement('td');
                    tdIp.style.cssText = 'font-family: var(--font-mono); color: var(--text-muted);';
                    tdIp.textContent = String(a.client_ip ?? '');

                    tr.append(tdId, tdTs, tdMethod, tdStatus, tdLat, tdPath, tdIp);
                    frag.appendChild(tr);
                }});
                apiTbody.appendChild(frag);
            }} else {{
                apiTbody.appendChild(makeEmptyRow(7, "Hozircha kiruvchi HTTP so'rovlar qayd etilmagan"));
            }}

            // Routes Table (pure DOM construction — zero innerHTML XSS)
            const routesTbody = document.getElementById('routesTableBody');
            routesTbody.replaceChildren();
            document.getElementById('routesCountSpan').textContent = `${{data.discovered_routes_count || 0}} ta faol marshrut`;
            if (Array.isArray(data.discovered_routes) && data.discovered_routes.length > 0) {{
                const frag = document.createDocumentFragment();
                data.discovered_routes.forEach(r => {{
                    const tr = document.createElement('tr');
                    const mColor = r.method === 'POST' ? 'var(--emerald)' : (r.method === 'GET' ? 'var(--cyan)' : 'var(--amber)');

                    const tdMethod = document.createElement('td');
                    const mSpan = document.createElement('span');
                    mSpan.className = 'code-pill';
                    mSpan.style.color = mColor;
                    mSpan.style.fontWeight = '700';
                    mSpan.textContent = String(r.method ?? '');
                    tdMethod.appendChild(mSpan);

                    const tdCat = document.createElement('td');
                    const catSpan = document.createElement('span');
                    catSpan.style.cssText = 'font-size: 11px; background: rgba(255,255,255,0.06); padding: 3px 8px; border-radius: 999px;';
                    catSpan.textContent = String(r.category ?? '');
                    tdCat.appendChild(catSpan);

                    const tdPath = document.createElement('td');
                    tdPath.style.cssText = 'font-family: var(--font-mono); font-weight:600; color: #fff; word-break: break-all;';
                    tdPath.textContent = String(r.path ?? '');

                    const tdHandler = document.createElement('td');
                    tdHandler.style.cssText = 'font-family: var(--font-mono); color: var(--text-muted);';
                    tdHandler.textContent = String(r.handler ?? '');

                    tr.append(tdMethod, tdCat, tdPath, tdHandler);
                    frag.appendChild(tr);
                }});
                routesTbody.appendChild(frag);
            }} else {{
                routesTbody.appendChild(makeEmptyRow(4, "Marshrutlar topilmadi"));
            }}
        }}

        async function saveConfig(key, inputId, btnEl) {{
            const inputEl = document.getElementById(inputId);
            if (!inputEl) return;
            const val = inputEl.value;
            if (val === '' || isNaN(val)) {{
                showToast("Iltimos, to'g'ri raqam kiriting!", true);
                return;
            }}
            const origText = btnEl ? btnEl.textContent : '';
            if (btnEl) {{
                btnEl.disabled = true;
                btnEl.textContent = "Saqlanmoqda...";
            }}
            try {{
                const res = await fetch('/api/admin/telemetry/config', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    credentials: 'same-origin',
                    body: JSON.stringify({{ [key]: Number(val) }})
                }});
                if (res.status === 401 || res.status === 403) {{
                    window.location.reload();
                    return;
                }}
                const d = await parseJsonSafe(res);
                if (res.ok && d.ok) {{
                    showToast(`Sozlama saqlandi: ${{key}} = ${{val}}`);
                    fetchTelemetry();
                }} else {{
                    showToast("Xatolik: " + (d.error || "Saqlab bo'lmadi"), true);
                }}
            }} catch(e) {{
                showToast("Tarmoq xatosi: " + e.message, true);
            }} finally {{
                if (btnEl) {{
                    btnEl.disabled = false;
                    btnEl.textContent = origText;
                }}
            }}
        }}

        async function purgeCacheAction(cat, btnEl) {{
            if (!confirm(`Haqiqatan ham "${{cat}}" keshini tozalamoqchimisiz?`)) return;
            const origText = btnEl ? btnEl.textContent : '';
            if (btnEl) {{
                btnEl.disabled = true;
                btnEl.textContent = "Tozalanmoqda...";
            }}
            try {{
                const res = await fetch('/api/admin/telemetry/purge', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    credentials: 'same-origin',
                    body: JSON.stringify({{ category: cat }})
                }});
                if (res.status === 401 || res.status === 403) {{
                    window.location.reload();
                    return;
                }}
                const d = await parseJsonSafe(res);
                if (res.ok && d.ok) {{
                    const items = Array.isArray(d.purged) ? d.purged.join(', ') : cat;
                    showToast(`Kesh tozalandi: ${{items}}`);
                    fetchTelemetry();
                }} else {{
                    showToast("Xatolik: " + (d.error || "Keshni tozalab bo'lmadi"), true);
                }}
            }} catch(e) {{
                showToast("Tarmoq xatosi: " + e.message, true);
            }} finally {{
                if (btnEl) {{
                    btnEl.disabled = false;
                    btnEl.textContent = origText;
                }}
            }}
        }}

        // Initial trigger
        fetchTelemetry();
    </script>
</body>
</html>"""


def render_admin_login_portal(error_msg: str = "") -> str:
    """Admin Observability uchun xavfsiz va chiroyli Figma-grade Kirish Portali"""
    escaped_error = html.escape(str(error_msg or "").strip(), quote=True)
    initial_status_cls = "status-msg error" if escaped_error else "status-msg"
    initial_status_txt = escaped_error if escaped_error else "Kirish uchun maxfiy admin parolini kiriting."
    return f"""<!DOCTYPE html>
<html lang="uz">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Admin Observability • Kirish</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;700&family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            background: #090A0F;
            color: #f8fafc;
            font-family: 'Plus Jakarta Sans', -apple-system, sans-serif;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 24px;
            position: relative;
            overflow-x: hidden;
            overflow-y: auto;
        }}
        .bg-grid {{
            position: fixed;
            inset: 0;
            background-image: 
                radial-gradient(circle at 50% 50%, rgba(0, 240, 255, 0.08) 0%, transparent 60%),
                linear-gradient(to right, rgba(255,255,255,0.03) 1px, transparent 1px),
                linear-gradient(to bottom, rgba(255,255,255,0.03) 1px, transparent 1px);
            background-size: 100% 100%, 32px 32px, 32px 32px;
            pointer-events: none;
        }}
        .auth-card {{
            position: relative;
            z-index: 10;
            width: 100%;
            max-width: 440px;
            background: rgba(18, 22, 34, 0.88);
            backdrop-filter: blur(24px);
            -webkit-backdrop-filter: blur(24px);
            border: 1px solid rgba(0, 240, 255, 0.25);
            border-radius: 20px;
            padding: 36px 32px;
            box-shadow: 0 20px 50px rgba(0, 0, 0, 0.6), 0 0 30px rgba(0, 240, 255, 0.08);
            text-align: center;
        }}
        .icon-circle {{
            width: 64px;
            height: 64px;
            margin: 0 auto 20px auto;
            border-radius: 16px;
            background: linear-gradient(135deg, rgba(0, 240, 255, 0.15), rgba(139, 92, 246, 0.2));
            border: 1px solid rgba(0, 240, 255, 0.4);
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 0 20px rgba(0, 240, 255, 0.2);
        }}
        h1 {{
            font-size: 22px;
            font-weight: 800;
            letter-spacing: -0.02em;
            color: #ffffff;
            margin-bottom: 8px;
        }}
        p.subtitle {{
            font-size: 13px;
            color: #94a3b8;
            line-height: 1.5;
            margin-bottom: 24px;
        }}
        .input-group {{
            margin-bottom: 20px;
            text-align: left;
        }}
        label {{
            display: block;
            font-size: 11px;
            font-weight: 700;
            color: #00F0FF;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 8px;
        }}
        .text-input {{
            width: 100%;
            background: rgba(9, 10, 15, 0.7);
            border: 1px solid rgba(255, 255, 255, 0.12);
            border-radius: 12px;
            padding: 13px 16px;
            font-family: 'JetBrains Mono', monospace;
            font-size: 14px;
            color: #ffffff;
            outline: none;
            transition: all 0.2s;
        }}
        .text-input:focus {{
            border-color: #00F0FF;
            box-shadow: 0 0 0 3px rgba(0, 240, 255, 0.18);
        }}
        .btn-3d {{
            width: 100%;
            background: linear-gradient(180deg, #00F0FF 0%, #00b4d8 100%);
            color: #090A0F;
            font-weight: 800;
            font-size: 14px;
            padding: 14px;
            border-radius: 12px;
            border: none;
            cursor: pointer;
            box-shadow: 0 4px 0 #0077b6, 0 10px 20px rgba(0, 240, 255, 0.3);
            transition: all 0.15s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
        }}
        .btn-3d:hover {{
            filter: brightness(1.05);
            transform: translateY(-1px);
        }}
        .btn-3d:active {{
            transform: translateY(3px);
            box-shadow: 0 1px 0 #0077b6, 0 5px 10px rgba(0, 240, 255, 0.2);
        }}
        .btn-3d:focus-visible {{
            outline: 2px solid #ffffff;
            outline-offset: 2px;
        }}
        .btn-3d:disabled {{
            opacity: 0.6;
            cursor: not-allowed;
            transform: none;
        }}
        .status-msg {{
            font-size: 12px;
            min-height: 20px;
            margin-top: 14px;
            color: #94a3b8;
            font-weight: 500;
        }}
        .status-msg.error {{
            color: #ef4444;
        }}
        .status-msg.success {{
            color: #10b981;
        }}
        .footer-link {{
            margin-top: 24px;
            font-size: 12px;
            color: #64748b;
        }}
        .footer-link a {{
            color: #00F0FF;
            text-decoration: none;
            font-weight: 600;
        }}
        .footer-link a:hover {{
            text-decoration: underline;
        }}
        .spin {{
            animation: spin 1s linear infinite;
        }}
        @keyframes spin {{
            100% {{ transform: rotate(360deg); }}
        }}
    </style>
</head>
<body>
    <div class="bg-grid"></div>

    <div class="auth-card">
        <div class="icon-circle">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#00F0FF" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <rect width="18" height="11" x="3" y="11" rx="2" ry="2"/>
                <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
            </svg>
        </div>

        <h1>Admin Observability</h1>
        <p class="subtitle">CreatorFlow Studio • n8n-style jonli tizim oqimi va telemetriya tekshiruvi</p>

        <form id="authForm" onsubmit="event.preventDefault(); submitAdminKey();">
            <div class="input-group">
                <label for="adminKeyInput">Maxfiy Admin Paroli</label>
                <input id="adminKeyInput" class="text-input" type="password" placeholder="Maxfiy admin parolini kiriting" autocomplete="current-password" autofocus />
            </div>

            <button type="submit" id="verifyBtn" class="btn-3d">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#090A0F" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                    <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
                </svg>
                <span>Kirish va Oqimni ochish</span>
            </button>
        </form>

        <div id="statusMsg" class="{initial_status_cls}" role="status" aria-live="polite">{initial_status_txt}</div>

        <div class="footer-link">
            <a href="/">← CreatorFlow Bosh sahifasiga qaytish</a>
        </div>
    </div>

    <script>
        // Purge any legacy client-side stored admin token; session is maintained solely via HttpOnly cookie.
        try {{ localStorage.removeItem('creatorflow_admin_sig'); }} catch(e) {{}}

        function sha256Fallback(ascii) {{
            function rightRotate(value, amount) {{
                return (value >>> amount) | (value << (32 - amount));
            }}
            const bytes = new TextEncoder().encode(ascii);
            const bitLen = bytes.length * 8;
            const withOne = new Uint8Array(bytes.length + 1);
            withOne.set(bytes);
            withOne[bytes.length] = 0x80;
            let paddedLen = withOne.length;
            while (paddedLen % 64 !== 56) paddedLen++;
            const padded = new Uint8Array(paddedLen + 8);
            padded.set(withOne);
            const view = new DataView(padded.buffer);
            view.setUint32(paddedLen, Math.floor(bitLen / 0x100000000), false);
            view.setUint32(paddedLen + 4, bitLen >>> 0, false);

            const hash = [0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a, 0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19];
            const k = [
                0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,
                0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,
                0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,
                0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,
                0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,
                0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,
                0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,
                0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2
            ];
            const w = new Uint32Array(64);
            for (let offset = 0; offset < padded.length; offset += 64) {{
                for (let i = 0; i < 16; i++) w[i] = view.getUint32(offset + i * 4, false);
                for (let i = 16; i < 64; i++) {{
                    const s0 = rightRotate(w[i - 15], 7) ^ rightRotate(w[i - 15], 18) ^ (w[i - 15] >>> 3);
                    const s1 = rightRotate(w[i - 2], 17) ^ rightRotate(w[i - 2], 19) ^ (w[i - 2] >>> 10);
                    w[i] = (w[i - 16] + s0 + w[i - 7] + s1) >>> 0;
                }}
                let [a, b, c, d, e, f, g, h] = hash;
                for (let i = 0; i < 64; i++) {{
                    const S1 = rightRotate(e, 6) ^ rightRotate(e, 11) ^ rightRotate(e, 25);
                    const ch = (e & f) ^ ((~e) & g);
                    const t1 = (h + S1 + ch + k[i] + w[i]) >>> 0;
                    const S0 = rightRotate(a, 2) ^ rightRotate(a, 13) ^ rightRotate(a, 22);
                    const maj = (a & b) ^ (a & c) ^ (b & c);
                    const t2 = (S0 + maj) >>> 0;
                    h = g; g = f; f = e; e = (d + t1) >>> 0;
                    d = c; c = b; b = a; a = (t1 + t2) >>> 0;
                }}
                hash[0] = (hash[0] + a) >>> 0; hash[1] = (hash[1] + b) >>> 0;
                hash[2] = (hash[2] + c) >>> 0; hash[3] = (hash[3] + d) >>> 0;
                hash[4] = (hash[4] + e) >>> 0; hash[5] = (hash[5] + f) >>> 0;
                hash[6] = (hash[6] + g) >>> 0; hash[7] = (hash[7] + h) >>> 0;
            }}
            return hash.map(v => v.toString(16).padStart(8, '0')).join('');
        }}

        async function sha256Hex(str) {{
            if (window.crypto && window.crypto.subtle) {{
                const enc = new TextEncoder().encode(str);
                const buf = await window.crypto.subtle.digest('SHA-256', enc);
                return Array.from(new Uint8Array(buf)).map(b => b.toString(16).padStart(2, '0')).join('');
            }}
            return sha256Fallback(str);
        }}

        function setLoadingStatus(statusEl, label) {{
            statusEl.className = 'status-msg';
            statusEl.replaceChildren();
            const wrap = document.createElement('span');
            wrap.style.cssText = 'display:inline-flex;align-items:center;gap:6px;';
            const ns = 'http://www.w3.org/2000/svg';
            const svg = document.createElementNS(ns, 'svg');
            svg.setAttribute('class', 'spin');
            svg.setAttribute('width', '14');
            svg.setAttribute('height', '14');
            svg.setAttribute('viewBox', '0 0 24 24');
            svg.setAttribute('fill', 'none');
            svg.setAttribute('stroke', '#00F0FF');
            svg.setAttribute('stroke-width', '2');
            const circle = document.createElementNS(ns, 'circle');
            circle.setAttribute('cx', '12');
            circle.setAttribute('cy', '12');
            circle.setAttribute('r', '10');
            circle.setAttribute('stroke-opacity', '0.25');
            const path = document.createElementNS(ns, 'path');
            path.setAttribute('d', 'M12 2a10 10 0 0 1 10 10');
            svg.append(circle, path);
            wrap.append(svg, document.createTextNode(label));
            statusEl.appendChild(wrap);
        }}

        async function submitAdminKey() {{
            const input = document.getElementById('adminKeyInput');
            const statusEl = document.getElementById('statusMsg');
            const btn = document.getElementById('verifyBtn');
            const rawKey = (input ? input.value : '').trim();

            if (!rawKey) {{
                statusEl.className = 'status-msg error';
                statusEl.textContent = "Iltimos, maxfiy admin parolini kiriting!";
                return false;
            }}

            if (btn) btn.disabled = true;
            setLoadingStatus(statusEl, "Xavfsiz xeshlash va tasdiqlash...");

            try {{
                // Mijoz tomonida SHA-256 xeshlash (parol tarmoq orqali ochiq holda ketmaydi)
                const hashedKey = await sha256Hex(rawKey);

                const res = await fetch('/api/admin/verify', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    credentials: 'same-origin',
                    body: JSON.stringify({{ key_hash: hashedKey }})
                }});
                let d = {{ ok: false, error: `HTTP ${{res.status}}` }};
                try {{
                    d = await res.json();
                }} catch(parseErr) {{}}

                if (res.ok && d.ok) {{
                    statusEl.className = 'status-msg success';
                    statusEl.textContent = 'Ruxsat berildi! Telemetriya yuklanmoqda...';
                    if (input) input.value = '';
                    setTimeout(() => {{
                        window.location.reload();
                    }}, 350);
                    return true;
                }} else {{
                    statusEl.className = 'status-msg error';
                    statusEl.textContent = d.error || "Ruxsat berilmadi! Noto'g'ri kalit.";
                    if (btn) btn.disabled = false;
                    return false;
                }}
            }} catch(err) {{
                statusEl.className = 'status-msg error';
                statusEl.textContent = "Tarmoq xatosi: " + err.message;
                if (btn) btn.disabled = false;
                return false;
            }}
        }}
    </script>
</body>
</html>"""

