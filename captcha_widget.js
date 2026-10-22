/**
 * BotShield Captcha as a Service - Client Widget SDK
 * (c) 2026 AutoReply AI & BotShield Protection Services
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
                border-color: #7342E2;
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
                color: #7342E2;
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
                border-top-color: #7342E2;
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

            /* Modal Header with User Website Theme Accent (#7342E2) */
            .bsh-card-header {
                padding: 14px 16px;
                background: linear-gradient(135deg, #7342E2, #5B21B6);
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
                height: 170px;
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
                background: linear-gradient(90deg, rgba(115, 66, 226, 0.2), rgba(115, 66, 226, 0.4));
                border-radius: 22px;
                pointer-events: none;
                width: 0px;
            }
            .bsh-slider-thumb {
                width: 38px;
                height: 38px;
                border-radius: 19px;
                background: linear-gradient(135deg, #7342E2, #5B21B6);
                display: flex;
                align-items: center;
                justify-content: center;
                color: #FFFFFF;
                cursor: grab;
                box-shadow: 0 2px 8px rgba(115, 66, 226, 0.35);
                transition: transform 0.1s ease;
                position: absolute;
                left: 3px;
                z-index: 15;
            }
            .bsh-slider-thumb:hover {
                box-shadow: 0 4px 12px rgba(115, 66, 226, 0.5);
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
                grid-template-columns: repeat(3, 94px);
                gap: 8px;
            }
            .bsh-grid-tile {
                width: 94px;
                height: 94px;
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
                border-color: #7342E2;
                transform: scale(1.02);
            }
            .bsh-grid-tile.bsh-selected {
                border-color: #7342E2;
                box-shadow: 0 0 10px rgba(115, 66, 226, 0.35);
                transform: scale(0.96);
            }
            .bsh-tile-check {
                position: absolute;
                top: 6px;
                right: 6px;
                width: 22px;
                height: 22px;
                border-radius: 50%;
                background: #7342E2;
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
                gap: 14px;
            }
            .bsh-rotate-disk {
                width: 170px;
                height: 170px;
                border-radius: 50%;
                border: 2px solid #CBD5E1;
                box-shadow: 0 2px 12px rgba(0,0,0,0.08);
                display: flex;
                align-items: center;
                justify-content: center;
                position: relative;
                background: #FFFFFF;
                overflow: hidden;
                cursor: grab;
                touch-action: none;
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
                background: linear-gradient(135deg, #7342E2, #5B21B6);
                cursor: pointer;
                box-shadow: 0 2px 6px rgba(115, 66, 226, 0.4);
            }
            .bsh-dial-badge {
                font-family: -apple-system, monospace;
                font-size: 12px;
                font-weight: 700;
                color: #7342E2;
                background: #F3E8FF;
                border: 1px solid #E9D5FF;
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
                background: #7342E2;
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
                height: 180px;
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
                background: #7342E2;
                color: #FFFFFF;
                font-weight: 700;
                font-size: 14px;
                display: flex;
                align-items: center;
                justify-content: center;
                transform: translate(-50%, -50%) scale(0);
                box-shadow: 0 2px 8px rgba(115, 66, 226, 0.5);
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
                background: linear-gradient(135deg, #7342E2, #5B21B6);
                color: #FFFFFF;
                font-weight: 600;
                font-size: 13px;
                display: flex;
                align-items: center;
                gap: 6px;
                cursor: pointer;
                transition: all 0.15s ease;
                box-shadow: 0 2px 6px rgba(115, 66, 226, 0.3);
            }
            .bsh-btn-submit:hover {
                transform: translateY(-1px);
                box-shadow: 0 4px 12px rgba(115, 66, 226, 0.45);
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
        this.onSuccess = this.options.onSuccess || window[container.getAttribute("data-callback")];
        this.isVerified = false;
        this.token = null;
        this.modal = null;
        this.challenge = null;
        this.startTime = 0;
        this.trajectory = [];
        this.clicks = [];

        this.init();
    }

    BotShieldInstance.prototype.init = function () {
        var self = this;
        injectStyles();

        this.isVerified = false;
        this.token = null;
        this.challenge = null;
        this.startTime = 0;
        this.trajectory = [];
        this.clicks = [];

        this.container.innerHTML = `
            <div class="bsh-trigger-box" id="bsh-trigger-${Date.now()}">
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

        this.triggerBox.addEventListener("click", function () {
            if (self.isVerified) return;
            self.openChallengeModal();
        });
    };

    BotShieldInstance.prototype.openChallengeModal = function () {
        var self = this;
        if (this.modal) return;

        var overlay = document.createElement("div");
        overlay.className = "bsh-modal-overlay";
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
                        <div class="bsh-btn-icon" id="bsh-btn-refresh" title="Yangilash">
                            ${SVG_ICONS.refresh}
                        </div>
                        <div class="bsh-btn-icon" id="bsh-btn-close" title="Yopish">
                            ${SVG_ICONS.close}
                        </div>
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
                    <button class="bsh-btn-submit" id="bsh-btn-verify">
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
        if (this._escListener) {
            window.removeEventListener("keydown", this._escListener);
            this._escListener = null;
        }
        if (this.modal) {
            document.body.removeChild(this.modal);
            this.modal = null;
        }
    };

    BotShieldInstance.prototype.fetchChallenge = function () {
        var self = this;
        var body = this.modal.querySelector("#bsh-body");
        var footer = this.modal.querySelector("#bsh-footer");
        var instrText = this.modal.querySelector("#bsh-instr-text");

        body.innerHTML = '<div class="bsh-spinner"></div>';
        footer.style.display = "none";
        instrText.textContent = "Tekshiruv yuklanmoqda...";

        fetch(API_BASE + "/api/v1/captcha/create", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ sitekey: this.sitekey, type: this.type })
        })
        .then(function (res) { return res.json(); })
        .then(function (data) {
            if (!data.ok) {
                body.innerHTML = '<div style="color: #DC2626; font-size: 13px;">Xatolik: ' + (data.message || "Yuklab bo'lmadi") + '</div>';
                return;
            }
            self.challenge = data;
            self.renderChallenge(data);
        })
        .catch(function (err) {
            body.innerHTML = '<div style="color: #DC2626; font-size: 13px;">Serverga ulanish xatosi</div>';
        });
    };

    BotShieldInstance.prototype.renderChallenge = function (challenge) {
        var self = this;
        var body = this.modal.querySelector("#bsh-body");
        var footer = this.modal.querySelector("#bsh-footer");
        var instrText = this.modal.querySelector("#bsh-instr-text");

        this.startTime = Date.now();
        this.trajectory = [];
        this.clicks = [];

        var p = challenge.payload;

        if (challenge.type === "slider") {
            instrText.textContent = "Pazlni bo'sh joyga to'g'ri keltiring";
            footer.style.display = "none"; // Submits automatically on release

            body.innerHTML = `
                <div class="bsh-slider-stage" id="bsh-slider-stage">
                    <img class="bsh-slider-bg" src="${p.bg_image}" />
                    <img class="bsh-slider-piece" id="bsh-slider-piece" src="${p.piece_image}" style="top: ${p.y}px; left: 0px;" />
                </div>
                <div class="bsh-slider-track" id="bsh-slider-track">
                    <div class="bsh-slider-fill" id="bsh-slider-fill"></div>
                    <div class="bsh-slider-thumb" id="bsh-slider-thumb">
                        ${SVG_ICONS.arrowRight}
                    </div>
                    <span class="bsh-slider-text">Tutqichni o'ngga suring</span>
                </div>
            `;

            self.setupSliderEvents(p);

        } else if (challenge.type === "grid") {
            instrText.textContent = p.instruction || p.prompt;
            footer.style.display = "flex";

            var targetIconHtml = p.target_icon ? `<div style="display:inline-flex; align-items:center; gap:6px;">${p.target_icon} <span><b>${p.target_name || ''}</b></span></div>` : '';

            var tilesHtml = "";
            for (var i = 0; i < p.tiles.length; i++) {
                tilesHtml += `
                    <div class="bsh-grid-tile" data-idx="${i}">
                        <img src="${p.tiles[i]}" />
                        <div class="bsh-tile-check">${SVG_ICONS.check}</div>
                    </div>
                `;
            }

            body.innerHTML = `
                <div class="bsh-visual-header">
                    <div class="bsh-visual-header-left">
                        ${targetIconHtml}
                    </div>
                    <span style="font-size: 11px; color: #64748B;">Mos kataklarni bosing</span>
                </div>
                <div class="bsh-grid-container" id="bsh-grid">${tilesHtml}</div>
            `;

            var selectedIndices = [];
            var tiles = body.querySelectorAll(".bsh-grid-tile");
            tiles.forEach(function (tile) {
                tile.addEventListener("click", function () {
                    var idx = parseInt(tile.getAttribute("data-idx"), 10);
                    if (tile.classList.contains("bsh-selected")) {
                        tile.classList.remove("bsh-selected");
                        selectedIndices = selectedIndices.filter(function (x) { return x !== idx; });
                    } else {
                        tile.classList.add("bsh-selected");
                        selectedIndices.push(idx);
                    }
                    self.clicks.push({ t: Date.now() - self.startTime, idx: idx });
                });
            });

            var verifyBtn = footer.querySelector("#bsh-btn-verify");
            verifyBtn.onclick = function () {
                self.submitSolution({ selected: selectedIndices });
            };

        } else if (challenge.type === "rotate") {
            instrText.textContent = p.instruction || p.prompt;
            footer.style.display = "flex";

            body.innerHTML = `
                <div class="bsh-rotate-wrap">
                    <div class="bsh-rotate-disk" id="bsh-rotate-disk" title="Aylantirish uchun ushlab buring">
                        <img class="bsh-rotate-img" id="bsh-rotate-img" src="${p.image}" />
                    </div>
                    <div class="bsh-rotate-controls">
                        <input type="range" class="bsh-dial-slider" id="bsh-dial-slider" min="0" max="360" value="0" />
                        <div class="bsh-dial-badge" id="bsh-dial-badge">0°</div>
                    </div>
                </div>
            `;

            var disk = body.querySelector("#bsh-rotate-disk");
            var img = body.querySelector("#bsh-rotate-img");
            var slider = body.querySelector("#bsh-dial-slider");
            var badge = body.querySelector("#bsh-dial-badge");

            var currentDeg = 0;
            var isRotating = false;
            var startAngle = 0;

            function applyAngle(deg) {
                currentDeg = Math.round(((deg % 360) + 360) % 360);
                img.style.transform = "rotate(" + currentDeg + "deg)";
                slider.value = currentDeg;
                badge.textContent = currentDeg + "°";
            }

            function getPointerAngle(e) {
                var rect = disk.getBoundingClientRect();
                var cx = rect.left + rect.width / 2;
                var cy = rect.top + rect.height / 2;
                var isTouch = e.type.indexOf("touch") !== -1;
                var clientX = isTouch ? e.touches[0].clientX : e.clientX;
                var clientY = isTouch ? e.touches[0].clientY : e.clientY;
                var rad = Math.atan2(clientY - cy, clientX - cx);
                var deg = rad * (180 / Math.PI);
                return (deg + 360) % 360;
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
                isRotating = false;
                window.removeEventListener("mousemove", onRotMove);
                window.removeEventListener("mouseup", onRotEnd);
                window.removeEventListener("touchmove", onRotMove);
                window.removeEventListener("touchend", onRotEnd);
            }

            disk.addEventListener("mousedown", onRotStart);
            disk.addEventListener("touchstart", onRotStart, { passive: false });

            slider.addEventListener("input", function () {
                applyAngle(parseInt(slider.value, 10));
                self.trajectory.push({ t: Date.now() - self.startTime, angle: currentDeg });
            });

            var verifyBtn = footer.querySelector("#bsh-btn-verify");
            verifyBtn.onclick = function () {
                self.submitSolution({ angle: currentDeg });
            };

        } else if (challenge.type === "sequence") {
            instrText.textContent = "Belgilarni 1-2-3 ketma-ketlikda bosing";
            footer.style.display = "none";

            // Visual step indicator with actual SVG icons
            var stepsHtml = "";
            if (p.sequence_steps && p.sequence_steps.length) {
                for (var s = 0; s < p.sequence_steps.length; s++) {
                    var st = p.sequence_steps[s];
                    stepsHtml += `
                        <div class="bsh-seq-step-pill">
                            <span class="bsh-seq-step-num">${st.step}</span>
                            ${st.svg}
                            <span class="bsh-seq-step-name">${st.uz}</span>
                        </div>
                    `;
                    if (s < p.sequence_steps.length - 1) {
                        stepsHtml += '<span class="bsh-seq-arrow">➔</span>';
                    }
                }
            } else if (p.sequence_uz) {
                for (var s2 = 0; s2 < p.sequence_uz.length; s2++) {
                    stepsHtml += `
                        <div class="bsh-seq-step-pill">
                            <span class="bsh-seq-step-num">${s2 + 1}</span>
                            <span class="bsh-seq-step-name">${p.sequence_uz[s2]}</span>
                        </div>
                    `;
                    if (s2 < p.sequence_uz.length - 1) {
                        stepsHtml += '<span class="bsh-seq-arrow">➔</span>';
                    }
                }
            }

            body.innerHTML = `
                <div class="bsh-seq-container">
                    <div class="bsh-seq-step-bar">
                        <div class="bsh-seq-steps-list">
                            ${stepsHtml}
                        </div>
                        <button type="button" class="bsh-seq-reset-btn" id="bsh-seq-reset" title="Qaytadan bosish">
                            ${SVG_ICONS.undo}
                            <span>Tozalash</span>
                        </button>
                    </div>
                    <div class="bsh-seq-canvas-wrap" id="bsh-seq-wrap">
                        <img class="bsh-seq-bg" src="${p.bg_image}" />
                    </div>
                    <span style="font-size: 11px; color: #64748B;" id="bsh-seq-count">Bosildi: 0 / ${p.count}</span>
                </div>
            `;

            var wrap = body.querySelector("#bsh-seq-wrap");
            var countLabel = body.querySelector("#bsh-seq-count");
            var resetBtn = body.querySelector("#bsh-seq-reset");
            var clickSeq = [];
            var lastClickTime = 0;

            function clearClicks() {
                clickSeq = [];
                self.clicks = [];
                wrap.querySelectorAll(".bsh-seq-badge").forEach(function (b) { b.remove(); });
                countLabel.textContent = "Bosildi: 0 / " + p.count;
            }

            resetBtn.addEventListener("click", clearClicks);

            function handleCanvasInteraction(e) {
                if (clickSeq.length >= p.count) return;

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
                badge.textContent = clickSeq.length;
                wrap.appendChild(badge);

                countLabel.textContent = "Bosildi: " + clickSeq.length + " / " + p.count;

                if (clickSeq.length === p.count) {
                    setTimeout(function () {
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
        var existing = this.modal.querySelector(".bsh-error-toast");
        if (existing) existing.remove();

        var toast = document.createElement("div");
        toast.className = "bsh-error-toast";
        toast.innerHTML = '<span class="bsh-error-toast-icon">' + SVG_ICONS.alert + '</span><span>' + message + '</span>';

        var body = this.modal.querySelector(".bsh-card-body");
        if (body) {
            body.insertBefore(toast, body.firstChild);
        }
    };

    BotShieldInstance.prototype.setupSliderEvents = function (p) {
        var self = this;
        var thumb = this.modal.querySelector("#bsh-slider-thumb");
        var fill = this.modal.querySelector("#bsh-slider-fill");
        var piece = this.modal.querySelector("#bsh-slider-piece");
        var track = this.modal.querySelector("#bsh-slider-track");

        var isDragging = false;
        var startX = 0;
        var maxSlide = p.width - p.piece_width;

        function onStart(e) {
            isDragging = true;
            var isTouch = e.type.indexOf("touch") !== -1;
            startX = isTouch ? e.touches[0].clientX : e.clientX;
            var startY = isTouch ? e.touches[0].clientY : e.clientY;
            self.trajectory.push({ x: 0, y: startY, t: Date.now() - self.startTime });

            window.addEventListener("mousemove", onMove);
            window.addEventListener("mouseup", onEnd);
            window.addEventListener("touchmove", onMove, { passive: false });
            window.addEventListener("touchend", onEnd);
            e.preventDefault();
        }

        function onMove(e) {
            if (!isDragging) return;
            var isTouch = e.type.indexOf("touch") !== -1;
            var clientX = isTouch ? e.touches[0].clientX : e.clientX;
            var clientY = isTouch ? e.touches[0].clientY : e.clientY;
            var deltaX = clientX - startX;
            deltaX = Math.max(0, Math.min(deltaX, maxSlide));

            thumb.style.left = (deltaX + 3) + "px";
            fill.style.width = (deltaX + 18) + "px";
            piece.style.left = deltaX + "px";

            self.trajectory.push({ x: deltaX, y: clientY, t: Date.now() - self.startTime });
            if (isTouch) e.preventDefault();
        }

        function onEnd(e) {
            if (!isDragging) return;
            isDragging = false;
            window.removeEventListener("mousemove", onMove);
            window.removeEventListener("mouseup", onEnd);
            window.removeEventListener("touchmove", onMove);
            window.removeEventListener("touchend", onEnd);

            var finalX = parseFloat(piece.style.left) || 0;
            self.submitSolution({ x: finalX });
        }

        thumb.addEventListener("mousedown", onStart);
        thumb.addEventListener("touchstart", onStart, { passive: false });
        piece.addEventListener("mousedown", onStart);
        piece.addEventListener("touchstart", onStart, { passive: false });
    };

    BotShieldInstance.prototype.submitSolution = function (solution) {
        var self = this;
        var durationMs = Date.now() - this.startTime;

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
            return res.json().then(function (data) {
                return { status: res.status, ok: res.ok, data: data };
            });
        })
        .then(function (result) {
            var data = result.data;
            if (data && data.ok) {
                self.handleVerified(data);
            } else {
                console.warn("[BotShield Verify Error]:", data || result);
                var errMsg = (data && data.message) ? data.message : "Javob noto'g'ri. Belgilarni ko'rsatilgan 1-2-3 tartibda bosing!";
                self.showErrorToast(errMsg);
                card.classList.add("bsh-shake");
                setTimeout(function () {
                    card.classList.remove("bsh-shake");
                }, 400);
                setTimeout(function () {
                    self.fetchChallenge();
                }, 1300);
            }
        })
        .catch(function (err) {
            console.error("[BotShield Network Error]:", err);
            self.showErrorToast("Tarmoq xatosi. Qaytadan urinib ko'ring.");
            card.classList.add("bsh-shake");
            setTimeout(function () {
                card.classList.remove("bsh-shake");
            }, 400);
            setTimeout(function () {
                self.fetchChallenge();
            }, 1300);
        });
    };

    BotShieldInstance.prototype.handleVerified = function (data) {
        var self = this;
        this.isVerified = true;
        this.token = data.token;

        if (this.hiddenInput) {
            this.hiddenInput.value = data.token;
        }

        this.triggerBox.classList.add("bsh-verified");
        var label = this.triggerBox.querySelector(".bsh-trigger-label");
        if (label) {
            label.textContent = "Inson ekanligingiz tasdiqlandi";
        }

        this.closeModal();

        // Custom Event
        var event = new CustomEvent("botshield:success", {
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
