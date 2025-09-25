#!/usr/bin/env bash
set -euo pipefail

echo "[1/7] Updating apt cache..."
export DEBIAN_FRONTEND=noninteractive
apt-get update -y

echo "[2/7] Installing MariaDB server and client..."
apt-get install -y mariadb-server mariadb-client

echo "[3/7] Enabling and starting MariaDB service..."
systemctl enable --now mariadb

CONF="/etc/mysql/mariadb.conf.d/50-server.cnf"
PORT_LINE="port = 30306"
echo "[4/8] Configuring bind-address and port in ${CONF}..."

# Ensure bind-address is 127.0.0.1 (local-only)
if grep -Eq '^\s*bind-address\s*=\s*' "$CONF"; then
  sed -i 's/^\s*bind-address\s*=.*/bind-address = 127.0.0.1/' "$CONF"
else
  printf '\n# Added by install_local_mariadb.sh\nbind-address = 127.0.0.1\n' >> "$CONF"
fi

# Ensure port is set to 30306 (idempotent)
if grep -Eq '^\s*port\s*=\s*' "$CONF"; then
  sed -i 's/^\s*port\s*=.*/port = 30306/' "$CONF"
else
  printf '\n# Added by install_local_mariadb.sh\nport = 30306\n' >> "$CONF"
fi

echo "[5/8] Restarting MariaDB to apply config..."
systemctl restart mariadb

# Load credentials from project .env (if present) and set safe defaults
echo "[6/8] Loading credentials from .env (if present)..."
ENV_FILE="/home/mongreldatalab/mongrel_price_ticker/src/.env"
if [ -f "$ENV_FILE" ]; then
  set -a
  . "$ENV_FILE"
  set +a
fi

DB_NAME="${DB_NAME:-u488367489_Price_Ticker}"
DB_USER="${DB_USER:-u488367489_mongrel_data}"
DB_PASS="${DB_PASSWORD:-}"
DB_PORT_CONF="${DB_PORT:-30306}"

# If DB_PASSWORD not provided, generate one and persist to .env
if [ -z "${DB_PASS}" ]; then
  echo "No DB_PASSWORD found in .env; generating a strong random password..."
  DB_PASS="$(tr -dc 'A-Za-z0-9' </dev/urandom | head -c 40)"
  mkdir -p "$(dirname "$ENV_FILE")"
  if [ -f "$ENV_FILE" ] && grep -Eq '^DB_PASSWORD=' "$ENV_FILE"; then
    sed -i "s/^DB_PASSWORD=.*/DB_PASSWORD=${DB_PASS}/" "$ENV_FILE"
  else
    printf '\nDB_PASSWORD=%s\n' "$DB_PASS" >> "$ENV_FILE"
  fi
  # Ensure required connection vars are present for local-only setup
  if ! grep -Eq '^DB_HOST=' "$ENV_FILE"; then echo 'DB_HOST=127.0.0.1' >> "$ENV_FILE"; fi
  if ! grep -Eq '^DB_PORT=' "$ENV_FILE"; then echo "DB_PORT=${DB_PORT_CONF}" >> "$ENV_FILE"; fi
  if ! grep -Eq '^DB_NAME=' "$ENV_FILE"; then echo "DB_NAME=${DB_NAME}" >> "$ENV_FILE"; fi
  if ! grep -Eq '^DB_USER=' "$ENV_FILE"; then echo "DB_USER=${DB_USER}" >> "$ENV_FILE"; fi
  chmod 600 "$ENV_FILE" || true
fi

echo "[7/8] Creating database and local-only user (idempotent)..."
# Use unix_socket auth as root (default on Ubuntu/MariaDB). This will not expose root password.
mariadb <<SQL
CREATE DATABASE IF NOT EXISTS \`${DB_NAME}\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS '${DB_USER}'@'127.0.0.1' IDENTIFIED BY '${DB_PASS}';
GRANT ALL PRIVILEGES ON \`${DB_NAME}\`.* TO '${DB_USER}'@'127.0.0.1';
DROP USER IF EXISTS '${DB_USER}'@'%';
FLUSH PRIVILEGES;
SQL

echo "[8/8] Verifying service status and open port..."
systemctl --no-pager status mariadb | sed -n '1,20p' || true
ss -ltnp | egrep ':30306|:3306' || true

echo "---"
echo "MariaDB installation and configuration complete."
echo "- Host: 127.0.0.1"
echo "- Port: 30306 (host)"
echo "- Database: ${DB_NAME}"
echo "- User: ${DB_USER}"
echo "Next steps:"
echo "1) Local test: mysql -h 127.0.0.1 -P 30306 -u ${DB_USER} -p\"\$DB_PASSWORD\" ${DB_NAME} -e 'SELECT 1;'"
echo "2) .env updated/used at ${ENV_FILE}. Keep it out of version control."

