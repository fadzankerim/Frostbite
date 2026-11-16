#!/usr/bin/env bash
# Frostbite - osnovno podešavanje aplikacijske instance.
#   sudo ./01-osnova.sh <privatna-IP-VPN-servera>
set -euo pipefail

VPN_IP="${1:?Upotreba: sudo $0 <privatna-IP-VPN-servera>}"
VPC_CIDR="10.0.0.0/16"
APP_USER="frostbite"

[[ $EUID -eq 0 ]] || { echo "Pokrenite sa sudo."; exit 1; }
if [[ -d /etc/openvpn/server ]] || systemctl is-active --quiet openvpn-server@server 2>/dev/null; then
  echo "[!] Ovo je VPN server ($(hostname -I | awk '{print $1}')). Skripta je namijenjena instanci fb-app - provjerite HostName za fb-app u ~/.ssh/config."
  exit 1
fi

echo "[i] Provjera izlaza na internet (preko NAT-a na VPN serveru)..."
curl -s --max-time 10 -o /dev/null http://archive.ubuntu.com \
  || { echo "[!] Nema interneta. Provjerite rutu 0.0.0.0/0 -> VPN instanca, source/dest check i vpn-hardening.sh."; exit 1; }

timedatectl set-timezone Europe/Sarajevo

export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get upgrade -y -qq
apt-get install -y -qq ufw fail2ban unattended-upgrades curl ca-certificates >/dev/null
dpkg-reconfigure -f noninteractive unattended-upgrades

# --- Firewall (drugi sloj iza AWS Security Group) -------------------------
ufw --force reset >/dev/null
ufw default deny incoming
ufw default allow outgoing
ufw allow from "$VPN_IP" to any port 22 proto tcp comment 'SSH samo preko VPN servera'
ufw allow from "$VPC_CIDR" to any port 80 proto tcp comment 'HTTP -> redirect'
ufw allow from "$VPC_CIDR" to any port 443 proto tcp comment 'HTTPS'
ufw --force enable
ufw status verbose

# --- SSH hardening --------------------------------------------------------
cat > /etc/ssh/sshd_config.d/99-fb-hardening.conf <<'EOF'
PermitRootLogin no
PasswordAuthentication no
KbdInteractiveAuthentication no
PubkeyAuthentication yes
MaxAuthTries 3
X11Forwarding no
AllowAgentForwarding no
AllowTcpForwarding no
EOF
sshd -t && systemctl reload ssh

# --- fail2ban za SSH ------------------------------------------------------
cat > /etc/fail2ban/jail.d/fb.local <<'EOF'
[sshd]
enabled = true
maxretry = 5
bantime = 1h
EOF
systemctl enable --now fail2ban >/dev/null
systemctl restart fail2ban

# --- Sistemski korisnik i direktoriji za aplikaciju -----------------------
id "$APP_USER" >/dev/null 2>&1 || useradd --system --home /opt/frostbite --shell /usr/sbin/nologin "$APP_USER"
install -d -o "$APP_USER" -g "$APP_USER" -m 750 /opt/frostbite
install -d -o root -g "$APP_USER" -m 750 /etc/frostbite
install -d -o "$APP_USER" -g www-data -m 750 /var/log/frostbite

echo
echo "[OK] Osnova podešena. Sljedeće: sudo ./02-postgresql.sh"
