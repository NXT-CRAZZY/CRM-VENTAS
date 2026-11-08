#!/bin/sh
# Respaldo de PostgreSQL con rotación: 7 diarios, 4 semanales (domingo) y 12 mensuales (día 1).
# Variables de conexión: PGHOST, PGUSER, PGPASSWORD, PGDATABASE.
# IMPORTANTE: sincroniza /backups fuera del VPS (rclone, S3, otro servidor). Un respaldo en el
# mismo disco no protege ante la pérdida del servidor.
set -eu

DIR=/backups
STAMP=$(date +%Y-%m-%d_%H%M)
mkdir -p "$DIR/daily" "$DIR/weekly" "$DIR/monthly"

FILE="$DIR/daily/crm_$STAMP.dump"
pg_dump --format=custom --compress=9 --no-owner --file="$FILE"
pg_restore --list "$FILE" > /dev/null   # verifica que el archivo sea legible
echo "$(date -Iseconds) OK $FILE ($(du -h "$FILE" | cut -f1))"

[ "$(date +%u)" = "7" ] && cp "$FILE" "$DIR/weekly/"
[ "$(date +%d)" = "01" ] && cp "$FILE" "$DIR/monthly/"

ls -1t "$DIR/daily"/*.dump   2>/dev/null | tail -n +8  | xargs -r rm -f
ls -1t "$DIR/weekly"/*.dump  2>/dev/null | tail -n +5  | xargs -r rm -f
ls -1t "$DIR/monthly"/*.dump 2>/dev/null | tail -n +13 | xargs -r rm -f
