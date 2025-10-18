FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    nmap \
    iputils-ping \
    net-tools \
    && apt install -y --no-install-recommends libexpat1 \
    && apt-get install -y --only-upgrade libexpat1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

#creation dossier logs
RUN mkdir -p /app/logs

EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "app:app"]
