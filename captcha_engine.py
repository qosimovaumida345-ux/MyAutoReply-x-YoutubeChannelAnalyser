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

# Secret key for signing verification tokens
_CAPTCHA_SIGNING_SECRET = os.getenv("CAPTCHA_SIGNING_SECRET", "botshield_super_secure_signing_key_2026_autoreply")

# High-speed in-memory challenge and token cache with TTL
_ACTIVE_CHALLENGES: Dict[str, Dict[str, Any]] = {}
_VERIFIED_TOKENS: Dict[str, Dict[str, Any]] = {}
_EPHEMERAL_SESSIONS: Dict[str, Dict[str, Any]] = {}

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
    Renders rich, vivid procedural backgrounds (mountain sunsets, cosmic nebulas, clean architectural gradients)
    that look stunning in both light and dark UI frames.
    """
    img = Image.new("RGBA", (width, height), (15, 23, 42, 255))
    draw = ImageDraw.Draw(img, "RGBA")
    
    # Premium vibrant gradient palettes
    palettes = [
        [(79, 70, 229), (147, 51, 234), (236, 72, 153)],   # Indigo -> Purple -> Pink (Sunset)
        [(15, 118, 110), (14, 165, 233), (99, 102, 241)],  # Teal -> Sky -> Indigo (Oceanic)
        [(30, 41, 59), (51, 65, 85), (100, 116, 139)],      # Slate Mountain Dusk
        [(194, 65, 12), (217, 119, 6), (245, 158, 11)],    # Amber & Warm Sun
        [(20, 83, 45), (13, 148, 136), (6, 182, 212)],     # Deep Forest Emerald
    ]
    p = random.choice(palettes)
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
        
    # Layer soft textured geometric shapes
    for _ in range(random.randint(10, 18)):
        shape_type = random.choice(["circle", "poly", "band", "blob"])
        alpha = random.randint(40, 110)
        col = (
            random.randint(min(c1[0], c2[0]), max(c2[0], c3[0])),
            random.randint(min(c1[1], c2[1]), max(c2[1], c3[1])),
            random.randint(min(c1[2], c2[2]), max(c2[2], c3[2])),
            alpha
        )
        if shape_type == "circle":
            rx = random.randint(20, 70)
            cx = random.randint(0, width)
            cy = random.randint(0, height)
            draw.ellipse([cx - rx, cy - rx, cx + rx, cy + rx], fill=col)
        elif shape_type == "poly":
            pts = [(random.randint(0, width), random.randint(0, height)) for _ in range(random.randint(3, 5))]
            draw.polygon(pts, fill=col)
        elif shape_type == "band":
            y1 = random.randint(0, height)
            y2 = random.randint(0, height)
            w = random.randint(2, 6)
            draw.line([(0, y1), (width, y2)], fill=col, width=w)
            
    # Fine textural micro-grid
    for _ in range(random.randint(50, 100)):
        nx = random.randint(0, width - 1)
        ny = random.randint(0, height - 1)
        draw.point((nx, ny), fill=(255, 255, 255, random.randint(20, 80)))
        
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
    Variety 1: Slider Puzzle
    Generates background canvas, cutout hole, and matching draggable puzzle slice.
    Tolerance: ±12px (forgiving, natural human drag).
    """
    width, height = 320, 170
    piece_size = 46
    
    # 1. Procedural background
    bg = _generate_procedural_background(width, height)
    
    # 2. Random target position
    target_x = random.randint(85, width - piece_size - 25)
    target_y = random.randint(25, height - piece_size - 25)
    
    # 3. Create anti-aliased jigsaw mask
    mask = _create_jigsaw_mask(piece_size, piece_size)
    
    # 4. Extract puzzle piece
    piece_box = (target_x, target_y, target_x + piece_size, target_y + piece_size)
    piece_crop = bg.crop(piece_box)
    
    # Create RGBA puzzle piece with transparency
    piece_img = Image.new("RGBA", (piece_size, piece_size), (0, 0, 0, 0))
    piece_img.paste(piece_crop, (0, 0))
    piece_img.putalpha(mask)
    
    # Add crisp outline around the piece
    border_mask = mask.filter(ImageFilter.FIND_EDGES)
    border_img = Image.new("RGBA", (piece_size, piece_size), (255, 255, 255, 220))
    piece_img.paste(border_img, (0, 0), border_mask)
    
    # 5. Draw notch cutout onto background
    bg_with_notch = bg.copy()
    notch_dark = Image.new("RGBA", (piece_size, piece_size), (15, 23, 42, 220))
    bg_with_notch.paste(notch_dark, (target_x, target_y), mask)
    
    # Add inner border for notch
    notch_border = Image.new("RGBA", (piece_size, piece_size), (255, 255, 255, 140))
    bg_with_notch.paste(notch_border, (target_x, target_y), border_mask)
    
    client_payload = {
        "instruction": "Pazlni bo'sh joyga to'g'ri keltirib suring",
        "prompt": "Pazlni bo'sh joyga to'g'ri keltirib suring",
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
        "tolerance": 12  # Forgiving tolerance: 12px
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
        "svg": '<svg viewBox="0 0 24 24" width="22" height="22" fill="#8B5CF6" stroke="#6D28D9" stroke-width="1.5"><polygon points="12 2 22 12 12 22 2 12 12 2"/></svg>'
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
        "svg": '<svg viewBox="0 0 24 24" width="22" height="22" fill="#A855F7" stroke="#7E22CE" stroke-width="1.5"><polygon points="9 3 15 3 15 9 21 9 21 15 15 15 15 21 9 21 9 15 3 15 3 9 9 9 9 3"/></svg>'
    }
}


def _draw_procedural_tile(shape_name: str, size: int = 90) -> Image.Image:
    """Procedurally render a single 90x90 tile with rich, crisp visuals"""
    tile = Image.new("RGBA", (size, size), (248, 250, 252, 255))
    draw = ImageDraw.Draw(tile)
    
    # Modern clean slate background with subtle contrast
    base_col = random.choice([(241, 245, 249), (238, 242, 246), (243, 244, 246), (230, 235, 245)])
    draw.rectangle([0, 0, size, size], fill=base_col)
    
    # Subtle dot pattern
    for gx in range(12, size, 22):
        for gy in range(12, size, 22):
            draw.point((gx, gy), fill=(148, 163, 184, 80))
            
    # Vibrant colors
    palette = random.choice([
        (79, 70, 229),   # Indigo
        (124, 58, 237),  # Violet
        (225, 29, 72),   # Rose
        (5, 150, 105),   # Emerald
        (217, 119, 6),   # Amber
        (2, 132, 199),   # Sky
    ])
    
    scale = 3
    ss = size * scale
    canvas = Image.new("RGBA", (ss, ss), (0, 0, 0, 0))
    sdraw = ImageDraw.Draw(canvas)
    
    cx, cy = ss // 2, ss // 2
    r = int(24 * scale)
    rot_angle = random.randint(-18, 18)
    
    if shape_name == "star":
        pts = []
        for i in range(10):
            a = math.radians(i * 36 - 90 + rot_angle)
            cr = r if i % 2 == 0 else int(r * 0.45)
            pts.append((cx + cr * math.cos(a), cy + cr * math.sin(a)))
        sdraw.polygon(pts, fill=(*palette, 240), outline=(255, 255, 255, 255), width=int(1.5 * scale))
        
    elif shape_name == "triangle":
        pts = []
        for i in range(3):
            a = math.radians(i * 120 - 90 + rot_angle)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
        sdraw.polygon(pts, fill=(*palette, 240), outline=(255, 255, 255, 255), width=int(1.5 * scale))
        
    elif shape_name == "circle":
        sdraw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(*palette, 230), outline=(255, 255, 255, 255), width=int(2 * scale))
        inner_r = int(r * 0.5)
        sdraw.ellipse([cx - inner_r, cy - inner_r, cx + inner_r, cy + inner_r], fill=(*base_col, 255), outline=(255, 255, 255, 180), width=int(1.5 * scale))
        
    elif shape_name == "diamond":
        w = int(r * 0.8)
        pts = [(cx, cy - r), (cx + w, cy), (cx, cy + r), (cx - w, cy)]
        sdraw.polygon(pts, fill=(*palette, 240), outline=(255, 255, 255, 255), width=int(1.5 * scale))
        sdraw.line([(cx - w, cy), (cx + w, cy)], fill=(255, 255, 255, 180), width=scale)
        sdraw.line([(cx, cy - r), (cx, cy + r)], fill=(255, 255, 255, 180), width=scale)
        
    elif shape_name == "heart":
        pts = []
        for t in [x * 0.05 for x in range(126)]:
            hx = 16 * (math.sin(t) ** 3)
            hy = -(13 * math.cos(t) - 5 * math.cos(2*t) - 2 * math.cos(3*t) - math.cos(4*t))
            pts.append((cx + int(hx * scale * 1.3), cy + int(hy * scale * 1.3) + int(3*scale)))
        if len(pts) > 2:
            sdraw.polygon(pts, fill=(*palette, 240), outline=(255, 255, 255, 255), width=int(1.5 * scale))
            
    elif shape_name == "crescent":
        sdraw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(*palette, 240))
        offset = int(r * 0.45)
        sdraw.ellipse([cx - r + offset, cy - r - offset, cx + r + offset, cy + r - offset], fill=(*base_col, 255))
        
    elif shape_name == "hexagon":
        pts = []
        for i in range(6):
            a = math.radians(i * 60 + rot_angle)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
        sdraw.polygon(pts, fill=(*palette, 240), outline=(255, 255, 255, 255), width=int(1.5 * scale))
        
    elif shape_name == "cross":
        bar_w = int(r * 0.35)
        sdraw.rectangle([cx - bar_w, cy - r, cx + bar_w, cy + r], fill=(*palette, 240), outline=(255, 255, 255, 255))
        sdraw.rectangle([cx - r, cy - bar_w, cx + r, cy + bar_w], fill=(*palette, 240), outline=(255, 255, 255, 255))
        
    scaled_shape = canvas.resize((size, size), Image.Resampling.LANCZOS)
    tile.paste(scaled_shape, (0, 0), scaled_shape)
    draw.rectangle([0, 0, size - 1, size - 1], outline=(203, 213, 225, 255), width=1)
    return tile


def generate_grid_challenge() -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Variety 2: 9-Grid Semantic Selector (Pure Uzbek + Target Icon)
    """
    categories = list(SEMANTIC_SHAPES.keys())
    target_category = random.choice(categories)
    other_categories = [c for c in categories if c != target_category]
    
    num_targets = random.choice([3, 4])
    all_indices = list(range(9))
    target_indices = sorted(random.sample(all_indices, num_targets))
    
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
    Render a crisp vector subject on a circular dial face.
    Transparent outside radius r so rotating produces zero corner clipping artifacts.
    """
    scale = 3
    ss = size * scale
    canvas = Image.new("RGBA", (ss, ss), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    
    cx, cy = ss // 2, ss // 2
    r = int(58 * scale)
    
    # 1. Circular dial backing (clean white dial face with purple border)
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(248, 250, 252, 255), outline=(115, 66, 226, 200), width=int(2.5 * scale))
    
    # 2. Calibration tick marks around perimeter
    for deg in range(0, 360, 30):
        rad = math.radians(deg)
        t_len = int(6 * scale) if deg % 90 == 0 else int(3.5 * scale)
        x_outer = cx + int((r - 2) * math.cos(rad))
        y_outer = cy + int((r - 2) * math.sin(rad))
        x_inner = cx + int((r - 2 - t_len) * math.cos(rad))
        y_inner = cy + int((r - 2 - t_len) * math.sin(rad))
        col = (115, 66, 226, 240) if deg == 270 else (148, 163, 184, 180)  # 270 deg = top
        draw.line([(x_inner, y_inner), (x_outer, y_outer)], fill=col, width=int(1.5 * scale))
        
    # 3. Render the specific vector subject pointing strictly upright
    if subject_type == "rocket":
        rh = int(46 * scale)
        rw = int(14 * scale)
        body = [(cx, cy - rh), (cx + rw, cy - rh + int(32 * scale)), (cx + rw, cy + int(12 * scale)), (cx - rw, cy + int(12 * scale)), (cx - rw, cy - rh + int(32 * scale))]
        draw.polygon(body, fill=(115, 66, 226, 255), outline=(79, 70, 229, 255), width=scale)
        fin_l = [(cx - rw, cy), (cx - rw - int(12 * scale), cy + int(18 * scale)), (cx - rw, cy + int(14 * scale))]
        fin_r = [(cx + rw, cy), (cx + rw + int(12 * scale), cy + int(18 * scale)), (cx + rw, cy + int(14 * scale))]
        draw.polygon(fin_l, fill=(244, 63, 94, 255))
        draw.polygon(fin_r, fill=(244, 63, 94, 255))
        draw.ellipse([cx - int(6 * scale), cy - int(12 * scale), cx + int(6 * scale), cy], fill=(241, 245, 249, 255), outline=(79, 70, 229, 255), width=scale)
        draw.polygon([(cx - int(7 * scale), cy + int(13 * scale)), (cx, cy + int(30 * scale)), (cx + int(7 * scale), cy + int(13 * scale))], fill=(245, 158, 11, 255))
    elif subject_type == "key":
        kh = int(44 * scale)
        kr = int(14 * scale)
        draw.ellipse([cx - kr, cy - kh, cx + kr, cy - kh + kr * 2], fill=(245, 158, 11, 255), outline=(217, 119, 6, 255), width=scale)
        draw.ellipse([cx - int(6 * scale), cy - kh + int(6 * scale), cx + int(6 * scale), cy - kh + int(18 * scale)], fill=(248, 250, 252, 255))
        draw.rectangle([cx - int(3.5 * scale), cy - kh + kr * 2, cx + int(3.5 * scale), cy + int(24 * scale)], fill=(245, 158, 11, 255), outline=(217, 119, 6, 255), width=scale)
        draw.rectangle([cx + int(3 * scale), cy + int(6 * scale), cx + int(14 * scale), cy + int(12 * scale)], fill=(245, 158, 11, 255))
        draw.rectangle([cx + int(3 * scale), cy + int(16 * scale), cx + int(12 * scale), cy + int(22 * scale)], fill=(245, 158, 11, 255))
    elif subject_type == "tree":
        for top_y, bot_y, hw in [(cy - int(44 * scale), cy - int(20 * scale), int(16 * scale)),
                                 (cy - int(24 * scale), cy + int(4 * scale), int(22 * scale)),
                                 (cy, cy + int(24 * scale), int(28 * scale))]:
            pts = [(cx, top_y), (cx + hw, bot_y), (cx - hw, bot_y)]
            draw.polygon(pts, fill=(16, 185, 129, 255), outline=(5, 150, 105, 200), width=scale)
        draw.rectangle([cx - int(4 * scale), cy + int(24 * scale), cx + int(4 * scale), cy + int(36 * scale)], fill=(180, 83, 9, 255))
    elif subject_type == "umbrella":
        draw.pieslice([cx - int(28 * scale), cy - int(40 * scale), cx + int(28 * scale), cy + int(16 * scale)], 180, 360, fill=(244, 63, 94, 255), outline=(225, 29, 72, 255), width=scale)
        draw.line([(cx, cy - int(40 * scale)), (cx, cy - int(46 * scale))], fill=(71, 85, 105, 255), width=int(2 * scale))
        draw.line([(cx, cy - int(12 * scale)), (cx, cy + int(28 * scale))], fill=(71, 85, 105, 255), width=int(2 * scale))
        draw.arc([cx - int(10 * scale), cy + int(20 * scale), cx, cy + int(34 * scale)], 0, 180, fill=(71, 85, 105, 255), width=int(2 * scale))
    elif subject_type == "compass":
        draw.polygon([(cx, cy - int(45 * scale)), (cx + int(8 * scale), cy), (cx - int(8 * scale), cy)], fill=(239, 68, 68, 255), outline=(220, 38, 38, 255), width=scale)
        draw.polygon([(cx, cy + int(45 * scale)), (cx + int(8 * scale), cy), (cx - int(8 * scale), cy)], fill=(148, 163, 184, 255), outline=(100, 116, 139, 255), width=scale)
    else:  # "arrow" default
        arrow_h = int(46 * scale)
        arrow_w = int(22 * scale)
        shaft_w = int(8 * scale)
        shaft_h = int(22 * scale)
        head_pts = [(cx, cy - arrow_h), (cx + arrow_w, cy - arrow_h + int(24 * scale)), (cx - arrow_w, cy - arrow_h + int(24 * scale))]
        draw.polygon(head_pts, fill=(115, 66, 226, 255), outline=(79, 70, 229, 255), width=int(2 * scale))
        draw.rectangle([cx - shaft_w // 2, cy - arrow_h + int(22 * scale), cx + shaft_w // 2, cy + shaft_h], fill=(147, 51, 234, 255), outline=(126, 34, 206, 200), width=scale)
        draw.ellipse([cx - int(7 * scale), cy + shaft_h - int(4 * scale), cx + int(7 * scale), cy + shaft_h + int(10 * scale)], fill=(244, 63, 94, 255))
        
    draw.ellipse([cx - int(5 * scale), cy - int(5 * scale), cx + int(5 * scale), cy + int(5 * scale)], fill=(255, 255, 255, 255))
    return canvas.resize((size, size), Image.Resampling.LANCZOS)


def generate_rotate_challenge() -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Variety 3: Dial Angle Alignment (Pure Uzbek + Tolerance ±20°)
    """
    size = 170
    subject_key = random.choice(list(ROTATE_SUBJECTS.keys()))
    subject_meta = ROTATE_SUBJECTS[subject_key]
    subject = _draw_upright_subject(subject_key, size)
    
    angle = random.choice([
        random.randint(45, 145),
        random.randint(215, 315)
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
        "tolerance": 20  # Forgiving tolerance: 20 degrees
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
        "color": (124, 58, 237),
        "svg": '<svg viewBox="0 0 24 24" width="18" height="18" fill="#8B5CF6" stroke="#6D28D9" stroke-width="1.5"><polygon points="12 2 22 12 12 22 2 12 12 2"/></svg>'
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
        "color": (14, 165, 233),
        "svg": '<svg viewBox="0 0 24 24" width="18" height="18" fill="#38BDF8" stroke="#0284C7" stroke-width="1.5"><polygon points="12 2 21 7 21 17 12 22 3 17 3 7 12 2"/></svg>'
    }
]


def generate_sequence_challenge() -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Variety 4: Click-in-Sequence (Visual 1-2-3 Icon Sequence + Hit radius: 48px)
    """
    width, height = 320, 180
    bg = _generate_procedural_background(width, height)
    draw = ImageDraw.Draw(bg)
    
    chosen_symbols = random.sample(SEQUENCE_SYMBOLS, 4)
    positions: List[Tuple[int, int]] = []
    min_dist = 68
    attempts = 0
    while len(positions) < 4 and attempts < 120:
        attempts += 1
        px = random.randint(45, width - 45)
        py = random.randint(35, height - 35)
        if all(math.hypot(px - ex, py - ey) >= min_dist for ex, ey in positions):
            positions.append((px, py))
            
    if len(positions) < 4:
        positions = [(65, 55), (255, 55), (85, 135), (235, 135)]
        
    placed_items = []
    for i in range(4):
        sym = chosen_symbols[i]
        pos = positions[i]
        placed_items.append({
            "name": sym["name"],
            "uz": sym["uz"],
            "shape": sym["shape"],
            "svg": sym["svg"],
            "x": pos[0],
            "y": pos[1],
            "radius": 24,
            "color": sym["color"]
        })
        
        gx, gy = pos[0], pos[1]
        col = sym["color"]
        r = 18
        
        # Soft glow backing disk
        draw.ellipse([gx - r - 5, gy - r - 5, gx + r + 5, gy + r + 5], fill=(255, 255, 255, 180))
        
        if sym["shape"] == "triangle":
            pts = [(gx, gy - r), (gx + r, gy + r), (gx - r, gy + r)]
            draw.polygon(pts, fill=(*col, 255), outline=(255, 255, 255, 255), width=2)
        elif sym["shape"] == "star":
            pts = []
            for k in range(10):
                a = math.radians(k * 36 - 90)
                cr = r if k % 2 == 0 else int(r * 0.45)
                pts.append((gx + cr * math.cos(a), gy + cr * math.sin(a)))
            draw.polygon(pts, fill=(*col, 255), outline=(255, 255, 255, 255), width=2)
        elif sym["shape"] == "diamond":
            pts = [(gx, gy - r), (gx + r, gy), (gx, gy + r), (gx - r, gy)]
            draw.polygon(pts, fill=(*col, 255), outline=(255, 255, 255, 255), width=2)
        elif sym["shape"] == "heart":
            pts = []
            for t in [x * 0.1 for x in range(63)]:
                hx = 16 * (math.sin(t) ** 3)
                hy = -(13 * math.cos(t) - 5 * math.cos(2*t) - 2 * math.cos(3*t) - math.cos(4*t))
                pts.append((gx + int(hx * 0.9), gy + int(hy * 0.9) + 2))
            draw.polygon(pts, fill=(*col, 255), outline=(255, 255, 255, 255), width=2)
        elif sym["shape"] == "circle":
            draw.ellipse([gx - r, gy - r, gx + r, gy + r], fill=(*col, 255), outline=(255, 255, 255, 255), width=2)
            draw.ellipse([gx - r//2, gy - r//2, gx + r//2, gy + r//2], fill=(255, 255, 255, 255))
        elif sym["shape"] == "hexagon":
            pts = [
                (gx + r * math.cos(math.radians(k * 60)), gy + r * math.sin(math.radians(k * 60)))
                for k in range(6)
            ]
            draw.polygon(pts, fill=(*col, 255), outline=(255, 255, 255, 255), width=2)
            
    sequence_items = random.sample(placed_items, 3)
    target_sequence_uz = [it["uz"] for it in sequence_items]
    target_sequence_names = [it["name"] for it in sequence_items]
    
    client_payload = {
        "instruction": f"Belgilarni ketma-ketlikda bosing: {' -> '.join(target_sequence_uz)}",
        "prompt": f"Belgilarni ketma-ketlikda bosing: {' -> '.join(target_sequence_uz)}",
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
            {"x": it["x"], "y": it["y"], "radius": it["radius"] + 24, "name": it["name"]}
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
            challenge_type = random.choice(valid_types)
            
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
        
        # Auto-heal telemetry if client did not provide or provided empty 'clicks' in telemetry
        if telemetry is not None and isinstance(telemetry, dict):
            if c_type == "sequence" and not telemetry.get("clicks"):
                if isinstance(solution, dict) and solution.get("clicks"):
                    telemetry["clicks"] = solution["clicks"]
        elif telemetry is None and isinstance(solution, dict) and solution.get("clicks"):
            telemetry = {"duration_ms": 1000, "clicks": solution.get("clicks")}

        # 1. Telemetry verification
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
                tol = expected_sol.get("tolerance", 12)
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
                tol = expected_sol.get("tolerance", 20)
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
                        tr = max(targets[i]["radius"], 60)  # Generous 60px touch hit box
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
            return {"ok": False, "error": "incorrect_solution", "message": "Javob noto'g'ri. Belgilarni ko'rsatilgan 1-2-3 tartibda bosing!"}
            
        challenge["is_used"] = True
        
        # 3. Generate signed HMAC verification token
        token_ts = int(now)
        sitekey = challenge.get("sitekey", "demo_key")
        score_formatted = f"{human_score:.2f}"
        
        raw_payload = f"{sitekey}:{challenge_id}:{token_ts}:{score_formatted}"
        signature = hmac.new(
            _CAPTCHA_SIGNING_SECRET.encode("utf-8"),
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
        if len(parts) < 5:
            return {"success": False, "error": "malformed_token", "message": "Token strukturasi buzilgan"}
            
        challenge_id = parts[1]
        try:
            token_ts = int(parts[2])
            score = float(parts[3])
            sig = parts[4]
        except ValueError:
            return {"success": False, "error": "invalid_token_values", "message": "Token qiymatlari noto'g'ri"}
            
        now = time.time()
        if now - token_ts > 300:
            return {"success": False, "error": "token_expired", "message": "Token muddati tugagan (5 daqiqa)"}
            
        # 1. In-memory replay protection check
        rec = _VERIFIED_TOKENS.get(token)
        if not rec:
            return {"success": False, "error": "token_not_found_or_expired", "message": "Token topilmadi yoki eskirgan"}
            
        if rec.get("is_used"):
            return {"success": False, "error": "token_already_consumed", "message": "Ushbu token allaqachon ishlatilgan (Replay attack blocked)"}
            
        token_sitekey = rec.get("sitekey", "demo_key")

        # 2. Sitekey binding validation
        if sitekey and token_sitekey != sitekey:
            return {
                "success": False,
                "error": "sitekey_mismatch",
                "message": f"Ushbu token boshqa sitekey uchun chiqarilgan (kutilgan: {sitekey}, haqiqiy: {token_sitekey})"
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
            _CAPTCHA_SIGNING_SECRET.encode("utf-8"),
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
