FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1
WORKDIR /app
# mise à jour et installation des dépendance
RUN apt-get update && apt-get install -y \
    build-essential \
    nmap \
    iproute2 \
    iputils-ping \
    vim \
    nano \
    net-tools \
    && apt install -y --no-install-recommends libexpat1 \
    && apt-get install -y --only-upgrade libexpat1 \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m pip install --upgrade pip 
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

#creation dossier logs
RUN mkdir -p /app/logs

EXPOSE 5000
# worker compatible WebSockets
CMD ["gunicorn", "--worker-class", "eventlet", "--bind", "0.0.0.0:5000", "app:app"]
