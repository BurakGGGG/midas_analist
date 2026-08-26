# Midas Analist API — Cloud Run / herhangi bir konteyner ortamı için.
FROM python:3.12-slim

# yfinance ve pandas'ın derleme gerektirmeyen tekerlekleri var; yine de
# curl sağlık kontrolü için duruyor.
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /uygulama

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY cekirdek/ ./cekirdek/
COPY api/ ./api/

# Önbellek dizini: konteyner yeniden başlarsa veri yeniden iner.
# Cloud Run'da kalıcı disk yok; ilk istek yavaş olur, sonrası hızlı.
RUN mkdir -p veri/temel

ENV PYTHONUNBUFFERED=1 \
    PORT=8080

EXPOSE 8080

HEALTHCHECK --interval=60s --timeout=10s --start-period=90s \
  CMD curl -fsS http://localhost:${PORT}/saglik || exit 1

# Cloud Run PORT değişkenini kendisi verir.
CMD exec uvicorn api.main:app --host 0.0.0.0 --port ${PORT} --workers 1
