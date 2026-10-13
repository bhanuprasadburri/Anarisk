#!/bin/sh
# Applies database migrations (never create_all) and then starts the given command.
set -e
if [ "${RUN_MIGRATIONS:-true}" = "true" ]; then
  echo "[entrypoint] alembic upgrade head"
  alembic upgrade head
fi
exec "$@"
