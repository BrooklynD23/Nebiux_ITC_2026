#!/bin/sh
set -eu

APP_DIR=${APP_DIR:-$(pwd)}
cd "$APP_DIR"

if [ ! -f .env ]; then
  echo "Missing .env in $APP_DIR" >&2
  exit 1
fi

if [ -n "$(git status --porcelain)" ]; then
  echo "Refusing to deploy from a dirty checkout." >&2
  exit 1
fi

set -a
. ./.env
set +a

if [ -z "${ADMIN_API_TOKEN:-}" ]; then
  echo "ADMIN_API_TOKEN must be set in .env before deploy." >&2
  exit 1
fi

git fetch origin main
git checkout main
git pull --ff-only origin main

docker compose -f docker-compose.hosted.yml up -d --build --force-recreate

curl -fsS http://127.0.0.1:8000/health >/tmp/nebiux-health.json
curl -fsS http://127.0.0.1/ >/tmp/nebiux-home.html
curl -fsS http://127.0.0.1/admin >/tmp/nebiux-admin.html

noauth_code=$(curl -sS -o /tmp/nebiux-admin-noauth.json -w '%{http_code}' \
  http://127.0.0.1/admin/conversations?limit=1)
if [ "$noauth_code" != "401" ]; then
  echo "Expected 401 from unauthenticated admin API, got $noauth_code" >&2
  exit 1
fi

auth_code=$(curl -sS -o /tmp/nebiux-admin-auth.json -w '%{http_code}' \
  -H "Authorization: Bearer ${ADMIN_API_TOKEN}" \
  http://127.0.0.1/admin/conversations?limit=1)
if [ "$auth_code" != "200" ]; then
  echo "Expected 200 from authenticated admin API, got $auth_code" >&2
  exit 1
fi

printf 'Deploy verification complete.\n'
printf 'Health: %s\n' "$(cat /tmp/nebiux-health.json)"
