#!/usr/bin/env bash
# 云主机一键：挂上 listing-review nginx + 修 sw.js
# 用法: sudo bash /opt/xhs-cloud/cloud_deploy/scripts/fix_listing_review_nginx.sh
set -euo pipefail

SNIP_SRC="/opt/xhs-cloud/cloud_deploy/deploy/snippets/listing_review.conf"
SNIP_DST="/etc/nginx/snippets/listing_review.conf"
SW="/opt/digit-hub/apps/web/sw.js"

echo "== 1) 安装 snippet =="
[ -f "$SNIP_SRC" ] || { echo "缺少 $SNIP_SRC"; exit 1; }
cp -a "$SNIP_SRC" "$SNIP_DST"
echo "ok $SNIP_DST"

echo "== 2) 定位 monitor.xhs365.cn 配置 =="
mapfile -t CONFS < <(grep -Rl 'server_name.*monitor\.xhs365\.cn' /etc/nginx 2>/dev/null || true)
if [ ${#CONFS[@]} -eq 0 ]; then
  echo "未找到 monitor.xhs365.cn server；列出 conf:"
  ls -la /etc/nginx/conf.d/ /etc/nginx/sites-enabled/ 2>/dev/null || true
  exit 1
fi
printf '候选:\n'; printf '  %s\n' "${CONFS[@]}"

echo "== 3) 在含 xianyu_board 的 conf 里插入 include（若尚未） =="
TARGET=""
for f in "${CONFS[@]}"; do
  if grep -q 'xianyu_board' "$f" 2>/dev/null; then
    TARGET="$f"
    break
  fi
done
if [ -z "$TARGET" ]; then
  TARGET="${CONFS[0]}"
fi
echo "使用: $TARGET"
cp -a "$TARGET" "${TARGET}.bak.$(date +%Y%m%d%H%M%S)"

if grep -q 'snippets/listing_review.conf' "$TARGET"; then
  echo "已有 listing_review include，跳过插入"
else
  # 优先插在 xianyu_board include 下一行
  if grep -q 'snippets/xianyu_board.conf' "$TARGET"; then
    sed -i '/snippets\/xianyu_board.conf/a\    include /etc/nginx/snippets/listing_review.conf;' "$TARGET"
    echo "已插入到 xianyu_board include 之后"
  else
    # 插在第一个 server { 后
    awk '
      BEGIN{done=0}
      /server_name[[:space:]]+monitor\.xhs365\.cn/ && done==0 {
        print
        getline
        print
        print "    include /etc/nginx/snippets/listing_review.conf;"
        done=1
        next
      }
      {print}
    ' "$TARGET" > "${TARGET}.new"
    mv "${TARGET}.new" "$TARGET"
    echo "已插入到 server_name 附近"
  fi
fi

grep -n 'listing_review\|xianyu_board' "$TARGET" | head -20

echo "== 4) 修 sw.js bypass =="
if [ -f "$SW" ]; then
  cp -a "$SW" "${SW}.bak.$(date +%Y%m%d%H%M%S)"
  if grep -q 'listing-review' "$SW"; then
    echo "sw.js 已含 listing-review"
  elif grep -q 'pathname.startsWith("/xianyu/")' "$SW"; then
    python3 - <<'PY'
from pathlib import Path
p = Path("/opt/digit-hub/apps/web/sw.js")
t = p.read_text(encoding="utf-8")
old = 'if (u.pathname.startsWith("/xianyu/")) return;'
new = '''const BYPASS = ["/xianyu/", "/listing-review/", "/psyche/", "/api/"];
    if (BYPASS.some((p) => u.pathname.startsWith(p))) return;'''
if old not in t:
    # 宽松匹配
    import re
    t2, n = re.subn(
        r'if\s*\(\s*u\.pathname\.startsWith\(\s*"/xianyu/"\s*\)\s*\)\s*return\s*;',
        new,
        t,
        count=1,
    )
    if n == 0:
        raise SystemExit("sw.js 未找到 xianyu bypass 行，请手改")
    t = t2
else:
    t = t.replace(old, new, 1)
p.write_text(t, encoding="utf-8")
print("sw.js patched")
PY
  else
    echo "WARN: sw.js 无 xianyu bypass 行，请手改"
  fi
  grep -n 'listing-review\|BYPASS\|xianyu' "$SW" | head -10
else
  echo "WARN: 无 $SW"
fi

echo "== 5) nginx -t && reload =="
nginx -t
systemctl reload nginx

echo "== 6) 验收 =="
sleep 1
echo "--- local :8080 ---"
curl -sI http://127.0.0.1:8080/listing-review/ | head -15 || true
curl -s -o /dev/null -w "local_GET=%{http_code}\n" http://127.0.0.1:8080/listing-review/
echo "--- public ---"
curl -sI https://monitor.xhs365.cn/listing-review/ | head -20 || true
curl -s -o /dev/null -w "public_GET=%{http_code}\n" https://monitor.xhs365.cn/listing-review/
echo "--- body title ---"
curl -s https://monitor.xhs365.cn/listing-review/ | grep -oE '<title>[^<]+</title>' | head -3
echo "--- sw ---"
curl -s https://monitor.xhs365.cn/sw.js | grep -E 'listing-review|BYPASS' | head -5
echo "DONE"
