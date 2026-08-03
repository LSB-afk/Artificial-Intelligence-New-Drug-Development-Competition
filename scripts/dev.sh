#!/usr/bin/env bash
#
# 콘솔을 띄웁니다. 파이썬 하네스(:8765)와 웹 개발 서버(:4173) 두 개가 필요하고,
# 둘 중 하나만 살아 있으면 화면은 열리지만 규칙은 돌지 않습니다.
#
#   ./scripts/dev.sh
#
# 조용히 반쯤 뜨느니 멈추는 쪽을 택합니다. 포트가 막혀 있으면 누가 잡고 있는지
# 알려주고 끝냅니다 — 밀린 포트로 뜬 개발 서버는 QA 게이트 기본 주소와 어긋나고,
# 죽은 줄 알았던 예전 서버를 계속 보게 만듭니다.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WEB_DIR="$REPO_ROOT/web_dongseop"
HARNESS_PORT="${H2L_HARNESS_PORT:-8765}"
WEB_PORT="${H2L_WEB_PORT:-4173}"

say() { printf '  %s\n' "$*"; }
die() { printf '\n오류: %s\n' "$*" >&2; exit 1; }

# `|| true` 가 필요합니다. lsof 는 찾은 게 없으면 1을 반환하고, `set -e`+`pipefail`
# 아래서는 그 1이 대입문을 실패시켜 스크립트를 아무 말 없이 죽입니다.
port_owner() { lsof -nP -iTCP:"$1" -sTCP:LISTEN -t 2>/dev/null | head -1 || true; }

require_free_port() {
  local port=$1 label=$2 pid
  pid="$(port_owner "$port")"
  [ -z "$pid" ] && return 0
  die "$label 포트 :$port 를 이미 다른 프로세스가 쓰고 있습니다 (PID $pid).
     무엇인지 확인:  ps -p $pid -o command=
     정리하려면:      kill $pid"
}

wait_for() {
  local url=$1 label=$2
  for _ in $(seq 1 60); do
    curl -sf "$url" >/dev/null 2>&1 && return 0
    sleep 1
  done
  die "$label 이(가) 60초 안에 응답하지 않았습니다: $url"
}

command -v python3 >/dev/null || die "python3 가 없습니다."
command -v node >/dev/null || die "node 가 없습니다."
command -v npm >/dev/null || die "npm 이 없습니다."

require_free_port "$HARNESS_PORT" "하네스"
require_free_port "$WEB_PORT" "웹"

# 락파일 기준으로 설치합니다. 재현 가능한 실행이 목적이므로 버전이 흔들리면 안 됩니다.
if [ ! -d "$WEB_DIR/node_modules" ]; then
  say "웹 의존성 설치 중 (npm ci)…"
  (cd "$WEB_DIR" && npm ci)
fi

HARNESS_PID=""
WEB_PID=""
cleanup() {
  trap - INT TERM EXIT
  printf '\n종료 중…\n'
  [ -n "$WEB_PID" ] && kill "$WEB_PID" 2>/dev/null || true
  [ -n "$HARNESS_PID" ] && kill "$HARNESS_PID" 2>/dev/null || true
  wait 2>/dev/null || true
}
trap cleanup INT TERM EXIT

say "하네스 기동 :$HARNESS_PORT"
(cd "$REPO_ROOT" && PYTHONPATH=src python3 -m h2l.server --host 127.0.0.1 --port "$HARNESS_PORT") &
HARNESS_PID=$!
wait_for "http://127.0.0.1:$HARNESS_PORT/api/health" "하네스"

say "웹 개발 서버 기동 :$WEB_PORT"
(cd "$WEB_DIR" && npm run dev) &
WEB_PID=$!
wait_for "http://127.0.0.1:$WEB_PORT/" "웹 개발 서버"

# 프록시까지 확인해야 "화면은 떴는데 규칙이 안 돈다"를 미리 잡습니다.
scenarios=$(curl -sf "http://127.0.0.1:$WEB_PORT/api/scenarios" \
  | python3 -c 'import json,sys; print(len(json.load(sys.stdin)["scenarios"]))' 2>/dev/null || echo 0)
[ "$scenarios" -gt 0 ] || die "웹 서버가 하네스에 닿지 못했습니다. /api 프록시를 확인하세요."

cat <<EOF

  콘솔      http://127.0.0.1:$WEB_PORT/
  하네스    http://127.0.0.1:$HARNESS_PORT/api/health
  시나리오  $scenarios 종 (연결 방식에서 "실제 하네스 API" 선택 가능)

  Ctrl-C 로 둘 다 종료합니다.

EOF

wait
