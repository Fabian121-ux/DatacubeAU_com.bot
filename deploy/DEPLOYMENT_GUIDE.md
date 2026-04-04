# Production Deployment Guide: Datacube WAHA + Backend on DigitalOcean

## Overview

This guide covers deploying the complete WhatsApp bot system on an Ubuntu VPS:
- **WAHA** (WhatsApp HTTP API) - Handles WhatsApp messaging
- **Backend API** - Processes messages, routes replies
- **PostgreSQL** - Database
- **Nginx** - Reverse proxy with SSL termination
- **Vercel Frontend** - Web interface (optional)

Architecture:
```
[WhatsApp User] → WAHA → Backend → WAHA → [WhatsApp User]
                    ↓
               PostgreSQL
```

---

## Table of Contents

1. [Server Preparation](#1-server-preparation)
2. [Docker Installation](#2-docker-installation)
3. [Project Deployment](#3-project-deployment)
4. [Systemd Services](#4-systemd-services)
5. [Firewall Configuration](#5-firewall-configuration)
6. [SSL/TLS Setup](#6-ssltls-setup)
7. [Monitoring & Backups](#7-monitoring--backups)
8. [Domain & Vercel](#8-domain--vercel)
9. [Testing Procedures](#9-testing-procedures)
10. [Troubleshooting](#10-troubleshooting)
11. [Maintenance](#11-maintenance)

---

## 1. Server Preparation

### 1.1 Initial Server Access

```bash
# Connect to your droplet
ssh root@YOUR_DROPLET_IP

# Create deployment user
adduser deploy
usermod -aG sudo deploy

# Exit and reconnect as deploy user
exit
ssh deploy@YOUR_DROPLET_IP
```

### 1.2 Server Hardening

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install essential packages
sudo apt install -y curl wget git ufw fail2ban unattended-upgrades

# Configure automatic security updates
sudo dpkg-reconfigure -plow unattended-upgrades
```

### 1.3 Create Project Directory

```bash
# Create project directory
sudo mkdir -p /srv/datacube
sudo chown deploy:deploy /srv/datacube
cd /srv/datacube
```

---

## 2. Docker Installation

### 2.1 Install Docker

```bash
# Install Docker
curl -fsSL https://get.docker.com | sh

# Add user to docker group
sudo usermod -aG docker deploy

# Enable Docker service
sudo systemctl enable docker
sudo systemctl start docker
```

### 2.2 Install Docker Compose

```bash
# Install Docker Compose v2
sudo curl -L "https://github.com/docker/compose/releases/download/v2.24.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Verify installation
docker compose version
```

### 2.3 Configure Docker Daemon

```bash
# Create Docker daemon config
sudo mkdir -p /etc/docker
sudo tee /etc/docker/daemon.json << 'EOF'
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  },
  "storage-driver": "overlay2"
}
EOF

# Restart Docker
sudo systemctl restart docker
```

---

## 3. Project Deployment

### 3.1 Upload Project Files

From your local machine:

```bash
# Navigate to project directory
cd /path/to/DatacubeAU_com.bot

# Upload to server (exclude unnecessary files)
rsync -avz --exclude '.git' --exclude '__pycache__' --exclude '*.pyc' \
  --exclude 'node_modules' --exclude '.env*' \
  -e "ssh -i ~/.ssh/your-key" \
  ./ deploy@YOUR_DROPLET_IP:/srv/datacube/
```

### 3.2 Environment Configuration

```bash
cd /srv/datacube

# Copy environment template
cp .env.production.example .env.production

# Edit with your settings
nano .env.production
```

**Required Environment Variables:**

| Variable | Example Value | Notes |
|----------|---------------|-------|
| `POSTGRES_USER` | `datacube` | Database user |
| `POSTGRES_PASSWORD` | `STRONG_PASSWORD_123` | Strong password |
| `POSTGRES_DB` | `datacube_bot` | Database name |
| `DATABASE_URL` | `postgresql+asyncpg://datacube:STRONG_PASSWORD_123@postgres:5432/datacube_bot` | Async connection string |
| `WAHA_SERVICE_URL` | `http://waha:3000` | Internal Docker URL |
| `WAHA_API_KEY` | `YOUR_WAHA_API_KEY` | From WAHA dashboard |
| `WAHA_SESSION_NAME` | `default` | WAHA session name |
| `WHATSAPP_HOOK_URL` | `http://api:8080/webhooks/waha` | Internal webhook |
| `PUBLIC_BASE_URL` | `https://your-domain.com` | Your public URL |
| `WAHA_BASE_URL` | `https://your-domain.com:3000` | External WAHA URL |
| `WAHA_HTTP_PORT` | `3000` | WAHA port |
| `PUBLIC_HTTP_PORT` | `80` | HTTP port |
| `BOT_WA_NUMBER` | `2349000000000` | Your WhatsApp number |

### 3.3 Build and Start Services

```bash
cd /srv/datacube

# Build images
docker compose build

# Start services
docker compose up -d

# Check status
docker compose ps
```

### 3.4 Verify Services

```bash
# Check all containers
docker compose ps

# Check API health
curl http://localhost:8080/health

# Check WAHA health
curl http://localhost:3000/api/health

# Check logs
docker compose logs -f api
docker compose logs -f waha
```

---

## 4. Systemd Services

### 4.1 Create Docker Compose Service

```bash
sudo tee /etc/systemd/system/datacube.service << 'EOF'
[Unit]
Description=Datacube Docker Compose Application
Requires=docker.service
After=network.target docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/srv/datacube
ExecStart=/usr/local/bin/docker compose up -d
ExecStop=/usr/local/bin/docker compose down
TimeoutStartSec=0
User=deploy
Group=deploy

[Install]
WantedBy=multi-user.target
EOF
```

### 4.2 Enable Service

```bash
sudo systemctl daemon-reload
sudo systemctl enable datacube
sudo systemctl start datacube

# Check status
sudo systemctl status datacube
```

---

## 5. Firewall Configuration

### 5.1 Configure UFW

```bash
# Enable UFW
sudo ufw --force enable

# Set default policies
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Allow SSH
sudo ufw allow 22/tcp comment 'SSH'

# Allow HTTP/HTTPS
sudo ufw allow 80/tcp comment 'HTTP'
sudo ufw allow 443/tcp comment 'HTTPS'

# Allow WAHA port (only if needed externally)
# sudo ufw allow 3000/tcp comment 'WAHA'

# Check status
sudo ufw status verbose
```

### 5.2 Configure Fail2Ban

```bash
# Configure fail2ban
sudo tee /etc/fail2ban/jail.local << 'EOF'
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

# Restart fail2ban
sudo systemctl restart fail2ban
```

---

## 6. SSL/TLS Setup

### 6.1 Install Certbot

```bash
# Install certbot
sudo snap install --classic certbot

# Allow certbot through firewall
sudo ufw allow --snaps certbot
```

### 6.2 Generate SSL Certificate

```bash
# Stop nginx temporarily
cd /srv/datacube
docker compose stop nginx

# Generate certificate
sudo certbot certonly --standalone -d your-domain.com --non-interactive --agree-tos --email your-email@example.com

# Copy certificates to project
sudo cp /etc/letsencrypt/live your-domain.com/fullchain.pem /srv/datacube/deploy/ssl/fullchain.pem
sudo cp /etc/letsencrypt/live your-domain.com/privkey.pem /srv/datacube/deploy/ssl/privkey.pem
sudo cp /etc/letsencrypt/live your-domain.com/chain.pem /srv/datacube/deploy/ssl/chain.pem
sudo chown -R deploy:deploy /srv/datacube/deploy/ssl/
```

### 6.3 Configure Nginx with SSL

Update `deploy/nginx/default.conf`:

```nginx
upstream api_backend {
    server api:8080;
}

server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /etc/nginx/ssl/fullchain.pem;
    ssl_certificate_key /etc/nginx/ssl/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;

    client_max_body_size 20m;

    location / {
        proxy_pass http://api_backend;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Connection "";
    }

    location /health {
        proxy_pass http://api_backend/health;
        proxy_set_header Host $host;
    }
}
```

Update docker-compose.yml volumes:

```yaml
nginx:
  volumes:
    - ./deploy/nginx/default.conf:/etc/nginx/conf.d/default.conf:ro
    - ./deploy/ssl:/etc/nginx/ssl:ro
```

### 6.4 Auto-Renewal

```bash
# Test renewal
sudo certbot renew --dry-run

# Create renewal cron
sudo crontab -e
# Add: 0 3 * * * /usr/bin/certbot renew --quiet --deploy-hook "cd /srv/datacube && docker compose restart nginx"
```

---

## 7. Monitoring & Backups

### 7.1 Log Aggregation

```bash
# Create log directory
mkdir -p /srv/datacube/deploy/logs

# Configure logging in docker-compose.yml
logging:
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "3"
```

### 7.2 Health Check Script

Create `deploy/scripts/health-check.sh`:

```bash
#!/bin/bash
set -eu

HOST="${1:-localhost}"
FAILED=0

echo "Checking services on $HOST..."

# Check API
if curl -sf "http://$HOST:80/health" > /dev/null 2>&1; then
    echo "✓ API is healthy"
else
    echo "✗ API is down"
    FAILED=1
fi

# Check WAHA
if curl -sf "http://$HOST:3000/api/health" > /dev/null 2>&1; then
    echo "✓ WAHA is healthy"
else
    echo "✗ WAHA is down"
    FAILED=1
fi

# Check Postgres
if docker compose exec -T postgres pg_isready -U datacube > /dev/null 2>&1; then
    echo "✓ PostgreSQL is healthy"
else
    echo "✗ PostgreSQL is down"
    FAILED=1
fi

# Check disk space
USAGE=$(df -h / | tail -1 | awk '{print $5}' | sed 's/%//')
if [ "$USAGE" -lt 80 ]; then
    echo "✓ Disk space OK ($USAGE%)"
else
    echo "✗ Disk space low ($USAGE%)"
    FAILED=1
fi

exit $FAILED
```

Make executable:

```bash
chmod +x deploy/scripts/health-check.sh
./deploy/scripts/health-check.sh
```

### 7.3 Automated Backups

Create `deploy/scripts/backup-cron.sh`:

```bash
#!/bin/bash
set -eu

BACKUP_DIR="/srv/datacube/deploy/backups"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
BACKUP_FILE="$BACKUP_DIR/datacube_bot_${TIMESTAMP}.dump"

mkdir -p "$BACKUP_DIR"

cd /srv/datacube
docker compose exec -T postgres pg_dump -U datacube -d datacube_bot -Fc > "$BACKUP_FILE"

# Keep only last 7 daily backups
cd "$BACKUP_DIR"
ls -t datacube_bot_*.dump | tail -n +8 | xargs -r rm

echo "Backup completed: $BACKUP_FILE"
```

Add to crontab:

```bash
crontab -e
# Add: 0 3 * * * /srv/datacube/deploy/scripts/backup-cron.sh
```

---

## 8. Domain & Vercel

### 8.1 Domain Configuration

1. In your domain registrar, create DNS records:

| Type | Name | Value |
|------|------|-------|
| A | @ | YOUR_DROPLET_IP |
| A | www | YOUR_DROPLET_IP |

2. Wait for DNS propagation (can take up to 24 hours)

### 8.2 Vercel Frontend Configuration

In your Vercel project settings:

**Environment Variables:**

| Variable | Value |
|----------|-------|
| `NEXT_PUBLIC_API_URL` | `https://your-domain.com` |
| `NEXT_PUBLIC_WAHA_URL` | `https://your-domain.com:3000` |

**Build Settings:**

- Framework Preset: Next.js
- Build Command: `npm run build`
- Output Directory: `.next`

---

## 9. Testing Procedures

### 9.1 Unit Tests

```bash
cd /srv/datacube

# Run tests
docker compose exec api python -m pytest

# Run with coverage
docker compose exec api python -m pytest --cov=app
```

### 9.2 Integration Tests

```bash
cd /srv/datacube

# Run health checks
./deploy/scripts/health-check.sh

# Test API endpoints
curl http://localhost:8080/health | jq .

# Test webhook endpoint
curl -X POST http://localhost:8080/webhooks/waha \
  -H "Content-Type: application/json" \
  -d '{
    "event": "message",
    "session": "default",
    "payload": {
      "id": "test_123",
      "from": "2349000000000@c.us",
      "to": "2349000000001@c.us",
      "body": "test"
    }
  }'
```

### 9.3 End-to-End WhatsApp Test

1. Open WhatsApp on your phone
2. Send a message to your bot's WhatsApp number
3. Verify the webhook is received:

```bash
# Check backend logs
docker compose logs api | grep -i webhook

# Check WAHA logs
docker compose logs waha | grep -i message
```

4. Verify reply is sent back

### 9.4 Performance Testing

```bash
# Load test with hey
docker run -it --rm --network datacube_datacube \
  r性hey -n 1000 -c 10 http://api:8080/health
```

---

## 10. Troubleshooting

### 10.1 Service Won't Start

```bash
# Check logs
docker compose logs service_name

# Check container status
docker compose ps

# Restart service
docker compose restart service_name
```

### 10.2 Database Connection Failed

```bash
# Check PostgreSQL
docker compose exec postgres pg_isready -U datacube

# Check connection from API
docker compose exec api python -c "from app.db import ping_database; import asyncio; asyncio.run(ping_database())"
```

### 10.3 WAHA Not Connecting

```bash
# Check WAHA API key
docker compose exec api env | grep WAHA_API_KEY

# Test WAHA connectivity
docker compose exec api curl http://waha:3000/api/health

# Check WAHA logs
docker compose logs waha
```

### 10.4 Webhook Not Working

```bash
# Verify webhook URL
docker compose exec api env | grep WHATSAPP_HOOK_URL

# Test webhook manually
docker compose exec waha curl -X POST http://api:8080/webhooks/waha \
  -H "Content-Type: application/json" \
  -d '{"event":"message","payload":{"id":"test"}}'
```

### 10.5 Port Already in Use

```bash
# Check what's using the port
sudo lsof -i :80
sudo lsof -i :3000
sudo lsof -i :5432

# Kill process if needed
sudo kill -9 PID
```

### 10.6 SSL Certificate Issues

```bash
# Check certificate validity
sudo certbot certificates

# Renewal test
sudo certbot renew --dry-run

# Manually renew if needed
sudo certbot renew --force-renewal
```

---

## 11. Maintenance

### 11.1 Daily Checklist

- [ ] Check service status: `docker compose ps`
- [ ] Check disk space: `df -h`
- [ ] Check logs for errors: `docker compose logs --tail=50`

### 11.2 Weekly Checklist

- [ ] Run health check: `./deploy/scripts/health-check.sh`
- [ ] Check backup files: `ls -la deploy/backups/`
- [ ] Check SSL certificate expiry
- [ ] Review error logs

### 11.3 Monthly Checklist

- [ ] Update Docker images: `docker compose pull`
- [ ] Review and rotate logs
- [ ] Test backup restoration
- [ ] Check for security updates

### 11.4 Update Procedure

```bash
cd /srv/datacube

# Pull latest images
docker compose pull

# Rebuild with changes
docker compose build

# Restart services
docker compose down
docker compose up -d

# Verify
./deploy/scripts/health-check.sh
```

---

## Quick Reference

### Common Commands

```bash
# Start/stop services
docker compose up -d
docker compose down

# View logs
docker compose logs -f
docker compose logs -f api

# Restart service
docker compose restart api

# SSH into container
docker compose exec api /bin/bash

# Database backup
docker compose exec -T postgres pg_dump -U datacube -d datacube_bot -Fc > backup.dump

# Database restore
docker compose exec -T postgres pg_restore -U datacube -d datacube_bot < backup.dump
```

### Ports

| Port | Service |
|------|---------|
| 80 | HTTP (Nginx) |
| 443 | HTTPS (Nginx) |
| 3000 | WAHA |
| 5432 | PostgreSQL |
| 8080 | API (internal) |

### Key URLs

| URL | Description |
|-----|-------------|
| `http://localhost:8080/health` | API health check |
| `http://localhost:3000/api/health` | WAHA health check |
| `http://localhost:3000/api/sessions/default` | WAHA session status |
| `https://your-domain.com` | Public API endpoint |