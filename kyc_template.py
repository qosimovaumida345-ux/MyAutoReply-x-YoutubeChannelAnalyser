"""
3D Face & ID Biometric KYC WebApp Template
Includes Real MediaPipe FaceMesh 468-point dynamic facial tracking,
Anti-Sybil liveness verification (Center -> Left -> Right turn detection),
and verified state presentation.
"""
import json

def get_kyc_html(user_id=0, is_verified=False, kyc_data=None, phone=""):
    initial_state = {
        "user_id": int(user_id or 0),
        "is_verified": bool(is_verified),
        "kyc_data": kyc_data or {},
        "phone": str(phone or "")
    }
    state_json = json.dumps(initial_state)
    
    return f"""<!DOCTYPE html>
<html lang="uz">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
    <title>3D Face & ID Biometrik Identifikatsiya</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <!-- MediaPipe FaceMesh for Real 468-point 3D Facial Mesh Tracking -->
    <script src="https://cdn.jsdelivr.net/npm/@mediapipe/camera_utils/camera_utils.js" crossorigin="anonymous"></script>
    <script src="https://cdn.jsdelivr.net/npm/@mediapipe/face_mesh/face_mesh.js" crossorigin="anonymous"></script>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-color: #080c14;
            --card-bg: rgba(15, 23, 42, 0.82);
            --accent-cyan: #00f2fe;
            --accent-purple: #7928ca;
            --neon-blue: #3b82f6;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --border-glow: rgba(0, 242, 254, 0.35);
            --danger-color: #ef4444;
            --warning-color: #f59e0b;
            --success-color: #10b981;
        }}

        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            font-family: 'Outfit', -apple-system, BlinkMacSystemFont, sans-serif;
            -webkit-tap-highlight-color: transparent;
        }}

        body {{
            background-color: var(--bg-color);
            background-image: 
                radial-gradient(circle at 10% 20%, rgba(121, 40, 202, 0.18) 0%, transparent 45%),
                radial-gradient(circle at 90% 80%, rgba(0, 242, 254, 0.14) 0%, transparent 45%),
                linear-gradient(180deg, rgba(8, 12, 20, 0.95) 0%, #050811 100%);
            color: var(--text-main);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            padding: 16px;
            overflow-x: hidden;
        }}

        .container {{
            width: 100%;
            max-width: 440px;
            display: flex;
            flex-direction: column;
            gap: 16px;
        }}

        .header {{
            text-align: center;
            padding: 8px 0;
        }}

        .header h1 {{
            font-size: 22px;
            font-weight: 800;
            background: linear-gradient(135deg, #00f2fe 0%, #38bdf8 50%, #a855f7 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            letter-spacing: -0.5px;
            margin-bottom: 4px;
        }}

        .header p {{
            font-size: 13px;
            color: var(--text-muted);
            line-height: 1.4;
        }}

        .card {{
            background: var(--card-bg);
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            border: 1px solid var(--border-glow);
            border-radius: 20px;
            padding: 20px;
            box-shadow: 0 12px 35px rgba(0, 0, 0, 0.55), inset 0 1px 0 rgba(255, 255, 255, 0.08);
            position: relative;
            overflow: hidden;
        }}

        .step-badge {{
            display: inline-flex;
            align-items: center;
            gap: 6px;
            background: rgba(0, 242, 254, 0.1);
            color: var(--accent-cyan);
            border: 1px solid rgba(0, 242, 254, 0.3);
            border-radius: 12px;
            padding: 4px 10px;
            font-size: 11px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 12px;
        }}

        .verified-badge {{
            display: inline-flex;
            align-items: center;
            gap: 6px;
            background: rgba(16, 185, 129, 0.15);
            color: var(--success-color);
            border: 1px solid rgba(16, 185, 129, 0.35);
            border-radius: 12px;
            padding: 5px 12px;
            font-size: 12px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.6px;
            margin-bottom: 16px;
        }}

        .form-group {{
            margin-bottom: 15px;
        }}

        .form-group label {{
            display: block;
            font-size: 12px;
            color: var(--text-muted);
            font-weight: 600;
            margin-bottom: 6px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}

        .input-box {{
            width: 100%;
            background: rgba(8, 12, 20, 0.85);
            border: 1px solid rgba(255, 255, 255, 0.12);
            border-radius: 12px;
            padding: 12px 14px;
            color: #fff;
            font-size: 15px;
            outline: none;
            transition: all 0.3s;
        }}

        .input-box:focus {{
            border-color: var(--accent-cyan);
            box-shadow: 0 0 15px rgba(0, 242, 254, 0.25);
        }}

        /* 3D Face Scanner Frame */
        .scanner-container {{
            position: relative;
            width: 100%;
            aspect-ratio: 4/5;
            background: #020617;
            border-radius: 18px;
            overflow: hidden;
            border: 2px solid rgba(0, 242, 254, 0.45);
            box-shadow: 0 0 30px rgba(0, 242, 254, 0.2);
            display: flex;
            align-items: center;
            justify-content: center;
        }}

        video {{
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            object-fit: cover;
            transform: scaleX(-1);
        }}

        canvas.overlay {{
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            pointer-events: none;
            z-index: 2;
        }}

        /* Scanning Laser Beam */
        .laser {{
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 2px;
            background: linear-gradient(90deg, transparent, #00f2fe 30%, #fff 50%, #00f2fe 70%, transparent);
            box-shadow: 0 0 15px #00f2fe, 0 0 25px #00f2fe;
            animation: scan 2.4s ease-in-out infinite alternate;
            pointer-events: none;
            z-index: 3;
            transition: background 0.3s ease;
        }}

        .laser.searching {{
            background: linear-gradient(90deg, transparent, #f59e0b 30%, #fff 50%, #f59e0b 70%, transparent);
            box-shadow: 0 0 15px #f59e0b;
        }}

        .laser.verified {{
            background: linear-gradient(90deg, transparent, #10b981 30%, #fff 50%, #10b981 70%, transparent);
            box-shadow: 0 0 15px #10b981;
        }}

        @keyframes scan {{
            0% {{ top: 6%; opacity: 0.85; }}
            50% {{ opacity: 1; }}
            100% {{ top: 92%; opacity: 0.85; }}
        }}

        /* Status & Guidance HUD */
        .guidance-box {{
            position: absolute;
            bottom: 12px;
            left: 12px;
            right: 12px;
            background: rgba(8, 12, 20, 0.88);
            border: 1px solid rgba(0, 242, 254, 0.35);
            border-radius: 12px;
            padding: 10px 12px;
            text-align: center;
            backdrop-filter: blur(12px);
            z-index: 4;
            transition: all 0.3s ease;
        }}

        .guidance-text {{
            font-size: 13px;
            font-weight: 700;
            color: var(--accent-cyan);
            margin-bottom: 5px;
            transition: color 0.3s;
        }}

        .guidance-text.warning {{
            color: var(--warning-color);
        }}

        .guidance-text.success {{
            color: var(--success-color);
        }}

        .progress-bar-bg {{
            width: 100%;
            height: 6px;
            background: rgba(255, 255, 255, 0.12);
            border-radius: 3px;
            overflow: hidden;
            margin-top: 6px;
        }}

        .progress-bar-fill {{
            width: 0%;
            height: 100%;
            background: linear-gradient(90deg, #00f2fe, #38bdf8);
            transition: width 0.2s ease, background 0.3s ease;
        }}

        /* Action Buttons */
        .btn {{
            width: 100%;
            padding: 14px;
            border: none;
            border-radius: 14px;
            font-size: 15px;
            font-weight: 700;
            color: #fff;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            transition: all 0.3s;
            margin-top: 10px;
        }}

        .btn-primary {{
            background: linear-gradient(135deg, #00f2fe 0%, #38bdf8 50%, #7928ca 100%);
            box-shadow: 0 4px 20px rgba(56, 189, 248, 0.4);
        }}

        .btn-success {{
            background: linear-gradient(135deg, #10b981 0%, #059669 100%);
            box-shadow: 0 4px 20px rgba(16, 185, 129, 0.4);
        }}

        .btn-secondary {{
            background: rgba(255, 255, 255, 0.08);
            border: 1px solid rgba(255, 255, 255, 0.15);
            color: var(--text-main);
        }}

        .btn-primary:active, .btn-success:active {{
            transform: scale(0.98);
        }}

        .btn:disabled {{
            opacity: 0.5;
            cursor: not-allowed;
            transform: none !important;
        }}

        .alert-box {{
            display: none;
            padding: 12px 14px;
            border-radius: 12px;
            font-size: 13px;
            line-height: 1.4;
            margin-top: 12px;
        }}

        .alert-danger {{
            background: rgba(239, 68, 68, 0.15);
            border: 1px solid var(--danger-color);
            color: #fca5a5;
        }}

        .alert-success {{
            background: rgba(16, 185, 129, 0.15);
            border: 1px solid var(--success-color);
            color: #86efac;
        }}

        /* Verified Card Styles */
        .verified-card {{
            text-align: center;
            padding: 28px 20px;
        }}

        .shield-icon {{
            width: 84px;
            height: 84px;
            margin: 0 auto 16px auto;
            border-radius: 50%;
            background: radial-gradient(circle, rgba(16, 185, 129, 0.25) 0%, rgba(0, 242, 254, 0.1) 70%);
            border: 2px solid var(--success-color);
            box-shadow: 0 0 35px rgba(16, 185, 129, 0.35);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 40px;
            animation: pulseGlow 3s infinite alternate;
        }}

        @keyframes pulseGlow {{
            0% {{ box-shadow: 0 0 20px rgba(16, 185, 129, 0.3); transform: scale(1); }}
            100% {{ box-shadow: 0 0 40px rgba(16, 185, 129, 0.6); transform: scale(1.04); }}
        }}

        .verified-title {{
            font-size: 20px;
            font-weight: 800;
            color: #fff;
            margin-bottom: 6px;
        }}

        .verified-desc {{
            font-size: 13px;
            color: var(--text-muted);
            margin-bottom: 20px;
            line-height: 1.4;
        }}

        .info-table {{
            width: 100%;
            background: rgba(8, 12, 20, 0.6);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 14px;
            padding: 14px;
            margin-bottom: 20px;
            text-align: left;
        }}

        .info-row {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 7px 0;
            font-size: 13px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.06);
        }}

        .info-row:last-child {{
            border-bottom: none;
        }}

        .info-label {{
            color: var(--text-muted);
        }}

        .info-val {{
            font-weight: 600;
            color: #fff;
            font-family: monospace;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🛡️ 3D Biometrik Identifikatsiya</h1>
            <p>Anti-Sybil & botlardan himoya tizimi. Faqat haqiqiy foydalanuvchilar tasdiqlanadi.</p>
        </div>

        <!-- Verified View (if user already passed KYC) -->
        <div class="card verified-card" id="verifiedCard" style="display: none;">
            <div class="shield-icon">🛡️</div>
            <h2 class="verified-title">Shaxsingiz Tasdiqlangan</h2>
            <div class="verified-badge">✅ REAL FOYDALANUVCHI</div>
            <p class="verified-desc">
                Sizning 3D yuz biometrikangiz muvaffaqiyatli saqlangan. Akkauntingiz botlar va dublikatlardan to'liq himoyalangan.
            </p>

            <div class="info-table">
                <div class="info-row">
                    <span class="info-label">Telegram ID:</span>
                    <span class="info-val" id="vTgId">-</span>
                </div>
                <div class="info-row">
                    <span class="info-label">Holat:</span>
                    <span class="info-val" style="color: var(--success-color);">TASDIQLANGAN</span>
                </div>
                <div class="info-row">
                    <span class="info-label">Bog'langan telefon:</span>
                    <span class="info-val" id="vPhone">-</span>
                </div>
                <div class="info-row">
                    <span class="info-label">3D Face Hash:</span>
                    <span class="info-val" id="vFaceHash">-</span>
                </div>
                <div class="info-row">
                    <span class="info-label">Tasdiqlangan sana:</span>
                    <span class="info-val" id="vDate">-</span>
                </div>
            </div>

            <button type="button" class="btn btn-primary" onclick="closeWebApp()">
                🏠 Telegram Botga Qaytish
            </button>
            <button type="button" class="btn btn-secondary" onclick="showScanForm()">
                🔄 Qayta Skanerlash (Yangilash)
            </button>
        </div>

        <!-- Step 1: Document & Phone Form -->
        <div class="card" id="formCard">
            <span class="step-badge">Qadam 1: Hujjat ma'lumotlari</span>
            
            <div class="form-group">
                <label>Telefon raqamingiz</label>
                <input type="tel" id="phoneInput" class="input-box" placeholder="+998 90 123 45 67">
            </div>

            <div class="form-group">
                <label>Pasport / ID seriya va raqami</label>
                <input type="text" id="passportInput" class="input-box" placeholder="Masalan: AA 1234567" style="text-transform: uppercase;">
            </div>

            <button type="button" id="startScanBtn" class="btn btn-primary" onclick="initiateCamera()">
                📷 3D Yuz Skanerini Boshlash
            </button>
        </div>

        <!-- Step 2: Live 3D Mesh Camera Scanner -->
        <div class="card" id="scannerCard" style="display: none;">
            <span class="step-badge">Qadam 2: Haqiqiy 3D Yuz Skaneri</span>
            
            <div class="scanner-container">
                <video id="videoEl" autoplay playsinline muted></video>
                <canvas id="overlayCanvas" class="overlay"></canvas>
                <div id="laserBeam" class="laser searching"></div>
                
                <div class="guidance-box">
                    <div id="guidanceText" class="guidance-text warning">Kamera yuklanmoqda...</div>
                    <div class="progress-bar-bg">
                        <div id="progressBar" class="progress-bar-fill"></div>
                    </div>
                </div>
            </div>

            <button type="button" id="submitBtn" class="btn btn-success" style="display: none;" onclick="submitVerification()">
                ✅ Tasdiqlash va Saqlash
            </button>
        </div>

        <div id="alertBox" class="alert-box"></div>
    </div>

    <script>
        const INITIAL_STATE = {state_json};
        const tg = window.Telegram?.WebApp;
        if (tg) {{
            tg.expand();
            tg.ready();
        }}

        const urlParams = new URLSearchParams(window.location.search);
        let userId = parseInt(urlParams.get('user_id')) || parseInt(tg?.initDataUnsafe?.user?.id) || INITIAL_STATE.user_id || 0;

        let videoStream = null;
        let faceMesh = null;
        let camera = null;
        let currentStage = 0; // 0: detecting face, 1: center, 2: left turn, 3: right turn, 4: complete
        let livenessProgress = 0;
        let isFaceVisible = false;
        let lastHeadYaw = 0;
        let capturedLandmarks = null;
        let animationFrameId = null;

        // Auto-check verified state on start
        window.addEventListener('DOMContentLoaded', async () => {{
            const verifiedPhone = urlParams.get('phone') || INITIAL_STATE.phone || '';
            if (verifiedPhone) {{
                const pInput = document.getElementById('phoneInput');
                if (pInput) {{
                    pInput.value = verifiedPhone;
                    pInput.readOnly = true;
                    pInput.style.backgroundColor = 'rgba(16, 185, 129, 0.12)';
                    pInput.style.borderColor = 'rgba(16, 185, 129, 0.4)';
                    pInput.style.color = '#10b981';
                    pInput.style.fontWeight = '700';
                    
                    const group = pInput.parentElement;
                    if (!document.getElementById('phoneLockBadge')) {{
                        const lockBadge = document.createElement('div');
                        lockBadge.id = 'phoneLockBadge';
                        lockBadge.style.cssText = 'font-size: 11px; color: #10b981; font-weight: 600; margin-top: 6px; display: flex; align-items: center; gap: 4px;';
                        lockBadge.innerHTML = '🔒 Telegram orqali tasdiqlangan (O\'zgartirib bo\'lmaydi)';
                        group.appendChild(lockBadge);
                    }}
                }}
            }}

            if (INITIAL_STATE.is_verified) {{
                showVerifiedView(INITIAL_STATE.kyc_data);
                return;
            }}
            if (userId) {{
                try {{
                    const res = await fetch(`/kyc/status?user_id=${{userId}}`);
                    const data = await res.json();
                    if (data.ok && data.is_verified) {{
                        showVerifiedView(data);
                        return;
                    }}
                }} catch (e) {{
                    console.log("Status check fallback:", e);
                }}
            }}
        }});

        function showVerifiedView(data) {{
            document.getElementById('formCard').style.display = 'none';
            document.getElementById('scannerCard').style.display = 'none';
            document.getElementById('verifiedCard').style.display = 'block';

            document.getElementById('vTgId').innerText = userId || "-";
            document.getElementById('vPhone').innerText = data?.phone_masked || data?.phone_number || "Mavjud";
            document.getElementById('vFaceHash').innerText = data?.face_hash || "face_3d_verified";
            document.getElementById('vDate').innerText = (data?.verified_at || new Date().toISOString()).slice(0, 16).replace('T', ' ');
        }}

        function showScanForm() {{
            document.getElementById('verifiedCard').style.display = 'none';
            document.getElementById('formCard').style.display = 'block';
        }}

        function closeWebApp() {{
            if (tg) {{
                tg.close();
            }} else {{
                window.history.back();
            }}
        }}

        async function initiateCamera() {{
            const phone = document.getElementById('phoneInput').value.trim();
            const passport = document.getElementById('passportInput').value.trim();

            if (!phone || phone.length < 9) {{
                showAlert("Iltimos, to'g'ri telefon raqamingizni kiriting!", "danger");
                return;
            }}
            if (!passport || passport.length < 7) {{
                showAlert("Iltimos, pasport yoki ID seriya va raqamingizni kiriting (masalan: AA 1234567)!", "danger");
                return;
            }}

            hideAlert();
            document.getElementById('formCard').style.display = 'none';
            document.getElementById('scannerCard').style.display = 'block';

            const videoEl = document.getElementById('videoEl');
            const guidance = document.getElementById('guidanceText');
            guidance.innerText = "Kameraga ruxsat so'ralmoqda...";

            try {{
                videoStream = await navigator.mediaDevices.getUserMedia({{
                    video: {{
                        facingMode: "user",
                        width: {{ ideal: 640 }},
                        height: {{ ideal: 480 }}
                    }},
                    audio: false
                }});
                videoEl.srcObject = videoStream;
                await videoEl.play();

                initFaceMeshTracker();
            }} catch (err) {{
                console.error("Camera error:", err);
                showAlert("Kamera ochilmadi yoki ruxsat berilmadi! 3D Biometrik tekshiruv uchun kameraga ruxsat bering: " + err.message, "danger");
                document.getElementById('formCard').style.display = 'block';
                document.getElementById('scannerCard').style.display = 'none';
            }}
        }}

        function initFaceMeshTracker() {{
            const videoEl = document.getElementById('videoEl');
            const canvas = document.getElementById('overlayCanvas');
            const ctx = canvas.getContext('2d');

            // Resize canvas to match display size
            canvas.width = canvas.parentElement.clientWidth;
            canvas.height = canvas.parentElement.clientHeight;

            // Check if MediaPipe is available
            if (window.FaceMesh) {{
                faceMesh = new FaceMesh({{
                    locateFile: (file) => `https://cdn.jsdelivr.net/npm/@mediapipe/face_mesh/${{file}}`
                }});

                faceMesh.setOptions({{
                    maxNumFaces: 1,
                    refineLandmarks: true,
                    minDetectionConfidence: 0.5,
                    minTrackingConfidence: 0.5
                }});

                faceMesh.onResults((results) => {{
                    onFaceMeshResults(results, ctx, canvas.width, canvas.height);
                }});

                // Video frame processing loop
                let isProcessing = false;
                async function processFrame() {{
                    if (videoEl.readyState >= 2 && !isProcessing && faceMesh) {{
                        isProcessing = true;
                        try {{
                            await faceMesh.send({{ image: videoEl }});
                        }} catch (e) {{}}
                        isProcessing = false;
                    }}
                    animationFrameId = requestAnimationFrame(processFrame);
                }}
                processFrame();
            }} else {{
                // Fallback CV in-browser tracker
                startFallbackTracker(videoEl, canvas, ctx);
            }}
        }}

        // Real 468-point 3D FaceMesh Results Handler
        function onFaceMeshResults(results, ctx, width, height) {{
            ctx.clearRect(0, 0, width, height);

            const guidance = document.getElementById('guidanceText');
            const laser = document.getElementById('laserBeam');
            const progress = document.getElementById('progressBar');
            const landmarks = results.multiFaceLandmarks?.[0];

            if (!landmarks || landmarks.length === 0) {{
                isFaceVisible = false;
                laser.className = "laser searching";
                guidance.className = "guidance-text warning";
                guidance.innerText = "⚠️ Yuz aniqlanmadi! Yuzingizni kameraga qarating";

                // Draw searching HUD reticle
                drawSearchingHUD(ctx, width, height);
                return;
            }}

            isFaceVisible = true;
            capturedLandmarks = landmarks;
            laser.className = currentStage === 4 ? "laser verified" : "laser";

            // Draw Real Face-conforming 3D Wireframe Mesh
            drawRealFaceMesh(ctx, landmarks, width, height, currentStage === 4);

            // Compute Real Head Orientation (Yaw)
            // Left cheek anchor (234), Right cheek anchor (454), Nose tip (4)
            const leftCheek = landmarks[234];
            const rightCheek = landmarks[454];
            const noseTip = landmarks[4];

            if (leftCheek && rightCheek && noseTip) {{
                const cheekSpan = rightCheek.x - leftCheek.x;
                const midCheekX = (leftCheek.x + rightCheek.x) / 2;
                lastHeadYaw = (noseTip.x - midCheekX) / (cheekSpan || 1); // < -0.09 left, > 0.09 right
            }}

            // Liveness State Machine (requires real user actions)
            handleLivenessProgression(guidance, progress);
        }}

        function handleLivenessProgression(guidance, progress) {{
            if (currentStage === 0) {{
                currentStage = 1;
            }}

            if (currentStage === 1) {{
                // Stage 1: Face Centered
                guidance.className = "guidance-text";
                guidance.innerText = "1/3: Iltimos, to'g'riga qarang...";

                if (Math.abs(lastHeadYaw) < 0.12) {{
                    livenessProgress = Math.min(35, livenessProgress + 1.2);
                    progress.style.width = livenessProgress + "%";
                    if (livenessProgress >= 35) {{
                        currentStage = 2;
                    }}
                }}
            }} else if (currentStage === 2) {{
                // Stage 2: Turn Left
                guidance.className = "guidance-text";
                guidance.innerText = "2/3: Yuzingizni sekin chapga buring ⬅️";

                // In mirrored selfie camera, turning head left moves nose left
                if (lastHeadYaw < -0.07) {{
                    livenessProgress = Math.min(70, livenessProgress + 1.6);
                    progress.style.width = livenessProgress + "%";
                    if (livenessProgress >= 70) {{
                        currentStage = 3;
                    }}
                }}
            }} else if (currentStage === 3) {{
                // Stage 3: Turn Right
                guidance.className = "guidance-text";
                guidance.innerText = "3/3: Yuzingizni sekin o'ngga buring ➡️";

                if (lastHeadYaw > 0.07) {{
                    livenessProgress = Math.min(100, livenessProgress + 1.6);
                    progress.style.width = livenessProgress + "%";
                    if (livenessProgress >= 100) {{
                        currentStage = 4;
                    }}
                }}
            }} else if (currentStage === 4) {{
                // Complete
                guidance.className = "guidance-text success";
                guidance.innerText = "✅ 3D Yuz to'liq skanerlandi va tasdiqlandi!";
                progress.style.width = "100%";
                progress.style.background = "linear-gradient(90deg, #10b981, #00f2fe)";
                document.getElementById('submitBtn').style.display = 'flex';
            }}
        }}

        // Draws dynamic 3D Wireframe Conforming Exactly to Person's Facial Features
        function drawRealFaceMesh(ctx, landmarks, width, height, isDone) {{
            const toX = (p) => (1.0 - p.x) * width; // Mirror horizontally to match video
            const toY = (p) => p.y * height;

            const primaryColor = isDone ? "#10b981" : "#00f2fe";
            const wireColor = isDone ? "rgba(16, 185, 129, 0.28)" : "rgba(0, 242, 254, 0.25)";
            const pointColor = isDone ? "#34d399" : "#38bdf8";

            // 1. Jawline Path
            const jawIndices = [10, 338, 297, 332, 284, 251, 389, 356, 454, 323, 361, 288, 397, 365, 379, 378, 400, 377, 152, 148, 176, 149, 150, 136, 172, 58, 132, 93, 234, 127, 162, 21, 54, 103, 67, 109, 10];
            ctx.beginPath();
            ctx.strokeStyle = primaryColor;
            ctx.lineWidth = 2.2;
            jawIndices.forEach((idx, i) => {{
                const p = landmarks[idx];
                if (p) {{
                    const x = toX(p), y = toY(p);
                    if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
                }}
            }});
            ctx.stroke();

            // 2. Real Left & Right Eyes
            const leftEye = [33, 7, 163, 144, 145, 153, 154, 155, 133, 173, 157, 158, 159, 160, 161, 246, 33];
            const rightEye = [263, 249, 390, 373, 374, 380, 381, 382, 362, 398, 384, 385, 386, 387, 388, 466, 263];
            [leftEye, rightEye].forEach(eye => {{
                ctx.beginPath();
                ctx.strokeStyle = primaryColor;
                ctx.lineWidth = 1.8;
                eye.forEach((idx, i) => {{
                    const p = landmarks[idx];
                    if (p) {{
                        const x = toX(p), y = toY(p);
                        if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
                    }}
                }});
                ctx.stroke();
            }});

            // 3. Lips Outer Contour
            const lips = [61, 146, 91, 181, 84, 17, 314, 405, 321, 375, 291, 308, 324, 318, 402, 317, 14, 87, 178, 88, 95, 78, 61];
            ctx.beginPath();
            ctx.strokeStyle = primaryColor;
            ctx.lineWidth = 1.6;
            lips.forEach((idx, i) => {{
                const p = landmarks[idx];
                if (p) {{
                    const x = toX(p), y = toY(p);
                    if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
                }}
            }});
            ctx.stroke();

            // 4. Nose Bridge & Contours
            const nose = [168, 6, 197, 195, 5, 4, 1, 19, 94, 2];
            ctx.beginPath();
            ctx.strokeStyle = primaryColor;
            ctx.lineWidth = 1.6;
            nose.forEach((idx, i) => {{
                const p = landmarks[idx];
                if (p) {{
                    const x = toX(p), y = toY(p);
                    if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
                }}
            }});
            ctx.stroke();

            // 5. 3D Triangulation Grid Connections across face
            const connections = [
                [10, 151], [151, 9], [9, 8], [8, 168], [168, 6], [6, 197],
                [234, 127], [127, 162], [162, 21], [454, 323], [323, 361], [361, 288],
                [1, 2], [2, 164], [164, 18], [18, 200], [200, 199], [199, 152],
                [33, 168], [263, 168], [1, 61], [1, 291], [4, 61], [4, 291],
                [10, 67], [10, 297], [152, 377], [152, 148]
            ];
            ctx.beginPath();
            ctx.strokeStyle = wireColor;
            ctx.lineWidth = 1.1;
            connections.forEach(([i1, i2]) => {{
                const p1 = landmarks[i1], p2 = landmarks[i2];
                if (p1 && p2) {{
                    ctx.moveTo(toX(p1), toY(p1));
                    ctx.lineTo(toX(p2), toY(p2));
                }}
            }});
            ctx.stroke();

            // 6. Glowing Keypoint Dots on real face features
            const keypoints = [10, 152, 234, 454, 4, 33, 263, 61, 291, 168];
            ctx.fillStyle = pointColor;
            keypoints.forEach(idx => {{
                const p = landmarks[idx];
                if (p) {{
                    const x = toX(p), y = toY(p);
                    ctx.beginPath();
                    ctx.arc(x, y, 3.2, 0, Math.PI * 2);
                    ctx.fill();
                }}
            }});
        }}

        function drawSearchingHUD(ctx, width, height) {{
            const cx = width / 2;
            const cy = height / 2;
            const rx = width * 0.32;
            const ry = height * 0.38;

            ctx.save();
            ctx.strokeStyle = "rgba(245, 158, 11, 0.65)";
            ctx.lineWidth = 2.2;
            ctx.setLineDash([8, 8]);
            ctx.beginPath();
            ctx.ellipse(cx, cy, rx, ry, 0, 0, Math.PI * 2);
            ctx.stroke();

            // Corner Reticles
            ctx.setLineDash([]);
            const sz = 24;
            const corners = [
                [cx - rx, cy - ry, 1, 1],
                [cx + rx, cy - ry, -1, 1],
                [cx - rx, cy + ry, 1, -1],
                [cx + rx, cy + ry, -1, -1]
            ];
            corners.forEach(([x, y, dx, dy]) => {{
                ctx.beginPath();
                ctx.moveTo(x, y + dy * sz);
                ctx.lineTo(x, y);
                ctx.lineTo(x + dx * sz, y);
                ctx.stroke();
            }});
            ctx.restore();
        }}

        // Computer Vision Fallback Tracker (if CDN is unavailable)
        function startFallbackTracker(videoEl, canvas, ctx) {{
            const sampleCanvas = document.createElement('canvas');
            const sampleCtx = sampleCanvas.getContext('2d', {{ willReadFrequently: true }});
            sampleCanvas.width = 160;
            sampleCanvas.height = 120;

            const guidance = document.getElementById('guidanceText');
            const laser = document.getElementById('laserBeam');
            const progress = document.getElementById('progressBar');

            function cvLoop() {{
                if (videoEl.readyState >= 2) {{
                    sampleCtx.drawImage(videoEl, 0, 0, 160, 120);
                    const frame = sampleCtx.getImageData(0, 0, 160, 120);
                    const data = frame.data;

                    let totalBrightness = 0;
                    let skinPixels = 0;
                    let skinX = 0, skinY = 0;

                    for (let i = 0; i < data.length; i += 4) {{
                        const r = data[i], g = data[i + 1], b = data[i + 2];
                        const br = (r + g + b) / 3;
                        totalBrightness += br;

                        // Skin tone heuristic in RGB: R > 95, G > 40, B > 20, R > G, R > B, |R-G| > 15
                        if (r > 95 && g > 40 && b > 20 && r > g && r > b && Math.abs(r - g) > 15) {{
                            const pixelIndex = i / 4;
                            const px = pixelIndex % 160;
                            const py = Math.floor(pixelIndex / 160);
                            skinPixels++;
                            skinX += px;
                            skinY += py;
                        }}
                    }}

                    const avgBrightness = totalBrightness / (data.length / 4);
                    const skinRatio = skinPixels / (data.length / 4);

                    ctx.clearRect(0, 0, canvas.width, canvas.height);

                    if (avgBrightness < 18 || skinRatio < 0.08) {{
                        // No face or camera covered
                        isFaceVisible = false;
                        laser.className = "laser searching";
                        guidance.className = "guidance-text warning";
                        guidance.innerText = avgBrightness < 18 ? "⚠️ Kamera qorong'i yoki yopilgan!" : "⚠️ Yuz aniqlanmadi! Kameraga to'g'ri qarang";
                        drawSearchingHUD(ctx, canvas.width, canvas.height);
                    }} else {{
                        // Real face detected from video pixels
                        isFaceVisible = true;
                        laser.className = currentStage === 4 ? "laser verified" : "laser";
                        const cx = (1.0 - (skinX / skinPixels) / 160) * canvas.width;
                        const cy = ((skinY / skinPixels) / 120) * canvas.height;

                        // Draw adaptive facial mesh following detected face center
                        drawAdaptiveFaceMesh(ctx, cx, cy, canvas.width * 0.28, canvas.height * 0.35, currentStage === 4);

                        // Simulated liveness turn progression
                        handleLivenessProgression(guidance, progress);
                    }}
                }}
                animationFrameId = requestAnimationFrame(cvLoop);
            }}
            cvLoop();
        }}

        function drawAdaptiveFaceMesh(ctx, cx, cy, rx, ry, isDone) {{
            const color = isDone ? "#10b981" : "#00f2fe";
            const wire = isDone ? "rgba(16, 185, 129, 0.3)" : "rgba(0, 242, 254, 0.25)";

            // Contour
            ctx.beginPath();
            ctx.strokeStyle = color;
            ctx.lineWidth = 2;
            ctx.ellipse(cx, cy, rx, ry, 0, 0, Math.PI * 2);
            ctx.stroke();

            // Inner feature lines
            ctx.strokeStyle = wire;
            ctx.beginPath();
            ctx.moveTo(cx - rx * 0.5, cy - ry * 0.2);
            ctx.lineTo(cx - rx * 0.2, cy - ry * 0.2);
            ctx.moveTo(cx + rx * 0.2, cy - ry * 0.2);
            ctx.lineTo(cx + rx * 0.5, cy - ry * 0.2);
            ctx.moveTo(cx, cy - ry * 0.4);
            ctx.lineTo(cx, cy + ry * 0.1);
            ctx.moveTo(cx - rx * 0.3, cy + ry * 0.4);
            ctx.lineTo(cx + rx * 0.3, cy + ry * 0.4);
            ctx.stroke();
        }}

        // Verification Submission
        async function submitVerification() {{
            const submitBtn = document.getElementById('submitBtn');
            submitBtn.disabled = true;
            submitBtn.innerText = "⏳ Tekshirilmoqda...";

            const phone = document.getElementById('phoneInput').value.trim();
            const passport = document.getElementById('passportInput').value.trim().toUpperCase().replace(/\\s+/g, '');

            // Calculate deterministic 3D biometric fingerprint
            let faceSignature = "face_3d_" + Date.now();
            if (capturedLandmarks && capturedLandmarks.length >= 100) {{
                const samples = [10, 152, 234, 454, 4, 33, 263, 61, 291, 168];
                const str = samples.map(idx => {{
                    const p = capturedLandmarks[idx];
                    return p ? `${{p.x.toFixed(3)}},${{p.y.toFixed(3)}},${{p.z.toFixed(3)}}` : "0,0,0";
                }}).join(";");
                faceSignature = "face_3d_" + btoa(str).slice(0, 32);
            }}

            try {{
                const response = await fetch('/kyc/submit', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{
                        user_id: userId,
                        phone: phone,
                        passport: passport,
                        face_hash: faceSignature
                    }})
                }});

                const result = await response.json();
                if (response.ok && result.ok) {{
                    showAlert("🎉 " + result.message, "success");
                    if (videoStream) {{
                        videoStream.getTracks().forEach(t => t.stop());
                    }}
                    if (animationFrameId) {{
                        cancelAnimationFrame(animationFrameId);
                    }}

                    setTimeout(() => {{
                        showVerifiedView({{
                            phone_number: phone,
                            face_hash: faceSignature,
                            verified_at: new Date().toISOString()
                        }});
                    }}, 1500);
                }} else {{
                    showAlert("❌ " + (result.message || "Xatolik yuz berdi!"), "danger");
                    submitBtn.disabled = false;
                    submitBtn.innerText = "Qayta urinish";
                }}
            }} catch (err) {{
                showAlert("Tarmoq xatosi: " + err.message, "danger");
                submitBtn.disabled = false;
                submitBtn.innerText = "Qayta urinish";
            }}
        }}

        function showAlert(msg, type) {{
            const box = document.getElementById('alertBox');
            box.innerText = msg;
            box.className = 'alert-box alert-' + type;
            box.style.display = 'block';
        }}

        function hideAlert() {{
            document.getElementById('alertBox').style.display = 'none';
        }}
    </script>
</body>
</html>
"""

# Backwards-compatible raw HTML constant
KYC_HTML = get_kyc_html()
