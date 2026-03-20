#!/bin/bash
set -e

echo "============================================"
echo "  Tunnel VPS Setup Script"
echo "============================================"

echo "[1/10] Updating system packages..."
apt update && apt upgrade -y

echo "[2/10] Installing Docker and Docker Compose..."
apt install -y docker.io docker-compose-plugin
systemctl enable --now docker

echo "[3/10] Installing essential tools..."
apt install -y curl wget git ufw unzip

echo "[4/10] Creating tunnel system user..."
useradd --system --no-create-home --shell /usr/sbin/nologin tunnel || true
mkdir -p /etc/tunnel/authorized_keys
touch /etc/tunnel/authorized_keys/tunnel
chmod 600 /etc/tunnel/authorized_keys/tunnel
chown -R tunnel:tunnel /etc/tunnel

echo "[5/10] Configuring SSH..."
if ! grep -q "ForceCommand /usr/local/bin/tunnel-ssh-handler" /etc/ssh/sshd_config; then
    cat >> /etc/ssh/sshd_config << 'EOF'

# Tunnel service configuration
Match User tunnel
    AllowTcpForwarding yes
    X11Forwarding no
    AllowAgentForwarding no
    PermitTTY no
    ForceCommand /usr/local/bin/tunnel-ssh-handler
    AuthorizedKeysFile /etc/tunnel/authorized_keys/%u
    PermitOpen any
    GatewayPorts clientspecified
    ClientAliveInterval 30
    ClientAliveCountMax 3
EOF
fi

echo "[6/10] Installing SSH handler..."
cp infra/tunnel-ssh-handler /usr/local/bin/
chmod +x /usr/local/bin/tunnel-ssh-handler
chown tunnel:tunnel /usr/local/bin/tunnel-ssh-handler

echo "[7/10] Configuring firewall..."
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

echo "[8/10] Restarting SSH..."
systemctl restart sshd

echo "[9/10] Cloning repository..."
if [ ! -d /opt/tunnel ]; then
    git clone https://github.com/nawaz/tunnel.git /opt/tunnel || git clone $(git remote get-url origin) /opt/tunnel
fi
cd /opt/tunnel

echo "[10/10] Ready for deployment!"
echo ""
echo "Next steps:"
echo "  1. Copy .env.example to .env and fill in your values"
echo "  2. Run: docker compose up -d"
echo "  3. Run: docker compose exec api python -m app.scripts.init_port_pool"
echo "  4. Run: docker compose exec api alembic upgrade head"
echo ""
echo "============================================"
echo "  Setup complete!"
echo "============================================"
