FROM python:3.10-slim

# System updates
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Requirements install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Code copy
COPY . .

# 🔥 Port 8000 expose karna zaroori hai Koyeb Web Service ke liye
EXPOSE 8000

CMD ["python", "main.py"]
