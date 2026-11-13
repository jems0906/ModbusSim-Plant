#!/usr/bin/env bash
set -euo pipefail

export PORT="${PORT:-8080}"
export MODBUS_HOST=127.0.0.1
export MODBUS_PORT=502
export ALARMAWATCH_MODBUS_HOST=127.0.0.1
export ALARMAWATCH_MODBUS_PORT=502
export ALARMAWATCH_AUDIT_API_URL=http://127.0.0.1:8000
export RAILWAY_READ_ONLY_DEMO=1

envsubst '${PORT}' < /etc/nginx/railway-nginx.conf.template > /etc/nginx/conf.d/default.conf
nginx -t

uvicorn api.main:app --host 127.0.0.1 --port 8000 &
plant_pid=$!
uvicorn alarmwatch.main:app --host 127.0.0.1 --port 8001 &
alarm_pid=$!
nginx -g 'daemon off;' &
nginx_pid=$!

shutdown() {
    kill "$plant_pid" "$alarm_pid" "$nginx_pid" 2>/dev/null || true
}
trap shutdown TERM INT

set +e
wait -n "$plant_pid" "$alarm_pid" "$nginx_pid"
result=$?
set -e
shutdown
exit "$result"