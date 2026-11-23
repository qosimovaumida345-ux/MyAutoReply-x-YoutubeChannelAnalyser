"""Generate real Chrome-rendered 1080x1920 Telegram & Mini App promo videos for Mono Deck Studio (@monodeck_app).

Outputs:
  downloads/monodeck_promo_uz.mp4  (Uzbek voiceover via ElevenLabs + ambient synth bed)
  downloads/monodeck_promo_en.mp4  (English voiceover via ElevenLabs + ambient synth bed)
Keyframes exported to downloads/_promo_keyframe_s1..s4.png for visual QA.
"""
import asyncio
import base64
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
import wave
from io import BytesIO
from pathlib import Path

import aiohttp
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except Exception:
    pass

DOWNLOADS = ROOT / "downloads"
DOWNLOADS.mkdir(parents=True, exist_ok=True)
ASSETS = ROOT / "nft_assets"

W, H = 1080, 1920
FPS = 30
CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"


def _asset_b64(path: Path, max_dim: int = 256, mime: str = "image/png") -> str:
    if not path.exists():
        return ""
    try:
        with Image.open(path) as im:
            im.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)
            buf = BytesIO()
            fmt = "PNG" if mime == "image/png" else "WEBP"
            im.save(buf, format=fmt)
            b64 = base64.b64encode(buf.getvalue()).decode("ascii")
            return f"data:{mime};base64,{b64}"
    except Exception:
        return ""


def _build_scene_html() -> str:
    logo_uri = _asset_b64(DOWNLOADS / "Mono Deck Studio Logo.png", 256, "image/png")
    user_uri = _asset_b64(ASSETS / "user_avatars" / "6735799833.jpg", 96, "image/webp")
    bronze_uri = _asset_b64(ASSETS / "case_bronze_3d.webp", 180, "image/webp")
    gold_uri = _asset_b64(ASSETS / "case_gold_3d.webp", 180, "image/webp")
    galaxy_uri = _asset_b64(ASSETS / "case_galaxy_3d.webp", 180, "image/webp")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=540, initial-scale=1.0" />
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  html, body {{
    width: 540px; height: 960px; overflow: hidden;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    background: #0E1621; color: #F5F5F5;
    -webkit-font-smoothing: antialiased;
  }}
  .phone {{ position: relative; width: 540px; height: 960px; background: #0E1621; overflow: hidden; }}

  /* Subtle Telegram Dark Chat Pattern Overlay */
  .tg-bg {{
    position: absolute; inset: 0;
    background:
      radial-gradient(circle at 20% 25%, rgba(56,189,248,0.06), transparent 42%),
      radial-gradient(circle at 80% 70%, rgba(139,92,246,0.07), transparent 45%),
      #0E1621;
  }}
  .tg-pattern {{
    position: absolute; inset: 0; opacity: 0.045;
    background-image: radial-gradient(#FFFFFF 1px, transparent 1px), radial-gradient(#94A3B8 1px, transparent 1px);
    background-size: 38px 38px; background-position: 0 0, 19px 19px;
  }}

  /* Status bar */
  .status-bar {{
    position: relative; z-index: 40; height: 34px; padding: 0 18px;
    display: flex; align-items: center; justify-content: space-between;
    background: #17212B; font-size: 12.5px; font-weight: 600; color: #E2E8F0;
  }}

  /* Scene 1: Telegram Chats List + Search */
  #scene-search {{
    position: absolute; inset: 34px 0 0 0; z-index: 20;
    background: #17212B; display: flex; flex-direction: column;
  }}
  .tg-top-search {{
    padding: 12px 16px; display: flex; align-items: center; gap: 12px;
    border-bottom: 1px solid #0E1621;
  }}
  .tg-burger {{ width: 22px; height: 14px; display: flex; flex-direction: column; justify-content: space-between; }}
  .tg-burger span {{ display: block; height: 2px; background: #8E9AA8; border-radius: 2px; }}
  .tg-title {{ font-size: 19px; font-weight: 600; color: #FFFFFF; }}
  .search-input-wrap {{
    margin: 12px 16px; padding: 11px 16px; border-radius: 22px;
    background: #242F3D; display: flex; align-items: center; gap: 10px;
    border: 1.5px solid #2B5278; font-size: 15px; color: #FFFFFF;
  }}
  .caret {{ display: inline-block; width: 2px; height: 18px; background: #5EB5F7; vertical-align: middle; margin-left: 1px; }}
  .chat-list {{ flex: 1; }}
  .chat-row {{
    padding: 12px 16px; display: flex; align-items: center; gap: 14px;
    border-bottom: 1px solid rgba(255,255,255,0.04); position: relative;
  }}
  .chat-row.selected {{ background: #202B38; }}
  .av {{
    width: 52px; height: 52px; border-radius: 50%; flex-shrink: 0;
    object-fit: cover; background: #101016; border: 1px solid rgba(255,255,255,0.12);
    display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 18px; color: #fff;
  }}
  .chat-meta {{ flex: 1; min-width: 0; }}
  .chat-name {{ font-size: 15.5px; font-weight: 600; color: #FFFFFF; display: flex; justify-content: space-between; }}
  .chat-time {{ font-size: 12px; color: #6C7883; font-weight: 400; }}
  .chat-sub {{ font-size: 13.5px; color: #5EB5F7; margin-top: 3px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
  .chat-sub.muted {{ color: #7F91A4; }}
  .section-sep {{ padding: 8px 16px; font-size: 12px; font-weight: 600; color: #7F91A4; background: #101923; text-transform: uppercase; letter-spacing: 0.04em; }}

  /* Scene 2: Real Telegram Bot Chat Room */
  #scene-chat {{
    position: absolute; inset: 34px 0 0 0; z-index: 15; display: flex; flex-direction: column;
  }}
  .chat-header {{
    height: 62px; padding: 0 14px; background: #17212B;
    border-bottom: 1px solid #0B121B; display: flex; align-items: center; gap: 12px;
  }}
  .chat-header .av {{ width: 42px; height: 42px; }}
  .chat-header-info {{ flex: 1; }}
  .chat-header-title {{ font-size: 16px; font-weight: 600; color: #FFFFFF; display: flex; align-items: center; gap: 6px; }}
  .verified-tick {{
    display: inline-flex; align-items: center; justify-content: center;
    width: 16px; height: 16px; border-radius: 50%; background: #4EA4F6; color: #fff; font-size: 10px; font-weight: 800;
  }}
  .chat-header-sub {{ font-size: 12.5px; color: #7F91A4; }}
  .chat-messages {{
    flex: 1; padding: 14px 12px; display: flex; flex-direction: column; gap: 10px; overflow: hidden;
  }}
  .msg-row {{ display: flex; align-items: flex-end; gap: 8px; width: 100%; }}
  .msg-row.user {{ justify-content: flex-end; }}
  .msg-av {{ width: 34px; height: 34px; border-radius: 50%; object-fit: cover; flex-shrink: 0; border: 1px solid rgba(255,255,255,0.12); }}
  .bubble-in {{
    background: #182533; color: #F5F5F5; border-radius: 14px 14px 14px 4px;
    padding: 11px 14px; font-size: 13.5px; line-height: 1.44; max-width: 410px;
    box-shadow: 0 1px 2px rgba(0,0,0,0.3);
  }}
  .bubble-out {{
    background: #2B5278; color: #FFFFFF; border-radius: 14px 14px 4px 14px;
    padding: 9px 14px; font-size: 14px; line-height: 1.35; display: inline-flex; align-items: baseline; gap: 10px;
  }}
  .msg-time {{ font-size: 11px; color: rgba(255,255,255,0.58); }}
  .date-pill {{
    align-self: center; padding: 4px 12px; border-radius: 999px;
    background: rgba(24, 37, 51, 0.88); font-size: 12px; font-weight: 600; color: #CBD5E1;
  }}
  .what-card {{
    align-self: center; margin-top: 24px; background: #182533; border-radius: 14px;
    padding: 14px 18px; width: 370px; font-size: 13px; line-height: 1.45; color: #CBD5E1;
  }}
  .what-card h4 {{ color: #FFFFFF; font-size: 14px; margin-bottom: 6px; }}

  /* Authentic Telegram Green & Teal Inline Keyboards */
  .ikb-grid {{ display: flex; flex-direction: column; gap: 5px; margin-top: 6px; width: 410px; margin-left: 42px; }}
  .ikb-row {{ display: flex; gap: 5px; }}
  .ikb-btn {{
    flex: 1; height: 38px; border-radius: 9px; display: flex; align-items: center; justify-content: center;
    gap: 6px; font-size: 12.8px; font-weight: 600; color: #FFFFFF; position: relative;
    background: #2C5E3B;
  }}
  .ikb-btn.teal {{ background: #2D5A73; }}
  .ikb-btn.accent-glow {{ background: #2E7031; box-shadow: inset 0 0 0 1.5px #4ADE80; }}
  .miniapp-icon {{ position: absolute; right: 10px; top: 9px; font-size: 11px; opacity: 0.78; }}

  /* Compose bar matching real screenshot */
  .compose-bar {{
    height: 58px; background: #17212B; border-top: 1px solid #0B121B;
    padding: 0 12px; display: flex; align-items: center; gap: 10px;
  }}
  .menu-pill {{
    background: #336986; color: #FFFFFF; border-radius: 20px; padding: 7px 14px;
    font-size: 13px; font-weight: 600; display: inline-flex; align-items: center; gap: 6px;
  }}
  .compose-text {{ flex: 1; color: #6C7883; font-size: 14px; }}
  .compose-text.typing {{ color: #FFFFFF; }}
  .send-circle {{
    width: 34px; height: 34px; border-radius: 50%; background: #5288C1;
    display: flex; align-items: center; justify-content: center; color: #FFFFFF; font-weight: 700;
  }}

  /* Scene 3 & 4: Telegram Mini App Sheet sliding up inside Telegram */
  #miniapp-sheet {{
    position: absolute; left: 0; right: 0; top: 52px; bottom: 0; z-index: 30;
    background: #F4F4F5; color: #09090B; border-radius: 18px 18px 0 0;
    box-shadow: 0 -10px 40px rgba(0,0,0,0.65); display: flex; flex-direction: column; overflow: hidden;
    transform: translateY(960px);
  }}
  .ma-top {{
    height: 48px; background: #FFFFFF; border-bottom: 1px solid #E4E4E7;
    padding: 0 14px; display: flex; align-items: center; justify-content: space-between;
  }}
  .ma-close {{ font-size: 13px; font-weight: 600; color: #3B82F6; }}
  .ma-title-col {{ text-align: center; }}
  .ma-title {{ font-size: 14px; font-weight: 700; color: #09090B; }}
  .ma-sub {{ font-size: 11px; color: #71717A; }}
  .ma-body {{ flex: 1; padding: 14px; display: flex; flex-direction: column; gap: 12px; overflow: hidden; }}
  .ma-nav {{
    display: flex; justify-content: space-between; align-items: center;
    background: #FFFFFF; border: 1px solid #E4E4E7; border-radius: 12px; padding: 8px 12px;
  }}
  .ma-pills {{ display: flex; gap: 4px; }}
  .ma-pill {{ font-size: 11.5px; font-weight: 600; padding: 5px 10px; border-radius: 999px; color: #52525B; }}
  .ma-pill.active {{ background: #09090B; color: #FFFFFF; }}
  .ma-card {{ background: #FFFFFF; border: 1px solid #E4E4E7; border-radius: 14px; padding: 14px; }}
  .ma-badge-green {{
    display: inline-block; font-size: 10px; font-weight: 700; font-family: Consolas, monospace;
    padding: 3px 8px; border-radius: 999px; background: rgba(16,185,129,0.12); color: #059669;
  }}
  .vid-player {{
    position: relative; height: 300px; border-radius: 12px; overflow: hidden;
    background: linear-gradient(145deg, #18181B, #09090B); color: #FFFFFF; padding: 16px;
    display: flex; flex-direction: column; justify-content: space-between;
  }}
  .scan-laser {{
    position: absolute; left: 0; right: 0; height: 3px; background: #22C55E;
    box-shadow: 0 0 14px #22C55E; z-index: 5;
  }}
  .wm-box {{
    align-self: flex-end; padding: 5px 10px; border-radius: 8px; font-family: Consolas, monospace;
    font-size: 12px; font-weight: 700; background: rgba(250,204,21,0.18); border: 1.5px solid #FACC15; color: #FACC15;
  }}
  .wm-box.cleaned {{
    background: rgba(34,197,94,0.18); border-color: #22C55E; color: #4ADE80;
  }}

  /* Wheel inside Dark Upgrader Card */
  .upgrader-dark {{
    background: #0A0A0A; color: #FFFFFF; border-radius: 16px; padding: 18px;
    display: flex; flex-direction: column; align-items: center; gap: 14px;
  }}
  .wheel-wrap {{ position: relative; width: 220px; height: 220px; }}
  .wheel-ring {{
    position: absolute; inset: 12px; border-radius: 50%;
    background: conic-gradient(#FF5A1F 0deg 72deg, #1A1A20 72deg 360deg);
    display: flex; align-items: center; justify-content: center;
  }}
  .wheel-inner {{
    width: 158px; height: 158px; border-radius: 50%; background: #0A0A0A;
    border: 1px solid rgba(255,255,255,0.1); display: flex; flex-direction: column;
    align-items: center; justify-content: center;
  }}
  .wheel-pointer-wrap {{ position: absolute; inset: 0; pointer-events: none; }}

  /* Scene 5 Finale */
  #scene-finale {{
    position: absolute; inset: 0; z-index: 35; background: rgba(9, 13, 20, 0.96);
    display: none; flex-direction: column; align-items: center; justify-content: center;
    padding: 32px; text-align: center; gap: 18px;
  }}

  /* Cursor / Tap finger indicator */
  #tap-dot {{
    position: absolute; z-index: 50; width: 28px; height: 28px; border-radius: 50%;
    border: 2.5px solid #FFFFFF; background: rgba(255, 90, 31, 0.72);
    box-shadow: 0 0 18px rgba(255, 90, 31, 0.9); transform: translate(-50%, -50%);
    display: none; pointer-events: none;
  }}
</style>
</head>
<body>
<div class="phone">
  <div class="tg-bg"></div>
  <div class="tg-pattern"></div>

  <div class="status-bar">
    <span>01:25</span>
    <span>MonoDeck · Telegram</span>
    <span>5G 100%</span>
  </div>

  <!-- SCENE 1: TELEGRAM CHATS & SEARCH -->
  <div id="scene-search">
    <div class="tg-top-search">
      <div class="tg-burger"><span></span><span></span><span></span></div>
      <div class="tg-title">Telegram</div>
    </div>
    <div class="search-input-wrap">
      <span style="color:#7F91A4;">🔍</span>
      <span id="search-typed"></span><span class="caret" id="search-caret"></span>
    </div>
    <div id="search-default-chats" class="chat-list">
      <div class="chat-row">
        <div class="av" style="background:#336986;">SD</div>
        <div class="chat-meta">
          <div class="chat-name"><span>Saved Messages</span><span class="chat-time">00:40</span></div>
          <div class="chat-sub muted">Video drafts &amp; keys</div>
        </div>
      </div>
      <div class="chat-row">
        <div class="av" style="background:#7C3AED;">YC</div>
        <div class="chat-meta">
          <div class="chat-name"><span>YouTube Creators UZ</span><span class="chat-time">Yesterday</span></div>
          <div class="chat-sub muted">New Shorts upload schedule ready</div>
        </div>
      </div>
    </div>
    <div id="search-results" style="display:none;">
      <div class="section-sep" id="global-search-label">Global search</div>
      <div class="chat-row selected" id="bot-search-row">
        <img class="av" src="{logo_uri}" alt="Mono Deck" />
        <div class="chat-meta">
          <div class="chat-name"><span>Mono Deck Store | Studio</span><span class="chat-time">bot</span></div>
          <div class="chat-sub">@monodeck_app</div>
        </div>
      </div>
    </div>
  </div>

  <!-- SCENE 2: REAL TELEGRAM BOT CHAT -->
  <div id="scene-chat" style="display:none;">
    <div class="chat-header">
      <span style="font-size:20px; color:#8E9AA8;">&#8592;</span>
      <img class="av" src="{logo_uri}" alt="Bot" />
      <div class="chat-header-info">
        <div class="chat-header-title">Mono Deck Store | Studio <span class="verified-tick">&#10003;</span></div>
        <div class="chat-header-sub" id="bot-sub-status">bot</div>
      </div>
      <span style="color:#8E9AA8; font-size:18px;">&#8942;</span>
    </div>

    <div class="chat-messages">
      <div class="what-card" id="what-card">
        <h4>What can this bot do?</h4>
        <div id="what-desc">All-in-one YouTube AI Auto-Post, Watermark Cleaner, 4K Downloader &amp; Telegram Gifts Studio.</div>
      </div>

      <div class="date-pill">November 23</div>

      <div class="msg-row user" id="user-start-msg" style="display:none;">
        <div class="bubble-out">
          <span>/start</span>
          <span class="msg-time">1:25 AM &#10003;&#10003;</span>
        </div>
        <img class="msg-av" src="{user_uri}" alt="User" />
      </div>

      <div id="bot-reply-block" style="display:none;">
        <div class="msg-row">
          <img class="msg-av" src="{logo_uri}" alt="Bot" />
          <div class="bubble-in" id="bot-welcome-bubble"></div>
        </div>
        <div class="ikb-grid" id="bot-inline-kb"></div>
      </div>
    </div>

    <div class="compose-bar">
      <div class="menu-pill">&#9776; Menu</div>
      <div class="compose-text" id="compose-text">Write a message...</div>
      <div class="send-circle">&#10148;</div>
    </div>
  </div>

  <!-- SCENE 3 & 4: TELEGRAM MINI APP DRAWER -->
  <div id="miniapp-sheet">
    <div class="ma-top">
      <span class="ma-close" id="ma-cancel">Close</span>
      <div class="ma-title-col">
        <div class="ma-title">Mono Deck Store | Studio</div>
        <div class="ma-sub">mini app &middot; monodeck.site</div>
      </div>
      <span style="color:#71717A; font-size:16px;">&#8942;</span>
    </div>

    <div class="ma-body">
      <div class="ma-nav">
        <div style="display:flex; align-items:center; gap:8px; font-weight:700; font-size:13px;">
          <img src="{logo_uri}" style="width:22px; height:22px; border-radius:6px;" />
          <span>MonoDeck</span>
        </div>
        <div class="ma-pills">
          <span class="ma-pill active" id="tab-studio">Studio</span>
          <span class="ma-pill" id="tab-cases">Cases</span>
          <span class="ma-pill">NFTs</span>
        </div>
        <div style="font-size:11px; font-weight:700; color:#FF4F18;" id="ma-balance-pill">30,000 UZS</div>
      </div>

      <!-- MiniApp Sub-view 1: Autopost Preview + Watermark Cleaner -->
      <div id="ma-studio-view" style="display:flex; flex-direction:column; gap:10px;">
        <div class="ma-card">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
            <span style="font-weight:700; font-size:15px;">Autopost Queue</span>
            <span class="ma-badge-green">AUTO WATERMARK CLEAN: ON</span>
          </div>
          <div style="display:flex; gap:8px;">
            <div style="flex:1; padding:8px 12px; border:1px solid #D4D4D8; border-radius:10px; font-size:13px; background:#FAFAFA;">Patrick Jane</div>
            <div style="padding:8px 14px; border-radius:10px; background:#FF4F18; color:#fff; font-size:12.5px; font-weight:600;" id="ma-post-btn">Queue Task</div>
          </div>
        </div>

        <div class="vid-player">
          <div style="display:flex; justify-content:space-between; align-items:flex-start;">
            <div>
              <div style="font-size:14.5px; font-weight:700;" id="vid-title">Patrick Jane — Best Deduction #shorts</div>
              <div style="font-size:11.5px; color:#38BDF8; margin-top:2px;">125,400 views &middot; 0:42 &middot; Candidate Preview</div>
            </div>
            <span style="font-size:11px; padding:3px 8px; border-radius:6px; background:rgba(255,255,255,0.12);">1080p</span>
          </div>

          <div style="align-self:center; width:56px; height:56px; border-radius:50%; background:#FF4F18; display:flex; align-items:center; justify-content:center; font-size:20px; box-shadow:0 6px 20px rgba(255,79,24,0.45);">&#9654;</div>

          <div class="scan-laser" id="wm-laser" style="top:60px; display:none;"></div>
          <div class="wm-box" id="wm-badge">@OldWatermark</div>
        </div>

        <div class="ma-card" style="display:flex; justify-content:space-between; align-items:center; padding:10px 14px;">
          <span style="font-size:12.5px; font-weight:600;" id="ma-upload-status">Step: Scanning &amp; removing watermarks...</span>
          <span style="font-size:11.5px; font-family:Consolas, monospace; color:#059669; font-weight:700;" id="ma-task-state">CLEANING</span>
        </div>
      </div>

      <!-- MiniApp Sub-view 2: Mystery Cases + Upgrader Wheel -->
      <div id="ma-cases-view" style="display:none; flex-direction:column; gap:12px;">
        <div style="display:grid; grid-template-columns:repeat(3, 1fr); gap:8px;">
          <div class="ma-card" style="padding:10px; text-align:center;">
            <img src="{bronze_uri}" style="width:58px; height:58px; object-fit:contain;" />
            <div style="font-size:11px; font-weight:700; margin-top:4px;">100 Stars</div>
          </div>
          <div class="ma-card" style="padding:10px; text-align:center;">
            <img src="{gold_uri}" style="width:58px; height:58px; object-fit:contain;" />
            <div style="font-size:11px; font-weight:700; margin-top:4px;">500 Stars</div>
          </div>
          <div class="ma-card" style="padding:10px; text-align:center;">
            <img src="{galaxy_uri}" style="width:58px; height:58px; object-fit:contain;" />
            <div style="font-size:11px; font-weight:700; margin-top:4px;">5,000 Stars</div>
          </div>
        </div>

        <div class="upgrader-dark">
          <div style="font-size:11.5px; font-family:Consolas, monospace; color:#FF5A1F; font-weight:700;">GIFT UPGRADER &middot; UP TO 100x</div>
          <div class="wheel-wrap">
            <div class="wheel-ring">
              <div class="wheel-inner">
                <div style="font-size:34px; font-weight:800; font-family:Consolas, monospace;">5.0x</div>
                <div style="font-size:11px; color:#A1A1AA;">WIN SECTOR 20%</div>
              </div>
            </div>
            <div class="wheel-pointer-wrap" id="wheel-pointer">
              <svg viewBox="0 0 32 38" width="26" height="32" style="display:block; margin:-10px auto 0;">
                <path d="M16 35 L4 8 C3.5 5 5.8 2 9 2 L23 2 C26.2 2 28.5 5 28 8 Z" fill="#FFF" stroke="#0A0A0A" stroke-width="2"/>
                <polygon points="16,32 10.5,11 21.5,11" fill="#FF5A1F"/>
              </svg>
            </div>
          </div>
          <div id="win-banner" style="display:none; width:100%; padding:10px 14px; border-radius:12px; background:rgba(34,197,94,0.16); border:1px solid #22C55E; text-align:center;">
            <div style="font-size:14px; font-weight:800; color:#4ADE80;" id="win-banner-txt">WIN! +150,000 UZS UNLOCKED</div>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- SCENE 5: FINALE -->
  <div id="scene-finale">
    <img src="{logo_uri}" style="width:144px; height:144px; border-radius:32px; box-shadow:0 14px 40px rgba(139,92,246,0.35);" />
    <div style="font-size:13px; font-family:Consolas, monospace; color:#FF5A1F; font-weight:700; letter-spacing:0.08em;" id="fin-kicker">ALL-IN-ONE CREATOR STUDIO</div>
    <div style="font-size:34px; font-weight:800; color:#FFFFFF; line-height:1.1;">Mono Deck Studio</div>
    <div style="font-size:15px; color:#94A3B8; max-width:360px;" id="fin-sub">Open Telegram and launch the bot + web studio in one tap.</div>
    <div style="width:340px; padding:14px 20px; border-radius:16px; background:#17212B; border:1.5px solid #4EA4F6; font-size:21px; font-weight:700; color:#FFFFFF;">@monodeck_app</div>
    <div style="font-size:14px; font-family:Consolas, monospace; color:#5EB5F7;">monodeck.site</div>
    <div style="margin-top:8px; width:340px; padding:16px 24px; border-radius:999px; background:#FF4F18; font-size:18px; font-weight:800; color:#FFFFFF;" id="fin-cta">START IN TELEGRAM</div>
  </div>

  <div id="tap-dot"></div>
</div>

<script>
const COPY = {{
  uz: {{
    global: "Global qidiruv",
    welcome: "<b>Mono Deck Studio ga xush kelibsiz!</b><br><br>• <b>YouTube Auto-Post</b> + avto watermark tozalash<br>• <b>4K Reels &amp; Shorts</b> yuklovchi<br>• <b>Mystery Cases</b> &amp; AI do'koni<br><br><i>Kerakli bo'limni tanlang:</i>",
    btns: [
      [["Web Studio (monodeck.site)", "accent-glow", true]],
      [["Hamyon: HUMO / Uzcard", "teal", false], ["Telegram Stars", "teal", false]],
      [["Mystery Cases & Upgrader", "", false], ["AI Store", "", false]]
    ],
    scanClean: "WATERMARK TOZALANDI (delogo)",
    statusCleaning: "Watermark aniqlanmoqda va tozalanmoqda...",
    statusDone: "YouTube Shorts ga 7GB Cloud orqali joylandi!",
    winTxt: "YUTUQ! 5.0x SOVG'A (+150,000 UZS)",
    finKicker: "HAMMASI BITTA TELEGRAM BOTDA",
    finSub: "YouTube Avto-Post, Watermark Tozalash, Yuklovchi va Cases studiyasi.",
    finCta: "TELEGRAM DA BOSHLASH"
  }},
  en: {{
    global: "Global search",
    welcome: "<b>Welcome to Mono Deck Studio!</b><br><br>• <b>YouTube Auto-Post</b> + Auto Watermark Cleaner<br>• <b>4K Shorts &amp; Reels</b> Downloader<br>• <b>Mystery Cases</b> &amp; AI Keys Store<br><br><i>Select an action below:</i>",
    btns: [
      [["Open Web Studio (monodeck.site)", "accent-glow", true]],
      [["Deposit: HUMO / Card", "teal", false], ["Telegram Stars", "teal", false]],
      [["Cases & Gift Upgrader", "", false], ["AI Store", "", false]]
    ],
    scanClean: "CLEANED (FFmpeg delogo)",
    statusCleaning: "Scanning & stripping watermarks...",
    statusDone: "Uploaded cleanly via 7GB Cloud Worker!",
    winTxt: "WIN! +5.0x GIFT (+150,000 UZS)",
    finKicker: "ALL-IN-ONE TELEGRAM STUDIO",
    finSub: "YouTube Auto-Post, Auto Watermark Cleaner, 4K Downloader &amp; Cases.",
    finCta: "START @MONODECK_APP"
  }}
}};

function renderButtons(btns) {{
  return btns.map(row => `<div class="ikb-row">` + row.map(([lbl, cls, isMa]) =>
    `<div class="ikb-btn ${{cls}}">${{lbl}}${{isMa ? '<span class="miniapp-icon">&#10697;</span>' : ''}}</div>`
  ).join('') + `</div>`).join('');
}}

window.setTimeline = function(t, lang) {{
  const c = COPY[lang] || COPY.en;
  const sSearch = document.getElementById('scene-search');
  const sChat = document.getElementById('scene-chat');
  const sheet = document.getElementById('miniapp-sheet');
  const fin = document.getElementById('scene-finale');
  const tap = document.getElementById('tap-dot');

  tap.style.display = 'none';
  fin.style.display = 'none';

  // Phase 1: 0.0 -> 4.2 Telegram Chat Search -> Tap @monodeck_app -> Open Empty Chat
  if (t < 3.4) {{
    sSearch.style.display = 'flex';
    sChat.style.display = 'none';
    sheet.style.transform = 'translateY(960px)';

    const targetQ = '@monodeck_app';
    const typedLen = Math.min(targetQ.length, Math.floor((t / 1.7) * targetQ.length));
    document.getElementById('search-typed').textContent = targetQ.slice(0, typedLen);
    document.getElementById('search-caret').style.display = (Math.floor(t * 3) % 2 === 0 && t < 2.2) ? 'inline-block' : 'none';

    const showRes = t >= 1.6;
    document.getElementById('search-default-chats').style.display = showRes ? 'none' : 'block';
    document.getElementById('search-results').style.display = showRes ? 'block' : 'none';
    document.getElementById('global-search-label').textContent = c.global;

    if (t >= 2.55 && t < 3.35) {{
      tap.style.display = 'block';
      tap.style.left = '220px'; tap.style.top = '225px';
    }}
    return;
  }}

  // Phase 2: 3.4 -> 9.8 Real Bot Chat -> Type /start -> Receive Welcome Card + Buttons -> Tap Web Studio
  if (t < 9.8) {{
    sSearch.style.display = 'none';
    sChat.style.display = 'flex';
    sheet.style.transform = 'translateY(960px)';

    const lt = t - 3.4;
    const comp = document.getElementById('compose-text');
    const cmd = '/start';
    if (lt < 1.1) {{
      const cl = Math.max(1, Math.min(cmd.length, Math.floor((lt / 0.85) * cmd.length)));
      comp.textContent = cmd.slice(0, cl);
      comp.className = 'compose-text typing';
      document.getElementById('user-start-msg').style.display = 'none';
      document.getElementById('bot-reply-block').style.display = 'none';
      document.getElementById('bot-sub-status').textContent = 'bot';
    }} else {{
      comp.textContent = 'Write a message...';
      comp.className = 'compose-text';
      document.getElementById('user-start-msg').style.display = 'flex';
      if (lt < 2.1) {{
        document.getElementById('bot-sub-status').textContent = 'typing...';
        document.getElementById('bot-reply-block').style.display = 'none';
      }} else {{
        document.getElementById('bot-sub-status').textContent = 'bot';
        document.getElementById('bot-reply-block').style.display = 'block';
        document.getElementById('bot-welcome-bubble').innerHTML = c.welcome;
        document.getElementById('bot-inline-kb').innerHTML = renderButtons(c.btns);
      }}
    }}
    if (lt >= 5.2) {{
      tap.style.display = 'block';
      tap.style.left = '250px'; tap.style.top = '658px';
    }}
    return;
  }}

  // Phase 3: 9.8 -> 15.6 Mini App Sheet Slides Up -> Autopost Preview + Watermark Cleaner
  if (t < 15.6) {{
    sSearch.style.display = 'none';
    sChat.style.display = 'flex';
    const lt = t - 9.8;
    const slide = Math.min(1, lt / 0.45);
    const ty = Math.round((1 - (1 - Math.pow(1 - slide, 3))) * 960);
    sheet.style.transform = `translateY(${{ty}}px)`;

    document.getElementById('tab-studio').className = 'ma-pill active';
    document.getElementById('tab-cases').className = 'ma-pill';
    document.getElementById('ma-studio-view').style.display = 'flex';
    document.getElementById('ma-cases-view').style.display = 'none';
    document.getElementById('ma-balance-pill').textContent = '30,000 UZS';

    const scanProg = Math.max(0, Math.min(1, (lt - 1.2) / 2.6));
    const laser = document.getElementById('wm-laser');
    const wm = document.getElementById('wm-badge');
    if (lt > 1.2 && scanProg < 1.0) {{
      laser.style.display = 'block';
      laser.style.top = `${{Math.round(52 + scanProg * 228)}}px`;
    }} else {{
      laser.style.display = 'none';
    }}

    if (scanProg >= 0.85) {{
      wm.textContent = c.scanClean;
      wm.className = 'wm-box cleaned';
      document.getElementById('ma-upload-status').textContent = c.statusDone;
      document.getElementById('ma-task-state').textContent = 'COMPLETED';
    }} else {{
      wm.textContent = '@OldWatermark';
      wm.className = 'wm-box';
      document.getElementById('ma-upload-status').textContent = c.statusCleaning;
      document.getElementById('ma-task-state').textContent = 'CLEANING';
    }}
    return;
  }}

  // Phase 4: 15.6 -> 20.6 Mini App Cases & Gift Upgrader Wheel
  if (t < 20.6) {{
    sChat.style.display = 'flex';
    sheet.style.transform = 'translateY(0px)';
    document.getElementById('tab-studio').className = 'ma-pill';
    document.getElementById('tab-cases').className = 'ma-pill active';
    document.getElementById('ma-studio-view').style.display = 'none';
    document.getElementById('ma-cases-view').style.display = 'flex';

    const lt = t - 15.6;
    const spinP = Math.min(1, lt / 3.3);
    const easeSpin = 1 - Math.pow(1 - spinP, 4);
    const deg = easeSpin * (360 * 4 + 34);
    document.getElementById('wheel-pointer').style.transform = `rotate(${{deg.toFixed(1)}}deg)`;

    const won = lt >= 3.35;
    document.getElementById('win-banner').style.display = won ? 'block' : 'none';
    document.getElementById('win-banner-txt').textContent = c.winTxt;
    document.getElementById('ma-balance-pill').textContent = won ? '180,000 UZS' : '30,000 UZS';
    return;
  }}

  // Phase 5: 20.6 -> end Telegram Brand Finale
  sChat.style.display = 'flex';
  sheet.style.transform = 'translateY(0px)';
  fin.style.display = 'flex';
  document.getElementById('fin-kicker').textContent = c.finKicker;
  document.getElementById('fin-sub').innerHTML = c.finSub;
  document.getElementById('fin-cta').textContent = c.finCta;
}};
</script>
</body>
</html>"""


def render_frame(t: float, total_dur: float, lang: str) -> Image.Image:
    """Quick RGB check helper for unit tests."""
    return Image.new("RGB", (W, H), (14, 22, 33))


async def _generate_voiceover(lang: str, out_mp3: Path) -> Path:
    el_key = os.getenv("ELEVENLABS_API_KEY", "").strip()
    if lang == "en":
        text = (
            "Open Telegram and search at monodeck_app. "
            "Tap Start to launch Mono Deck Studio: preview and auto-post YouTube Shorts "
            "with automatic watermark removal, 4K downloads, and Gift Upgrader up to 100x. Start free today!"
        )
        voice_id = "IKne3meq5aSn9XLyUdCD"  # Charlie
    else:
        text = (
            "Telegramga kiring va monodeck_app botini qidiring. "
            "Start tugmasini bosing va Mono Deck Studio-ni oching: "
            "videolarni oldindan ko'rib, watermarkni avtomatik tozalab YouTube Shortsga joylash, "
            "4K yuklovchi va Gift Upgrader hammasi Telegram ichida!"
        )
        voice_id = "JBFqnCBsd6RMkjVDRZzb"  # George

    if el_key:
        req = urllib.request.Request(
            f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
            data=json.dumps({
                "text": text,
                "model_id": "eleven_multilingual_v2",
                "voice_settings": {"stability": 0.54, "similarity_boost": 0.80},
            }).encode("utf-8"),
            headers={"xi-api-key": el_key, "Content-Type": "application/json", "Accept": "audio/mpeg"},
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            out_mp3.write_bytes(resp.read())
        print(f"[TTS-{lang.upper()}] ElevenLabs generated {out_mp3.name} ({out_mp3.stat().st_size} bytes)")
        return out_mp3

    raise RuntimeError("ELEVENLABS_API_KEY missing in .env")


def _probe_duration(media_path: Path) -> float:
    res = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(media_path)],
        capture_output=True, text=True, check=True,
    )
    return float(res.stdout.strip())


def _synth_ambient_bed(duration_sec: float, out_wav: Path) -> None:
    sr = 44100
    n = int((duration_sec + 0.5) * sr)
    t = np.linspace(0, n / sr, n, dtype=np.float32)
    pulse = 0.72 + 0.28 * np.sin(2 * np.pi * 2.0 * t)
    sig = (
        0.35 * np.sin(2 * np.pi * 87.31 * t)
        + 0.25 * np.sin(2 * np.pi * 130.81 * t)
        + 0.20 * np.sin(2 * np.pi * 196.00 * t)
        + 0.12 * np.sin(2 * np.pi * 329.63 * t)
    ) * pulse
    beat_phase = (t % 0.5)
    sig += 0.22 * np.exp(-beat_phase * 45.0) * np.sin(2 * np.pi * 65.0 * t)
    fade = int(0.8 * sr)
    sig[:fade] *= np.linspace(0, 1, fade, dtype=np.float32)
    sig[-fade:] *= np.linspace(1, 0, fade, dtype=np.float32)
    pcm = np.clip(sig * 0.22, -0.9, 0.9)
    pcm_i16 = (pcm * 32767.0).astype(np.int16)
    with wave.open(str(out_wav), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(pcm_i16.tobytes())


async def _cdp_call(ws, msg_id: int, method: str, params: dict | None = None) -> dict:
    await ws.send_json({"id": msg_id, "method": method, "params": params or {}})
    while True:
        msg = await ws.receive_json()
        if msg.get("id") == msg_id:
            if "error" in msg:
                raise RuntimeError(f"CDP error {method}: {msg['error']}")
            return msg.get("result", {})


async def build_promo_video_chrome(lang: str, html_path: Path, save_keyframes: bool = False) -> Path:
    voice_mp3 = DOWNLOADS / f"_voice_{lang}.mp3"
    music_wav = DOWNLOADS / f"_music_{lang}.wav"
    log_path = DOWNLOADS / f"_ffmpeg_{lang}.log"
    out_mp4 = DOWNLOADS / f"monodeck_promo_{lang}.mp4"

    await _generate_voiceover(lang, voice_mp3)
    v_dur = _probe_duration(voice_mp3)
    total_dur = max(23.5, v_dur + 1.2)
    _synth_ambient_bed(total_dur, music_wav)
    total_frames = int(total_dur * FPS)

    user_data_dir = Path(tempfile.mkdtemp(prefix="md_chrome_"))
    chrome_proc = subprocess.Popen(
        [
            CHROME_PATH,
            "--headless=new",
            "--remote-debugging-port=0",
            f"--user-data-dir={user_data_dir}",
            "--window-size=540,960",
            "--force-device-scale-factor=2",
            "--hide-scrollbars",
            "--disable-gpu",
            "--no-first-run",
            "--no-default-browser-check",
            html_path.resolve().as_uri(),
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    ff_cmd = [
        "ffmpeg", "-y", "-loglevel", "warning",
        "-f", "image2pipe", "-vcodec", "mjpeg", "-r", str(FPS),
        "-i", "-",
        "-i", str(voice_mp3),
        "-i", str(music_wav),
        "-filter_complex",
        "[1:a]aresample=44100,apad,volume=1.45[v];[2:a]aresample=44100,volume=0.25[m];[v][m]amix=inputs=2:duration=shortest[aout]",
        "-map", "0:v:0", "-map", "[aout]",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-t", f"{total_dur:.2f}", "-movflags", "+faststart",
        str(out_mp4),
    ]

    try:
        dev_port_file = user_data_dir / "DevToolsActivePort"
        for _ in range(80):
            if dev_port_file.exists():
                lines = dev_port_file.read_text(encoding="utf-8", errors="ignore").splitlines()
                if lines and lines[0].strip().isdigit():
                    break
            await asyncio.sleep(0.1)
        port = int(dev_port_file.read_text(encoding="utf-8").splitlines()[0].strip())

        async with aiohttp.ClientSession() as sess:
            async with sess.get(f"http://127.0.0.1:{port}/json/list") as resp:
                targets = await resp.json()
            page_ws_url = next(t["webSocketDebuggerUrl"] for t in targets if t.get("type") == "page")

            key_frames = {int(2.8 * FPS): "s1", int(7.5 * FPS): "s2", int(13.2 * FPS): "s3", int(19.2 * FPS): "s4"} if save_keyframes else {}

            async with sess.ws_connect(page_ws_url, max_msg_size=16 * 1024 * 1024) as ws:
                mid = 1
                await _cdp_call(ws, mid, "Emulation.setDeviceMetricsOverride", {
                    "width": 540, "height": 960, "deviceScaleFactor": 2, "mobile": True
                })
                mid += 1
                await asyncio.sleep(0.4)

                with open(log_path, "wb") as lf:
                    ff_proc = subprocess.Popen(ff_cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=lf)
                    try:
                        for f in range(total_frames):
                            t_sec = f / float(FPS)
                            await _cdp_call(ws, mid, "Runtime.evaluate", {"expression": f"window.setTimeline({t_sec:.4f}, '{lang}')"})
                            mid += 1
                            shot = await _cdp_call(ws, mid, "Page.captureScreenshot", {"format": "jpeg", "quality": 92})
                            mid += 1
                            jpeg_bytes = base64.b64decode(shot["data"])
                            ff_proc.stdin.write(jpeg_bytes)
                            if f in key_frames:
                                Image.open(BytesIO(jpeg_bytes)).save(DOWNLOADS / f"_promo_keyframe_{key_frames[f]}.png")
                    finally:
                        try:
                            ff_proc.stdin.close()
                        except Exception:
                            pass
                    rc = ff_proc.wait()
                    if rc != 0:
                        err_txt = log_path.read_text("utf-8", "ignore")[:400] if log_path.exists() else ""
                        raise RuntimeError(f"FFmpeg failed ({lang}, rc={rc}): {err_txt}")
    finally:
        chrome_proc.terminate()
        try:
            chrome_proc.wait(timeout=3)
        except Exception:
            chrome_proc.kill()
        shutil.rmtree(user_data_dir, ignore_errors=True)
        for tmp in (voice_mp3, music_wav, log_path):
            tmp.unlink(missing_ok=True)

    print(f"[CHROME VIDEO OK] {out_mp4} ({out_mp4.stat().st_size} bytes, {total_dur:.2f}s)")
    return out_mp4


async def main():
    html_file = DOWNLOADS / "_promo_scene.html"
    html_file.write_text(_build_scene_html(), encoding="utf-8")
    try:
        uz = await build_promo_video_chrome("uz", html_file, save_keyframes=True)
        en = await build_promo_video_chrome("en", html_file, save_keyframes=False)
        print("Generated:", uz, en)
    finally:
        html_file.unlink(missing_ok=True)


if __name__ == "__main__":
    asyncio.run(main())
