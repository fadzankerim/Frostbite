#!/usr/bin/env bash
# Frostbite - dodatno podešavanje VPN servera.
# Pokrenuti NAKON openvpn-install.sh:
#   sudo ./vpn-hardening.sh <privatna-IP-aplikacije> <CIDR-privatne-podmreže>
#   npr. sudo ./vpn-hardening.sh 10.0.140.25 10.0.128.0/20
#
# Šta radi:
#  1. Split tunnel: VPN klijenti kroz tunel šalju samo saobraćaj za privatnu podmrežu,
#     a ne sav internet saobraćaj.
#  2. NAT: aplikacijska instanca (privatna podmreža) dobija izlaz na internet preko
#     ovog servera (za apt update), bez plaćenog NAT Gateway-a.
#  3. Firewall: VPN klijenti mogu pristupiti SAMO aplikaciji na portovima 80 i 443.
#     Ne mogu na SSH aplikacije, na sam VPN server niti jedni na druge.
#  4. SSH hardening i automatske sigurnosne nadogradnje.
set -euo pipefail

USAGE="Upotreba: sudo $0 <privatna-IP-aplikacije> <CIDR-privatne-podmreže>"
APP_IP="${1:?$USAGE}"
PRIVATE_SUBNET="${2:?$USAGE}"

[[ $PRIVATE_SUBNET =~ ^([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)/([0-9]+)$ ]] \
  || { echo "[!] Neispravan CIDR: $PRIVATE_SUBNET (očekivano npr. 10.0.128.0/20)"; exit 1; }
NET="${BASH_REMATCH[1]}"; PREFIX="${BASH_REMATCH[2]}"
MASK_INT=$(( (0xFFFFFFFF << (32 - PREFIX)) & 0xFFFFFFFF ))
MASK="$(( MASK_INT >> 24 & 255 )).$(( MASK_INT >> 16 & 255 )).$(( MASK_INT >> 8 & 255 )).$(( MASK_INT & 255 ))"
PRIVATE_ROUTE="$NET $MASK"
echo "[i] Privatna podmreža: $PRIVATE_SUBNET (ruta za VPN klijente: $PRIVATE_ROUTE)"

[[ $EUID -eq 0 ]] || { echo "Pokrenite sa sudo."; exit 1; }

# --- Zaštita od pogrešnih argumenata ---------------------------------------
ip2int() { local IFS=.; read -r a b c d <<<"$1"; echo $(( (a<<24) + (b<<16) + (c<<8) + d )); }
in_subnet() { (( ( $(ip2int "$1") & MASK_INT ) == ( $(ip2int "$NET") & MASK_INT ) )); }
[[ $APP_IP =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]] || { echo "[!] Neispravna IP adresa aplikacije: $APP_IP"; exit 1; }
if hostname -I | tr ' ' '\n' | grep -qx "$APP_IP"; then
  echo "[!] $APP_IP je adresa OVOG servera (VPN). Navedite privatnu IP adresu instance fb-app."; exit 1
fi
in_subnet "$APP_IP" || { echo "[!] $APP_IP nije u podmreži $PRIVATE_SUBNET."; exit 1; }
for ip in $(hostname -I); do
  [[ $ip == *.*.*.* ]] && in_subnet "$ip" && { echo "[!] Ovaj server ($ip) je u podmreži $PRIVATE_SUBNET - to nije privatna podmreža aplikacije."; exit 1; }
done

IFACE=$(ip -4 route show default | awk '{print $5; exit}')
echo "[i] Mrežni interfejs: $IFACE"

# --- 1. Split tunnel -------------------------------------------------------
CONF=""
for f in /etc/openvpn/server/server.conf /etc/openvpn/server.conf; do
  [[ -f $f ]] && { CONF=$f; break; }
done
[[ -n $CONF ]] || { echo "[!] Nije pronađen server.conf - da li je openvpn-install.sh završen?"; exit 1; }
echo "[i] OpenVPN konfiguracija: $CONF"

cp -n "$CONF" "$CONF.orig" || true
sed -i -E 's/^push "redirect-gateway/# &/; s/^push "route-ipv6/# &/' "$CONF"
sed -i -E '/^push "route [0-9]/d' "$CONF"   # ukloni rute iz ranijih pokretanja
echo "push \"route $PRIVATE_ROUTE\"" >> "$CONF"

for svc in openvpn-server@server openvpn@server; do
  if systemctl is-enabled --quiet "$svc" 2>/dev/null; then
    systemctl restart "$svc"; echo "[i] Restartovan $svc"; break
  fi
done

# --- 2 + 3. NAT i firewall -------------------------------------------------
sysctl -w net.ipv4.ip_forward=1 >/dev/null
echo 'net.ipv4.ip_forward=1' > /etc/sysctl.d/99-fb-forward.conf

cat > /usr/local/sbin/fb-firewall.sh <<EOF
#!/usr/bin/env bash
# Generisano skriptom vpn-hardening.sh
set -e
APP_IP="$APP_IP"
PRIVATE_SUBNET="$PRIVATE_SUBNET"
IFACE="$IFACE"

# NAT za izlaz privatne podmreže na internet (vlastiti lanac, prazni se pri svakom pokretanju)
iptables -t nat -N FB_NAT 2>/dev/null || iptables -t nat -F FB_NAT
iptables -t nat -C POSTROUTING -j FB_NAT 2>/dev/null || iptables -t nat -A POSTROUTING -j FB_NAT
iptables -t nat -A FB_NAT -s \$PRIVATE_SUBNET -o \$IFACE -j MASQUERADE

# FORWARD lanac
iptables -N FB_FWD 2>/dev/null || iptables -F FB_FWD
iptables -C FORWARD -j FB_FWD 2>/dev/null || iptables -I FORWARD 1 -j FB_FWD
iptables -A FB_FWD -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
# VPN klijenti -> samo aplikacija, samo HTTP/HTTPS
iptables -A FB_FWD -i tun0 -d \$APP_IP -p tcp -m multiport --dports 80,443 -j ACCEPT
iptables -A FB_FWD -i tun0 -j DROP
# Aplikacija -> internet (apt update)
iptables -A FB_FWD -i \$IFACE -s \$PRIVATE_SUBNET -o \$IFACE -j ACCEPT

# INPUT sa VPN tunela: VPN klijenti ne smiju pristupati servisima samog VPN servera
iptables -N FB_IN 2>/dev/null || iptables -F FB_IN
iptables -C INPUT -i tun0 -j FB_IN 2>/dev/null || iptables -I INPUT 1 -i tun0 -j FB_IN
iptables -A FB_IN -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
iptables -A FB_IN -p icmp -j ACCEPT
iptables -A FB_IN -j DROP
EOF
chmod 750 /usr/local/sbin/fb-firewall.sh

cat > /etc/systemd/system/fb-firewall.service <<'EOF'
[Unit]
Description=Frostbite firewall i NAT pravila
After=network-online.target iptables-openvpn.service openvpn-server@server.service openvpn@server.service
Wants=network-online.target

[Service]
Type=oneshot
ExecStart=/usr/local/sbin/fb-firewall.sh
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable --now fb-firewall.service
systemctl restart fb-firewall.service
echo "[i] Firewall i NAT pravila aktivna."

# --- 4. SSH hardening i nadogradnje ---------------------------------------
cat > /etc/ssh/sshd_config.d/99-fb-hardening.conf <<'EOF'
PermitRootLogin no
PasswordAuthentication no
KbdInteractiveAuthentication no
PubkeyAuthentication yes
MaxAuthTries 3
X11Forwarding no
AllowAgentForwarding no
EOF
sshd -t && systemctl reload ssh
echo "[i] SSH: samo ključevi, root zabranjen."

apt-get update -qq
DEBIAN_FRONTEND=noninteractive apt-get install -y -qq unattended-upgrades >/dev/null
dpkg-reconfigure -f noninteractive unattended-upgrades
timedatectl set-timezone Europe/Sarajevo

echo
echo "[OK] VPN server podešen."
echo "     VPN klijenti vide samo https://$APP_IP"
echo "     VAŽNO: postojeće .ovpn datoteke i dalje rade (rute se šalju sa servera)."
