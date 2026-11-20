/**
 * MonoDeck Shield Captcha - Client Widget SDK
 * (c) 2026 MonoDeck Protection Services
 * 
 * Embed instructions:
 * <div id="botshield-captcha" data-sitekey="YOUR_SITE_KEY" data-theme="light"></div>
 * <script src="/captcha/widget.js" async defer></script>
 */

(function () {
    "use strict";

    // Prevent duplicate initialization
    if (window.BotShieldInitialized) return;
    window.BotShieldInitialized = true;

    // Detect base API URL from script tag or fallback to origin
    var scriptTag = document.currentScript || (function () {
        var scripts = document.getElementsByTagName("script");
        for (var i = 0; i < scripts.length; i++) {
            if (scripts[i].src && scripts[i].src.indexOf("/captcha/widget.js") !== -1) {
                return scripts[i];
            }
        }
        return null;
    })();

    var API_BASE = "";
    if (scriptTag && scriptTag.src) {
        try {
            var urlObj = new URL(scriptTag.src);
            API_BASE = urlObj.origin;
        } catch (e) {
            API_BASE = "";
        }
    }

    var widgetCounter = 0;

    var SAFE_SVG_TAGS = {
        svg: true, path: true, polygon: true, circle: true, rect: true,
        line: true, polyline: true, ellipse: true, g: true
    };
    var SAFE_SVG_ATTRS = {
        viewBox: true, width: true, height: true, fill: true, stroke: true,
        "stroke-width": true, "stroke-linecap": true, "stroke-linejoin": true,
        points: true, d: true, cx: true, cy: true, r: true, rx: true, ry: true,
        x: true, y: true, x1: true, y1: true, x2: true, y2: true
    };
    var BLOCKED_CALLBACKS = {
        eval: true, Function: true, setTimeout: true, setInterval: true,
        execScript: true, alert: true, confirm: true, prompt: true,
        open: true, close: true, fetch: true
    };

    function sanitizeImageSrc(src) {
        if (typeof src !== "string") return "";
        var trimmed = src.trim();
        if (/^data:image\/(png|jpeg|jpg|webp|gif);base64,[A-Za-z0-9+/=\s]+$/i.test(trimmed)) {
            return trimmed;
        }
        if (/^https?:\/\/[^\s"'<>]+$/i.test(trimmed)) {
            return trimmed;
        }
        return "";
    }

    function createSafeSvgNode(svgStr) {
        if (typeof svgStr !== "string" || !svgStr.trim()) return null;
        try {
            var parser = new DOMParser();
            var doc = parser.parseFromString(svgStr, "image/svg+xml");
            if (doc.querySelector("parsererror")) return null;
            var root = doc.documentElement;
            if (!root || root.tagName.toLowerCase() !== "svg") return null;

            function cloneSafe(node) {
                var tag = node.tagName ? node.tagName.toLowerCase() : "";
                if (!SAFE_SVG_TAGS[tag]) return null;
                var el = document.createElementNS("http://www.w3.org/2000/svg", tag);
                if (node.attributes) {
                    for (var i = 0; i < node.attributes.length; i++) {
                        var attr = node.attributes[i];
                        var name = attr.name;
                        if (!SAFE_SVG_ATTRS[name]) continue;
                        var val = String(attr.value || "");
                        if (/javascript:|expression\s*\(|url\s*\(/i.test(val)) continue;
                        el.setAttribute(name, val);
                    }
                }
                for (var c = 0; c < node.childNodes.length; c++) {
                    var child = node.childNodes[c];
                    if (child.nodeType === 1) {
                        var safeChild = cloneSafe(child);
                        if (safeChild) el.appendChild(safeChild);
                    }
                }
                return el;
            }

            return cloneSafe(root);
        } catch (e) {
            return null;
        }
    }

    function resolveSafeCallback(name) {
        if (typeof name !== "string") return null;
        var clean = name.trim();
        if (!/^[A-Za-z_$][A-Za-z0-9_$]*$/.test(clean)) return null;
        if (BLOCKED_CALLBACKS[clean]) return null;
        if (Object.prototype.hasOwnProperty.call(window, clean) && typeof window[clean] === "function") {
            return window[clean];
        }
        return null;
    }

    // High-precision SVGs
    var SVG_ICONS = {
        shield: '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path></svg>',
        check: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>',
        refresh: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 4 23 10 17 10"></polyline><polyline points="1 20 1 14 7 14"></polyline><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path></svg>',
        close: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>',
        arrowRight: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"></polyline></svg>',
        rotate: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67"/></svg>',
        grid: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="7"></rect><rect x="14" y="3" width="7" height="7"></rect><rect x="14" y="14" width="7" height="7"></rect><rect x="3" y="14" width="7" height="7"></rect></svg>',
        lock: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect><path d="M7 11V7a5 5 0 0 1 10 0v4"></path></svg>',
        undo: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="1 4 1 10 7 10"></polyline><path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10"></path></svg>',
        alert: '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>',
        hand: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 11V6a2 2 0 0 0-4 0v5"/><path d="M14 10V4a2 2 0 0 0-4 0v7"/><path d="M10 10.5V6a2 2 0 0 0-4 0v8"/><path d="M18 8a2 2 0 0 1 4 4v4a8 8 0 0 1-8 8h-2c-2.5 0-4.5-1.5-5.5-3.5L4 16.5a2 2 0 0 1 3-2.5l1.5 1.5V11"/></svg>'
    };

    // Inject Scoped Styles (Light & Dark mode aware, Authentic reCAPTCHA styling)
    function injectStyles() {
        if (document.getElementById("botshield-css")) return;
        var style = document.createElement("style");
        style.id = "botshield-css";
        style.textContent = `
            .bsh-widget-container {
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
                display: inline-block;
                user-select: none;
                -webkit-user-select: none;
                box-sizing: border-box;
                position: relative;
                color-scheme: light;
            }
            .bsh-widget-container * {
                box-sizing: border-box;
            }

            /* Authentic Trustworthy Checkbox Trigger (Standard reCAPTCHA / Cloudflare aesthetic) */
            .bsh-trigger-box {
                width: 302px;
                max-width: 100%;
                height: 76px;
                background: #FFFFFF;
                border: 1px solid #D1D5DB;
                border-radius: 8px;
                display: flex;
                align-items: center;
                justify-content: space-between;
                padding: 0 14px;
                cursor: pointer;
                transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
                box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05), 0 4px 10px rgba(0, 0, 0, 0.03);
            }
            .bsh-trigger-box:focus-visible, .bsh-btn-icon:focus-visible, .bsh-btn-submit:focus-visible, .bsh-seq-reset-btn:focus-visible {
                outline: 2px solid #FF5A1F;
                outline-offset: 2px;
            }
            .bsh-btn-icon {
                border: none;
                padding: 0;
            }
            .bsh-btn-submit:disabled {
                opacity: 0.6;
                cursor: not-allowed;
                transform: none !important;
            }
            .bsh-theme-dark .bsh-trigger-box {
                background: #0F172A;
                border-color: #334155;
            }
            .bsh-theme-dark .bsh-trigger-label,
            .bsh-theme-dark .bsh-brand-title {
                color: #F8FAFC;
            }
            .bsh-theme-dark .bsh-brand-sub {
                color: #94A3B8;
            }
            .bsh-theme-dark .bsh-checkbox {
                background: #1E293B;
                border-color: #475569;
            }
            .bsh-theme-dark .bsh-trigger-box.bsh-verified {
                background: rgba(16, 185, 129, 0.14);
                border-color: #10B981;
            }
            .bsh-theme-dark .bsh-trigger-box.bsh-verified .bsh-trigger-label {
                color: #34D399;
            }
            .bsh-theme-dark.bsh-modal-overlay .bsh-modal-card {
                background: #0F172A;
                border-color: #334155;
            }
            .bsh-theme-dark.bsh-modal-overlay .bsh-card-body {
                background: #0F172A;
                color: #F8FAFC;
            }
            .bsh-theme-dark.bsh-modal-overlay .bsh-card-footer,
            .bsh-theme-dark.bsh-modal-overlay .bsh-visual-header,
            .bsh-theme-dark.bsh-modal-overlay .bsh-seq-step-bar {
                background: #1E293B;
                border-color: #334155;
            }
            .bsh-theme-dark.bsh-modal-overlay .bsh-visual-header-left,
            .bsh-theme-dark.bsh-modal-overlay .bsh-footer-info {
                color: #E2E8F0;
            }
            .bsh-theme-dark.bsh-modal-overlay .bsh-slider-track {
                background: #1E293B;
                border-color: #334155;
            }
            .bsh-theme-dark.bsh-modal-overlay .bsh-slider-text {
                color: #94A3B8;
            }
            .bsh-theme-dark.bsh-modal-overlay .bsh-seq-step-pill,
            .bsh-theme-dark.bsh-modal-overlay .bsh-seq-reset-btn {
                background: #0F172A;
                border-color: #334155;
                color: #E2E8F0;
            }
            .bsh-trigger-box:hover {
                border-color: #9CA3AF;
                box-shadow: 0 2px 6px rgba(0, 0, 0, 0.08), 0 6px 14px rgba(0, 0, 0, 0.04);
            }
            .bsh-trigger-box:active {
                transform: translateY(1px);
            }

            .bsh-trigger-left {
                display: flex;
                align-items: center;
                gap: 12px;
            }
            .bsh-checkbox {
                width: 28px;
                height: 28px;
                border-radius: 4px;
                border: 2px solid #C4C4C4;
                background: #F9FAFB;
                display: flex;
                align-items: center;
                justify-content: center;
                transition: all 0.2s ease;
                color: transparent;
                flex-shrink: 0;
            }
            .bsh-trigger-box:hover .bsh-checkbox {
                border-color: #0A0A0A;
            }
            .bsh-trigger-label {
                font-size: 14px;
                font-weight: 500;
                color: #1F2937;
                letter-spacing: -0.2px;
            }

            .bsh-trigger-brand {
                display: flex;
                flex-direction: column;
                align-items: flex-end;
                gap: 2px;
            }
            .bsh-brand-badge {
                display: flex;
                align-items: center;
                gap: 4px;
                color: #0A0A0A;
            }
            .bsh-brand-title {
                font-size: 11px;
                font-weight: 700;
                color: #111827;
                letter-spacing: 0.2px;
            }
            .bsh-brand-sub {
                font-size: 9px;
                color: #6B7280;
                display: flex;
                align-items: center;
                gap: 3px;
            }

            /* Success Verified State */
            .bsh-trigger-box.bsh-verified {
                border-color: #10B981;
                background: #F0FDF4;
                cursor: default;
                box-shadow: 0 1px 4px rgba(16, 185, 129, 0.15);
            }
            .bsh-trigger-box.bsh-verified .bsh-checkbox {
                background: #10B981;
                border-color: #10B981;
                color: #FFFFFF;
            }
            .bsh-trigger-box.bsh-verified .bsh-trigger-label {
                color: #047857;
                font-weight: 600;
            }

            /* Loading Spinner inside Checkbox */
            .bsh-spinner {
                width: 20px;
                height: 20px;
                border: 2px solid #E5E7EB;
                border-top-color: #FF5A1F;
                border-radius: 50%;
                animation: bsh-spin 0.75s linear infinite;
            }
            @keyframes bsh-spin {
                to { transform: rotate(360deg); }
            }

            /* Modal Overlay & Card (Clean, Trustworthy, Light Theme Default) */
            .bsh-modal-overlay {
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                width: 100%;
                height: 100%;
                background: rgba(15, 23, 42, 0.65);
                backdrop-filter: blur(6px);
                -webkit-backdrop-filter: blur(6px);
                z-index: 999999;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 16px;
                box-sizing: border-box;
                animation: bsh-fade-in 0.2s cubic-bezier(0.16, 1, 0.3, 1);
            }
            @keyframes bsh-fade-in {
                from { opacity: 0; }
                to { opacity: 1; }
            }

            .bsh-modal-card {
                width: 396px;
                max-width: min(396px, calc(100vw - 24px));
                margin: auto;
                background: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 16px;
                box-shadow: 0 20px 45px -10px rgba(0, 0, 0, 0.25), 0 0 1px rgba(0,0,0,0.1);
                overflow: hidden;
                display: flex;
                flex-direction: column;
                box-sizing: border-box;
                animation: bsh-pop-in 0.22s cubic-bezier(0.16, 1, 0.3, 1);
            }
            @keyframes bsh-pop-in {
                from { transform: scale(0.96); opacity: 0; }
                to { transform: scale(1); opacity: 1; }
            }

            /* Modal Header with User Website Theme Accent (#FF5A1F) */
            .bsh-card-header {
                padding: 14px 16px;
                background: #0A0A0A;
                color: #FFFFFF;
                display: flex;
                align-items: center;
                justify-content: space-between;
            }
            .bsh-card-header-left {
                display: flex;
                flex-direction: column;
                gap: 2px;
            }
            .bsh-card-title {
                font-size: 13px;
                font-weight: 700;
                color: #FFFFFF;
                display: flex;
                align-items: center;
                gap: 6px;
                letter-spacing: 0.2px;
            }
            .bsh-card-instruction {
                font-size: 12px;
                color: rgba(255, 255, 255, 0.9);
                font-weight: 500;
            }
            .bsh-card-actions {
                display: flex;
                align-items: center;
                gap: 6px;
            }
            .bsh-btn-icon {
                width: 28px;
                height: 28px;
                border-radius: 6px;
                background: rgba(255, 255, 255, 0.15);
                color: #FFFFFF;
                display: flex;
                align-items: center;
                justify-content: center;
                cursor: pointer;
                transition: all 0.15s ease;
            }
            .bsh-btn-icon:hover {
                background: rgba(255, 255, 255, 0.3);
            }

            /* Challenge Body */
            .bsh-card-body {
                padding: 16px;
                display: flex;
                flex-direction: column;
                align-items: center;
                min-height: 200px;
                position: relative;
                background: #FFFFFF;
            }

            /* Error Toast Notification */
            .bsh-error-toast {
                display: flex;
                align-items: center;
                gap: 8px;
                background: #FEF2F2;
                border: 1px solid #FCA5A5;
                color: #B91C1C;
                font-size: 11px;
                font-weight: 600;
                padding: 6px 10px;
                border-radius: 6px;
                margin-bottom: 8px;
                animation: bsh-toast-in 0.2s cubic-bezier(0.16, 1, 0.3, 1);
                box-sizing: border-box;
                width: 100%;
                max-width: 320px;
            }
            .bsh-error-toast-icon {
                display: inline-flex;
                align-items: center;
                flex-shrink: 0;
            }
            @keyframes bsh-toast-in {
                from { opacity: 0; transform: translateY(-4px); }
                to { opacity: 1; transform: translateY(0); }
            }

            /* Visual Instruction Header (Icons for target shape or steps) */
            .bsh-visual-header {
                width: 100%;
                background: #F8FAFC;
                border: 1px solid #E2E8F0;
                border-radius: 8px;
                padding: 8px 12px;
                margin-bottom: 12px;
                display: flex;
                align-items: center;
                justify-content: space-between;
                gap: 8px;
            }
            .bsh-visual-header-left {
                display: flex;
                align-items: center;
                gap: 8px;
                font-size: 12px;
                font-weight: 600;
                color: #1E293B;
            }

            /* Variety 1: Slider Styles */
            .bsh-slider-stage {
                position: relative;
                width: 320px;
                max-width: 100%;
                aspect-ratio: 320 / 170;
                border-radius: 10px;
                overflow: hidden;
                box-shadow: 0 2px 10px rgba(0,0,0,0.12);
                border: 1px solid #E2E8F0;
            }
            .bsh-slider-bg {
                width: 100%;
                height: 100%;
                display: block;
                pointer-events: none;
            }
            .bsh-slider-piece {
                position: absolute;
                top: 0;
                left: 0;
                cursor: grab;
                z-index: 10;
                filter: drop-shadow(0 3px 6px rgba(0,0,0,0.45));
                transition: transform 0.05s ease;
            }
            .bsh-slider-piece:active {
                cursor: grabbing;
            }
            .bsh-slider-track {
                width: 320px;
                max-width: 100%;
                height: 44px;
                background: #F1F5F9;
                border: 1px solid #CBD5E1;
                border-radius: 22px;
                margin-top: 14px;
                position: relative;
                display: flex;
                align-items: center;
                padding: 3px;
            }
            .bsh-slider-fill {
                position: absolute;
                left: 0;
                top: 0;
                bottom: 0;
                background: linear-gradient(90deg, rgba(255, 90, 31, 0.14), rgba(255, 90, 31, 0.28));
                border-radius: 22px;
                pointer-events: none;
                width: 0px;
            }
            .bsh-slider-thumb {
                width: 38px;
                height: 38px;
                border-radius: 19px;
                background: #0A0A0A;
                display: flex;
                align-items: center;
                justify-content: center;
                color: #FFFFFF;
                cursor: grab;
                box-shadow: 0 2px 8px rgba(10, 10, 10, 0.22);
                transition: transform 0.1s ease;
                position: absolute;
                left: 3px;
                z-index: 15;
            }
            .bsh-slider-thumb:hover {
                box-shadow: 0 4px 12px rgba(255, 90, 31, 0.35);
            }
            .bsh-slider-thumb:active {
                cursor: grabbing;
                transform: scale(1.05);
            }
            .bsh-slider-text {
                position: absolute;
                width: 100%;
                text-align: center;
                font-size: 11px;
                font-weight: 500;
                color: #64748B;
                pointer-events: none;
            }

            /* Variety 2: 9-Grid Styles */
            .bsh-grid-container {
                display: grid;
                grid-template-columns: repeat(3, minmax(0, 94px));
                gap: 8px;
                max-width: 100%;
            }
            .bsh-grid-tile {
                width: 100%;
                aspect-ratio: 1 / 1;
                max-width: 94px;
                max-height: 94px;
                border-radius: 8px;
                overflow: hidden;
                position: relative;
                cursor: pointer;
                border: 2px solid #E2E8F0;
                transition: all 0.15s cubic-bezier(0.16, 1, 0.3, 1);
                background: #F8FAFC;
            }
            .bsh-grid-tile img {
                width: 100%;
                height: 100%;
                display: block;
                pointer-events: none;
            }
            .bsh-grid-tile:hover {
                border-color: #FF5A1F;
                transform: scale(1.02);
            }
            .bsh-grid-tile.bsh-selected {
                border-color: #FF5A1F;
                box-shadow: 0 0 10px rgba(255, 90, 31, 0.28);
                transform: scale(0.96);
            }
            .bsh-tile-check {
                position: absolute;
                top: 6px;
                right: 6px;
                width: 22px;
                height: 22px;
                border-radius: 50%;
                background: #FF5A1F;
                color: #FFFFFF;
                display: none;
                align-items: center;
                justify-content: center;
                box-shadow: 0 2px 4px rgba(0,0,0,0.3);
            }
            .bsh-grid-tile.bsh-selected .bsh-tile-check {
                display: flex;
            }

            /* Variety 3: Dial Rotate Styles */
            .bsh-rotate-wrap {
                display: flex;
                flex-direction: column;
                align-items: center;
                gap: 12px;
                position: relative;
                padding-top: 10px;
            }
            .bsh-rotate-stage {
                position: relative;
                width: 170px;
                height: 170px;
                display: flex;
                align-items: center;
                justify-content: center;
            }
            .bsh-rotate-target-pin {
                position: absolute;
                top: -9px;
                left: 50%;
                transform: translateX(-50%);
                width: 20px;
                height: 16px;
                background: #FF5A1F;
                color: #FFFFFF;
                border-radius: 4px;
                font-size: 10px;
                font-weight: 800;
                display: flex;
                align-items: center;
                justify-content: center;
                box-shadow: 0 2px 6px rgba(255, 90, 31, 0.45);
                z-index: 6;
                pointer-events: none;
            }
            .bsh-rotate-disk {
                width: 170px;
                height: 170px;
                border-radius: 50%;
                border: 2px solid #0A0A0A;
                box-shadow: 0 4px 16px rgba(10, 10, 10, 0.10);
                display: flex;
                align-items: center;
                justify-content: center;
                position: relative;
                background: #FFFFFF;
                overflow: hidden;
                cursor: grab;
                touch-action: none;
            }
            .bsh-rotate-nudge {
                width: 28px;
                height: 28px;
                border-radius: 6px;
                border: 1px solid #CBD5E1;
                background: #FFFFFF;
                color: #0F172A;
                font-size: 13px;
                font-weight: 700;
                display: inline-flex;
                align-items: center;
                justify-content: center;
                cursor: pointer;
                transition: all 0.15s ease;
                flex-shrink: 0;
            }
            .bsh-rotate-nudge:hover {
                border-color: #FF5A1F;
                color: #FF5A1F;
            }
            .bsh-theme-dark.bsh-modal-overlay .bsh-rotate-nudge {
                background: #1E293B;
                border-color: #334155;
                color: #F8FAFC;
            }
            .bsh-rotate-disk:active {
                cursor: grabbing;
            }
            .bsh-rotate-img {
                width: 100%;
                height: 100%;
                display: block;
                transition: transform 0.05s ease;
                pointer-events: none;
            }
            .bsh-rotate-controls {
                display: flex;
                align-items: center;
                gap: 12px;
                width: 290px;
                max-width: 100%;
                justify-content: space-between;
            }
            .bsh-dial-slider {
                flex: 1;
                -webkit-appearance: none;
                background: #E2E8F0;
                height: 6px;
                border-radius: 3px;
                outline: none;
            }
            .bsh-dial-slider::-webkit-slider-thumb {
                -webkit-appearance: none;
                appearance: none;
                width: 24px;
                height: 24px;
                border-radius: 50%;
                background: #0A0A0A;
                cursor: pointer;
                box-shadow: 0 2px 6px rgba(10, 10, 10, 0.25);
            }
            .bsh-dial-badge {
                font-family: -apple-system, monospace;
                font-size: 12px;
                font-weight: 700;
                color: #FF5A1F;
                background: #FFF2EC;
                border: 1px solid #FFD6C7;
                padding: 2px 8px;
                border-radius: 6px;
                min-width: 44px;
                text-align: center;
            }

            /* Variety 4: Sequence Styles (Visual 1-2-3 Badges with Icons) */
            .bsh-seq-container {
                display: flex;
                flex-direction: column;
                align-items: center;
                gap: 8px;
                width: 100%;
                box-sizing: border-box;
            }
            .bsh-seq-step-bar {
                width: 320px;
                max-width: 100%;
                box-sizing: border-box;
                background: #F8FAFC;
                border: 1px solid #E2E8F0;
                border-radius: 8px;
                padding: 4px 6px;
                display: flex;
                align-items: center;
                justify-content: space-between;
                gap: 4px;
            }
            .bsh-seq-steps-list {
                display: flex;
                align-items: center;
                gap: 3px;
                flex: 1;
                min-width: 0;
            }
            .bsh-seq-step-pill {
                display: inline-flex;
                align-items: center;
                gap: 3px;
                background: #FFFFFF;
                border: 1px solid #CBD5E1;
                padding: 2px 5px;
                border-radius: 6px;
                font-size: 10px;
                font-weight: 600;
                color: #334155;
                white-space: nowrap;
                box-shadow: 0 1px 2px rgba(0,0,0,0.03);
                min-width: 0;
            }
            .bsh-seq-step-pill svg {
                width: 12px;
                height: 12px;
                flex-shrink: 0;
            }
            .bsh-seq-step-name {
                font-size: 10px;
                white-space: nowrap;
            }
            .bsh-seq-step-num {
                width: 15px;
                height: 15px;
                border-radius: 50%;
                background: #FF5A1F;
                color: #FFFFFF;
                display: inline-flex;
                align-items: center;
                justify-content: center;
                font-size: 9px;
                font-weight: 700;
                flex-shrink: 0;
            }
            .bsh-seq-arrow {
                color: #94A3B8;
                font-size: 9px;
                flex-shrink: 0;
            }
            .bsh-seq-reset-btn {
                background: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 6px;
                color: #64748B;
                font-size: 10px;
                font-weight: 600;
                display: inline-flex;
                align-items: center;
                gap: 3px;
                padding: 2px 6px;
                cursor: pointer;
                flex-shrink: 0;
                white-space: nowrap;
                transition: all 0.15s ease;
            }
            .bsh-seq-reset-btn:hover {
                background: #FEE2E2;
                border-color: #FCA5A5;
                color: #DC2626;
            }

            .bsh-seq-canvas-wrap {
                position: relative;
                width: 320px;
                aspect-ratio: 320 / 180;
                max-width: 100%;
                border-radius: 10px;
                overflow: hidden;
                border: 1px solid #CBD5E1;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                cursor: crosshair;
                user-select: none;
                -webkit-user-select: none;
                touch-action: none;
            }
            .bsh-seq-bg {
                width: 100%;
                height: 100%;
                display: block;
                pointer-events: none;
            }
            .bsh-seq-badge {
                position: absolute;
                width: 28px;
                height: 28px;
                border-radius: 50%;
                background: #FF5A1F;
                color: #FFFFFF;
                font-weight: 700;
                font-size: 14px;
                display: flex;
                align-items: center;
                justify-content: center;
                transform: translate(-50%, -50%) scale(0);
                box-shadow: 0 2px 8px rgba(10, 10, 10, 0.28);
                animation: bsh-badge-pop 0.22s cubic-bezier(0.16, 1, 0.3, 1) forwards;
                pointer-events: none;
                border: 2px solid #FFFFFF;
            }
            @keyframes bsh-badge-pop {
                to { transform: translate(-50%, -50%) scale(1); }
            }

            /* Action Footer */
            .bsh-card-footer {
                padding: 12px 16px 14px 16px;
                width: 100%;
                display: flex;
                align-items: center;
                justify-content: space-between;
                border-top: 1px solid #F1F5F9;
                background: #F8FAFC;
            }
            .bsh-footer-info {
                display: flex;
                align-items: center;
                gap: 5px;
                font-size: 11px;
                color: #64748B;
            }
            .bsh-btn-submit {
                height: 36px;
                padding: 0 20px;
                border-radius: 8px;
                border: none;
                background: #0A0A0A;
                color: #FFFFFF;
                font-weight: 600;
                font-size: 13px;
                display: flex;
                align-items: center;
                gap: 6px;
                cursor: pointer;
                transition: all 0.15s ease;
                box-shadow: 0 2px 6px rgba(10, 10, 10, 0.2);
            }
            .bsh-btn-submit:hover {
                transform: translateY(-1px);
                background: #FF5A1F;
                box-shadow: 0 4px 12px rgba(255, 90, 31, 0.32);
            }
            .bsh-btn-submit:active {
                transform: translateY(1px);
            }

            /* Shake animation for errors */
            .bsh-shake {
                animation: bsh-shake-anim 0.35s ease-in-out;
            }
            @keyframes bsh-shake-anim {
                0%, 100% { transform: translateX(0); }
                20%, 60% { transform: translateX(-6px); }
                40%, 80% { transform: translateX(6px); }
            }
        `;
        document.head.appendChild(style);
    }

    // Main Widget Controller
    function BotShieldInstance(container, options) {
        this.container = container;
        this.options = options || {};
        this.sitekey = this.options.sitekey || container.getAttribute("data-sitekey") || "demo_key";
        this.type = this.options.type || container.getAttribute("data-type") || "auto";
        this.theme = (this.options.theme || container.getAttribute("data-theme") || "light").toLowerCase();
        this.onSuccess = (typeof this.options.onSuccess === "function")
            ? this.options.onSuccess
            : resolveSafeCallback(container.getAttribute("data-callback"));
        this.isVerified = false;
        this.isSubmitting = false;
        this.token = null;
        this.modal = null;
        this.challenge = null;
        this.startTime = 0;
        this.trajectory = [];
        this.clicks = [];
        this._requestSeq = 0;
        this._pendingTimers = [];
        this._activeCleanups = [];
        this._escListener = null;

        this.init();
    }

    BotShieldInstance.prototype._trackTimer = function (fn, delayMs) {
        var self = this;
        var tid = setTimeout(function () {
            self._pendingTimers = self._pendingTimers.filter(function (id) { return id !== tid; });
            fn();
        }, delayMs);
        this._pendingTimers.push(tid);
        return tid;
    };

    BotShieldInstance.prototype._clearModalActivity = function () {
        this._pendingTimers.forEach(function (tid) { clearTimeout(tid); });
        this._pendingTimers = [];
        this._activeCleanups.forEach(function (fn) {
            try { fn(); } catch (e) {}
        });
        this._activeCleanups = [];
    };

    BotShieldInstance.prototype.init = function () {
        var self = this;
        injectStyles();
        this.closeModal();

        this.isVerified = false;
        this.isSubmitting = false;
        this.token = null;
        this.challenge = null;
        this.startTime = 0;
        this.trajectory = [];
        this.clicks = [];

        this.container.classList.add("bsh-widget-container");
        this.container.classList.toggle("bsh-theme-dark", this.theme === "dark");

        widgetCounter += 1;
        this.container.innerHTML = `
            <div class="bsh-trigger-box" id="bsh-trigger-${widgetCounter}" role="button" tabindex="0" aria-label="Men insonman — BotShield tekshiruvi">
                <div class="bsh-trigger-left">
                    <div class="bsh-checkbox">
                        ${SVG_ICONS.check}
                    </div>
                    <span class="bsh-trigger-label">Men insonman</span>
                </div>
                <div class="bsh-trigger-brand">
                    <div class="bsh-brand-badge">
                        ${SVG_ICONS.shield}
                        <span class="bsh-brand-title">BotShield</span>
                    </div>
                    <div class="bsh-brand-sub">
                        ${SVG_ICONS.lock}
                        <span>Xavfsizlik tizimi</span>
                    </div>
                </div>
            </div>
            <input type="hidden" name="botshield_token" value="" />
        `;

        this.triggerBox = this.container.querySelector(".bsh-trigger-box");
        this.hiddenInput = this.container.querySelector('input[name="botshield_token"]');

        function activateTrigger() {
            if (self.isVerified) return;
            self.openChallengeModal();
        }

        this.triggerBox.addEventListener("click", activateTrigger);
        this.triggerBox.addEventListener("keydown", function (e) {
            if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                activateTrigger();
            }
        });
    };

    BotShieldInstance.prototype.openChallengeModal = function () {
        var self = this;
        if (this.modal) return;

        var overlay = document.createElement("div");
        overlay.className = "bsh-modal-overlay" + (this.theme === "dark" ? " bsh-theme-dark" : "");
        overlay.setAttribute("role", "dialog");
        overlay.setAttribute("aria-modal", "true");
        overlay.setAttribute("aria-label", "BotShield Xavfsizlik Tekshiruvi");
        overlay.innerHTML = `
            <div class="bsh-modal-card">
                <div class="bsh-card-header">
                    <div class="bsh-card-header-left">
                        <div class="bsh-card-title">
                            ${SVG_ICONS.shield}
                            <span>BotShield Xavfsizlik Tekshiruvi</span>
                        </div>
                        <div class="bsh-card-instruction" id="bsh-instr-text">Xavfsizlik tekshiruvi yuklanmoqda...</div>
                    </div>
                    <div class="bsh-card-actions">
                        <button type="button" class="bsh-btn-icon" id="bsh-btn-refresh" title="Yangilash" aria-label="Tekshiruvni yangilash">
                            ${SVG_ICONS.refresh}
                        </button>
                        <button type="button" class="bsh-btn-icon" id="bsh-btn-close" title="Yopish" aria-label="Oyna yopish">
                            ${SVG_ICONS.close}
                        </button>
                    </div>
                </div>
                <div class="bsh-card-body" id="bsh-body">
                    <div class="bsh-spinner"></div>
                </div>
                <div class="bsh-card-footer" id="bsh-footer" style="display: none;">
                    <div class="bsh-footer-info">
                        ${SVG_ICONS.lock}
                        <span>BotShield AI Himoyasi</span>
                    </div>
                    <button type="button" class="bsh-btn-submit" id="bsh-btn-verify">
                        <span>Tasdiqlash</span>
                        ${SVG_ICONS.arrowRight}
                    </button>
                </div>
            </div>
        `;

        document.body.appendChild(overlay);
        this.modal = overlay;

        overlay.querySelector("#bsh-btn-close").addEventListener("click", function () {
            self.closeModal();
        });

        overlay.addEventListener("click", function (e) {
            if (e.target === overlay) {
                self.closeModal();
            }
        });

        this._escListener = function (e) {
            if (e.key === "Escape") {
                self.closeModal();
            }
        };
        window.addEventListener("keydown", this._escListener);

        overlay.querySelector("#bsh-btn-refresh").addEventListener("click", function () {
            self.fetchChallenge();
        });

        this.fetchChallenge();
    };

    BotShieldInstance.prototype.closeModal = function () {
        this._requestSeq += 1;
        this.isSubmitting = false;
        this._clearModalActivity();
        if (this._escListener) {
            window.removeEventListener("keydown", this._escListener);
            this._escListener = null;
        }
        if (this.modal) {
            if (this.modal.parentNode) {
                this.modal.parentNode.removeChild(this.modal);
            }
            this.modal = null;
        }
    };

    BotShieldInstance.prototype._renderErrorInBody = function (body, message) {
        var self = this;
        body.replaceChildren();
        var wrap = document.createElement("div");
        wrap.style.cssText = "display:flex; flex-direction:column; align-items:center; gap:12px; text-align:center; padding:16px 8px;";

        var msgEl = document.createElement("div");
        msgEl.style.cssText = "color: #DC2626; font-size: 13px; font-weight: 600;";
        msgEl.textContent = String(message || "Yuklab bo'lmadi");

        var retryBtn = document.createElement("button");
        retryBtn.type = "button";
        retryBtn.className = "bsh-btn-submit";
        retryBtn.textContent = "Qayta urinish";
        retryBtn.addEventListener("click", function () {
            self.fetchChallenge();
        });

        wrap.append(msgEl, retryBtn);
        body.appendChild(wrap);
    };

    BotShieldInstance.prototype.fetchChallenge = function () {
        var self = this;
        if (!this.modal) return;
        this._clearModalActivity();
        this.isSubmitting = false;

        var seq = ++this._requestSeq;
        var body = this.modal.querySelector("#bsh-body");
        var footer = this.modal.querySelector("#bsh-footer");
        var instrText = this.modal.querySelector("#bsh-instr-text");
        var verifyBtn = footer.querySelector("#bsh-btn-verify");
        if (verifyBtn) verifyBtn.disabled = false;

        body.replaceChildren();
        var spinner = document.createElement("div");
        spinner.className = "bsh-spinner";
        body.appendChild(spinner);

        footer.style.display = "none";
        instrText.textContent = "Tekshiruv yuklanmoqda...";

        fetch(API_BASE + "/api/v1/captcha/create", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ sitekey: this.sitekey, type: this.type })
        })
        .then(function (res) {
            return res.text().then(function (txt) {
                try {
                    return { ok: res.ok, status: res.status, data: JSON.parse(txt) };
                } catch (e) {
                    return { ok: false, status: res.status, data: { ok: false, message: "Server javobi noto'g'ri (HTTP " + res.status + ")" } };
                }
            });
        })
        .then(function (res) {
            if (!self.modal || seq !== self._requestSeq) return;
            var data = res.data;
            if (!res.ok || !data || !data.ok) {
                self._renderErrorInBody(body, "Xatolik: " + ((data && data.message) || "Yuklab bo'lmadi"));
                return;
            }
            self.challenge = data;
            self.renderChallenge(data);
        })
        .catch(function () {
            if (!self.modal || seq !== self._requestSeq) return;
            self._renderErrorInBody(body, "Serverga ulanish xatosi");
        });
    };

    BotShieldInstance.prototype.renderChallenge = function (challenge) {
        var self = this;
        if (!this.modal) return;
        var body = this.modal.querySelector("#bsh-body");
        var footer = this.modal.querySelector("#bsh-footer");
        var instrText = this.modal.querySelector("#bsh-instr-text");

        this.startTime = Date.now();
        this.trajectory = [];
        this.clicks = [];
        body.replaceChildren();

        var p = challenge.payload || {};

        if (challenge.type === "slider") {
            instrText.textContent = "Pazlni bo'sh joyga to'g'ri keltiring";
            footer.style.display = "none"; // Submits automatically on release

            var stage = document.createElement("div");
            stage.className = "bsh-slider-stage";
            stage.id = "bsh-slider-stage";

            var bgImg = document.createElement("img");
            bgImg.className = "bsh-slider-bg";
            bgImg.alt = "Captcha background";
            bgImg.src = sanitizeImageSrc(p.bg_image);

            var logicalW = Number(p.width) || 320;
            var logicalH = Number(p.height) || 170;
            var pieceW = Number(p.piece_width) || 46;
            var pieceH = Number(p.piece_height) || 46;
            var pieceY = Math.max(0, Math.min(logicalH - pieceH, Number(p.y) || 0));
            var pieceImg = document.createElement("img");
            pieceImg.className = "bsh-slider-piece";
            pieceImg.id = "bsh-slider-piece";
            pieceImg.alt = "Puzzle piece";
            pieceImg.src = sanitizeImageSrc(p.piece_image);
            pieceImg.style.width = ((pieceW / logicalW) * 100).toFixed(4) + "%";
            pieceImg.style.height = ((pieceH / logicalH) * 100).toFixed(4) + "%";
            pieceImg.style.top = ((pieceY / logicalH) * 100).toFixed(4) + "%";
            pieceImg.style.left = "0px";

            stage.append(bgImg, pieceImg);

            var track = document.createElement("div");
            track.className = "bsh-slider-track";
            track.id = "bsh-slider-track";

            var fill = document.createElement("div");
            fill.className = "bsh-slider-fill";
            fill.id = "bsh-slider-fill";

            var thumb = document.createElement("div");
            thumb.className = "bsh-slider-thumb";
            thumb.id = "bsh-slider-thumb";
            var arrowSvg = createSafeSvgNode(SVG_ICONS.arrowRight);
            if (arrowSvg) thumb.appendChild(arrowSvg);

            var trackText = document.createElement("span");
            trackText.className = "bsh-slider-text";
            trackText.textContent = "Tutqichni o'ngga suring";

            track.append(fill, thumb, trackText);
            body.append(stage, track);

            self.setupSliderEvents(p);

        } else if (challenge.type === "grid") {
            instrText.textContent = p.instruction || p.prompt || "Mos kataklarni tanlang";
            footer.style.display = "flex";

            var visualHeader = document.createElement("div");
            visualHeader.className = "bsh-visual-header";

            var headerLeft = document.createElement("div");
            headerLeft.className = "bsh-visual-header-left";

            if (p.target_icon || p.target_name) {
                var targetWrap = document.createElement("div");
                targetWrap.style.cssText = "display:inline-flex; align-items:center; gap:6px;";
                var targetSvg = createSafeSvgNode(p.target_icon);
                if (targetSvg) targetWrap.appendChild(targetSvg);
                var nameSpan = document.createElement("span");
                var nameBold = document.createElement("b");
                nameBold.textContent = String(p.target_name || "");
                nameSpan.appendChild(nameBold);
                targetWrap.appendChild(nameSpan);
                headerLeft.appendChild(targetWrap);
            }

            var hintSpan = document.createElement("span");
            hintSpan.style.cssText = "font-size: 11px; color: #64748B;";
            hintSpan.textContent = "Mos kataklarni bosing";
            visualHeader.append(headerLeft, hintSpan);

            var gridContainer = document.createElement("div");
            gridContainer.className = "bsh-grid-container";
            gridContainer.id = "bsh-grid";

            var tileList = Array.isArray(p.tiles) ? p.tiles : [];
            var selectedIndices = [];

            tileList.forEach(function (tileSrc, idx) {
                var tile = document.createElement("div");
                tile.className = "bsh-grid-tile";
                tile.setAttribute("data-idx", String(idx));
                tile.setAttribute("role", "checkbox");
                tile.setAttribute("aria-checked", "false");
                tile.setAttribute("tabindex", "0");

                var tImg = document.createElement("img");
                tImg.alt = "Captcha tile " + (idx + 1);
                tImg.src = sanitizeImageSrc(tileSrc);

                var checkDiv = document.createElement("div");
                checkDiv.className = "bsh-tile-check";
                var checkSvg = createSafeSvgNode(SVG_ICONS.check);
                if (checkSvg) checkDiv.appendChild(checkSvg);

                tile.append(tImg, checkDiv);

                function toggleTile() {
                    if (tile.classList.contains("bsh-selected")) {
                        tile.classList.remove("bsh-selected");
                        tile.setAttribute("aria-checked", "false");
                        selectedIndices = selectedIndices.filter(function (x) { return x !== idx; });
                    } else {
                        tile.classList.add("bsh-selected");
                        tile.setAttribute("aria-checked", "true");
                        selectedIndices.push(idx);
                    }
                    self.clicks.push({ t: Date.now() - self.startTime, idx: idx });
                }

                tile.addEventListener("click", toggleTile);
                tile.addEventListener("keydown", function (e) {
                    if (e.key === "Enter" || e.key === " ") {
                        e.preventDefault();
                        toggleTile();
                    }
                });
                gridContainer.appendChild(tile);
            });

            body.append(visualHeader, gridContainer);

            var verifyBtn = footer.querySelector("#bsh-btn-verify");
            verifyBtn.onclick = function () {
                self.submitSolution({ selected: selectedIndices });
            };

        } else if (challenge.type === "rotate") {
            instrText.textContent = p.instruction || p.prompt || "Rasmni tik (▲ nuqtaga) aylantiring";
            footer.style.display = "flex";

            var wrap = document.createElement("div");
            wrap.className = "bsh-rotate-wrap";

            var rStage = document.createElement("div");
            rStage.className = "bsh-rotate-stage";

            var targetPin = document.createElement("div");
            targetPin.className = "bsh-rotate-target-pin";
            targetPin.textContent = "▼";
            targetPin.title = "Tik yuqori nuqta (0°)";

            var disk = document.createElement("div");
            disk.className = "bsh-rotate-disk";
            disk.id = "bsh-rotate-disk";
            disk.title = "Aylantirish uchun ushlab buring";

            var img = document.createElement("img");
            img.className = "bsh-rotate-img";
            img.id = "bsh-rotate-img";
            img.alt = "Rotate subject";
            img.src = sanitizeImageSrc(p.image);
            disk.appendChild(img);
            rStage.append(targetPin, disk);

            var controls = document.createElement("div");
            controls.className = "bsh-rotate-controls";

            var btnLeft = document.createElement("button");
            btnLeft.type = "button";
            btnLeft.className = "bsh-rotate-nudge";
            btnLeft.textContent = "↺";
            btnLeft.title = "-15° chapga";
            btnLeft.setAttribute("aria-label", "15 gradus chapga burish");

            var slider = document.createElement("input");
            slider.type = "range";
            slider.className = "bsh-dial-slider";
            slider.id = "bsh-dial-slider";
            slider.min = "0";
            slider.max = "360";
            slider.value = "0";
            slider.setAttribute("aria-label", "Aylantirish burchagi");

            var btnRight = document.createElement("button");
            btnRight.type = "button";
            btnRight.className = "bsh-rotate-nudge";
            btnRight.textContent = "↻";
            btnRight.title = "+15° o'ngga";
            btnRight.setAttribute("aria-label", "15 gradus o'ngga burish");

            var badge = document.createElement("div");
            badge.className = "bsh-dial-badge";
            badge.id = "bsh-dial-badge";
            badge.textContent = "0°";

            controls.append(btnLeft, slider, btnRight, badge);
            wrap.append(rStage, controls);
            body.appendChild(wrap);

            var currentDeg = 0;
            var isRotating = false;
            var startAngle = 0;

            function applyAngle(deg) {
                currentDeg = Math.round(((deg % 360) + 360) % 360);
                img.style.transform = "rotate(" + currentDeg + "deg)";
                slider.value = String(currentDeg);
                badge.textContent = currentDeg + "°";
            }

            btnLeft.addEventListener("click", function () {
                applyAngle(currentDeg - 15);
                self.trajectory.push({ t: Date.now() - self.startTime, angle: currentDeg });
            });
            btnRight.addEventListener("click", function () {
                applyAngle(currentDeg + 15);
                self.trajectory.push({ t: Date.now() - self.startTime, angle: currentDeg });
            });

            function getPointerAngle(e) {
                var rect = disk.getBoundingClientRect();
                var cx = rect.left + rect.width / 2;
                var cy = rect.top + rect.height / 2;
                var isTouch = e.type.indexOf("touch") !== -1;
                var pt = isTouch ? (e.touches[0] || e.changedTouches[0]) : e;
                if (!pt) return currentDeg;
                var rad = Math.atan2(pt.clientY - cy, pt.clientX - cx);
                var deg = rad * (180 / Math.PI);
                return (deg + 360) % 360;
            }

            function removeRotListeners() {
                isRotating = false;
                window.removeEventListener("mousemove", onRotMove);
                window.removeEventListener("mouseup", onRotEnd);
                window.removeEventListener("touchmove", onRotMove);
                window.removeEventListener("touchend", onRotEnd);
            }

            function onRotStart(e) {
                isRotating = true;
                startAngle = getPointerAngle(e) - currentDeg;
                self.trajectory.push({ t: Date.now() - self.startTime, angle: currentDeg });
                window.addEventListener("mousemove", onRotMove);
                window.addEventListener("mouseup", onRotEnd);
                window.addEventListener("touchmove", onRotMove, { passive: false });
                window.addEventListener("touchend", onRotEnd);
                e.preventDefault();
            }

            function onRotMove(e) {
                if (!isRotating) return;
                var a = getPointerAngle(e) - startAngle;
                applyAngle(a);
                self.trajectory.push({ t: Date.now() - self.startTime, angle: currentDeg });
                if (e.type.indexOf("touch") !== -1) e.preventDefault();
            }

            function onRotEnd() {
                if (!isRotating) return;
                removeRotListeners();
            }

            this._activeCleanups.push(removeRotListeners);
            disk.addEventListener("mousedown", onRotStart);
            disk.addEventListener("touchstart", onRotStart, { passive: false });

            slider.addEventListener("input", function () {
                applyAngle(parseInt(slider.value, 10) || 0);
                self.trajectory.push({ t: Date.now() - self.startTime, angle: currentDeg });
            });

            var verifyBtn = footer.querySelector("#bsh-btn-verify");
            verifyBtn.onclick = function () {
                self.submitSolution({ angle: currentDeg });
            };

        } else if (challenge.type === "sequence") {
            instrText.textContent = "Ko'rsatilgan 3 ta belgini 1 ➔ 2 ➔ 3 tartibda bosing";
            footer.style.display = "none";

            var seqCount = Math.max(1, Math.min(10, parseInt(p.count, 10) || 3));
            var seqContainer = document.createElement("div");
            seqContainer.className = "bsh-seq-container";

            var stepBar = document.createElement("div");
            stepBar.className = "bsh-seq-step-bar";

            var stepsList = document.createElement("div");
            stepsList.className = "bsh-seq-steps-list";

            if (Array.isArray(p.sequence_steps) && p.sequence_steps.length) {
                p.sequence_steps.forEach(function (st, sIdx) {
                    var pill = document.createElement("div");
                    pill.className = "bsh-seq-step-pill";

                    var numSpan = document.createElement("span");
                    numSpan.className = "bsh-seq-step-num";
                    numSpan.textContent = String(st.step || (sIdx + 1));
                    pill.appendChild(numSpan);

                    var stSvg = createSafeSvgNode(st.svg);
                    if (stSvg) pill.appendChild(stSvg);

                    var nmSpan = document.createElement("span");
                    nmSpan.className = "bsh-seq-step-name";
                    nmSpan.textContent = String(st.uz || "");
                    pill.appendChild(nmSpan);

                    stepsList.appendChild(pill);
                    if (sIdx < p.sequence_steps.length - 1) {
                        var arr = document.createElement("span");
                        arr.className = "bsh-seq-arrow";
                        arr.textContent = "➔";
                        stepsList.appendChild(arr);
                    }
                });
            } else if (Array.isArray(p.sequence_uz)) {
                p.sequence_uz.forEach(function (uzLabel, s2) {
                    var pill = document.createElement("div");
                    pill.className = "bsh-seq-step-pill";

                    var numSpan = document.createElement("span");
                    numSpan.className = "bsh-seq-step-num";
                    numSpan.textContent = String(s2 + 1);

                    var nmSpan = document.createElement("span");
                    nmSpan.className = "bsh-seq-step-name";
                    nmSpan.textContent = String(uzLabel || "");

                    pill.append(numSpan, nmSpan);
                    stepsList.appendChild(pill);
                    if (s2 < p.sequence_uz.length - 1) {
                        var arr = document.createElement("span");
                        arr.className = "bsh-seq-arrow";
                        arr.textContent = "➔";
                        stepsList.appendChild(arr);
                    }
                });
            }

            var resetBtn = document.createElement("button");
            resetBtn.type = "button";
            resetBtn.className = "bsh-seq-reset-btn";
            resetBtn.id = "bsh-seq-reset";
            resetBtn.title = "Qaytadan bosish";
            var undoSvg = createSafeSvgNode(SVG_ICONS.undo);
            if (undoSvg) resetBtn.appendChild(undoSvg);
            var resetLabel = document.createElement("span");
            resetLabel.textContent = "Tozalash";
            resetBtn.appendChild(resetLabel);

            stepBar.append(stepsList, resetBtn);

            var wrap = document.createElement("div");
            wrap.className = "bsh-seq-canvas-wrap";
            wrap.id = "bsh-seq-wrap";

            var seqBg = document.createElement("img");
            seqBg.className = "bsh-seq-bg";
            seqBg.alt = "Sequence captcha canvas";
            seqBg.src = sanitizeImageSrc(p.bg_image);
            wrap.appendChild(seqBg);

            var countLabel = document.createElement("span");
            countLabel.style.cssText = "font-size: 11px; color: #64748B;";
            countLabel.id = "bsh-seq-count";
            countLabel.textContent = "Bosildi: 0 / " + seqCount;

            seqContainer.append(stepBar, wrap, countLabel);
            body.appendChild(seqContainer);

            var clickSeq = [];
            var lastClickTime = 0;

            function clearClicks() {
                clickSeq = [];
                self.clicks = [];
                wrap.querySelectorAll(".bsh-seq-badge").forEach(function (b) { b.remove(); });
                countLabel.textContent = "Bosildi: 0 / " + seqCount;
            }

            resetBtn.addEventListener("click", clearClicks);

            function handleCanvasInteraction(e) {
                if (clickSeq.length >= seqCount || self.isSubmitting) return;

                var now = Date.now();
                // 250ms debouncer prevents simulated double clicks from firing in touch emulation or rapid taps
                if (now - lastClickTime < 250) {
                    if (e.cancelable) e.preventDefault();
                    return;
                }

                var rect = wrap.getBoundingClientRect();
                var scaleX = 320 / (rect.width || 320);
                var scaleY = 180 / (rect.height || 180);

                var clientX = e.clientX;
                var clientY = e.clientY;
                if (e.changedTouches && e.changedTouches[0]) {
                    clientX = e.changedTouches[0].clientX;
                    clientY = e.changedTouches[0].clientY;
                } else if (e.touches && e.touches[0]) {
                    clientX = e.touches[0].clientX;
                    clientY = e.touches[0].clientY;
                }

                if (clientX === undefined || clientY === undefined) return;

                lastClickTime = now;
                if (e.cancelable) {
                    e.preventDefault();
                }

                var cx = Math.max(0, Math.min(320, Math.round((clientX - rect.left) * scaleX)));
                var cy = Math.max(0, Math.min(180, Math.round((clientY - rect.top) * scaleY)));

                var clickItem = { x: cx, y: cy, t: now - self.startTime };

                clickSeq.push(clickItem);
                self.clicks.push(clickItem);

                var badge = document.createElement("div");
                badge.className = "bsh-seq-badge";
                badge.style.left = (cx / scaleX) + "px";
                badge.style.top = (cy / scaleY) + "px";
                badge.textContent = String(clickSeq.length);
                wrap.appendChild(badge);

                countLabel.textContent = "Bosildi: " + clickSeq.length + " / " + seqCount;

                if (clickSeq.length === seqCount) {
                    self._trackTimer(function () {
                        self.submitSolution({ clicks: clickSeq });
                    }, 250);
                }
            }

            if (window.PointerEvent) {
                wrap.addEventListener("pointerdown", handleCanvasInteraction);
            } else {
                wrap.addEventListener("touchstart", handleCanvasInteraction, { passive: false });
                wrap.addEventListener("click", handleCanvasInteraction);
            }
        }
    };

    BotShieldInstance.prototype.showErrorToast = function (message) {
        if (!this.modal) return;
        var existing = this.modal.querySelector(".bsh-error-toast");
        if (existing) existing.remove();

        var toast = document.createElement("div");
        toast.className = "bsh-error-toast";
        toast.setAttribute("role", "alert");

        var iconWrap = document.createElement("span");
        iconWrap.className = "bsh-error-toast-icon";
        var alertSvg = createSafeSvgNode(SVG_ICONS.alert);
        if (alertSvg) iconWrap.appendChild(alertSvg);

        var textSpan = document.createElement("span");
        textSpan.textContent = String(message || "Xatolik yuz berdi");

        toast.append(iconWrap, textSpan);

        var body = this.modal.querySelector(".bsh-card-body");
        if (body) {
            body.insertBefore(toast, body.firstChild);
        }
    };

    BotShieldInstance.prototype.setupSliderEvents = function (p) {
        var self = this;
        if (!this.modal) return;
        var thumb = this.modal.querySelector("#bsh-slider-thumb");
        var fill = this.modal.querySelector("#bsh-slider-fill");
        var piece = this.modal.querySelector("#bsh-slider-piece");
        var stage = this.modal.querySelector("#bsh-slider-stage");

        var isDragging = false;
        var startX = 0;
        var logicalWidth = Number(p.width) || 320;
        var pieceWidth = Number(p.piece_width) || 46;
        var maxSlide = Math.max(40, logicalWidth - pieceWidth);

        function removeDragListeners() {
            isDragging = false;
            window.removeEventListener("mousemove", onMove);
            window.removeEventListener("mouseup", onEnd);
            window.removeEventListener("touchmove", onMove);
            window.removeEventListener("touchend", onEnd);
        }

        function onStart(e) {
            if (self.isSubmitting) return;
            isDragging = true;
            var isTouch = e.type.indexOf("touch") !== -1;
            var pt = isTouch ? (e.touches[0] || e.changedTouches[0]) : e;
            if (!pt) return;
            startX = pt.clientX;
            self.trajectory.push({ x: 0, y: pt.clientY, t: Date.now() - self.startTime });

            window.addEventListener("mousemove", onMove);
            window.addEventListener("mouseup", onEnd);
            window.addEventListener("touchmove", onMove, { passive: false });
            window.addEventListener("touchend", onEnd);
            e.preventDefault();
        }

        function onMove(e) {
            if (!isDragging) return;
            var isTouch = e.type.indexOf("touch") !== -1;
            var pt = isTouch ? (e.touches[0] || e.changedTouches[0]) : e;
            if (!pt) return;
            var renderedWidth = (stage && stage.getBoundingClientRect().width) || logicalWidth;
            var ratio = renderedWidth / logicalWidth;
            var maxRenderSlide = maxSlide * ratio;
            var deltaRender = Math.max(0, Math.min(pt.clientX - startX, maxRenderSlide));
            var logicalX = deltaRender / (ratio || 1);

            thumb.style.left = (deltaRender + 3) + "px";
            fill.style.width = (deltaRender + 18) + "px";
            piece.style.left = deltaRender + "px";
            piece.setAttribute("data-logical-x", String(logicalX));

            self.trajectory.push({ x: logicalX, y: pt.clientY, t: Date.now() - self.startTime });
            if (isTouch) e.preventDefault();
        }

        function onEnd() {
            if (!isDragging) return;
            removeDragListeners();

            var finalX = parseFloat(piece.getAttribute("data-logical-x")) || parseFloat(piece.style.left) || 0;
            self.submitSolution({ x: finalX });
        }

        this._activeCleanups.push(removeDragListeners);
        thumb.addEventListener("mousedown", onStart);
        thumb.addEventListener("touchstart", onStart, { passive: false });
        piece.addEventListener("mousedown", onStart);
        piece.addEventListener("touchstart", onStart, { passive: false });
    };

    BotShieldInstance.prototype.submitSolution = function (solution) {
        var self = this;
        if (!this.modal || !this.challenge || this.isSubmitting) return;
        this.isSubmitting = true;

        var seq = this._requestSeq;
        var durationMs = Date.now() - this.startTime;
        var verifyBtn = this.modal.querySelector("#bsh-btn-verify");
        if (verifyBtn) verifyBtn.disabled = true;

        var payload = {
            challenge_id: this.challenge.challenge_id,
            solution: solution,
            telemetry: {
                duration_ms: durationMs,
                trajectory: this.trajectory,
                clicks: (solution && solution.clicks && solution.clicks.length) ? solution.clicks : (this.clicks && this.clicks.length ? this.clicks : []),
                user_agent: navigator.userAgent
            }
        };

        var card = this.modal.querySelector(".bsh-modal-card");

        fetch(API_BASE + "/api/v1/captcha/verify", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        })
        .then(function (res) {
            return res.text().then(function (txt) {
                try {
                    return { status: res.status, ok: res.ok, data: JSON.parse(txt) };
                } catch (e) {
                    return { status: res.status, ok: false, data: { ok: false, message: "Server javobi noto'g'ri (HTTP " + res.status + ")" } };
                }
            });
        })
        .then(function (result) {
            if (!self.modal || seq !== self._requestSeq) return;
            var data = result.data;
            if (result.ok && data && data.ok) {
                self.handleVerified(data);
            } else {
                console.warn("[BotShield Verify Error]:", data || result);
                var fallbackMsg = (self.challenge && self.challenge.type === "sequence")
                    ? "Javob noto'g'ri. Belgilarni ko'rsatilgan 1-2-3 tartibda bosing!"
                    : "Javob noto'g'ri. Qaytadan urinib ko'ring!";
                var errMsg = (data && data.message) ? data.message : fallbackMsg;
                self.showErrorToast(errMsg);
                if (card) {
                    card.classList.add("bsh-shake");
                    self._trackTimer(function () {
                        if (card) card.classList.remove("bsh-shake");
                    }, 400);
                }
                self._trackTimer(function () {
                    if (self.modal && seq === self._requestSeq) {
                        self.fetchChallenge();
                    }
                }, 1300);
            }
        })
        .catch(function (err) {
            if (!self.modal || seq !== self._requestSeq) return;
            console.error("[BotShield Network Error]:", err);
            self.showErrorToast("Tarmoq xatosi. Qaytadan urinib ko'ring.");
            if (card) {
                card.classList.add("bsh-shake");
                self._trackTimer(function () {
                    if (card) card.classList.remove("bsh-shake");
                }, 400);
            }
            self._trackTimer(function () {
                if (self.modal && seq === self._requestSeq) {
                    self.fetchChallenge();
                }
            }, 1300);
        });
    };

    BotShieldInstance.prototype.handleVerified = function (data) {
        this.isVerified = true;
        this.isSubmitting = false;
        this.token = data.token;

        if (this.hiddenInput) {
            this.hiddenInput.value = data.token;
        }

        if (this.triggerBox) {
            this.triggerBox.classList.add("bsh-verified");
            var label = this.triggerBox.querySelector(".bsh-trigger-label");
            if (label) {
                label.textContent = "Inson ekanligingiz tasdiqlandi";
            }
        }

        this.closeModal();

        // Custom Event (bubbles so document-level listeners receive it)
        var event = new CustomEvent("botshield:success", {
            bubbles: true,
            composed: true,
            detail: { token: data.token, score: data.score, type: data.type }
        });
        this.container.dispatchEvent(event);

        if (typeof this.onSuccess === "function") {
            this.onSuccess(data.token, data.score);
        }
    };

    // Auto-mount on DOMContentLoaded
    function autoMount() {
        var containers = document.querySelectorAll("#botshield-captcha, .botshield-captcha, [data-botshield-container]");
        containers.forEach(function (el) {
            if (!el._botshield) {
                el._botshield = new BotShieldInstance(el);
            }
        });
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", autoMount);
    } else {
        autoMount();
    }

    // Public Global API
    window.BotShield = {
        render: function (container, options) {
            if (typeof container === "string") {
                container = document.querySelector(container);
            }
            if (!container) return null;
            var inst = new BotShieldInstance(container, options);
            container._botshield = inst;
            return inst;
        },
        reset: function (container) {
            if (typeof container === "string") {
                container = document.querySelector(container);
            }
            if (container && container._botshield) {
                container._botshield.init();
            }
        }
    };
})();
