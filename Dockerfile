FROM node:22-slim AS frontend-builder

WORKDIR /build/frontend
COPY frontend/package*.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    unzip \
    gnupg \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Deno (for yt-dlp EJS n-challenge solver - deno is enabled by default)
RUN curl -fsSL https://deno.land/install.sh | sh \
    && ln -s /root/.deno/bin/deno /usr/local/bin/deno \
    && deno --version

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download EJS challenge solver from GitHub
# This runs at BUILD TIME so it's cached in the Docker image
RUN yt-dlp --remote-components ejs:github \
    --skip-download \
    "https://www.youtube.com/watch?v=dQw4w9WgXcQ" || echo "[WARNING] EJS pre-download failed, will retry at runtime"

COPY . .
COPY --from=frontend-builder /build/static/dist ./static/dist
RUN cp ./static/dist/index.html ./index.html

CMD ["sh", "-c", "if [ \"$PORT\" = \"8080\" ]; then python worker.py; else python main.py; fi"]