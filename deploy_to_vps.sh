#!/bin/bash
set -e

if [ -z "$1" ]; then
    echo "Usage: ./deploy_to_vps.sh <VM_IP_ADDRESS> [SSH_KEY_PATH]"
    echo "Example: ./deploy_to_vps.sh 140.238.12.34 ~/.ssh/id_rsa"
    exit 1
fi

VM_IP="$1"
SSH_KEY="${2:-~/.ssh/id_rsa}"
SSH_USER="ubuntu"

echo "=========================================================="
echo "🚀 Deploying ShippingAssistant to Oracle Cloud VM: $VM_IP"
echo "=========================================================="

# Check SSH connection
echo "🔍 Testing SSH connection..."
ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no "$SSH_USER@$VM_IP" "echo 'Connected successfully to cloud server!'"

# 1. Sync project files (including authenticated WhatsApp session and .env)
echo "📦 Uploading project files..."
rsync -avz --exclude 'node_modules' --exclude '__pycache__' --exclude '.git' \
    -e "ssh -i $SSH_KEY" \
    ./ "$SSH_USER@$VM_IP:~/ShippingAssistant/"

# 2. Remote setup: Install Docker & Start container
echo "⚙️ Setting up Docker and starting 24/7 service on VM..."
ssh -i "$SSH_KEY" "$SSH_USER@$VM_IP" << 'EOF'
set -e
# Install Docker if not present
if ! command -v docker &> /dev/null; then
    echo "Installing Docker..."
    curl -fsSL https://get.docker.com | sh
    sudo usermod -aG docker $USER
fi

cd ~/ShippingAssistant

# Ensure data directory exists and preserve authenticated WhatsApp session
mkdir -p data/auth_info
if [ -d whatsapp_bridge/auth_info ] && [ "$(ls -A whatsapp_bridge/auth_info 2>/dev/null)" ]; then
    cp -rn whatsapp_bridge/auth_info/* data/auth_info/ 2>/dev/null || true
fi

# Build and start container with restart: always
echo "Starting Docker container..."
sudo docker compose down 2>/dev/null || true
sudo docker compose up -d --build

echo "Checking container status..."
sudo docker ps
EOF

echo ""
echo "=========================================================="
echo "🎉 SUCCESS! Your ShippingAssistant is now running 24/7 in the cloud!"
echo "Your laptop can now be completely turned off."
echo "=========================================================="
