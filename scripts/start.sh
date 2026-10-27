#!/bin/sh
# Start the whole CRVR dev stack with one command.
#
#   sh scripts/start.sh            check the machine, build what changed, start db/backend/frontend,
#                                  wait until they answer, then print the URLs and demo accounts
#   sh scripts/start.sh --check    only run the checks (Docker installed and running, ports free, …)
#   sh scripts/start.sh --fresh    wipe the local database and evidence files first (asks to confirm;
#                                  add --yes to skip the question)
#   sh scripts/start.sh --logs     follow the logs once everything is up (Ctrl+C stops following)
#
# When something is missing it says what to do and exits non-zero. Safe to run again at any time —
# after a `git pull` it rebuilds only what changed and refreshes dependencies.
# Works in macOS/Linux terminals and on Windows in Git Bash or WSL.
set -eu

cd "$(dirname "$0")/.."

check_only=false
fresh=false
assume_yes=false
follow_logs=false
for arg in "$@"; do
  case "$arg" in
    --check) check_only=true ;;
    --fresh) fresh=true ;;
    --yes | -y) assume_yes=true ;;
    --logs) follow_logs=true ;;
    -h | --help)
      awk 'NR > 1 && /^#/ { sub(/^# ?/, ""); print; next } NR > 1 { exit }' "$0"
      exit 0
      ;;
    *)
      echo "Unknown option: $arg (try --help)" >&2
      exit 2
      ;;
  esac
done

if [ -t 1 ]; then
  bold=$(printf '\033[1m') red=$(printf '\033[31m') green=$(printf '\033[32m')
  yellow=$(printf '\033[33m') dim=$(printf '\033[2m') reset=$(printf '\033[0m')
else
  bold='' red='' green='' yellow='' dim='' reset=''
fi

problems=0
ok() { printf '  %s✓%s %s\n' "$green" "$reset" "$1"; }
note() { printf '    %s%s%s\n' "$dim" "$1" "$reset"; }
# warn/problem <summary> [what to do …]: each extra argument is printed as a line of advice
warn() {
  printf '  %s!%s %s\n' "$yellow" "$reset" "$1"
  shift
  for line in "$@"; do printf '      → %s\n' "$line"; done
}
problem() {
  problems=$((problems + 1))
  printf '  %s✗%s %s\n' "$red" "$reset" "$1"
  shift
  for line in "$@"; do printf '      → %s\n' "$line"; done
}
give_up() {
  printf '\n%sFix the %s problem(s) above, then run %ssh scripts/start.sh%s again.%s\n' \
    "$red" "$problems" "$bold" "$reset$red" "$reset"
  exit 1
}

case "$(uname -s)" in
  Darwin) os=mac ;;
  Linux) if grep -qi microsoft /proc/version 2>/dev/null; then os=wsl; else os=linux; fi ;;
  MINGW* | MSYS* | CYGWIN*) os=windows ;;
  *) os=other ;;
esac

# Value of a setting as docker compose sees it: shell environment first, then .env, then default.
setting() {
  eval "current=\${$1:-}"
  if [ -z "$current" ] && [ -f .env ]; then
    current=$(sed -n "s/^[[:space:]]*$1[[:space:]]*=[[:space:]]*//p" .env | tail -n 1 | tr -d "\r\"'")
  fi
  printf '%s' "${current:-$2}"
}

frontend_port=$(setting FRONTEND_PORT 5173)
backend_port=$(setting BACKEND_PORT 8000)
db_port=$(setting DB_PORT 5432)

printf '%sChecking your machine%s\n' "$bold" "$reset"

# 1. Docker CLI ------------------------------------------------------------------------------------
if ! command -v docker >/dev/null 2>&1; then
  case "$os" in
    mac) problem "Docker is not installed." \
      "Install Docker Desktop: https://docs.docker.com/desktop/setup/install/mac-install/" \
      "(pick Apple silicon or Intel to match your Mac — or: brew install --cask docker)" \
      "Open Docker Desktop once and finish its setup." ;;
    windows) problem "Docker is not installed." \
      "Install Docker Desktop (WSL 2 backend): https://docs.docker.com/desktop/setup/install/windows-install/" \
      "Open it once, finish its setup, then reopen this terminal." ;;
    wsl) problem "Docker is not available inside WSL." \
      "Install Docker Desktop on Windows: https://docs.docker.com/desktop/setup/install/windows-install/" \
      "Then Docker Desktop → Settings → Resources → WSL integration → turn it on for this distro." ;;
    *) problem "Docker is not installed." \
      "Install Docker Engine and the Compose plugin: https://docs.docker.com/engine/install/" \
      "Then let your user run it: sudo usermod -aG docker \$USER (log out and back in)." ;;
  esac
  give_up
fi
ok "Docker installed ($(docker --version 2>/dev/null | sed 's/^Docker version //; s/,.*//'))"

# 2. Compose v2 ------------------------------------------------------------------------------------
if ! docker compose version >/dev/null 2>&1; then
  if [ "$os" = linux ]; then
    problem "Docker Compose v2 is missing (the 'docker compose' command)." \
      "Install the plugin: https://docs.docker.com/compose/install/linux/ (package docker-compose-plugin)."
  else
    problem "Docker Compose v2 is missing (the 'docker compose' command)." \
      "Update Docker Desktop to the latest version — it includes Compose v2."
  fi
  give_up
fi
ok "Docker Compose $(docker compose version --short 2>/dev/null)"

# 3. Docker engine running -------------------------------------------------------------------------
if ! docker_error=$(docker info 2>&1 >/dev/null); then
  if printf '%s' "$docker_error" | grep -qi 'permission denied'; then
    problem "Your user is not allowed to use Docker." \
      "Run: sudo usermod -aG docker \$USER — then log out and back in."
  else
    case "$os" in
      mac) problem "Docker is installed but not running." \
        "Start Docker Desktop (open -a Docker) and wait until it says 'Engine running'." ;;
      windows | wsl) problem "Docker is installed but not running." \
        "Start Docker Desktop from the Start menu and wait until it says 'Engine running'." \
        "WSL: also check Settings → Resources → WSL integration is on for this distro." ;;
      *) problem "Docker is installed but the engine is not running." \
        "Run: sudo systemctl start docker" ;;
    esac
  fi
  give_up
fi
ok "Docker engine running"

memory_bytes=$(docker info --format '{{.MemTotal}}' 2>/dev/null || echo 0)
case "$memory_bytes" in '' | *[!0-9]*) memory_bytes=0 ;; esac
if [ "$memory_bytes" -gt 0 ] && [ "$memory_bytes" -lt 2000000000 ]; then
  warn "Docker has only $((memory_bytes / 1000000)) MB of memory — builds may fail or be slow." \
    "Docker Desktop → Settings → Resources → Memory: give it at least 4 GB."
fi

# 4. Line endings (Windows checkouts) --------------------------------------------------------------
cr=$(printf '\r')
if grep -l "$cr" backend/scripts/entrypoint.sh scripts/*.sh >/dev/null 2>&1; then
  problem "Shell scripts have Windows (CRLF) line endings — the backend container cannot run them." \
    "Run: git config --global core.autocrlf false" \
    "Then re-clone the repository (or, with no uncommitted work: git rm -rq --cached . && git reset --hard)."
else
  ok "Line endings OK"
fi

# 5. Ports -----------------------------------------------------------------------------------------
running_services=$(docker compose ps --status running --services 2>/dev/null || true)

port_owner() {
  if command -v lsof >/dev/null 2>&1; then
    lsof -nP -iTCP:"$1" -sTCP:LISTEN 2>/dev/null | awk 'NR == 2 { print $1 }'
  elif command -v ss >/dev/null 2>&1; then
    ss -ltn "sport = :$1" 2>/dev/null | grep -q LISTEN && echo "another program"
  elif command -v netstat >/dev/null 2>&1; then
    netstat -an 2>/dev/null | grep -Eq "[:.]$1[[:space:]].*LISTEN" && echo "another program"
  fi
  return 0
}

check_port() { # <service> <port> <.env variable> <suggested free port>
  if printf '%s\n' "$running_services" | grep -qx "$1"; then
    ok "Port $2 ($1) — already ours"
    return
  fi
  owner=$(port_owner "$2")
  if [ -z "$owner" ]; then
    ok "Port $2 ($1) is free"
    return
  fi
  case "$owner" in
    com.docke* | docker*) hint="Another Docker container uses it — see: docker ps (stop it with docker stop <name>)." ;;
    postgres*) hint="A local PostgreSQL uses it — stop it (brew services stop postgresql) or change the port." ;;
    *) hint="Stop that program, or change the port." ;;
  esac
  problem "Port $2 ($1) is in use by $owner." \
    "$hint" \
    "To change the port: cp .env.example .env, then set $3=$4 in .env."
}

check_port frontend "$frontend_port" FRONTEND_PORT 5174
check_port backend "$backend_port" BACKEND_PORT 8001
check_port db "$db_port" DB_PORT 5433

# 6. Settings --------------------------------------------------------------------------------------
if [ -f .env ]; then
  ok ".env found (custom settings)"
else
  ok "No .env — using the defaults (that's fine)"
fi
if ! command -v curl >/dev/null 2>&1; then
  warn "curl is not installed — cannot wait for the app to answer; will only start the containers."
fi

[ "$problems" -eq 0 ] || give_up

if $check_only; then
  printf '\n%sAll checks passed.%s Start with: sh scripts/start.sh\n' "$green" "$reset"
  exit 0
fi

# Start --------------------------------------------------------------------------------------------
if $fresh; then
  if ! $assume_yes; then
    printf '\n%sThis deletes your local database and uploaded evidence files.%s Continue? [y/N] ' "$yellow" "$reset"
    read -r answer || answer=
    case "$answer" in
      y | Y | yes) ;;
      *) echo "Cancelled." && exit 1 ;;
    esac
  fi
  docker compose down -v --remove-orphans
fi

printf '\n%sStarting CRVR%s %s(the first time builds images: a few minutes)%s\n' "$bold" "$reset" "$dim" "$reset"
build_failed() {
  printf '\n  %s✗%s Docker could not build or start the containers (see the messages above).\n' "$red" "$reset"
  note "Network error while downloading? Check your internet/VPN and run sh scripts/start.sh again."
  note "'no space left on device'? Free Docker disk space: docker system prune"
  note "More fixes: .agents/skills/dev-environment/SKILL.md → 'When something is wrong'."
  exit 1
}

# Rebuild only images whose Dockerfile or dependencies changed (fast when nothing did).
# Without build attestations an unchanged image keeps its ID, so running containers are left alone
# instead of being recreated on every start.
BUILDX_NO_DEFAULT_ATTESTATIONS=1 docker compose build || build_failed

# node_modules lives in an anonymous volume that outlives the container. When the frontend image
# was rebuilt (package.json changed after a pull), -V swaps in the new node_modules.
renew_volumes=
frontend_container=$(docker compose ps -aq frontend 2>/dev/null || true)
if [ -n "$frontend_container" ] &&
  [ "$(docker inspect -f '{{.Image}}' "$frontend_container" 2>/dev/null)" != \
    "$(docker image inspect -f '{{.Id}}' crvr-frontend 2>/dev/null)" ]; then
  renew_volumes=-V
fi
# shellcheck disable=SC2086 # renew_volumes is empty or a single flag
docker compose up -d --remove-orphans $renew_volumes || build_failed

show_failure() { # <service> <what happened>
  printf '\n  %s✗%s %s %s\n\n' "$red" "$reset" "$1" "$2"
  printf '%sLast lines of the %s log:%s\n' "$bold" "$1" "$reset"
  docker compose logs --tail 40 "$1" 2>&1 | sed 's/^/  /'
  printf '\n'
  case "$1" in
    backend) note "Usually a migration or import error. Fix it, or undo the last migration:" &&
      note "docker compose exec backend alembic downgrade -1 — or start over: sh scripts/start.sh --fresh" ;;
    frontend) note "'Cannot find module' → a dependency changed: run sh scripts/start.sh again." ;;
    db) note "Database will not start — sh scripts/start.sh --fresh resets it (deletes local data)." ;;
  esac
  note "More fixes: .agents/skills/dev-environment/SKILL.md → 'When something is wrong'."
  note "Full logs: docker compose logs $1"
  exit 1
}

wait_until_up() { # <service> <url> <seconds>
  printf '  waiting for %s ' "$1"
  waited=0
  until curl -fsS -o /dev/null --max-time 3 "$2" 2>/dev/null; do
    if ! docker compose ps --status running --services 2>/dev/null | grep -qx "$1"; then
      printf '\n'
      show_failure "$1" "stopped while starting."
    fi
    if [ "$waited" -ge "$3" ]; then
      printf '\n'
      show_failure "$1" "did not answer at $2 within $3 s."
    fi
    sleep 2
    waited=$((waited + 2))
    printf '.'
  done
  printf ' %s✓%s\n' "$green" "$reset"
}

if command -v curl >/dev/null 2>&1; then
  wait_until_up backend "http://localhost:$backend_port/api/health" 180
  wait_until_up frontend "http://localhost:$frontend_port/" 120
fi

cat <<EOF

${green}${bold}CRVR is running.${reset}

  App        http://localhost:$frontend_port
  API docs   http://localhost:$backend_port/api/docs

  Demo accounts (password ${bold}crvr-demo${reset}):
    developer@crvr.local   verifier@crvr.local   staff@crvr.local
    buyer@crvr.local       admin@crvr.local

  Logs       docker compose logs -f backend      (or frontend, db)
  Stop       docker compose down                 (your data is kept)
  Tests      docker compose exec backend pytest  ·  docker compose exec frontend npm test
EOF

if $follow_logs; then
  printf '\n'
  exec docker compose logs -f
fi
