#!/bin/sh
# Restaura un respaldo sobre la base de datos indicada (¡reemplaza su contenido!).
# Uso (desde el servidor):
#   docker compose -f infra/compose.prod.yml exec backup sh /restore.sh /backups/daily/crm_2026-10-30_0200.dump
# Recomendación: practicar la restauración una vez al mes en una base de prueba (PGDATABASE=crm_restore_test).
set -eu
FILE="${1:?Indica el archivo .dump a restaurar}"
echo "Restaurando $FILE en la base '$PGDATABASE' de $PGHOST..."
pg_restore --clean --if-exists --no-owner --exit-on-error --dbname="$PGDATABASE" "$FILE"
echo "Restauración completada."
