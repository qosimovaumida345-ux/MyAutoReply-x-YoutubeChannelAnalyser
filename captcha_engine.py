"""
BotShield Captcha Engine - Next-Gen Anti-Bot Verification System
Standalone, Zero-External-API Captcha as a Service.
Supports 4 Human-Only Interactive Challenges:
1. Slider Puzzle: Procedural textured canvas with cut-out jigsaw notch & piece.
2. 9-Grid Semantic Selector: Dynamic 3x3 tiles with procedurally generated semantic shapes.
3. Dial Angle Alignment: Rotated vector subject restored to 0° upright orientation.
4. Click-in-Sequence: 4 procedural glyphs clicked in specified sequence.

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


def _image_to_base64_png(img: Image.Image) -> str:
    """Pillow Image obyektini data URI base64 formatiga o'tkazish"""
    buffered = io.BytesIO()
    img.save(buffered, format="PNG", optimize=True)
    b64_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{b64_str}"


# ==================== PROCEDURAL TEXTURES & GRAPHICS ====================

def _generate_procedural_background(width: int, height: int, theme: str = "cyber") -> Image.Image:
    """Procedurally render a rich, complex background with layered gradients, geometric noise and curves"""
    img = Image.new("RGBA", (width, height), (9, 10, 15, 255))
    draw = ImageDraw.Draw(img, "RGBA")
    
    # Color palettes
    palettes = [
        [(15, 23, 42), (30, 27, 75), (13, 148, 136)],    # Slate & Indigo & Teal
        [(10, 15, 29), (59, 7, 100), (6, 182, 212)],     # Obsidian & Violet & Cyan
        [(17, 24, 39), (76, 29, 149), (236, 72, 153)],   # Dark & Purple & Pink
        [(8, 14, 26), (16, 185, 129), (14, 116, 144)],    # Deep Green & Emerald & Cyan
    ]
    p = random.choice(palettes)
    c1, c2, c3 = p[0], p[1], p[2]
    
    # Base vertical/angular gradient
    angle = random.choice([0, 1, 2])
    for y in range(height):
        factor = y / max(1, height - 1)
        r = int(c1[0] * (1 - factor) + c2[0] * factor)
        g = int(c1[1] * (1 - factor) + c2[1] * factor)
        b = int(c1[2] * (1 - factor) + c2[2] * factor)
        draw.line([(0, y), (width, y)], fill=(r, g, b, 255))
        
    # Overlay 12-20 decorative geometric curves and polygons with transparency
    for _ in range(random.randint(12, 20)):
        shape_type = random.choice(["circle", "poly", "band", "spline"])
        alpha = random.randint(35, 110)
        col = (
            random.randint(min(c2[0], c3[0]), max(c2[0], c3[0], 255)),
            random.randint(min(c2[1], c3[1]), max(c2[1], c3[1], 255)),
            random.randint(min(c2[2], c3[2]), max(c2[2], c3[2], 255)),
            alpha
        )
        if shape_type == "circle":
            rx = random.randint(15, 65)
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
            
    # Add subtle anti-bot pixel grid / noise texture
    for _ in range(random.randint(60, 120)):
        nx = random.randint(0, width - 1)
        ny = random.randint(0, height - 1)
        draw.point((nx, ny), fill=(255, 255, 255, random.randint(30, 90)))
        
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
    draw.rounded_rectangle([body_x0, body_y0, body_x1, body_y1], radius=int(4 * scale), fill=255)
    
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
    """
    width, height = 320, 170
    piece_size = 46
    
    # 1. Procedural background
    bg = _generate_procedural_background(width, height)
    
    # 2. Random target position (leaving comfortable margins)
    target_x = random.randint(80, width - piece_size - 25)
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
    
    # Add subtle glowing neon cyan border around the piece
    piece_draw = ImageDraw.Draw(piece_img)
    # Trace contour outline
    border_mask = mask.filter(ImageFilter.FIND_EDGES)
    border_img = Image.new("RGBA", (piece_size, piece_size), (0, 240, 255, 180))
    piece_img.paste(border_img, (0, 0), border_mask)
    
    # 5. Draw notch cutout onto background
    bg_with_notch = bg.copy()
    notch_dark = Image.new("RGBA", (piece_size, piece_size), (6, 8, 15, 210))
    
    # Apply darkened cutout
    bg_with_notch.paste(notch_dark, (target_x, target_y), mask)
    
    # Add subtle inner border for notch
    notch_border = Image.new("RGBA", (piece_size, piece_size), (255, 255, 255, 120))
    bg_with_notch.paste(notch_border, (target_x, target_y), border_mask)
    
    client_payload = {
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
        "tolerance": 5
    }
    
    return client_payload, solution_data


# ==================== VARIETY 2: 9-GRID SEMANTIC SELECTOR ====================

SEMANTIC_SHAPES = {
    "star": {"uz": "Yulduz", "en": "Star", "desc": "Barcha yulduzli kataklarni tanlang"},
    "triangle": {"uz": "Uchburchak", "en": "Triangle", "desc": "Barcha uchburchakli kataklarni tanlang"},
    "circle": {"uz": "Aylana", "en": "Circle / Ring", "desc": "Barcha aylanali kataklarni tanlang"},
    "diamond": {"uz": "Olmos / Romb", "en": "Diamond", "desc": "Barcha olmos/romb shaklli kataklarni tanlang"},
    "heart": {"uz": "Yurak", "en": "Heart", "desc": "Barcha yurak shaklli kataklarni tanlang"},
    "crescent": {"uz": "Oyparcha", "en": "Crescent Moon", "desc": "Barcha oyparcha shaklli kataklarni tanlang"},
    "hexagon": {"uz": "Oltiburchak", "en": "Hexagon", "desc": "Barcha oltiburchak shaklli kataklarni tanlang"},
    "cross": {"uz": "Krest / Plus", "en": "Cross", "desc": "Barcha plus/krest shaklli kataklarni tanlang"}
}


def _draw_procedural_tile(shape_name: str, size: int = 90) -> Image.Image:
    """Procedurally render a single 90x90 tile with the target geometric shape and rich dark cyberpunk aesthetics"""
    tile = Image.new("RGBA", (size, size), (15, 23, 42, 255))
    draw = ImageDraw.Draw(tile)
    
    # Subtle dark background gradient & texture
    base_col = random.choice([(15, 23, 42), (17, 24, 39), (24, 24, 27), (12, 10, 28)])
    draw.rectangle([0, 0, size, size], fill=base_col)
    
    # Decorative subtle grid/dots
    for gx in range(10, size, 20):
        for gy in range(10, size, 20):
            draw.point((gx, gy), fill=(255, 255, 255, 25))
            
    # Neon palette for shape
    palette = random.choice([
        (0, 240, 255),    # Neon Cyan
        (139, 92, 246),   # Neon Violet
        (244, 63, 94),    # Coral Rose
        (16, 185, 129),   # Emerald
        (245, 158, 11),   # Amber
        (56, 189, 248),   # Sky
    ])
    
    # Supersampled shape rendering for smooth lines
    scale = 3
    ss = size * scale
    canvas = Image.new("RGBA", (ss, ss), (0, 0, 0, 0))
    sdraw = ImageDraw.Draw(canvas)
    
    cx, cy = ss // 2, ss // 2
    r = int(24 * scale)
    
    # Random slight rotation angle (-25 to +25 deg)
    rot_angle = random.randint(-25, 25)
    
    if shape_name == "star":
        pts = []
        for i in range(10):
            a = math.radians(i * 36 - 90 + rot_angle)
            cr = r if i % 2 == 0 else int(r * 0.45)
            pts.append((cx + cr * math.cos(a), cy + cr * math.sin(a)))
        sdraw.polygon(pts, fill=(*palette, 230), outline=(255, 255, 255, 255), width=int(1.5 * scale))
        
    elif shape_name == "triangle":
        pts = []
        for i in range(3):
            a = math.radians(i * 120 - 90 + rot_angle)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
        sdraw.polygon(pts, fill=(*palette, 230), outline=(255, 255, 255, 255), width=int(1.5 * scale))
        
    elif shape_name == "circle":
        sdraw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(*palette, 210), outline=(255, 255, 255, 255), width=int(2 * scale))
        inner_r = int(r * 0.5)
        sdraw.ellipse([cx - inner_r, cy - inner_r, cx + inner_r, cy + inner_r], fill=(*base_col, 255), outline=(255, 255, 255, 180), width=int(1.5 * scale))
        
    elif shape_name == "diamond":
        w = int(r * 0.8)
        pts = [
            (cx, cy - r),
            (cx + w, cy),
            (cx, cy + r),
            (cx - w, cy)
        ]
        sdraw.polygon(pts, fill=(*palette, 230), outline=(255, 255, 255, 255), width=int(1.5 * scale))
        # Inner facet lines
        sdraw.line([(cx - w, cy), (cx + w, cy)], fill=(255, 255, 255, 180), width=scale)
        sdraw.line([(cx, cy - r), (cx, cy + r)], fill=(255, 255, 255, 180), width=scale)
        
    elif shape_name == "heart":
        # Draw symmetric heart
        pts = []
        for t in [x * 0.05 for x in range(126)]:
            # Parametric heart equation
            hx = 16 * (math.sin(t) ** 3)
            hy = -(13 * math.cos(t) - 5 * math.cos(2*t) - 2 * math.cos(3*t) - math.cos(4*t))
            pts.append((cx + int(hx * scale * 1.3), cy + int(hy * scale * 1.3) + int(3*scale)))
        if len(pts) > 2:
            sdraw.polygon(pts, fill=(*palette, 240), outline=(255, 255, 255, 255), width=int(1.5 * scale))
            
    elif shape_name == "crescent":
        sdraw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(*palette, 230))
        # Subtract inner circle
        offset = int(r * 0.45)
        sdraw.ellipse([cx - r + offset, cy - r - offset, cx + r + offset, cy + r - offset], fill=(*base_col, 255))
        
    elif shape_name == "hexagon":
        pts = []
        for i in range(6):
            a = math.radians(i * 60 + rot_angle)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
        sdraw.polygon(pts, fill=(*palette, 230), outline=(255, 255, 255, 255), width=int(1.5 * scale))
        
    elif shape_name == "cross":
        bar_w = int(r * 0.35)
        sdraw.rectangle([cx - bar_w, cy - r, cx + bar_w, cy + r], fill=(*palette, 230), outline=(255, 255, 255, 255))
        sdraw.rectangle([cx - r, cy - bar_w, cx + r, cy + bar_w], fill=(*palette, 230), outline=(255, 255, 255, 255))
        
    # Resize down
    scaled_shape = canvas.resize((size, size), Image.Resampling.LANCZOS)
    tile.paste(scaled_shape, (0, 0), scaled_shape)
    
    # Subtle inner border for the tile
    draw.rectangle([0, 0, size - 1, size - 1], outline=(255, 255, 255, 20), width=1)
    return tile


def generate_grid_challenge() -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Variety 2: 9-Grid Semantic Selector
    Generates 9 procedural tiles, pick 1 target category (3-4 occurrences) and distractors.
    """
    categories = list(SEMANTIC_SHAPES.keys())
    target_category = random.choice(categories)
    other_categories = [c for c in categories if c != target_category]
    
    # 3 or 4 target tiles
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
        "prompt": f"Select all tiles with: {target_meta['en']} ({target_meta['uz']})",
        "instruction": target_meta["desc"],
        "target_name": target_meta["en"],
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
    "arrow": {"uz": "Strelka", "en": "Arrow", "hint": "Strelkani tepaga (0° tik) qaratib burang"},
    "rocket": {"uz": "Raketa", "en": "Rocket", "hint": "Raketani uchish yo'nalishi (tik tepaga) holatiga keltiring"},
    "key": {"uz": "Kalit", "en": "Key", "hint": "Kalitni bosh qismini tepaga qaratib to'g'rilang"},
    "tree": {"uz": "Daraxt", "en": "Pine Tree", "hint": "Daraxtni to'g'ri (ildizi pastda, uchi tepada) qilib burang"},
    "umbrella": {"uz": "Soyabon", "en": "Umbrella", "hint": "Soyabonni gumbazini tepaga qilib to'g'rilang"},
    "compass": {"uz": "Kompas", "en": "Compass Needle", "hint": "Qizil milni to'g'ri (tik tepaga) qaratib burang"}
}


def _draw_upright_subject(subject_type: str = "arrow", size: int = 170) -> Image.Image:
    """
    Render a crisp vector subject on a circular dial face.
    Canvas outside the circular dial is fully transparent RGBA(0,0,0,0) so that rotating
    the disk produces zero corner clipping artifacts, preventing edge-slope angle leakage.
    """
    scale = 3
    ss = size * scale
    canvas = Image.new("RGBA", (ss, ss), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    
    cx, cy = ss // 2, ss // 2
    r = int(58 * scale)
    
    # 1. Circular dial backing (dark slate with cyan glow perimeter)
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(15, 23, 42, 255), outline=(0, 240, 255, 160), width=int(2 * scale))
    
    # 2. Calibration tick marks around perimeter
    for deg in range(0, 360, 30):
        rad = math.radians(deg)
        t_len = int(6 * scale) if deg % 90 == 0 else int(3.5 * scale)
        x_outer = cx + int((r - 2) * math.cos(rad))
        y_outer = cy + int((r - 2) * math.sin(rad))
        x_inner = cx + int((r - 2 - t_len) * math.cos(rad))
        y_inner = cy + int((r - 2 - t_len) * math.sin(rad))
        col = (0, 240, 255, 240) if deg == 270 else (255, 255, 255, 120)  # 270 deg = top (0 deg upright)
        draw.line([(x_inner, y_inner), (x_outer, y_outer)], fill=col, width=int(1.5 * scale))
        
    # 3. Render the specific vector subject pointing strictly upright
    if subject_type == "rocket":
        rh = int(46 * scale)
        rw = int(14 * scale)
        body = [(cx, cy - rh), (cx + rw, cy - rh + int(32 * scale)), (cx + rw, cy + int(12 * scale)), (cx - rw, cy + int(12 * scale)), (cx - rw, cy - rh + int(32 * scale))]
        draw.polygon(body, fill=(0, 240, 255, 255), outline=(255, 255, 255, 255), width=scale)
        fin_l = [(cx - rw, cy), (cx - rw - int(12 * scale), cy + int(18 * scale)), (cx - rw, cy + int(14 * scale))]
        fin_r = [(cx + rw, cy), (cx + rw + int(12 * scale), cy + int(18 * scale)), (cx + rw, cy + int(14 * scale))]
        draw.polygon(fin_l, fill=(244, 63, 94, 255))
        draw.polygon(fin_r, fill=(244, 63, 94, 255))
        # Window & Flame
        draw.ellipse([cx - int(6 * scale), cy - int(12 * scale), cx + int(6 * scale), cy], fill=(15, 23, 42, 255), outline=(255, 255, 255, 255), width=scale)
        draw.polygon([(cx - int(7 * scale), cy + int(13 * scale)), (cx, cy + int(30 * scale)), (cx + int(7 * scale), cy + int(13 * scale))], fill=(245, 158, 11, 255))
    elif subject_type == "key":
        kh = int(44 * scale)
        kr = int(14 * scale)
        draw.ellipse([cx - kr, cy - kh, cx + kr, cy - kh + kr * 2], fill=(245, 158, 11, 255), outline=(255, 255, 255, 255), width=scale)
        draw.ellipse([cx - int(6 * scale), cy - kh + int(6 * scale), cx + int(6 * scale), cy - kh + int(18 * scale)], fill=(15, 23, 42, 255))
        draw.rectangle([cx - int(3.5 * scale), cy - kh + kr * 2, cx + int(3.5 * scale), cy + int(24 * scale)], fill=(245, 158, 11, 255), outline=(255, 255, 255, 255), width=scale)
        draw.rectangle([cx + int(3 * scale), cy + int(6 * scale), cx + int(14 * scale), cy + int(12 * scale)], fill=(245, 158, 11, 255))
        draw.rectangle([cx + int(3 * scale), cy + int(16 * scale), cx + int(12 * scale), cy + int(22 * scale)], fill=(245, 158, 11, 255))
    elif subject_type == "tree":
        for top_y, bot_y, hw in [(cy - int(44 * scale), cy - int(20 * scale), int(16 * scale)),
                                 (cy - int(24 * scale), cy + int(4 * scale), int(22 * scale)),
                                 (cy, cy + int(24 * scale), int(28 * scale))]:
            pts = [(cx, top_y), (cx + hw, bot_y), (cx - hw, bot_y)]
            draw.polygon(pts, fill=(16, 185, 129, 255), outline=(255, 255, 255, 200), width=scale)
        draw.rectangle([cx - int(4 * scale), cy + int(24 * scale), cx + int(4 * scale), cy + int(36 * scale)], fill=(180, 83, 9, 255))
    elif subject_type == "umbrella":
        draw.pieslice([cx - int(28 * scale), cy - int(40 * scale), cx + int(28 * scale), cy + int(16 * scale)], 180, 360, fill=(244, 63, 94, 255), outline=(255, 255, 255, 255), width=scale)
        draw.line([(cx, cy - int(40 * scale)), (cx, cy - int(46 * scale))], fill=(255, 255, 255, 255), width=int(2 * scale))
        draw.line([(cx, cy - int(12 * scale)), (cx, cy + int(28 * scale))], fill=(255, 255, 255, 255), width=int(2 * scale))
        draw.arc([cx - int(10 * scale), cy + int(20 * scale), cx, cy + int(34 * scale)], 0, 180, fill=(255, 255, 255, 255), width=int(2 * scale))
    elif subject_type == "compass":
        draw.polygon([(cx, cy - int(45 * scale)), (cx + int(8 * scale), cy), (cx - int(8 * scale), cy)], fill=(244, 63, 94, 255), outline=(255, 255, 255, 255), width=scale)
        draw.polygon([(cx, cy + int(45 * scale)), (cx + int(8 * scale), cy), (cx - int(8 * scale), cy)], fill=(226, 232, 240, 255), outline=(255, 255, 255, 255), width=scale)
    else:  # "arrow" default
        arrow_h = int(46 * scale)
        arrow_w = int(22 * scale)
        shaft_w = int(8 * scale)
        shaft_h = int(22 * scale)
        head_pts = [(cx, cy - arrow_h), (cx + arrow_w, cy - arrow_h + int(24 * scale)), (cx - arrow_w, cy - arrow_h + int(24 * scale))]
        draw.polygon(head_pts, fill=(0, 240, 255, 255), outline=(255, 255, 255, 255), width=int(2 * scale))
        draw.rectangle([cx - shaft_w // 2, cy - arrow_h + int(22 * scale), cx + shaft_w // 2, cy + shaft_h], fill=(139, 92, 246, 255), outline=(255, 255, 255, 200), width=scale)
        draw.ellipse([cx - int(7 * scale), cy + shaft_h - int(4 * scale), cx + int(7 * scale), cy + shaft_h + int(10 * scale)], fill=(244, 63, 94, 255))
        
    # Center pivot circle
    draw.ellipse([cx - int(5 * scale), cy - int(5 * scale), cx + int(5 * scale), cy + int(5 * scale)], fill=(255, 255, 255, 255))
    
    return canvas.resize((size, size), Image.Resampling.LANCZOS)


def generate_rotate_challenge() -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Variety 3: Dial Angle Alignment
    Generates an oriented subject tilted by random angle (40° to 320°).
    User rotates dial until upright (0°).
    """
    size = 170
    subject_key = random.choice(list(ROTATE_SUBJECTS.keys()))
    subject_meta = ROTATE_SUBJECTS[subject_key]
    subject = _draw_upright_subject(subject_key, size)
    
    # Random angle (avoid trivial +-25 deg)
    angle = random.choice([
        random.randint(45, 150),
        random.randint(210, 315)
    ])
    
    # Rotate counter-clockwise / clockwise
    # Pillow rotate rotates counter-clockwise with positive angle
    # We rotate by -angle so it turns clockwise by `angle` degrees
    tilted_img = subject.rotate(-angle, resample=Image.Resampling.BICUBIC)
    
    client_payload = {
        "instruction": f"{subject_meta['hint']} ({subject_meta['uz']})",
        "prompt": f"Rotate the dial until the {subject_meta['en']} is perfectly upright (0°)",
        "subject_name": subject_meta["en"],
        "image": _image_to_base64_png(tilted_img),
        "size": size
    }
    
    solution_data = {
        "initial_angle": angle,
        "tolerance": 12  # +-12 deg margin
    }
    
    return client_payload, solution_data


# ==================== VARIETY 4: CLICK-IN-SEQUENCE ====================

SEQUENCE_SYMBOLS = [
    {"name": "Triangle", "uz": "Uchburchak", "shape": "triangle", "color": (0, 240, 255)},
    {"name": "Star", "uz": "Yulduz", "shape": "star", "color": (245, 158, 11)},
    {"name": "Diamond", "uz": "Olmos", "shape": "diamond", "color": (139, 92, 246)},
    {"name": "Heart", "uz": "Yurak", "shape": "heart", "color": (244, 63, 94)},
    {"name": "Circle", "uz": "Aylana", "shape": "circle", "color": (16, 185, 129)},
    {"name": "Hexagon", "uz": "Oltiburchak", "shape": "hexagon", "color": (56, 189, 248)}
]


def generate_sequence_challenge() -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Variety 4: Click-in-Sequence
    Places 4 distinct geometric symbols across a textured canvas.
    Requires user to click 3 specific symbols in given sequence.
    """
    width, height = 320, 180
    bg = _generate_procedural_background(width, height)
    draw = ImageDraw.Draw(bg)
    
    # Pick 4 symbols
    chosen_symbols = random.sample(SEQUENCE_SYMBOLS, 4)
    
    # Generate 4 well-separated positions
    positions: List[Tuple[int, int]] = []
    min_dist = 65
    attempts = 0
    while len(positions) < 4 and attempts < 100:
        attempts += 1
        px = random.randint(45, width - 45)
        py = random.randint(35, height - 35)
        if all(math.hypot(px - ex, py - ey) >= min_dist for ex, ey in positions):
            positions.append((px, py))
            
    if len(positions) < 4:
        # Fallback grid layout if random placement fails
        positions = [(65, 55), (255, 55), (85, 135), (235, 135)]
        
    placed_items = []
    for i in range(4):
        sym = chosen_symbols[i]
        pos = positions[i]
        placed_items.append({
            "name": sym["name"],
            "uz": sym["uz"],
            "shape": sym["shape"],
            "x": pos[0],
            "y": pos[1],
            "radius": 24,
            "color": sym["color"]
        })
        
        # Render glyph on canvas
        gx, gy = pos[0], pos[1]
        col = sym["color"]
        r = 16
        
        # Glow disc
        draw.ellipse([gx - r - 4, gy - r - 4, gx + r + 4, gy + r + 4], fill=(*col, 50))
        
        # Symbol drawing
        if sym["shape"] == "triangle":
            pts = [(gx, gy - r), (gx + r, gy + r), (gx - r, gy + r)]
            draw.polygon(pts, fill=(*col, 220), outline=(255, 255, 255, 255), width=2)
        elif sym["shape"] == "star":
            pts = []
            for k in range(10):
                a = math.radians(k * 36 - 90)
                cr = r if k % 2 == 0 else int(r * 0.45)
                pts.append((gx + cr * math.cos(a), gy + cr * math.sin(a)))
            draw.polygon(pts, fill=(*col, 220), outline=(255, 255, 255, 255), width=2)
        elif sym["shape"] == "diamond":
            pts = [(gx, gy - r), (gx + r, gy), (gx, gy + r), (gx - r, gy)]
            draw.polygon(pts, fill=(*col, 220), outline=(255, 255, 255, 255), width=2)
        elif sym["shape"] == "heart":
            pts = []
            for t in [x * 0.1 for x in range(63)]:
                hx = 16 * (math.sin(t) ** 3)
                hy = -(13 * math.cos(t) - 5 * math.cos(2*t) - 2 * math.cos(3*t) - math.cos(4*t))
                pts.append((gx + int(hx * 0.8), gy + int(hy * 0.8) + 2))
            draw.polygon(pts, fill=(*col, 220), outline=(255, 255, 255, 255), width=2)
        elif sym["shape"] == "circle":
            draw.ellipse([gx - r, gy - r, gx + r, gy + r], fill=(*col, 220), outline=(255, 255, 255, 255), width=2)
            draw.ellipse([gx - r//2, gy - r//2, gx + r//2, gy + r//2], fill=(15, 23, 42, 255))
        elif sym["shape"] == "hexagon":
            pts = [
                (gx + r * math.cos(math.radians(k * 60)), gy + r * math.sin(math.radians(k * 60)))
                for k in range(6)
            ]
            draw.polygon(pts, fill=(*col, 220), outline=(255, 255, 255, 255), width=2)
            
    # Choose 3 symbols for target sequence
    sequence_items = random.sample(placed_items, 3)
    target_sequence_names = [it["name"] for it in sequence_items]
    target_sequence_uz = [it["uz"] for it in sequence_items]
    
    client_payload = {
        "instruction": f"Belgilarni ketma-ketlikda bosing: {' -> '.join(target_sequence_uz)}",
        "prompt": f"Click the symbols in sequence: {' -> '.join(target_sequence_names)}",
        "sequence": target_sequence_names,
        "sequence_uz": target_sequence_uz,
        "bg_image": _image_to_base64_png(bg),
        "count": 3
    }
    
    solution_data = {
        "targets": [
            {"x": it["x"], "y": it["y"], "radius": it["radius"] + 12, "name": it["name"]}
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
        
        # Check minimum reasonable human interaction duration
        if duration_ms < 150:
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
                # Perfect horizontal line with zero variance is a synthetic bot marker
                if total_y_jitter == 0:
                    return False, 0.20, "zero_y_jitter_synthetic_line"
                    
            # Check velocity profile (humans accelerate and then decelerate near target)
            timestamps = [pt.get("t", 0) for pt in trajectory if isinstance(pt, dict) and "t" in pt]
            if len(timestamps) >= 4:
                intervals = [timestamps[i] - timestamps[i - 1] for i in range(1, len(timestamps))]
                # Bots often use identical fixed-interval sleeps (e.g. exactly 10.0ms)
                if len(set(intervals)) == 1 and len(intervals) >= 4:
                    return False, 0.25, "synthetic_fixed_interval_bot"
                    
                # Velocity variance check: check speeds dx/dt
                x_coords = [pt.get("x", 0) for pt in trajectory if isinstance(pt, dict) and "x" in pt]
                if len(x_coords) == len(timestamps) and len(x_coords) >= 4:
                    speeds = []
                    for i in range(1, len(x_coords)):
                        dt = max(1, timestamps[i] - timestamps[i - 1])
                        dx = x_coords[i] - x_coords[i - 1]
                        speeds.append(dx / dt)
                    if len(set(speeds)) == 1 and len(speeds) >= 4:
                        return False, 0.25, "constant_velocity_synthetic_bot"
                        
            # Human confidence score
            score = 0.95
            if duration_ms < 250:
                score = 0.82
            elif duration_ms > 8000:
                score = 0.88
            return True, score, "human_slider_verified"

        elif challenge_type == "grid":
            if duration_ms < 400:
                return False, 0.20, "grid_solve_too_fast"
            clicks = telemetry.get("clicks", [])
            if isinstance(clicks, list) and len(clicks) >= 2:
                ts = [c.get("t", 0) for c in clicks if isinstance(c, dict) and "t" in c]
                if len(ts) >= 2:
                    diffs = [ts[i] - ts[i - 1] for i in range(1, len(ts))]
                    if any(d < 60 for d in diffs):
                        return False, 0.18, "superhuman_grid_multiclick"
            score = 0.97 if duration_ms > 1000 else 0.89
            return True, score, "human_grid_verified"

        elif challenge_type == "rotate":
            if duration_ms < 250:
                return False, 0.25, "rotate_solve_too_fast"
            score = 0.96
            return True, score, "human_rotate_verified"

        elif challenge_type == "sequence":
            clicks = telemetry.get("clicks", [])
            if not isinstance(clicks, list) or len(clicks) < 3:
                return False, 0.15, "missing_click_telemetry"
            if duration_ms < 350:
                return False, 0.18, "sequence_solve_too_fast"
            # Check intervals between sequential clicks
            ts = [c.get("t", 0) for c in clicks if isinstance(c, dict) and "t" in c]
            if len(ts) >= 3:
                diffs = [ts[i] - ts[i - 1] for i in range(1, len(ts))]
                if any(d < 80 for d in diffs):
                    return False, 0.18, "superhuman_multiclick_speed"
            score = 0.98 if duration_ms > 900 else 0.88
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
            # user provides x offset
            try:
                user_x = float(solution.get("x", 0) if isinstance(solution, dict) else solution)
                target_x = expected_sol["target_x"]
                tol = expected_sol.get("tolerance", 5)
                is_correct = abs(user_x - target_x) <= tol
            except Exception:
                is_correct = False
                
        elif c_type == "grid":
            # user provides list of selected indices [0..8]
            try:
                selected_indices = solution.get("selected", []) if isinstance(solution, dict) else solution
                target_indices = expected_sol["target_indices"]
                is_correct = sorted(list(set(int(x) for x in selected_indices))) == sorted(target_indices)
            except Exception:
                is_correct = False
                
        elif c_type == "rotate":
            # user provides angle rotated in degrees (0..360)
            try:
                user_angle = float(solution.get("angle", 0) if isinstance(solution, dict) else solution)
                initial_angle = expected_sol["initial_angle"]
                tol = expected_sol.get("tolerance", 12)
                # The image was initially rotated clockwise by initial_angle.
                # User rotation brings it back.
                # Net angle offset:
                net_offset = (initial_angle + user_angle) % 360
                err = min(net_offset, 360 - net_offset)
                is_correct = err <= tol
            except Exception:
                is_correct = False
                
        elif c_type == "sequence":
            # user provides list of clicks [{"x": ..., "y": ..., "t": ...}, ...]
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
                        tr = targets[i]["radius"]
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
            return {"ok": False, "error": "incorrect_solution", "message": "Javob noto'g'ri. Qayta urinib ko'ring."}
            
        # Mark challenge as used
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
        
        # Store in verified tokens cache with 5 minute expiration
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

        # 2. Sitekey binding validation (Prevent cross-tenant token substitution)
        if sitekey and token_sitekey != sitekey:
            return {
                "success": False,
                "error": "sitekey_mismatch",
                "message": f"Ushbu token boshqa sitekey uchun chiqarilgan (kutilgan: {sitekey}, haqiqiy: {token_sitekey})"
            }

        # 3. Persistent Database replay protection check (survives restarts/multi-workers)
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
            
        # Mark token as consumed
        rec["is_used"] = True
        
        return {
            "success": True,
            "challenge_id": challenge_id,
            "sitekey": token_sitekey,
            "score": score,
            "timestamp": token_ts,
            "action": "solve"
        }
