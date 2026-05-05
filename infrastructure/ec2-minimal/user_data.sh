#!/bin/bash
# EC2 bootstrap script — runs once on first boot
set -euo pipefail
exec > /var/log/user-data.log 2>&1

# ── System packages ───────────────────────────────────────────────────────────
dnf update -y
dnf install -y docker git

# ── Docker + Docker Compose ───────────────────────────────────────────────────
systemctl enable --now docker
usermod -aG docker ec2-user

# Docker Compose v2
mkdir -p /usr/local/lib/docker/cli-plugins
curl -SL https://github.com/docker/compose/releases/download/v2.27.0/docker-compose-linux-x86_64 \
  -o /usr/local/lib/docker/cli-plugins/docker-compose
chmod +x /usr/local/lib/docker/cli-plugins/docker-compose

# ── Caddy (reverse proxy + automatic SSL) ────────────────────────────────────
dnf install -y 'dnf-command(copr)'
dnf copr enable -y @caddy/caddy
dnf install -y caddy

# ── App directory ─────────────────────────────────────────────────────────────
mkdir -p /opt/spendi
chown ec2-user:ec2-user /opt/spendi

# ── Systemd service — restarts the stack on reboot ───────────────────────────
cat > /etc/systemd/system/spendi.service <<'EOF'
[Unit]
Description=Spendi App
After=docker.service network-online.target
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/spendi
ExecStart=/usr/local/lib/docker/cli-plugins/docker-compose -f docker-compose.prod.yml up -d
ExecStop=/usr/local/lib/docker/cli-plugins/docker-compose -f docker-compose.prod.yml down
User=ec2-user

[Install]
WantedBy=multi-user.target
EOF

systemctl enable spendi

echo "Bootstrap complete. Deploy your app to /opt/spendi and run: systemctl start spendi"
