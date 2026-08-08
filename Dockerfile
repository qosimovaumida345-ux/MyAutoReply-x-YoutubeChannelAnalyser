FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    gnupg \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Node.js 20 (for yt-dlp EJS n-challenge solver)
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/* \
    && node --version && npm --version

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download EJS challenge solver from GitHub
# This runs at BUILD TIME so it's cached in the Docker image
RUN yt-dlp --remote-components ejs:github \
    --skip-download \
    --extractor-args "youtube:player_client=tv_embedded" \
    "https://www.youtube.com/watch?v=dQw4w9WgXcQ" || echo "[WARNING] EJS pre-download failed, will retry at runtime"

COPY . .

EXPOSE 10000
CMD ["python", "main.py"]