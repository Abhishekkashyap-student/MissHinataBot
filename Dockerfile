FROM python:3.10-slim

# System updates
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy code
COPY . .

# Expose Port for Koyeb Health Check
EXPOSE 8000

# Start Bot
CMD ["python", "main.py"]
