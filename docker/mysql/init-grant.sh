#!/bin/bash
# Runs once on first DB init. Env vars are provided by the MySQL image.
set -euo pipefail
mysql -uroot -p"${MYSQL_ROOT_PASSWORD}" <<-EOSQL
  GRANT ALL PRIVILEGES ON \`${MYSQL_DATABASE}\`.* TO '${MYSQL_USER}'@'%';
  FLUSH PRIVILEGES;
EOSQL
