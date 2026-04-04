#!/bin/bash
#
# SSL Certificate Setup Script
# Generates Let's Encrypt SSL certificates for the domain
#

set -eu

DOMAIN="${1:-}"
EMAIL="${2:-admin@example.com}"

if [ -z "$DOMAIN" ]; then
    echo "Usage: $0 <domain> [email]"
    echo "Example: $0 example.com admin@example.com"
    exit 1
fi

echo "Setting up SSL for $DOMAIN..."

# Stop nginx to free port 80
cd /srv/datacube
echo "Stopping nginx..."
docker compose stop nginx

# Install certbot if not installed
if ! command -v certbot > /dev/null 2>&1; then
    echo "Installing certbot..."
    sudo apt install -y certbot
fi

# Generate certificate
echo "Generating SSL certificate..."
sudo certbot certonly --standalone \
    -d "$DOMAIN" \
    --non-interactive \
    --agree-tos \
    --email "$EMAIL"

# Create SSL directory
mkdir -p deploy/ssl

# Copy certificates
echo "Copying certificates..."
sudo cp "/etc/letsencrypt/live/$DOMAIN/fullchain.pem" deploy/ssl/fullchain.pem
sudo cp "/etc/letsencrypt/live/$DOMAIN/privkey.pem" deploy/ssl/privkey.pem
sudo cp "/etc/letsencrypt/live/$DOMAIN/chain.pem" deploy/ssl/chain.pem

# Set permissions
sudo chown -R deploy:deploy deploy/ssl/
chmod 600 deploy/ssl/privkey.pem
chmod 644 deploy/ssl/fullchain.pem deploy/ssl/chain.pem

# Update nginx config with SSL
echo "Updating nginx configuration..."
cat > deploy/nginx/default.conf << NGINX_EOF
upstream api_backend {
    server api:8080;
}

server {
    listen 80;
    server_name $DOMAIN;
    return 301 https://\$host\$request_uri;
}

server {
    listen 443 ssl http2;
    server_name $DOMAIN;

    ssl_certificate /etc/nginx/ssl/fullchain.pem;
    ssl_certificate_key /etc/nginx/ssl/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;

    client_max_body_size 20m;

    location / {
        proxy_pass http://api_backend;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header Connection "";
    }

    location /health {
        proxy_pass http://api_backend/health;
        proxy_set_header Host \$host;
    }
}
NGINX_EOF

# Start nginx
echo "Starting nginx..."
docker compose up -d nginx

echo ""
echo "SSL setup completed!"
echo "Certificate location: /etc/letsencrypt/live/$DOMAIN/"
echo "Your site is now available at https://$DOMAIN"

# Set up auto-renewal
echo "Setting up auto-renewal..."
sudo crontab -l 2>/dev/null | grep -v "certbot renew" | sudo crontab -
echo "0 3 * * * /usr/bin/certbot renew --quiet --deploy-hook 'cd /srv/datacube && docker compose restart nginx'" | sudo crontab -

echo "Auto-renewal scheduled (runs daily at 3 AM)"