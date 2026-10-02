FROM node:22-bookworm-slim

# Install Python 3, pip, curl, and required system libraries for image processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    python3-venv \
    curl \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Set up Python virtual environment
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Node dependencies for WhatsApp bridge
WORKDIR /app/whatsapp_bridge
COPY whatsapp_bridge/package*.json ./
RUN npm install --omit=dev --cache /tmp/npm-cache && rm -rf /tmp/npm-cache

WORKDIR /app

# Copy application source code
COPY . .

# Ensure entrypoint is executable
RUN chmod +x entrypoint.sh

# Persist data (auth_info and sqlite database)
VOLUME ["/app/data"]

EXPOSE 3000

CMD ["./entrypoint.sh"]
