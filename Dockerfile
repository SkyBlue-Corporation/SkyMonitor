FROM python:3.14.0-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    nmap \
    iputils-ping \
    net-tools \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "app:app"]
