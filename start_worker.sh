#!/bin/bash
set -e

echo "============================================================"
echo " 1. FFMPEG o'rnatilmoqda / tekshirilmoqda..."
echo "============================================================"
if ! command -v ffmpeg &> /dev/null; then
    sudo apt-get update -qq && sudo apt-get install -y -qq ffmpeg
fi
echo "✅ ffmpeg tayyor: $(which ffmpeg)"

echo "============================================================"
echo " 2. Worker server ishga tushmoqda..."
echo "============================================================"
# Eski worker jarayonlarini tozalash
pkill -f "python3 worker.py" || true
pkill -f "cloudflared" || true
sleep 1

python3 worker.py &
WORKER_PID=$!
sleep 2

echo "============================================================"
echo " 3. Cloudflare Tunnel ulanmoqda..."
echo "============================================================"
if [ ! -f ./cloudflared ]; then
    echo "Cloudflared yuklab olinmoqda..."
    curl -fsSL https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o ./cloudflared
    chmod +x ./cloudflared
fi

echo ""
echo "************************************************************"
echo " DIQQAT: Pastda 'https://...trycloudflare.com' chiqadi!"
echo " O'sha havolani nusxalang va Render -> WORKER_API_URL ga qo'ying!"
echo "************************************************************"
echo ""

./cloudflared tunnel --url http://localhost:8080
