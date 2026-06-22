#!/bin/sh
# Usage: ./scripts/backup_db.sh
set -e
STAMP=$(date +%Y%m%d_%H%M%S)
FILE="backup_${STAMP}.sql"
docker exec rent-db mysqldump -u"${MYSQL_USER}" -p"${MYSQL_PASSWORD}" "${MYSQL_DATABASE}" > "backups/${FILE}"
echo "Saved backups/${FILE}"
