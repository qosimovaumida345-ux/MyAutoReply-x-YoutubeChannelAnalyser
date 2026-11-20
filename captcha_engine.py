"""
BotShield Captcha Engine - Next-Gen Anti-Bot Verification System
Standalone, Zero-External-API Captcha as a Service.
Supports 4 Human-Only Interactive Challenges (100% O'zbek tili & Visual SVG Icons):
1. Slider Puzzle: Procedural textured canvas with cut-out jigsaw notch & piece. (Tolerance: ±12px)
2. 9-Grid Semantic Selector: Dynamic 3x3 tiles with target shape preview icon.
3. Dial Angle Alignment: Rotated vector subject restored to 0° upright orientation. (Tolerance: ±20°)
4. Click-in-Sequence: 4 procedural glyphs clicked in visual 1-2-3 icon sequence. (Hit radius: 48px)

Includes human drag trajectory jitter, velocity curve, and timing telemetry verification.
Tokens are HMAC-SHA256 signed with replay protection.
"""

import os
import io
import time
import math
import hmac
import random
import base64
import secrets
import hashlib
from typing import Dict, Any, List, Tuple, Optional
from PIL import Image, ImageDraw, ImageFilter, ImageOps

# Secret key for signing verification tokens (process-ephemeral CSPRNG fallback if env unset)
_EPHEMERAL_CAPTCHA_SECRET = secrets.token_hex(32)
_CAPTCHA_SIGNING_SECRET = os.getenv("CAPTCHA_SIGNING_SECRET", "").strip() or _EPHEMERAL_CAPTCHA_SECRET

# Cryptographically secure RNG for challenge solutions
_SECURE_RNG = secrets.SystemRandom()

# High-speed in-memory challenge and token cache with TTL & bounded memory caps
_ACTIVE_CHALLENGES: Dict[str, Dict[str, Any]] = {}
_VERIFIED_TOKENS: Dict[str, Dict[str, Any]] = {}
_EPHEMERAL_SESSIONS: Dict[str, Dict[str, Any]] = {}
_MAX_CACHE_ENTRIES = 5000


def _get_captcha_signing_key() -> bytes:
    """Return signing secret dynamically from env or process-local CSPRNG fallback."""
    env_sec = os.getenv("CAPTCHA_SIGNING_SECRET", "").strip()
    sec = env_sec if env_sec else _CAPTCHA_SIGNING_SECRET
    return sec.encode("utf-8")


def _enforce_cache_cap(store: Dict[str, Dict[str, Any]], max_size: int = _MAX_CACHE_ENTRIES):
    """Evict oldest records if cache grows beyond max_size (memory exhaustion protection)."""
    if len(store) <= max_size:
        return
    overflow = len(store) - max_size
    for k in list(store.keys())[:overflow]:
        store.pop(k, None)

# Clean up interval tracker
_LAST_CLEANUP_TS = time.time()


def _cleanup_expired_records():
    """Muddati o'tgan challenge va tokenlarni xotiradan tozalash"""
    global _LAST_CLEANUP_TS
    now = time.time()
    if now - _LAST_CLEANUP_TS < 60:
        return
    _LAST_CLEANUP_TS = now
    
    # 5 daqiqadan oshgan challenge larni o'chirish
    expired_cids = [cid for cid, c in list(_ACTIVE_CHALLENGES.items()) if now > c.get("expires_at", 0)]
    for cid in expired_cids:
        _ACTIVE_CHALLENGES.pop(cid, None)
        
    # 10 daqiqadan oshgan tokenlarni o'chirish
    expired_tokens = [t for t, rec in list(_VERIFIED_TOKENS.items()) if now > rec.get("expires_at", 0)]
    for t in expired_tokens:
        _VERIFIED_TOKENS.pop(t, None)

    # 2 daqiqadan oshgan vaqtinchalik session kalitlarini tozalash
    expired_sessions = [s for s, rec in list(_EPHEMERAL_SESSIONS.items()) if now > rec.get("expires_at", 0)]
    for s in expired_sessions:
        _EPHEMERAL_SESSIONS.pop(s, None)


def create_session_nonce(sitekey: str, ttl: int = 90) -> str:
    """
    Enterprise Security: Bir martalik 90 soniyalik vaqtinchalik session kaliti.
    Sayt egasi frontend HTML da o'z statik site_key'ini ko'rsatishi shart emas.
    Backend orqali vaqtinchalik bsh_sess_... oladi va frontendga beradi.
    """
    _cleanup_expired_records()
    session_key = "bsh_sess_" + secrets.token_hex(16)
    _EPHEMERAL_SESSIONS[session_key] = {
        "sitekey": sitekey,
        "expires_at": time.time() + ttl,
        "is_used": False
    }
    _enforce_cache_cap(_EPHEMERAL_SESSIONS)
    return session_key


def resolve_session_nonce(session_key: str) -> Optional[str]:
    """Vaqtinchalik bsh_sess_ kalitini tekshirish va unga biriktirilgan sitekey ni qaytarish"""
    _cleanup_expired_records()
    rec = _EPHEMERAL_SESSIONS.get(session_key)
    if not rec:
        return None
    if time.time() > rec.get("expires_at", 0):
        _EPHEMERAL_SESSIONS.pop(session_key, None)
        return None
    if rec.get("is_used"):
        return None
    rec["is_used"] = True
    return rec["sitekey"]


def _image_to_base64_png(img: Image.Image) -> str:
    """Pillow Image obyektini data URI base64 formatiga o'tkazish"""
    buffered = io.BytesIO()
    img.save(buffered, format="PNG", optimize=True)
    b64_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{b64_str}"


# ==================== PROCEDURAL TEXTURES & GRAPHICS ====================

def _generate_procedural_background(width: int, height: int) -> Image.Image:
    """
    Renders sharp MonoDeck-styled procedural backgrounds (architectural slate, warm stone,
    obsidian & vermilion horizon, deep studio emerald) with anti-subtraction geometric noise.
    """
    img = Image.new("RGBA", (width, height), (15, 23, 42, 255))
    draw = ImageDraw.Draw(img, "RGBA")
    
    # MonoDeck editorial palettes (high contrast, zero generic neon purple/pink)
    palettes = [
        [(18, 18, 22), (39, 39, 46), (194, 65, 12)],      # Obsidian -> Graphite -> Vermilion Dusk
        [(15, 23, 42), (30, 41, 59), (3, 105, 161)],      # Blueprint Slate -> Deep Steel -> Cobalt
        [(28, 25, 23), (68, 64, 60), (217, 119, 6)],      # Warm Charcoal -> Umber -> Amber
        [(6, 78, 59), (15, 118, 110), (14, 116, 144)],    # Deep Emerald -> Studio Teal
        [(24, 24, 27), (51, 65, 85), (234, 88, 12)],      # Carbon -> Slate -> International Vermilion
    ]
    p = _SECURE_RNG.choice(palettes)
    c1, c2, c3 = p[0], p[1], p[2]
    
    # Smooth multi-stop gradient
    for y in range(height):
        factor = y / max(1, height - 1)
        if factor < 0.5:
            sub = factor * 2.0
            r = int(c1[0] * (1 - sub) + c2[0] * sub)
            g = int(c1[1] * (1 - sub) + c2[1] * sub)
            b = int(c1[2] * (1 - sub) + c2[2] * sub)
        else:
            sub = (factor - 0.5) * 2.0
            r = int(c2[0] * (1 - sub) + c3[0] * sub)
            g = int(c2[1] * (1 - sub) + c3[1] * sub)
            b = int(c2[2] * (1 - sub) + c3[2] * sub)
        draw.line([(0, y), (width, y)], fill=(r, g, b, 255))
        
    # Layer crisp architectural shapes
    for _ in range(_SECURE_RNG.randint(12, 20)):
        shape_type = _SECURE_RNG.choice(["circle", "poly", "band", "ring"])
        alpha = _SECURE_RNG.randint(36, 95)
        col = (
            _SECURE_RNG.randint(min(c1[0], c2[0]), max(c2[0], c3[0])),
            _SECURE_RNG.randint(min(c1[1], c2[1]), max(c2[1], c3[1])),
            _SECURE_RNG.randint(min(c1[2], c2[2]), max(c2[2], c3[2])),
            alpha
        )
        if shape_type == "circle":
            rx = _SECURE_RNG.randint(18, 64)
            cx = _SECURE_RNG.randint(0, width)
            cy = _SECURE_RNG.randint(0, height)
            draw.ellipse([cx - rx, cy - rx, cx + rx, cy + rx], fill=col)
        elif shape_type == "ring":
            rx = _SECURE_RNG.randint(16, 48)
            cx = _SECURE_RNG.randint(0, width)
            cy = _SECURE_RNG.randint(0, height)
            draw.ellipse([cx - rx, cy - rx, cx + rx, cy + rx], outline=(255, 255, 255, alpha // 2), width=2)
        elif shape_type == "poly":
            pts = [(_SECURE_RNG.randint(0, width), _SECURE_RNG.randint(0, height)) for _ in range(_SECURE_RNG.randint(3, 5))]
            draw.polygon(pts, fill=col)
        elif shape_type == "band":
            y1 = _SECURE_RNG.randint(0, height)
            y2 = _SECURE_RNG.randint(0, height)
            w = _SECURE_RNG.randint(2, 5)
            draw.line([(0, y1), (width, y2)], fill=col, width=w)

    # Subtle Swiss blueprint grid overlay (defeats pixel-diff bots cleanly)
    grid_step = _SECURE_RNG.choice([24, 28, 32])
    ox = _SECURE_RNG.randint(0, grid_step - 1)
    oy = _SECURE_RNG.randint(0, grid_step - 1)
    for gx in range(ox, width, grid_step):
        draw.line([(gx, 0), (gx, height)], fill=(255, 255, 255, 20), width=1)
    for gy in range(oy, height, grid_step):
        draw.line([(0, gy), (width, gy)], fill=(255, 255, 255, 20), width=1)
            
    # Fine textural micro-speckles
    for _ in range(_SECURE_RNG.randint(65, 110)):
        nx = _SECURE_RNG.randint(0, width - 1)
        ny = _SECURE_RNG.randint(0, height - 1)
        draw.point((nx, ny), fill=(255, 255, 255, _SECURE_RNG.randint(25, 85)))
        
    return img


# ==================== VARIETY 1: SLIDER PUZZLE ====================

def _create_jigsaw_mask(piece_w: int, piece_h: int) -> Image.Image:
    """Create a high-resolution, anti-aliased jigsaw tab puzzle piece alpha mask"""
    scale = 3  # Supersample for ultra-smooth edges
    sw = piece_w * scale
    sh = piece_h * scale
    
    mask = Image.new("L", (sw, sh), 0)
    draw = ImageDraw.Draw(mask)
    
    pad = int(8 * scale)
    body_x0, body_y0 = pad, pad
    body_x1, body_y1 = sw - pad, sh - pad
    
    # Main square body
    draw.rounded_rectangle([body_x0, body_y0, body_x1, body_y1], radius=int(5 * scale), fill=255)
    
    # Protruding top tab (circle)
    tab_r = int(5.5 * scale)
    cx = sw // 2
    cy = body_y0
    draw.ellipse([cx - tab_r, cy - tab_r, cx + tab_r, cy + tab_r], fill=255)
    
    # Protruding right tab (circle)
    rx = body_x1
    ry = sh // 2
    draw.ellipse([rx - tab_r, ry - tab_r, rx + tab_r, ry + tab_r], fill=255)
    
    # Indented bottom notch (cutout)
    bx = sw // 2
    by = body_y1
    draw.ellipse([bx - tab_r, by - tab_r, bx + tab_r, by + tab_r], fill=0)
    
    # Downscale with Lanczos for smooth subpixel anti-aliasing
    return mask.resize((piece_w, piece_h), Image.Resampling.LANCZOS)


def generate_slider_challenge() -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Variety 1: Precision Slider Puzzle with Anti-Edge-Solver Decoy Notch.
    Tolerance: ±9px (tighter vs automated scripts, smooth for real humans).
    """
    width, height = 320, 170
    piece_size = 46
    
    # 1. Procedural background
    bg = _generate_procedural_background(width, height)
    
    # 2. Cryptographically unpredictable target position
    target_x = _SECURE_RNG.randint(90, width - piece_size - 24)
    target_y = _SECURE_RNG.randint(22, height - piece_size - 22)
    
    # 3. Create anti-aliased jigsaw mask
    mask = _create_jigsaw_mask(piece_size, piece_size)
    border_mask = mask.filter(ImageFilter.FIND_EDGES)
    
    # 4. Extract puzzle piece with crisp double-bevel outline
    piece_box = (target_x, target_y, target_x + piece_size, target_y + piece_size)
    piece_crop = bg.crop(piece_box)
    
    piece_img = Image.new("RGBA", (piece_size, piece_size), (0, 0, 0, 0))
    piece_img.paste(piece_crop, (0, 0))
    piece_img.putalpha(mask)
    
    # Crisp MonoDeck highlight around draggable piece so humans spot alignment effortlessly
    accent_edge = Image.new("RGBA", (piece_size, piece_size), (255, 90, 31, 210))
    piece_img.paste(accent_edge, (0, 0), border_mask)
    white_edge = Image.new("RGBA", (piece_size, piece_size), (255, 255, 255, 220))
    inner_border = border_mask.filter(ImageFilter.MinFilter(3))
    piece_img.paste(white_edge, (0, 0), border_mask)
    
    # 5. Add a decoy ghost notch (offset horizontally & vertically to foil simple edge-detection bots)
    bg_with_notch = bg.copy()
    decoy_candidates_x = [x for x in range(60, width - piece_size - 20, 8) if abs(x - target_x) >= 68]
    decoy_x = _SECURE_RNG.choice(decoy_candidates_x) if decoy_candidates_x else max(55, width - target_x)
    decoy_y = target_y + 38 if target_y + 38 <= height - piece_size - 10 else max(10, target_y - 38)
    decoy_fill = Image.new("RGBA", (piece_size, piece_size), (10, 10, 14, 110))
    bg_with_notch.paste(decoy_fill, (decoy_x, decoy_y), mask)
    decoy_border = Image.new("RGBA", (piece_size, piece_size), (255, 255, 255, 70))
    bg_with_notch.paste(decoy_border, (decoy_x, decoy_y), border_mask)

    # 6. Draw genuine target cutout notch onto background (high-depth contrast + hairline guide)
    notch_dark = Image.new("RGBA", (piece_size, piece_size), (10, 10, 12, 230))
    bg_with_notch.paste(notch_dark, (target_x, target_y), mask)
    
    notch_border = Image.new("RGBA", (piece_size, piece_size), (255, 255, 255, 190))
    bg_with_notch.paste(notch_border, (target_x, target_y), border_mask)
    
    client_payload = {
        "instruction": "Pazlni bo'sh chuqurchaga aniq moslab suring",
        "prompt": "Pazlni bo'sh chuqurchaga aniq moslab suring",
        "bg_image": _image_to_base64_png(bg_with_notch),
        "piece_image": _image_to_base64_png(piece_img),
        "y": target_y,
        "width": width,
        "height": height,
        "piece_width": piece_size,
        "piece_height": piece_size
    }
    
    solution_data = {
        "target_x": target_x,
        "target_y": target_y,
        "tolerance": 9
    }
    
    return client_payload, solution_data


# ==================== VARIETY 2: 9-GRID SEMANTIC SELECTOR ====================

SEMANTIC_SHAPES = {
    "star": {
        "uz": "Yulduz",
        "desc": "Barcha yulduzli kataklarni tanlang",
        "svg": '<svg viewBox="0 0 24 24" width="22" height="22" fill="#F59E0B" stroke="#D97706" stroke-width="1.5"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>'
    },
    "triangle": {
        "uz": "Uchburchak",
        "desc": "Barcha uchburchakli kataklarni tanlang",
        "svg": '<svg viewBox="0 0 24 24" width="22" height="22" fill="#0284C7" stroke="#0369A1" stroke-width="1.5"><polygon points="12 3 22 21 2 21 12 3"/></svg>'
    },
    "circle": {
        "uz": "Aylana",
        "desc": "Barcha aylanali kataklarni tanlang",
        "svg": '<svg viewBox="0 0 24 24" width="22" height="22" fill="#10B981" stroke="#059669" stroke-width="1.5"><circle cx="12" cy="12" r="9"/></svg>'
    },
    "diamond": {
        "uz": "Olmos",
        "desc": "Barcha olmos shaklli kataklarni tanlang",
        "svg": '<svg viewBox="0 0 24 24" width="22" height="22" fill="#FF5A1F" stroke="#C2410C" stroke-width="1.5"><polygon points="12 2 22 12 12 22 2 12 12 2"/></svg>'
    },
    "heart": {
        "uz": "Yurak",
        "desc": "Barcha yurak shaklli kataklarni tanlang",
        "svg": '<svg viewBox="0 0 24 24" width="22" height="22" fill="#F43F5E" stroke="#E11D48" stroke-width="1.5"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/></svg>'
    },
    "crescent": {
        "uz": "Oyparcha",
        "desc": "Barcha oyparcha shaklli kataklarni tanlang",
        "svg": '<svg viewBox="0 0 24 24" width="22" height="22" fill="#F59E0B" stroke="#D97706" stroke-width="1.5"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>'
    },
    "hexagon": {
        "uz": "Oltiburchak",
        "desc": "Barcha oltiburchak shaklli kataklarni tanlang",
        "svg": '<svg viewBox="0 0 24 24" width="22" height="22" fill="#38BDF8" stroke="#0284C7" stroke-width="1.5"><polygon points="12 2 21 7 21 17 12 22 3 17 3 7 12 2"/></svg>'
    },
    "cross": {
        "uz": "Krest",
        "desc": "Barcha krest shaklli kataklarni tanlang",
        "svg": '<svg viewBox="0 0 24 24" width="22" height="22" fill="#0F172A" stroke="#334155" stroke-width="1.5"><polygon points="9 3 15 3 15 9 21 9 21 15 15 15 15 21 9 21 9 15 3 15 3 9 9 9 9 3"/></svg>'
    }
}


def _draw_procedural_tile(shape_name: str, size: int = 92) -> Image.Image:
    """Procedurally render a single tile with anti-hash geometric perturbations and crisp vector contrast"""
    tile = Image.new("RGBA", (size, size), (248, 250, 252, 255))
    draw = ImageDraw.Draw(tile, "RGBA")
    
    base_col = _SECURE_RNG.choice([(245, 245, 244), (241, 245, 249), (244, 244, 245), (250, 250, 249)])
    draw.rectangle([0, 0, size, size], fill=base_col)
    
    # Anti-hash architectural backdrop lines & subtle reticles
    for _ in range(3):
        lx0, ly0 = _SECURE_RNG.randint(0, size), _SECURE_RNG.randint(0, size)
        lx1, ly1 = _SECURE_RNG.randint(0, size), _SECURE_RNG.randint(0, size)
        draw.line([(lx0, ly0), (lx1, ly1)], fill=(148, 163, 184, 55), width=1)
    bg_rx = _SECURE_RNG.randint(14, 28)
    bg_cx = _SECURE_RNG.randint(20, size - 20)
    bg_cy = _SECURE_RNG.randint(20, size - 20)
    draw.ellipse([bg_cx - bg_rx, bg_cy - bg_rx, bg_cx + bg_rx, bg_cy + bg_rx], outline=(100, 116, 139, 40), width=1)

    for gx in range(_SECURE_RNG.randint(8, 14), size, 20):
        for gy in range(_SECURE_RNG.randint(8, 14), size, 20):
            draw.point((gx, gy), fill=(100, 116, 139, 90))
            
    # MonoDeck high-contrast ink & accent colors
    palette = _SECURE_RNG.choice([
        (255, 90, 31),   # International Vermilion
        (15, 23, 42),    # Editorial Obsidian
        (225, 29, 72),   # Crimson Rose
        (5, 150, 105),   # Studio Emerald
        (217, 119, 6),   # Rich Amber
        (2, 132, 199),   # Blueprint Blue
    ])
    
    scale = 3
    ss = size * scale
    canvas = Image.new("RGBA", (ss, ss), (0, 0, 0, 0))
    sdraw = ImageDraw.Draw(canvas, "RGBA")
    
    cx = ss // 2 + _SECURE_RNG.randint(-5 * scale, 5 * scale)
    cy = ss // 2 + _SECURE_RNG.randint(-5 * scale, 5 * scale)
    r = _SECURE_RNG.randint(21, 25) * scale
    rot_angle = _SECURE_RNG.randint(-26, 26)
    
    if shape_name == "star":
        pts = []
        for i in range(10):
            a = math.radians(i * 36 - 90 + rot_angle)
            cr = r if i % 2 == 0 else int(r * 0.45)
            pts.append((cx + cr * math.cos(a), cy + cr * math.sin(a)))
        sdraw.polygon(pts, fill=(*palette, 245), outline=(255, 255, 255, 255), width=int(1.8 * scale))
        
    elif shape_name == "triangle":
        pts = []
        for i in range(3):
            a = math.radians(i * 120 - 90 + rot_angle)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
        sdraw.polygon(pts, fill=(*palette, 245), outline=(255, 255, 255, 255), width=int(1.8 * scale))
        
    elif shape_name == "circle":
        sdraw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(*palette, 240), outline=(255, 255, 255, 255), width=int(2 * scale))
        inner_r = int(r * 0.48)
        sdraw.ellipse([cx - inner_r, cy - inner_r, cx + inner_r, cy + inner_r], fill=(*base_col, 255), outline=(255, 255, 255, 200), width=int(1.5 * scale))
        
    elif shape_name == "diamond":
        w = int(r * 0.78)
        tilt = math.radians(rot_angle * 0.5)
        raw_pts = [(0, -r), (w, 0), (0, r), (-w, 0)]
        pts = [(cx + px * math.cos(tilt) - py * math.sin(tilt), cy + px * math.sin(tilt) + py * math.cos(tilt)) for px, py in raw_pts]
        sdraw.polygon(pts, fill=(*palette, 245), outline=(255, 255, 255, 255), width=int(1.8 * scale))
        sdraw.line([pts[3], pts[1]], fill=(255, 255, 255, 190), width=scale)
        sdraw.line([pts[0], pts[2]], fill=(255, 255, 255, 190), width=scale)
        
    elif shape_name == "heart":
        pts = []
        for t in [x * 0.05 for x in range(126)]:
            hx = 16 * (math.sin(t) ** 3)
            hy = -(13 * math.cos(t) - 5 * math.cos(2*t) - 2 * math.cos(3*t) - math.cos(4*t))
            pts.append((cx + int(hx * scale * 1.25), cy + int(hy * scale * 1.25) + int(3 * scale)))
        if len(pts) > 2:
            sdraw.polygon(pts, fill=(*palette, 245), outline=(255, 255, 255, 255), width=int(1.8 * scale))
            
    elif shape_name == "crescent":
        sdraw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(*palette, 245))
        offset = int(r * 0.45)
        sdraw.ellipse([cx - r + offset, cy - r - offset, cx + r + offset, cy + r - offset], fill=(*base_col, 255))
        
    elif shape_name == "hexagon":
        pts = []
        for i in range(6):
            a = math.radians(i * 60 + rot_angle)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
        sdraw.polygon(pts, fill=(*palette, 245), outline=(255, 255, 255, 255), width=int(1.8 * scale))
        
    elif shape_name == "cross":
        arm = int(r * 0.34)
        tilt = math.radians(_SECURE_RNG.randint(-15, 15))
        cross_raw = [
            (-arm, -r), (arm, -r), (arm, -arm), (r, -arm),
            (r, arm), (arm, arm), (arm, r), (-arm, r),
            (-arm, arm), (-r, arm), (-r, -arm), (-arm, -arm),
        ]
        pts = [(cx + px * math.cos(tilt) - py * math.sin(tilt), cy + px * math.sin(tilt) + py * math.cos(tilt)) for px, py in cross_raw]
        sdraw.polygon(pts, fill=(*palette, 245), outline=(255, 255, 255, 255), width=int(1.6 * scale))
        
    scaled_shape = canvas.resize((size, size), Image.Resampling.LANCZOS)
    tile.paste(scaled_shape, (0, 0), scaled_shape)
    draw.rectangle([0, 0, size - 1, size - 1], outline=(212, 212, 216, 255), width=1)
    return tile


def generate_grid_challenge() -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Variety 2: 9-Grid Semantic Selector (Pure Uzbek + Target Icon)
    """
    categories = list(SEMANTIC_SHAPES.keys())
    target_category = _SECURE_RNG.choice(categories)
    other_categories = [c for c in categories if c != target_category]
    
    num_targets = _SECURE_RNG.choice([3, 4])
    all_indices = list(range(9))
    target_indices = sorted(_SECURE_RNG.sample(all_indices, num_targets))
    
    tiles_base64 = []
    for idx in range(9):
        if idx in target_indices:
            shape = target_category
        else:
            shape = random.choice(other_categories)
        t_img = _draw_procedural_tile(shape, size=92)
        tiles_base64.append(_image_to_base64_png(t_img))
        
    target_meta = SEMANTIC_SHAPES[target_category]
    client_payload = {
        "instruction": target_meta["desc"],
        "prompt": target_meta["desc"],
        "target_name": target_meta["uz"],
        "target_icon": target_meta["svg"],
        "target_key": target_category,
        "tiles": tiles_base64,
        "grid_size": 3,
        "total_targets": num_targets
    }
    
    solution_data = {
        "target_indices": target_indices,
        "target_category": target_category
    }
    
    return client_payload, solution_data


# ==================== VARIETY 3: DIAL ANGLE ALIGNMENT ====================

ROTATE_SUBJECTS = {
    "arrow": {"uz": "Strelka", "hint": "Strelkani to'g'ri (tik tepaga) qaratib buring"},
    "rocket": {"uz": "Raketa", "hint": "Raketani uchish yo'nalishiga (tik tepaga) buring"},
    "key": {"uz": "Kalit", "hint": "Kalitni bosh qismini tepaga qaratib to'g'rilang"},
    "tree": {"uz": "Daraxt", "hint": "Daraxtni to'g'ri (ildizi pastda) qilib buring"},
    "umbrella": {"uz": "Soyabon", "hint": "Soyabonni gumbazini tepaga qilib to'g'rilang"},
    "compass": {"uz": "Kompas", "hint": "Kompas milini to'g'ri (tik tepaga) qaratib buring"}
}


def _draw_upright_subject(subject_type: str = "arrow", size: int = 170) -> Image.Image:
    """
    Render a crisp vector subject on a MonoDeck circular dial face with a Vermilion top alignment beacon.
    Transparent outside radius r so rotating produces zero corner clipping artifacts.
    """
    scale = 3
    ss = size * scale
    canvas = Image.new("RGBA", (ss, ss), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas, "RGBA")
    
    cx, cy = ss // 2, ss // 2
    r = int(58 * scale)
    
    # 1. Circular dial backing (clean editorial white dial face with Obsidian rim)
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(250, 250, 249, 255), outline=(15, 23, 42, 230), width=int(2.5 * scale))
    inner_ring_r = r - int(5 * scale)
    draw.ellipse([cx - inner_ring_r, cy - inner_ring_r, cx + inner_ring_r, cy + inner_ring_r], outline=(212, 212, 216, 170), width=scale)
    
    # 2. Calibration tick marks around perimeter (270 deg = upright top has Vermilion #FF5A1F beacon)
    for deg in range(0, 360, 15):
        rad = math.radians(deg)
        t_len = int(7 * scale) if deg % 90 == 0 else (int(5 * scale) if deg % 30 == 0 else int(2.5 * scale))
        x_outer = cx + int((r - 2) * math.cos(rad))
        y_outer = cy + int((r - 2) * math.sin(rad))
        x_inner = cx + int((r - 2 - t_len) * math.cos(rad))
        y_inner = cy + int((r - 2 - t_len) * math.sin(rad))
        col = (255, 90, 31, 255) if deg == 270 else ((15, 23, 42, 180) if deg % 90 == 0 else (148, 163, 184, 160))
        w = int(2.2 * scale) if deg == 270 else (int(1.5 * scale) if deg % 30 == 0 else scale)
        draw.line([(x_inner, y_inner), (x_outer, y_outer)], fill=col, width=w)
        
    # Top 12-o'clock orientation triangle inside the rotating rim
    beacon_y = cy - r + int(10 * scale)
    draw.polygon(
        [(cx, cy - r + int(2 * scale)), (cx - int(5 * scale), beacon_y), (cx + int(5 * scale), beacon_y)],
        fill=(255, 90, 31, 255)
    )
        
    # 3. Render the specific vector subject pointing strictly upright
    if subject_type == "rocket":
        rh = int(42 * scale)
        rw = int(14 * scale)
        body = [(cx, cy - rh), (cx + rw, cy - rh + int(28 * scale)), (cx + rw, cy + int(12 * scale)), (cx - rw, cy + int(12 * scale)), (cx - rw, cy - rh + int(28 * scale))]
        draw.polygon(body, fill=(15, 23, 42, 255), outline=(10, 10, 12, 255), width=scale)
        fin_l = [(cx - rw, cy), (cx - rw - int(12 * scale), cy + int(18 * scale)), (cx - rw, cy + int(14 * scale))]
        fin_r = [(cx + rw, cy), (cx + rw + int(12 * scale), cy + int(18 * scale)), (cx + rw, cy + int(14 * scale))]
        draw.polygon(fin_l, fill=(255, 90, 31, 255))
        draw.polygon(fin_r, fill=(255, 90, 31, 255))
        draw.ellipse([cx - int(6 * scale), cy - int(12 * scale), cx + int(6 * scale), cy], fill=(248, 250, 252, 255), outline=(255, 90, 31, 255), width=scale)
        draw.polygon([(cx - int(7 * scale), cy + int(13 * scale)), (cx, cy + int(30 * scale)), (cx + int(7 * scale), cy + int(13 * scale))], fill=(245, 158, 11, 255))
    elif subject_type == "key":
        kh = int(40 * scale)
        kr = int(13 * scale)
        draw.ellipse([cx - kr, cy - kh, cx + kr, cy - kh + kr * 2], fill=(245, 158, 11, 255), outline=(180, 83, 9, 255), width=scale)
        draw.ellipse([cx - int(5 * scale), cy - kh + int(5 * scale), cx + int(5 * scale), cy - kh + int(16 * scale)], fill=(250, 250, 249, 255))
        draw.rectangle([cx - int(3.5 * scale), cy - kh + kr * 2, cx + int(3.5 * scale), cy + int(24 * scale)], fill=(245, 158, 11, 255), outline=(180, 83, 9, 255), width=scale)
        draw.rectangle([cx + int(3 * scale), cy + int(6 * scale), cx + int(14 * scale), cy + int(12 * scale)], fill=(245, 158, 11, 255))
        draw.rectangle([cx + int(3 * scale), cy + int(16 * scale), cx + int(12 * scale), cy + int(22 * scale)], fill=(245, 158, 11, 255))
    elif subject_type == "tree":
        for top_y, bot_y, hw in [(cy - int(40 * scale), cy - int(18 * scale), int(15 * scale)),
                                 (cy - int(22 * scale), cy + int(4 * scale), int(21 * scale)),
                                 (cy, cy + int(24 * scale), int(27 * scale))]:
            pts = [(cx, top_y), (cx + hw, bot_y), (cx - hw, bot_y)]
            draw.polygon(pts, fill=(16, 185, 129, 255), outline=(5, 150, 105, 220), width=scale)
        draw.rectangle([cx - int(4 * scale), cy + int(24 * scale), cx + int(4 * scale), cy + int(36 * scale)], fill=(120, 53, 15, 255))
    elif subject_type == "umbrella":
        draw.pieslice([cx - int(28 * scale), cy - int(36 * scale), cx + int(28 * scale), cy + int(16 * scale)], 180, 360, fill=(255, 90, 31, 255), outline=(194, 65, 12, 255), width=scale)
        draw.line([(cx, cy - int(36 * scale)), (cx, cy - int(42 * scale))], fill=(15, 23, 42, 255), width=int(2 * scale))
        draw.line([(cx, cy - int(10 * scale)), (cx, cy + int(28 * scale))], fill=(15, 23, 42, 255), width=int(2 * scale))
        draw.arc([cx - int(10 * scale), cy + int(20 * scale), cx, cy + int(34 * scale)], 0, 180, fill=(15, 23, 42, 255), width=int(2 * scale))
    elif subject_type == "compass":
        draw.polygon([(cx, cy - int(41 * scale)), (cx + int(8 * scale), cy), (cx - int(8 * scale), cy)], fill=(255, 90, 31, 255), outline=(194, 65, 12, 255), width=scale)
        draw.polygon([(cx, cy + int(41 * scale)), (cx + int(8 * scale), cy), (cx - int(8 * scale), cy)], fill=(15, 23, 42, 255), outline=(30, 41, 59, 255), width=scale)
    else:  # "arrow" default (Obsidian shaft + International Vermilion head)
        arrow_h = int(42 * scale)
        arrow_w = int(20 * scale)
        shaft_w = int(8 * scale)
        shaft_h = int(22 * scale)
        head_pts = [(cx, cy - arrow_h), (cx + arrow_w, cy - arrow_h + int(22 * scale)), (cx - arrow_w, cy - arrow_h + int(22 * scale))]
        draw.polygon(head_pts, fill=(255, 90, 31, 255), outline=(194, 65, 12, 255), width=int(1.8 * scale))
        draw.rectangle([cx - shaft_w // 2, cy - arrow_h + int(21 * scale), cx + shaft_w // 2, cy + shaft_h], fill=(15, 23, 42, 255), outline=(10, 10, 12, 220), width=scale)
        draw.ellipse([cx - int(6 * scale), cy + shaft_h - int(4 * scale), cx + int(6 * scale), cy + shaft_h + int(8 * scale)], fill=(255, 90, 31, 255))
        
    draw.ellipse([cx - int(4.5 * scale), cy - int(4.5 * scale), cx + int(4.5 * scale), cy + int(4.5 * scale)], fill=(255, 255, 255, 255), outline=(15, 23, 42, 200), width=scale)
    return canvas.resize((size, size), Image.Resampling.LANCZOS)


def generate_rotate_challenge() -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Variety 3: Dial Angle Alignment (MonoDeck Bezel + Tolerance ±15°)
    """
    size = 170
    subject_key = _SECURE_RNG.choice(list(ROTATE_SUBJECTS.keys()))
    subject_meta = ROTATE_SUBJECTS[subject_key]
    subject = _draw_upright_subject(subject_key, size)
    
    angle = _SECURE_RNG.choice([
        _SECURE_RNG.randint(35, 155),
        _SECURE_RNG.randint(205, 325)
    ])
    
    tilted_img = subject.rotate(-angle, resample=Image.Resampling.BICUBIC)
    
    client_payload = {
        "instruction": subject_meta["hint"],
        "prompt": subject_meta["hint"],
        "subject_name": subject_meta["uz"],
        "image": _image_to_base64_png(tilted_img),
        "size": size
    }
    
    solution_data = {
        "initial_angle": angle,
        "tolerance": 15
    }
    
    return client_payload, solution_data


# ==================== VARIETY 4: CLICK-IN-SEQUENCE ====================

SEQUENCE_SYMBOLS = [
    {
        "name": "Triangle",
        "uz": "Uchburchak",
        "shape": "triangle",
        "color": (2, 132, 199),
        "svg": '<svg viewBox="0 0 24 24" width="18" height="18" fill="#0284C7" stroke="#0369A1" stroke-width="1.5"><polygon points="12 3 22 21 2 21 12 3"/></svg>'
    },
    {
        "name": "Star",
        "uz": "Yulduz",
        "shape": "star",
        "color": (217, 119, 6),
        "svg": '<svg viewBox="0 0 24 24" width="18" height="18" fill="#F59E0B" stroke="#D97706" stroke-width="1.5"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>'
    },
    {
        "name": "Diamond",
        "uz": "Olmos",
        "shape": "diamond",
        "color": (255, 90, 31),
        "svg": '<svg viewBox="0 0 24 24" width="18" height="18" fill="#FF5A1F" stroke="#C2410C" stroke-width="1.5"><polygon points="12 2 22 12 12 22 2 12 12 2"/></svg>'
    },
    {
        "name": "Heart",
        "uz": "Yurak",
        "shape": "heart",
        "color": (225, 29, 72),
        "svg": '<svg viewBox="0 0 24 24" width="18" height="18" fill="#F43F5E" stroke="#E11D48" stroke-width="1.5"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/></svg>'
    },
    {
        "name": "Circle",
        "uz": "Aylana",
        "shape": "circle",
        "color": (5, 150, 105),
        "svg": '<svg viewBox="0 0 24 24" width="18" height="18" fill="#10B981" stroke="#059669" stroke-width="1.5"><circle cx="12" cy="12" r="9"/></svg>'
    },
    {
        "name": "Hexagon",
        "uz": "Oltiburchak",
        "shape": "hexagon",
        "color": (15, 23, 42),
        "svg": '<svg viewBox="0 0 24 24" width="18" height="18" fill="#0F172A" stroke="#334155" stroke-width="1.5"><polygon points="12 2 21 7 21 17 12 22 3 17 3 7 12 2"/></svg>'
    }
]


def generate_sequence_challenge() -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Variety 4: Click-in-Sequence (5 Symbols on Canvas -> Click 3 Target Symbols in Order)
    """
    width, height = 320, 180
    bg = _generate_procedural_background(width, height)
    draw = ImageDraw.Draw(bg, "RGBA")
    
    # Draw subtle anti-OCR wave curves across canvas before stamping crisp icon badges
    for _ in range(3):
        wave_pts = []
        base_y = _SECURE_RNG.randint(25, height - 25)
        amp = _SECURE_RNG.randint(8, 22)
        freq = _SECURE_RNG.uniform(0.025, 0.05)
        phase = _SECURE_RNG.uniform(0, 6.28)
        for wx in range(0, width + 1, 8):
            wy = int(base_y + amp * math.sin(wx * freq + phase))
            wave_pts.append((wx, wy))
        draw.line(wave_pts, fill=(255, 255, 255, 70), width=2)

    total_symbols = 5
    chosen_symbols = _SECURE_RNG.sample(SEQUENCE_SYMBOLS, total_symbols)
    positions: List[Tuple[int, int]] = []
    min_dist = 58
    attempts = 0
    while len(positions) < total_symbols and attempts < 220:
        attempts += 1
        px = _SECURE_RNG.randint(38, width - 38)
        py = _SECURE_RNG.randint(34, height - 34)
        if all(math.hypot(px - ex, py - ey) >= min_dist for ex, ey in positions):
            positions.append((px, py))
            
    if len(positions) < total_symbols:
        positions = [(54, 48), (160, 42), (266, 48), (96, 132), (224, 132)]
        
    placed_items = []
    for i in range(total_symbols):
        sym = chosen_symbols[i]
        pos = positions[i]
        placed_items.append({
            "name": sym["name"],
            "uz": sym["uz"],
            "shape": sym["shape"],
            "svg": sym["svg"],
            "x": pos[0],
            "y": pos[1],
            "radius": 22,
            "color": sym["color"]
        })
        
        gx, gy = pos[0], pos[1]
        col = sym["color"]
        r = 16
        tilt_deg = _SECURE_RNG.randint(-12, 12)
        
        # Crisp MonoDeck high-contrast rounded backing token (clean shadow + white badge)
        draw.ellipse([gx - r - 6, gy - r - 5, gx + r + 7, gy + r + 8], fill=(10, 10, 12, 70))
        draw.ellipse([gx - r - 6, gy - r - 6, gx + r + 6, gy + r + 6], fill=(255, 255, 255, 240), outline=(15, 23, 42, 190), width=2)
        
        if sym["shape"] == "triangle":
            pts = [(gx + r * math.cos(math.radians(k * 120 - 90 + tilt_deg)), gy + r * math.sin(math.radians(k * 120 - 90 + tilt_deg))) for k in range(3)]
            draw.polygon(pts, fill=(*col, 255), outline=(255, 255, 255, 255), width=2)
        elif sym["shape"] == "star":
            pts = []
            for k in range(10):
                a = math.radians(k * 36 - 90 + tilt_deg)
                cr = r if k % 2 == 0 else int(r * 0.45)
                pts.append((gx + cr * math.cos(a), gy + cr * math.sin(a)))
            draw.polygon(pts, fill=(*col, 255), outline=(255, 255, 255, 255), width=2)
        elif sym["shape"] == "diamond":
            tilt = math.radians(tilt_deg)
            raw_d = [(0, -r), (int(r * 0.85), 0), (0, r), (-int(r * 0.85), 0)]
            pts = [(gx + dx * math.cos(tilt) - dy * math.sin(tilt), gy + dx * math.sin(tilt) + dy * math.cos(tilt)) for dx, dy in raw_d]
            draw.polygon(pts, fill=(*col, 255), outline=(255, 255, 255, 255), width=2)
        elif sym["shape"] == "heart":
            pts = []
            for t in [x * 0.1 for x in range(63)]:
                hx = 16 * (math.sin(t) ** 3)
                hy = -(13 * math.cos(t) - 5 * math.cos(2*t) - 2 * math.cos(3*t) - math.cos(4*t))
                pts.append((gx + int(hx * 0.82), gy + int(hy * 0.82) + 2))
            draw.polygon(pts, fill=(*col, 255), outline=(255, 255, 255, 255), width=2)
        elif sym["shape"] == "circle":
            draw.ellipse([gx - r + 1, gy - r + 1, gx + r - 1, gy + r - 1], fill=(*col, 255), outline=(255, 255, 255, 255), width=2)
            draw.ellipse([gx - r // 2, gy - r // 2, gx + r // 2, gy + r // 2], fill=(255, 255, 255, 255))
        elif sym["shape"] == "hexagon":
            pts = [
                (gx + r * math.cos(math.radians(k * 60 + tilt_deg)), gy + r * math.sin(math.radians(k * 60 + tilt_deg)))
                for k in range(6)
            ]
            draw.polygon(pts, fill=(*col, 255), outline=(255, 255, 255, 255), width=2)
            
    sequence_items = _SECURE_RNG.sample(placed_items, 3)
    target_sequence_uz = [it["uz"] for it in sequence_items]
    target_sequence_names = [it["name"] for it in sequence_items]
    
    client_payload = {
        "instruction": f"Ko'rsatilgan 3 belgini tartib bilan bosing: {' -> '.join(target_sequence_uz)}",
        "prompt": f"Ko'rsatilgan 3 belgini tartib bilan bosing: {' -> '.join(target_sequence_uz)}",
        "sequence": target_sequence_names,
        "sequence_uz": target_sequence_uz,
        "sequence_steps": [
            {
                "step": i + 1,
                "name": it["name"],
                "uz": it["uz"],
                "svg": it["svg"]
            }
            for i, it in enumerate(sequence_items)
        ],
        "bg_image": _image_to_base64_png(bg),
        "count": 3
    }
    
    solution_data = {
        "targets": [
            {"x": it["x"], "y": it["y"], "radius": 36, "name": it["name"]}
            for it in sequence_items
        ]
    }
    
    return client_payload, solution_data


# ==================== CAPTCHA MANAGER & TELEMETRY VERIFICATION ====================

class CaptchaManager:
    """Manages challenge life-cycle, telemetry verification, and HMAC signed tokens"""

    @staticmethod
    def create_challenge(challenge_type: str = "auto", sitekey: str = "demo_key") -> Dict[str, Any]:
        """Yangi challenge yaratish"""
        _cleanup_expired_records()
        
        valid_types = ["slider", "grid", "rotate", "sequence"]
        if challenge_type not in valid_types or challenge_type == "auto":
            challenge_type = _SECURE_RNG.choice(valid_types)
            
        challenge_id = secrets.token_hex(16)
        
        if challenge_type == "slider":
            payload, solution = generate_slider_challenge()
        elif challenge_type == "grid":
            payload, solution = generate_grid_challenge()
        elif challenge_type == "rotate":
            payload, solution = generate_rotate_challenge()
        elif challenge_type == "sequence":
            payload, solution = generate_sequence_challenge()
        else:
            payload, solution = generate_slider_challenge()
            challenge_type = "slider"
            
        nonce = secrets.token_hex(8)
        now = time.time()
        expires_at = now + 300  # 5 minutes
        
        _ACTIVE_CHALLENGES[challenge_id] = {
            "challenge_id": challenge_id,
            "type": challenge_type,
            "solution": solution,
            "sitekey": sitekey,
            "nonce": nonce,
            "created_at": now,
            "expires_at": expires_at,
            "is_used": False
        }
        _enforce_cache_cap(_ACTIVE_CHALLENGES)
        
        return {
            "ok": True,
            "challenge_id": challenge_id,
            "type": challenge_type,
            "nonce": nonce,
            "expires_in": 300,
            "payload": payload
        }

    @staticmethod
    def evaluate_telemetry(challenge_type: str, telemetry: Optional[Dict[str, Any]]) -> Tuple[bool, float, str]:
        """
        Anti-Bot Telemetry Analysis:
        Analyzes human micro-movements, trajectory curvature, timing jitter, and drag acceleration.
        Returns: (is_human, confidence_score, reason)
        """
        if not telemetry or not isinstance(telemetry, dict) or not telemetry:
            return False, 0.15, "missing_or_empty_telemetry"
            
        duration_ms = telemetry.get("duration_ms", 0)
        
        # Check minimum reasonable human interaction duration (fast human fingers: >= 120ms)
        if duration_ms < 120:
            return False, 0.15, "superhuman_instant_solve"
            
        trajectory = telemetry.get("trajectory", [])
        
        if challenge_type == "slider":
            # For slider drag, pointer movement events MUST exist
            if not isinstance(trajectory, list) or len(trajectory) < 4:
                return False, 0.15, "insufficient_drag_trajectory_samples"
                
            # Calculate Y-jitter (humans have hand tremor; bots drag on strict y=const)
            y_coords = [pt.get("y", 0) for pt in trajectory if isinstance(pt, dict) and "y" in pt]
            if len(y_coords) >= 3:
                y_diffs = [abs(y_coords[i] - y_coords[i - 1]) for i in range(1, len(y_coords))]
                total_y_jitter = sum(y_diffs)
                if total_y_jitter == 0:
                    return False, 0.20, "zero_y_jitter_synthetic_line"
                    
            # Check velocity profile
            timestamps = [pt.get("t", 0) for pt in trajectory if isinstance(pt, dict) and "t" in pt]
            if len(timestamps) >= 4:
                intervals = [timestamps[i] - timestamps[i - 1] for i in range(1, len(timestamps))]
                if len(set(intervals)) == 1 and len(intervals) >= 4:
                    return False, 0.25, "synthetic_fixed_interval_bot"
                    
                x_coords = [pt.get("x", 0) for pt in trajectory if isinstance(pt, dict) and "x" in pt]
                if len(x_coords) == len(timestamps) and len(x_coords) >= 4:
                    speeds = []
                    for i in range(1, len(x_coords)):
                        dt = max(1, timestamps[i] - timestamps[i - 1])
                        dx = x_coords[i] - x_coords[i - 1]
                        speeds.append(dx / dt)
                    if len(set(speeds)) == 1 and len(speeds) >= 4:
                        return False, 0.25, "constant_velocity_synthetic_bot"
                        
            score = 0.95
            if duration_ms < 200:
                score = 0.85
            elif duration_ms > 8000:
                score = 0.88
            return True, score, "human_slider_verified"

        elif challenge_type == "grid":
            if duration_ms < 200:
                return False, 0.20, "grid_solve_too_fast"
            clicks = telemetry.get("clicks", [])
            if isinstance(clicks, list) and len(clicks) >= 2:
                ts = [c.get("t", 0) for c in clicks if isinstance(c, dict) and "t" in c]
                if len(ts) >= 2:
                    diffs = [ts[i] - ts[i - 1] for i in range(1, len(ts))]
                    if any(d < 40 for d in diffs):
                        return False, 0.18, "superhuman_grid_multiclick"
            score = 0.97 if duration_ms > 600 else 0.89
            return True, score, "human_grid_verified"

        elif challenge_type == "rotate":
            if duration_ms < 150:
                return False, 0.25, "rotate_solve_too_fast"
            score = 0.96
            return True, score, "human_rotate_verified"

        elif challenge_type == "sequence":
            clicks = telemetry.get("clicks", [])
            if not isinstance(clicks, list) or len(clicks) < 3:
                return False, 0.15, "missing_click_telemetry"
            if duration_ms < 150:
                return False, 0.18, "sequence_solve_too_fast"
            ts = [c.get("t", 0) for c in clicks if isinstance(c, dict) and "t" in c]
            if len(ts) >= 3 and all(t > 0 for t in ts):
                diffs = [ts[i] - ts[i - 1] for i in range(1, len(ts))]
                if any(d < 15 for d in diffs):
                    return False, 0.18, "superhuman_multiclick_speed"
            score = 0.98 if duration_ms > 500 else 0.88
            return True, score, "human_sequence_verified"

        return True, 0.90, "standard_passed"

    @staticmethod
    def verify_challenge(challenge_id: str, solution: Any, telemetry: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Widget orqali yechilgan challenge'ni tekshirish va HMAC token berish"""
        _cleanup_expired_records()
        
        challenge = _ACTIVE_CHALLENGES.get(challenge_id)
        if not challenge:
            return {"ok": False, "error": "challenge_not_found_or_expired", "message": "Challenge topilmadi yoki eskirgan"}
            
        if challenge.get("is_used"):
            return {"ok": False, "error": "challenge_already_used", "message": "Ushbu challenge allaqachon ishlatilgan"}
            
        now = time.time()
        if now > challenge.get("expires_at", 0):
            _ACTIVE_CHALLENGES.pop(challenge_id, None)
            return {"ok": False, "error": "challenge_expired", "message": "Vaqt tugadi, yangilang"}
            
        c_type = challenge["type"]
        expected_sol = challenge["solution"]

        # Single-use challenge: mark consumed immediately to block solution brute-force
        challenge["is_used"] = True
        _ACTIVE_CHALLENGES.pop(challenge_id, None)

        # Normalize sequence clicks from solution only when genuine client telemetry exists
        if telemetry is not None and isinstance(telemetry, dict):
            if c_type == "sequence" and not telemetry.get("clicks"):
                if isinstance(solution, dict) and solution.get("clicks"):
                    telemetry = dict(telemetry)
                    telemetry["clicks"] = solution["clicks"]

        # 1. Telemetry verification (rejects missing/None telemetry)
        is_human, human_score, reason = CaptchaManager.evaluate_telemetry(c_type, telemetry)
        if not is_human:
            return {
                "ok": False,
                "error": "bot_detected",
                "message": f"Avtomatlashtirilgan harakat aniqlandi: {reason}",
                "score": human_score
            }
            
        # 2. Mathematical solution verification
        is_correct = False
        
        if c_type == "slider":
            try:
                user_x = float(solution.get("x", 0) if isinstance(solution, dict) else solution)
                target_x = expected_sol["target_x"]
                tol = expected_sol.get("tolerance", 9)
                is_correct = abs(user_x - target_x) <= tol
            except Exception:
                is_correct = False
                
        elif c_type == "grid":
            try:
                selected_indices = solution.get("selected", []) if isinstance(solution, dict) else solution
                target_indices = expected_sol["target_indices"]
                is_correct = sorted(list(set(int(x) for x in selected_indices))) == sorted(target_indices)
            except Exception:
                is_correct = False
                
        elif c_type == "rotate":
            try:
                user_angle = float(solution.get("angle", 0) if isinstance(solution, dict) else solution)
                initial_angle = expected_sol["initial_angle"]
                tol = expected_sol.get("tolerance", 15)
                net_offset = (initial_angle + user_angle) % 360
                err = min(net_offset, 360 - net_offset)
                is_correct = err <= tol
            except Exception:
                is_correct = False
                
        elif c_type == "sequence":
            try:
                user_clicks = solution.get("clicks", []) if isinstance(solution, dict) else solution
                targets = expected_sol["targets"]
                if len(user_clicks) == len(targets):
                    match_all = True
                    for i in range(len(targets)):
                        cx = user_clicks[i].get("x", 0)
                        cy = user_clicks[i].get("y", 0)
                        tx = targets[i]["x"]
                        ty = targets[i]["y"]
                        tr = max(targets[i]["radius"], 36)  # Balanced 36px touch hit radius (prevents adjacent hit overlap)
                        dist = math.hypot(cx - tx, cy - ty)
                        if dist > tr:
                            match_all = False
                            break
                    is_correct = match_all
                else:
                    is_correct = False
            except Exception:
                is_correct = False

        if not is_correct:
            err_messages = {
                "slider": "Pazl joyiga aniq tushmadi. Qaytadan surib ko'ring!",
                "grid": "Barcha mos shakllar tanlanmadi yoki ortiqcha katak belgilandi.",
                "rotate": "Shakl to'liq tik holatga (yuqori ▲ nuqtaga) keltirilmadi.",
                "sequence": "Tartib noto'g'ri. Ko'rsatilgan 3 belgini 1-2-3 tartibda bosing!"
            }
            return {"ok": False, "error": "incorrect_solution", "message": err_messages.get(c_type, "Javob noto'g'ri. Qaytadan urinib ko'ring!")}
            
        challenge["is_used"] = True
        
        # 3. Generate signed HMAC verification token
        token_ts = int(now)
        sitekey = challenge.get("sitekey", "demo_key")
        score_formatted = f"{human_score:.2f}"
        
        raw_payload = f"{sitekey}:{challenge_id}:{token_ts}:{score_formatted}"
        signature = hmac.new(
            _get_captcha_signing_key(),
            raw_payload.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()[:24]
        
        token = f"bsh_{challenge_id}_{token_ts}_{score_formatted}_{signature}"
        
        _VERIFIED_TOKENS[token] = {
            "token": token,
            "challenge_id": challenge_id,
            "sitekey": sitekey,
            "score": human_score,
            "created_at": now,
            "expires_at": now + 300,
            "is_used": False
        }
        _enforce_cache_cap(_VERIFIED_TOKENS)
        
        return {
            "ok": True,
            "token": token,
            "score": human_score,
            "type": c_type,
            "message": "Muvaffaqiyatli tasdiqlandi!"
        }

    @staticmethod
    def siteverify_token(token: str, secret_key: str, sitekey: Optional[str] = None) -> Dict[str, Any]:
        """
        Server-to-Server endpoint for site owners to validate solved token.
        Checks signature, expiration, and enforces single-use replay protection.
        """
        _cleanup_expired_records()
        
        if not token or not token.startswith("bsh_"):
            return {"success": False, "error": "invalid_token_format", "message": "Noto'g'ri token formati"}
            
        parts = token.split("_")
        if len(parts) != 5:
            return {"success": False, "error": "malformed_token", "message": "Token strukturasi buzilgan"}
            
        challenge_id = parts[1]
        try:
            token_ts = int(parts[2])
            score = float(parts[3])
            sig = parts[4]
        except ValueError:
            return {"success": False, "error": "invalid_token_values", "message": "Token qiymatlari noto'g'ri"}
            
        now = time.time()
        if token_ts > now + 60 or now - token_ts > 300:
            return {"success": False, "error": "token_expired", "message": "Token muddati tugagan (5 daqiqa)"}
            
        # 1. In-memory replay protection check
        rec = _VERIFIED_TOKENS.get(token)
        if not rec:
            return {"success": False, "error": "token_not_found_or_expired", "message": "Token topilmadi yoki eskirgan"}
            
        if rec.get("is_used"):
            return {"success": False, "error": "token_already_consumed", "message": "Ushbu token allaqachon ishlatilgan (Replay attack blocked)"}
            
        token_sitekey = str(rec.get("sitekey", "demo_key"))

        # 2. Sitekey binding validation (constant-time, no sitekey oracle leak)
        if sitekey and not hmac.compare_digest(token_sitekey, str(sitekey)):
            return {
                "success": False,
                "error": "sitekey_mismatch",
                "message": "Ushbu token berilgan sitekey uchun yaroqsiz"
            }

        # 3. Persistent Database replay protection check
        try:
            import database
            if hasattr(database, "is_captcha_challenge_used") and database.is_captcha_challenge_used(challenge_id):
                return {
                    "success": False,
                    "error": "token_already_consumed",
                    "message": "Ushbu token allaqachon ishlatilgan (Baza darajasidagi Replay himoyasi)"
                }
        except Exception:
            pass
        
        # 4. Verify signature
        expected_raw = f"{token_sitekey}:{challenge_id}:{token_ts}:{score:.2f}"
        expected_sig = hmac.new(
            _get_captcha_signing_key(),
            expected_raw.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()[:24]
        
        if not hmac.compare_digest(sig, expected_sig):
            return {"success": False, "error": "signature_mismatch", "message": "Token imzosi yaroqsiz"}
            
        rec["is_used"] = True
        
        return {
            "success": True,
            "challenge_id": challenge_id,
            "sitekey": token_sitekey,
            "score": score,
            "timestamp": token_ts,
            "action": "solve"
        }
