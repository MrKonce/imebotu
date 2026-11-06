FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8

WORKDIR /app

# Sistem paketlerini güncelle ve temel araçları yükle
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libxml2-dev \
    libxslt-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Bağımlılıkları yükle
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Uygulama kodunu kopyala
COPY . .

# Veritabanını kalıcı depolamak için volume
VOLUME ["/app/data"]

# Varsayılan başlatma komutu (Sunucu Modu)
CMD ["python", "main.py", "--server"]
