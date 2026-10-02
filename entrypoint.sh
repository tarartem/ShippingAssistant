#!/bin/sh
set -e

echo "=========================================================="
echo "🚀 Starting ShippingAssistant 24/7 Cloud Container"
echo "=========================================================="

mkdir -p /app/data/auth_info

if [ -z "$DATABASE_URL" ]; then
  if [ ! -L /app/whatsapp_bridge/auth_info ]; then
    if [ -d /app/whatsapp_bridge/auth_info ]; then
      cp -r /app/whatsapp_bridge/auth_info/. /app/data/auth_info/ 2>/dev/null || true
      rm -rf /app/whatsapp_bridge/auth_info
    fi
    ln -s /app/data/auth_info /app/whatsapp_bridge/auth_info
  fi
fi

# 1. Start WhatsApp Bridge in the background
echo "📡 Launching WhatsApp Bridge on port ${PORT:-3000}..."
cd /app/whatsapp_bridge
node server.js &
BRIDGE_PID=$!
cd /app

# Wait for bridge to initialize
echo "⏳ Waiting for WhatsApp Bridge to come online..."
sleep 5

# 2. Start Python Shipping Monitor in background
echo "📬 Launching Python Shipping Monitor..."
python3 main.py --mode daemon --interval 300 &
MONITOR_PID=$!

# Trap signals for graceful shutdown
trap "kill -TERM $BRIDGE_PID $MONITOR_PID; exit 0" SIGINT SIGTERM

echo "✅ All services running 24/7."
wait
