"""
CreatorFlow Studio - Enterprise Telemetry, Observability & n8n-Style Workflow Inspector
Real-time database query tracing, dynamic TTL cache controls, live API node graph, and auto-discovered route registry.
"""

import time
import os
import re
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
    "dos_burst_max": 30,           # DoS 2-soniyalik burst chegarasi
    "dos_burst_window": 2,         # DoS burst oyna vaqti (soniya)
    "dos_minute_max": 90,          # 1 daqiqalik maksimal so'rovlar
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

def sanitize_sql(sql_str: str) -> str:
    """SQL matnidan maxfiy ma'lumotlar va uzun whitespace larni tozalash"""
    if not sql_str:
        return ""
    # Whitespace normalization
    cleaned = re.sub(r'\s+', ' ', str(sql_str).strip())
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
    """Admin tomonidan parametrni jonli o'zgartirish"""
    for k, v in updates.items():
        if k in _DYNAMIC_CONFIG:
            try:
                _DYNAMIC_CONFIG[k] = type(_DYNAMIC_CONFIG[k])(v)
            except Exception:
                _DYNAMIC_CONFIG[k] = v
    return dict(_DYNAMIC_CONFIG)

def purge_cache(category: str) -> Dict[str, Any]:
    """Keshni tozalash mexanizmi"""
    purged_items = []

    # 1. VenteBot Mahsulotlar Keshi
    if category in ("all", "products", "ventebot"):
        try:
            from ventebot_service import ventebot_service
            if hasattr(ventebot_service, "cache") and hasattr(ventebot_service.cache, "clear"):
                ventebot_service.cache.clear()
            purged_items.append("VenteBot Mahsulotlar & Narxlar Keshi")
        except Exception as e:
            purged_items.append(f"VenteBot xatosi: {e}")

    # 2. Valyuta Kursi Keshi
    if category in ("all", "currency"):
        try:
            from currency_service import currency_service
            currency_service._last_updated = 0.0
            purged_items.append("USD / UZS Valyuta Kursi Keshi")
        except Exception as e:
            purged_items.append(f"Valyuta kesh xatosi: {e}")

    # 3. DoS Rate Limiting Xotirasi
    if category in ("all", "rate_limits"):
        try:
            from main import _IP_RATE_LIMITS, _SENSITIVE_IP_LIMITS
            _IP_RATE_LIMITS.clear()
            _SENSITIVE_IP_LIMITS.clear()
            purged_items.append("DoS va Rate Limiting IP Ro'yxati")
        except Exception as e:
            purged_items.append(f"Rate limit xatosi: {e}")

    return {
        "ok": True,
        "category": category,
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
        "dos_burst_max": _DYNAMIC_CONFIG.get("dos_burst_max", 30),
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
    # Xavfsizlik: Bot tokeni (masalan 1234:ABC formatida) hech qachon HTML shablonga kiritilmaydi
    safe_admin_key = str(admin_key or "").strip()
    if ":" in safe_admin_key or "bot" in safe_admin_key.lower():
        safe_admin_key = "6735799833"
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
            --bg: #08090E;
            --surface: #0E111A;
            --surface-card: rgba(18, 22, 34, 0.75);
            --border: rgba(255, 255, 255, 0.08);
            --border-hover: rgba(255, 255, 255, 0.16);
            --cyan: #00F0FF;
            --emerald: #10B981;
            --violet: #8B5CF6;
            --amber: #F59E0B;
            --rose: #EF4444;
            --text-main: #F3F4F6;
            --text-muted: #94A3B8;
            --font-sans: 'Plus Jakarta Sans', sans-serif;
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
            background: linear-gradient(135deg, var(--violet) 0%, var(--cyan) 100%);
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 0 16px rgba(0, 240, 255, 0.35);
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
        /* n8n Node Flow Pipeline Canvas */
        .flow-canvas {{
            background: rgba(14, 17, 26, 0.85);
            border: 1px solid var(--border);
            border-radius: 24px;
            padding: 32px 24px;
            position: relative;
            overflow-x: auto;
            margin-bottom: 28px;
        }}
        .flow-nodes-wrapper {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            min-width: 960px;
            position: relative;
            padding: 20px 0;
        }}
        .flow-node {{
            background: rgba(22, 27, 42, 0.95);
            border: 1px solid rgba(255, 255, 255, 0.12);
            border-radius: 18px;
            padding: 18px;
            width: 180px;
            position: relative;
            z-index: 2;
            box-shadow: 0 8px 30px rgba(0, 0, 0, 0.4);
            transition: all 0.25s ease;
        }}
        .flow-node:hover {{
            transform: translateY(-4px);
            border-color: var(--cyan);
            box-shadow: 0 12px 36px rgba(0, 240, 255, 0.18);
        }}
        .flow-node-header {{
            display: flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 8px;
        }}
        .flow-node-icon {{
            width: 28px;
            height: 28px;
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 13px;
        }}
        .flow-node-title {{
            font-size: 12px;
            font-weight: 700;
            color: var(--text-main);
        }}
        .flow-node-metric {{
            font-family: var(--font-mono);
            font-size: 16px;
            font-weight: 800;
            color: var(--cyan);
        }}
        .flow-node-sub {{
            font-size: 10px;
            color: var(--text-muted);
            margin-top: 2px;
        }}
        .flow-wire {{
            flex: 1;
            height: 3px;
            background: linear-gradient(90deg, rgba(0, 240, 255, 0.3), rgba(139, 92, 246, 0.5));
            position: relative;
            margin: 0 -4px;
            z-index: 1;
        }}
        .flow-wire::after {{
            content: '';
            position: absolute;
            top: -3px;
            left: 0;
            width: 9px;
            height: 9px;
            border-radius: 50%;
            background: var(--cyan);
            box-shadow: 0 0 10px var(--cyan);
            animation: moveParticle 2.5s infinite linear;
        }}
        @keyframes moveParticle {{
            0% {{ left: 0%; opacity: 0; }}
            20% {{ opacity: 1; }}
            80% {{ opacity: 1; }}
            100% {{ left: 100%; opacity: 0; }}
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
        .badge-401, .badge-403 {{ background: rgba(245, 158, 11, 0.15); color: var(--amber); border: 1px solid rgba(245, 158, 11, 0.3); }}
        .badge-429, .badge-500 {{ background: rgba(239, 68, 68, 0.15); color: var(--rose); border: 1px solid rgba(239, 68, 68, 0.3); }}
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
        <div style="display: flex; gap: 10px; align-items: center;">
            <button id="pollBtn" class="btn-3d btn-3d-dark" onclick="togglePolling()">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10"/><polygon points="10 8 16 12 10 16 10 8"/></svg>
                <span id="pollBtnTxt">Avto-Yangilanish: Faol (2.5s)</span>
            </button>
            <a href="/" class="btn-3d btn-3d-dark" style="text-decoration: none;">
                Ilovaga qaytish
            </a>
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
        <button class="tab-btn active" onclick="switchTab('flow')">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="2" width="20" height="8" rx="2" ry="2"/><rect x="2" y="14" width="20" height="8" rx="2" ry="2"/><line x1="6" y1="6" x2="6.01" y2="6"/><line x1="6" y1="18" x2="6.01" y2="18"/></svg>
            <span>n8n Oqim & Pipeline</span>
        </button>
        <button class="tab-btn" onclick="switchTab('db')">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/></svg>
            <span>Baza So'rovlari (DB Inspector)</span>
        </button>
        <button class="tab-btn" onclick="switchTab('cache')">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>
            <span>Kesh & Dinamik TTL Sozlamalari</span>
        </button>
        <button class="tab-btn" onclick="switchTab('routes')">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>
            <span>Auto-Discovered Marshrutlar</span>
        </button>
        <button class="tab-btn" onclick="switchTab('api')">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
            <span>Kiruvchi / Chiquvchi API Jurnali</span>
        </button>
    </div>

    <div class="main-container">

        <!-- TAB 1: N8N INTERACTIVE NODE FLOW -->
        <div id="tabContent_flow">
            <div class="flow-canvas">
                <div style="font-size: 13px; font-weight: 800; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 20px;">
                    Jonli n8n Pipeline & Ma'lumotlar Harakati
                </div>
                <div class="flow-nodes-wrapper">
                    <!-- Node 1: Client Ingress -->
                    <div class="flow-node">
                        <div class="flow-node-header">
                            <div class="flow-node-icon" style="background: rgba(0, 240, 255, 0.15); color: var(--cyan);">
                                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10"/><path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20"/><path d="M2 12h20"/></svg>
                            </div>
                            <div class="flow-node-title">Client Ingress</div>
                        </div>
                        <div class="flow-node-metric" id="nodeClientMetric">Online</div>
                        <div class="flow-node-sub">Telegram & Web</div>
                    </div>

                    <div class="flow-wire"></div>

                    <!-- Node 2: Security & Rate Limiter -->
                    <div class="flow-node">
                        <div class="flow-node-header">
                            <div class="flow-node-icon" style="background: rgba(239, 68, 68, 0.15); color: var(--rose);">
                                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
                            </div>
                            <div class="flow-node-title">Security Guard</div>
                        </div>
                        <div class="flow-node-metric" id="nodeSecurityMetric" style="color: var(--rose);">0 Blk</div>
                        <div class="flow-node-sub">DoS & Method Guard</div>
                    </div>

                    <div class="flow-wire"></div>

                    <!-- Node 3: Router Dispatcher -->
                    <div class="flow-node">
                        <div class="flow-node-header">
                            <div class="flow-node-icon" style="background: rgba(245, 158, 11, 0.15); color: var(--amber);">
                                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/></svg>
                            </div>
                            <div class="flow-node-title">Router Engine</div>
                        </div>
                        <div class="flow-node-metric" id="nodeRouterMetric" style="color: var(--amber);">- Routes</div>
                        <div class="flow-node-sub">Auto-Discovered</div>
                    </div>

                    <div class="flow-wire"></div>

                    <!-- Node 4: Cache Layer -->
                    <div class="flow-node">
                        <div class="flow-node-header">
                            <div class="flow-node-icon" style="background: rgba(16, 185, 129, 0.15); color: var(--emerald);">
                                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>
                            </div>
                            <div class="flow-node-title">Cache Layer</div>
                        </div>
                        <div class="flow-node-metric" id="nodeCacheMetric" style="color: var(--emerald);">TTL: 60s</div>
                        <div class="flow-node-sub">In-Memory Fast</div>
                    </div>

                    <div class="flow-wire"></div>

                    <!-- Node 5: Neon PostgreSQL DB -->
                    <div class="flow-node">
                        <div class="flow-node-header">
                            <div class="flow-node-icon" style="background: rgba(139, 92, 246, 0.15); color: var(--violet);">
                                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/></svg>
                            </div>
                            <div class="flow-node-title">Neon Postgres</div>
                        </div>
                        <div class="flow-node-metric" id="nodeDbMetric" style="color: var(--violet);">- ms</div>
                        <div class="flow-node-sub">Connection Pool</div>
                    </div>

                    <div class="flow-wire"></div>

                    <!-- Node 6: Upstream APIs -->
                    <div class="flow-node">
                        <div class="flow-node-header">
                            <div class="flow-node-icon" style="background: rgba(0, 240, 255, 0.15); color: var(--cyan);">
                                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>
                            </div>
                            <div class="flow-node-title">VenteBot & TG</div>
                        </div>
                        <div class="flow-node-metric" id="nodeVendorMetric" style="color: var(--cyan);">Active</div>
                        <div class="flow-node-sub">External APIs</div>
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
                        <label>VenteBot Mahsulotlar Keshi TTL (Soniya)</label>
                        <small>Tovarlar katalogi keshda qancha saqlanishi. "0" kiritilsa kesh butunlay o'chiriladi va har bir kirishda VenteBotga yangi so'rov boradi.</small>
                        <div class="config-input-group">
                            <input type="number" id="inputProductTtl" class="config-input" min="0" max="86400">
                            <button class="btn-3d btn-3d-cyan" onclick="saveConfig('product_cache_ttl', 'inputProductTtl')">Saqlash</button>
                        </div>
                    </div>
                    <div class="config-item">
                        <label>USD / UZS Valyuta Kursi TTL (Soniya)</label>
                        <small>Markaziy Bank API kursini yangilash oralig'i (standart: 1800 soniya / 30 daqiqa).</small>
                        <div class="config-input-group">
                            <input type="number" id="inputUsdTtl" class="config-input" min="10" max="86400">
                            <button class="btn-3d btn-3d-cyan" onclick="saveConfig('usd_cache_ttl', 'inputUsdTtl')">Saqlash</button>
                        </div>
                    </div>
                    <div class="config-item">
                        <label>DoS 2-Soniyalik Burst Chegarasi</label>
                        <small>Bitta IP dan 2 soniyada kelishi mumkin bo'lgan maksimal so'rovlar (standart: 30).</small>
                        <div class="config-input-group">
                            <input type="number" id="inputDosBurst" class="config-input" min="5" max="200">
                            <button class="btn-3d btn-3d-cyan" onclick="saveConfig('dos_burst_max', 'inputDosBurst')">Saqlash</button>
                        </div>
                    </div>
                    <div class="config-item">
                        <label>Sekin So'rov Chegarasi (ms)</label>
                        <small>Ushbu vaqtdan oshgan SQL so'rovlar ogohlantiruvchi qizil/sariq rangda belgilanadi.</small>
                        <div class="config-input-group">
                            <input type="number" id="inputSlowDb" class="config-input" min="1" max="1000">
                            <button class="btn-3d btn-3d-cyan" onclick="saveConfig('db_slow_query_threshold_ms', 'inputSlowDb')">Saqlash</button>
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
                    <button class="btn-3d btn-3d-rose" onclick="purgeCacheAction('products')">
                        VenteBot Tovar Keshini Tozalash
                    </button>
                    <button class="btn-3d btn-3d-rose" onclick="purgeCacheAction('currency')">
                        Valyuta Kursi Keshini Tozalash
                    </button>
                    <button class="btn-3d btn-3d-rose" onclick="purgeCacheAction('rate_limits')">
                        DoS Rate Limit IP larini Tozalash
                    </button>
                    <button class="btn-3d btn-3d-rose" onclick="purgeCacheAction('all')">
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
        const ADMIN_KEY = "{safe_admin_key}" || (function() {{
            try {{
                return localStorage.getItem('creatorflow_auth_token') || '6735799833';
            }} catch(e) {{
                return '6735799833';
            }}
        }})();
        let isPolling = true;
        let pollTimer = null;
        let curTab = 'flow';

        function showToast(msg) {{
            const t = document.getElementById('toast');
            t.textContent = msg;
            t.style.display = 'block';
            setTimeout(() => {{ t.style.display = 'none'; }}, 2200);
        }}

        function switchTab(tabId) {{
            curTab = tabId;
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('[id^="tabContent_"]').forEach(c => c.style.display = 'none');
            
            const target = document.getElementById('tabContent_' + tabId);
            if (target) target.style.display = 'block';
            event.currentTarget.classList.add('active');
        }}

        function togglePolling() {{
            isPolling = !isPolling;
            const btn = document.getElementById('pollBtnTxt');
            if (isPolling) {{
                btn.textContent = "Avto-Yangilanish: Faol (2.5s)";
                fetchTelemetry();
            }} else {{
                btn.textContent = "To'xtatilgan (Pauza)";
                if (pollTimer) clearTimeout(pollTimer);
            }}
        }}

        async function fetchTelemetry() {{
            if (!isPolling) return;
            try {{
                const headers = {{}};
                if (ADMIN_KEY) {{
                    headers['Authorization'] = 'Bearer ' + ADMIN_KEY;
                    headers['X-Admin-Secret'] = ADMIN_KEY;
                }}
                const res = await fetch('/api/admin/telemetry/stream', {{ headers: headers }});
                if (res.status === 403) {{
                    window.location.reload();
                    return;
                }}
                const data = await res.json();
                if (data.ok) {{
                    updateDashboard(data);
                }}
            }} catch(err) {{
                console.error("Telemetry fetch error:", err);
            }} finally {{
                if (isPolling) {{
                    pollTimer = setTimeout(fetchTelemetry, 2500);
                }}
            }}
        }}

        function updateDashboard(data) {{
            // Top metrics
            document.getElementById('metricDbQueries').textContent = (data.metrics.total_db_queries || 0).toLocaleString();
            document.getElementById('metricDbLatency').textContent = (data.metrics.avg_db_latency_ms || 0) + ' ms';
            document.getElementById('metricApiRequests').textContent = (data.metrics.total_api_requests || 0).toLocaleString();
            document.getElementById('metricApiLatency').textContent = (data.metrics.avg_api_latency_ms || 0) + ' ms';
            document.getElementById('metricBlockedDos').textContent = (data.metrics.total_blocked_dos || 0).toLocaleString();
            document.getElementById('metricTrackedIps').textContent = data.cache.tracked_ips_count || 0;
            document.getElementById('metricPoolStatus').textContent = data.pool.status || 'Active';
            document.getElementById('metricPoolConns').textContent = `${{data.pool.used}} / ${{data.pool.max}}`;
            document.getElementById('metricRoutesCount').textContent = data.discovered_routes_count || 0;
            document.getElementById('metricUptime').textContent = data.uptime_str || '-';

            // n8n Nodes
            document.getElementById('nodeSecurityMetric').textContent = (data.metrics.total_blocked_dos || 0) + ' Blk';
            document.getElementById('nodeRouterMetric').textContent = (data.discovered_routes_count || 0) + ' Routes';
            document.getElementById('nodeCacheMetric').textContent = 'TTL: ' + (data.config.product_cache_ttl || 60) + 's';
            document.getElementById('nodeDbMetric').textContent = (data.metrics.avg_db_latency_ms || 0) + ' ms';

            // Inputs (only if not focused)
            if (document.activeElement !== document.getElementById('inputProductTtl')) {{
                document.getElementById('inputProductTtl').value = data.config.product_cache_ttl;
            }}
            if (document.activeElement !== document.getElementById('inputUsdTtl')) {{
                document.getElementById('inputUsdTtl').value = data.config.usd_cache_ttl;
            }}
            if (document.activeElement !== document.getElementById('inputDosBurst')) {{
                document.getElementById('inputDosBurst').value = data.config.dos_burst_max;
            }}
            if (document.activeElement !== document.getElementById('inputSlowDb')) {{
                document.getElementById('inputSlowDb').value = data.config.db_slow_query_threshold_ms;
            }}

            // DB Table
            const dbTbody = document.getElementById('dbQueriesTableBody');
            if (data.recent_db_queries && data.recent_db_queries.length > 0) {{
                dbTbody.innerHTML = data.recent_db_queries.map(q => {{
                    const durColor = q.duration_ms > 20 ? 'var(--rose)' : (q.duration_ms > 8 ? 'var(--amber)' : 'var(--emerald)');
                    const badge = q.status === 'ok' ? '<span class="badge-status badge-200">OK</span>' : '<span class="badge-status badge-500">ERR</span>';
                    return `<tr>
                        <td style="color: var(--text-muted); font-family: var(--font-mono);">${{q.id}}</td>
                        <td style="font-family: var(--font-mono); color: var(--text-muted);">${{q.timestamp}}</td>
                        <td style="font-family: var(--font-mono); font-weight:700; color:${{durColor}};">${{q.duration_ms}} ms</td>
                        <td>${{badge}}</td>
                        <td><span class="code-pill">${{q.query}}</span></td>
                    </tr>`;
                }}).join('');
            }}

            // API Table
            const apiTbody = document.getElementById('apiTableBody');
            if (data.recent_api_requests && data.recent_api_requests.length > 0) {{
                apiTbody.innerHTML = data.recent_api_requests.map(a => {{
                    const stBadge = `<span class="badge-status badge-${{a.status}}">${{a.status}}</span>`;
                    return `<tr>
                        <td style="color: var(--text-muted); font-family: var(--font-mono);">${{a.id}}</td>
                        <td style="font-family: var(--font-mono); color: var(--text-muted);">${{a.timestamp}}</td>
                        <td><span class="code-pill" style="font-weight:700;">${{a.method}}</span></td>
                        <td>${{stBadge}}</td>
                        <td style="font-family: var(--font-mono);">${{a.latency_ms}} ms</td>
                        <td style="font-family: var(--font-mono); color: var(--cyan);">${{a.path}}</td>
                        <td style="font-family: var(--font-mono); color: var(--text-muted);">${{a.client_ip}}</td>
                    </tr>`;
                }}).join('');
            }}

            // Routes Table
            const routesTbody = document.getElementById('routesTableBody');
            document.getElementById('routesCountSpan').textContent = `${{data.discovered_routes_count || 0}} ta faol marshrut`;
            if (data.discovered_routes && data.discovered_routes.length > 0) {{
                routesTbody.innerHTML = data.discovered_routes.map(r => {{
                    const mColor = r.method === 'POST' ? 'var(--emerald)' : (r.method === 'GET' ? 'var(--cyan)' : 'var(--amber)');
                    return `<tr>
                        <td><span class="code-pill" style="color: ${{mColor}}; font-weight:700;">${{r.method}}</span></td>
                        <td><span style="font-size: 11px; background: rgba(255,255,255,0.06); padding: 3px 8px; border-radius: 999px;">${{r.category}}</span></td>
                        <td style="font-family: var(--font-mono); font-weight:600; color: #fff;">${{r.path}}</td>
                        <td style="font-family: var(--font-mono); color: var(--text-muted);">${{r.handler}}</td>
                    </tr>`;
                }}).join('');
            }}
        }}

        async function saveConfig(key, inputId) {{
            const val = document.getElementById(inputId).value;
            try {{
                const headers = {{ 'Content-Type': 'application/json' }};
                if (ADMIN_KEY) {{
                    headers['Authorization'] = 'Bearer ' + ADMIN_KEY;
                    headers['X-Admin-Secret'] = ADMIN_KEY;
                }}
                const res = await fetch('/api/admin/telemetry/config', {{
                    method: 'POST',
                    headers: headers,
                    body: JSON.stringify({{ [key]: Number(val) }})
                }});
                const d = await res.json();
                if (d.ok) {{
                    showToast(`Sozlama saqlandi: ${{key}} = ${{val}}`);
                    fetchTelemetry();
                }}
            }} catch(e) {{
                alert("Xatolik: " + e);
            }}
        }}

        async function purgeCacheAction(cat) {{
            if (!confirm(`Haqiqatan ham "${{cat}}" keshini tozalamoqchimisiz?`)) return;
            try {{
                const headers = {{ 'Content-Type': 'application/json' }};
                if (ADMIN_KEY) {{
                    headers['Authorization'] = 'Bearer ' + ADMIN_KEY;
                    headers['X-Admin-Secret'] = ADMIN_KEY;
                }}
                const res = await fetch('/api/admin/telemetry/purge', {{
                    method: 'POST',
                    headers: headers,
                    body: JSON.stringify({{ category: cat }})
                }});
                const d = await res.json();
                if (d.ok) {{
                    showToast(`Kesh tozalandi: ${{d.purged.join(', ')}}`);
                    fetchTelemetry();
                }}
            }} catch(e) {{
                alert("Xatolik: " + e);
            }}
        }}

        // Initial trigger
        fetchTelemetry();
    </script>
</body>
</html>"""


def render_admin_login_portal(error_msg: str = "") -> str:
    """Admin Observability uchun xavfsiz va chiroyli Figma-grade Kirish Portali"""
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
            overflow: hidden;
        }}
        .bg-grid {{
            position: absolute;
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
        <p class="subtitle">CreatorFlow Studio • n8n-style jonli tizim oqimi va telemetriya tekshiruvi (@aiko_64)</p>

        <form id="authForm" onsubmit="event.preventDefault(); verifyAdminKey();">
            <div class="input-group">
                <label for="adminKeyInput">Admin Kaliti yoki Telegram ID</label>
                <input id="adminKeyInput" class="text-input" type="password" placeholder="6735799833 yoki maxfiy kalit" autocomplete="current-password" autofocus />
            </div>

            <button type="submit" id="verifyBtn" class="btn-3d">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#090A0F" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                    <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
                </svg>
                <span>Kirish va Oqimni ochish</span>
            </button>
        </form>

        <div id="statusMsg" class="status-msg">Tizim holati tekshirilmoqda...</div>

        <div class="footer-link">
            <a href="/">← CreatorFlow Bosh sahifasiga qaytish</a>
        </div>
    </div>

    <script>
        async function checkAutoAuth() {{
            const statusEl = document.getElementById('statusMsg');
            try {{
                const token = localStorage.getItem('creatorflow_auth_token');
                const uid = localStorage.getItem('creatorflow_tg_user_id');
                const candidate = token || (uid === '6735799833' ? uid : '');
                if (candidate) {{
                    statusEl.className = 'status-msg';
                    statusEl.innerHTML = '<span style="display:inline-flex;align-items:center;gap:6px;"><svg class="spin" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#00F0FF" stroke-width="2"><circle cx="12" cy="12" r="10" stroke-opacity="0.25"/><path d="M12 2a10 10 0 0 1 10 10"/></svg> Saqlangan sessiya tekshirilmoqda (@aiko_64)...</span>';
                    const ok = await verifyAdminKey(candidate, true);
                    if (ok) return;
                }}
            }} catch(e) {{
                console.warn('Auto auth check error:', e);
            }}
            statusEl.textContent = 'Kirish uchun admin kaliti yoki Telegram ID (6735799833) kiriting.';
        }}

        async function verifyAdminKey(explicitKey, isAuto = false) {{
            const input = document.getElementById('adminKeyInput');
            const statusEl = document.getElementById('statusMsg');
            const btn = document.getElementById('verifyBtn');
            const key = (explicitKey || (input ? input.value : '')).trim();

            if (!key) {{
                statusEl.className = 'status-msg error';
                statusEl.textContent = "Iltimos, kalitni yoki Telegram ID ni kiriting!";
                return false;
            }}

            if (btn) btn.disabled = true;
            statusEl.className = 'status-msg';
            statusEl.innerHTML = '<span style="display:inline-flex;align-items:center;gap:6px;"><svg class="spin" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#00F0FF" stroke-width="2"><circle cx="12" cy="12" r="10" stroke-opacity="0.25"/><path d="M12 2a10 10 0 0 1 10 10"/></svg> Tasdiqlanmoqda...</span>';

            try {{
                const res = await fetch('/api/admin/verify', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ key: key }})
                }});
                const d = await res.json();
                if (d.ok) {{
                    statusEl.className = 'status-msg success';
                    statusEl.textContent = 'Ruxsat berildi! Telemetriya yuklanmoqda...';
                    document.cookie = "admin_key=" + encodeURIComponent(key) + "; path=/; max-age=2592000; SameSite=Lax";
                    document.cookie = "cf_auth_token=" + encodeURIComponent(key) + "; path=/; max-age=2592000; SameSite=Lax";
                    setTimeout(() => {{
                        window.location.reload();
                    }}, 400);
                    return true;
                }} else {{
                    if (!isAuto) {{
                        statusEl.className = 'status-msg error';
                        statusEl.textContent = d.error || "Ruxsat berilmadi! Noto'g'ri kalit.";
                    }}
                    if (btn) btn.disabled = false;
                    return false;
                }}
            }} catch(err) {{
                if (!isAuto) {{
                    statusEl.className = 'status-msg error';
                    statusEl.textContent = "Tarmoq xatosi: " + err.message;
                }}
                if (btn) btn.disabled = false;
                return false;
            }}
        }}

        window.addEventListener('DOMContentLoaded', checkAutoAuth);
    </script>
</body>
</html>"""

