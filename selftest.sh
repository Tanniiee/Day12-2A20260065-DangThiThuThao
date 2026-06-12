#!/usr/bin/env bash
# Self-test bộ tiêu chí Day 12 trên service đã deploy.
# Chạy trong GIT BASH:  bash selftest.sh <AGENT_API_KEY>
# (key truyền qua tham số, KHÔNG in ra màn hình — chụp ảnh an toàn)

URL=https://day12-2a202600685-dangthithuthao-production.up.railway.app
KEY="$1"

if [ -z "$KEY" ]; then
  echo "Cach dung: bash selftest.sh <AGENT_API_KEY>"
  exit 1
fi

echo "=== 1. Health check (liveness) ==="
curl -s "$URL/health"; echo; echo

echo "=== 2. Readiness (check Redis) ==="
curl -s "$URL/ready"; echo; echo

echo "=== 3. Khong co API key -> expect 401 ==="
curl -s -w " [HTTP %{http_code}]" -X POST "$URL/ask" \
  -H "Content-Type: application/json" \
  -d '{"user_id":"grader","question":"Hello"}'
echo; echo

echo "=== 4. Co API key -> expect 200 + citation ==="
curl -s -X POST "$URL/ask" -H "X-API-Key: $KEY" \
  -H "Content-Type: application/json" \
  -d '{"user_id":"grader","question":"Tội tàng trữ trái phép chất ma túy bị phạt thế nào?"}' \
  | head -c 700
echo; echo

echo "=== 5. Rate limit: 15 calls -> expect 200 x9 (da dung 1 o buoc 4) roi 429 ==="
for i in $(seq 1 15); do
  curl -s -o /dev/null -w "%{http_code} " -X POST "$URL/ask" \
    -H "X-API-Key: $KEY" -H "Content-Type: application/json" \
    -d '{"user_id":"grader","question":"test"}'
done
echo; echo
echo "=== DONE ==="
