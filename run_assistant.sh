#!/bin/bash

# Navigate to project directory
cd "$(dirname "$0")"

echo "========================================================"
echo "📦 Starting ShippingAssistant & WhatsApp Gateway"
echo "========================================================"

# 1. Check if WhatsApp bridge is already running
if curl -s http://127.0.0.1:3000/status > /dev/null 2>&1; then
    echo "✅ WhatsApp Bridge is already running on port 3000."
else
    echo "🚀 Starting WhatsApp Bridge in background..."
    cd whatsapp_bridge
    nohup node server.js > ../whatsapp_bridge.log 2>&1 &
    cd ..
    sleep 3
fi

# 2. Run ShippingAssistant Daemon
echo "🚀 Starting Python Shipping Monitor (checking every 5 minutes)..."
python3 main.py --mode daemon --interval 300
