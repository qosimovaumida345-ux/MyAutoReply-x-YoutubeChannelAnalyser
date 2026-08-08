FROM python:3.11-slim

# OS darajasidagi kutubxonalarni o'rnatish
# ffmpeg - videolarni birlashtirish uchun
# curl, gnupg - nodejs o'rnatish uchun
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# Node.js o'rnatish (yt-dlp youtube challenge ni aylanib o'tishi uchun)
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Ishchi katalogni yaratish
WORKDIR /app

# Talab qilinadigan Python kutubxonalarini nusxalash va o'rnatish
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Barcha kodlarni nusxalash
COPY . .

# Portni ochish (Render standart porti)
EXPOSE 10000

# Bot va serverni ishga tushirish
CMD ["python", "main.py"]
