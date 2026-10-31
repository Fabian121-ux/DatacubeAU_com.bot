#!/bin/bash
#
# Server Quick Setup Script
# Runs initial server configuration for Docker deployment
#

set -eu

echo "========================================="
echo "Datacube Server Quick Setup"
echo "========================================="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root: sudo $0"
    exit 1
fi

echo "[1/8] Updating system..."
apt update && apt upgrade -y

echo "[2/8] Installing essential packages..."
apt install -y curl wget git ufw fail2ban

echo "[3/8] Installing Docker..."
if ! command -v docker > /dev/null 2>&1; then
    curl -fsSL https://get.docker.com | sh
    usermod -aG docker deploy
fi

echo "[4/8] Installing Docker Compose..."
if ! command -v docker-compose > /dev/null 2>&1; then
    curl -L "https://github.com/docker/compose/releases/download/v2.24.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
fi

echo "[5/8] Configuring Docker daemon..."
mkdir -p /etc/docker
cat > /etc/docker/daemon.json << 'EOF'
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  },
  "storage-driver": "overlay2"
}
EOF
systemctl restart docker

echo "[6/8] Configuring firewall..."
ufw --force enable
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp comment 'SSH'
ufw allow 80/tcp comment 'HTTP'
ufw allow 443/tcp comment 'HTTPS'
# ufw allow 3000/tcp comment 'WAHA'

echo "[7/8] Configuring fail2ban..."
cat > /etc/fail2ban/jail.local << 'EOF'
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 5

[sshd]
enabled = true
port = ssh
filter = sshd
logpath = /var/log/auth.log
maxretry = 3
EOF
systemctl restart fail2ban

echo "[8/8] Creating directories..."
mkdir -p /srv/datacube
mkdir -p /srv/datacube/deploy/backups
mkdir -p /srv/datacube/deploy/logs
mkdir -p /srv/datacube/deploy/ssl
chown -R deploy:deploy /srv/datacube

echo ""
echo "========================================="
echo "Server setup completed!"
echo "========================================="
echo ""
echo "Next steps:"
echo "  1. Upload project files to /srv/datacube"
echo "  2. Configure .env.production"
echo "  3. Run: cd /srv/datacube && docker compose up -d"
echo ""
echo "Useful commands:"
echo "  docker compose ps     - Check services"
echo "  docker compose logs - View logs"
echo "  ./deploy/scripts/health-check.sh - Run health check"