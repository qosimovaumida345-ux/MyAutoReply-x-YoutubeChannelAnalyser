FROM python:3.11-slim

# Node.js o'rnatish (yt-dlp challenge solver uchun)
RUN apt-get update && apt-get install -y \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

# Python 3.11 tanlash (Render'da 3.14 bo'lsa ham 3.11 barqaror)
WORKDIR /app

# Requirements avval o'rnatish (cache uchun)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Kodni nusxalash
COPY . .

# Web server PORT
ENV PORT=10000

CMD ["python", "main.py"]
