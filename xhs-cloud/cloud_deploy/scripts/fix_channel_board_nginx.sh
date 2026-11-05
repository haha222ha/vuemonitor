#!/usr/bin/env bash
# 云主机一键：挂上 /channel/ + /takeon/ nginx 反代 + 修 sw.js（防心象测劫持）
# 用法: sudo bash /opt/xhs-cloud/cloud_deploy/scripts/fix_channel_board_nginx.sh
set -euo pipefail

SNIP_SRC="/opt/xhs-cloud/cloud_deploy/deploy/snippets/channel_board.conf"
SNIP_DST="/etc/nginx/snippets/channel_board.conf"
TAKEON_SRC="/opt/xhs-cloud/cloud_deploy/deploy/snippets/takeon_board.conf"
TAKEON_DST="/etc/nginx/snippets/takeon_board.conf"
SW="/opt/digit-hub/apps/web/sw.js"

echo "== 1) 安装 snippet =="
[ -f "$SNIP_SRC" ] || { echo "缺少 $SNIP_SRC"; exit 1; }
cp -a "$SNIP_SRC" "$SNIP_DST"
echo "ok $SNIP_DST"
if [ -f "$TAKEON_SRC" ]; then
  cp -a "$TAKEON_SRC" "$TAKEON_DST"
  echo "ok $TAKEON_DST"
else
  echo "WARN: 缺 $TAKEON_SRC（跳过 takeon）"
fi

echo "== 2) 定位 monitor.xhs365.cn 配置 =="
mapfile -t CONFS < <(grep -Rl 'server_name.*monitor\.xhs365\.cn' /etc/nginx 2>/dev/null || true)
if [ ${#CONFS[@]} -eq 0 ]; then
  echo "未找到 monitor.xhs365.cn server；列出 conf:"
  ls -la /etc/nginx/conf.d/ /etc/nginx/sites-enabled/ 2>/dev/null || true
  exit 1
fi
printf '候选:\n'; printf '  %s\n' "${CONFS[@]}"

echo "== 3) 插入 include（优先挂在 listing_review / xianyu_board 旁） =="
TARGET=""
for f in "${CONFS[@]}"; do
  if grep -q 'listing_review\|xianyu_board' "$f" 2>/dev/null; then
    TARGET="$f"
    break
  fi
done
if [ -z "$TARGET" ]; then
  TARGET="${CONFS[0]}"
fi
echo "使用: $TARGET"
cp -a "$TARGET" "${TARGET}.bak.$(date +%Y%m%d%H%M%S)"

if grep -q 'snippets/channel_board.conf' "$TARGET"; then
  echo "已有 channel_board include，跳过插入"
else
  if grep -q 'snippets/listing_review.conf' "$TARGET"; then
    sed -i '/snippets\/listing_review.conf/a\    include /etc/nginx/snippets/channel_board.conf;' "$TARGET"
    echo "已插入到 listing_review include 之后"
  elif grep -q 'snippets/xianyu_board.conf' "$TARGET"; then
    sed -i '/snippets\/xianyu_board.conf/a\    include /etc/nginx/snippets/channel_board.conf;' "$TARGET"
    echo "已插入到 xianyu_board include 之后"
  else
    awk '
      BEGIN{done=0}
      /server_name[[:space:]]+monitor\.xhs365\.cn/ && done==0 {
        print
        getline
        print
        print "    include /etc/nginx/snippets/channel_board.conf;"
        done=1
        next
      }
      {print}
    ' "$TARGET" > "${TARGET}.new"
    mv "${TARGET}.new" "$TARGET"
    echo "已插入到 server_name 附近"
  fi
fi

# 顺带确保 listing-review 仍挂着（常被 nginx 重置弄丢）
if [ -f /opt/xhs-cloud/cloud_deploy/deploy/snippets/listing_review.conf ]; then
  cp -a /opt/xhs-cloud/cloud_deploy/deploy/snippets/listing_review.conf /etc/nginx/snippets/listing_review.conf
  if ! grep -q 'snippets/listing_review.conf' "$TARGET"; then
    sed -i '/snippets\/channel_board.conf/i\    include /etc/nginx/snippets/listing_review.conf;' "$TARGET" || true
    if ! grep -q 'snippets/listing_review.conf' "$TARGET"; then
      sed -i '/snippets\/xianyu_board.conf/a\    include /etc/nginx/snippets/listing_review.conf;' "$TARGET" || true
    fi
  fi
fi

# /takeon/ 防劫持
if [ -f "$TAKEON_DST" ]; then
  if grep -q 'snippets/takeon_board.conf' "$TARGET"; then
    echo "已有 takeon_board include，跳过插入"
  else
    sed -i '/snippets\/channel_board.conf/a\    include /etc/nginx/snippets/takeon_board.conf;' "$TARGET" || true
    if ! grep -q 'snippets/takeon_board.conf' "$TARGET"; then
      sed -i '/snippets\/listing_review.conf/a\    include /etc/nginx/snippets/takeon_board.conf;' "$TARGET" || true
    fi
    echo "已插入 takeon_board include"
  fi
fi

grep -n 'channel_board\|takeon_board\|listing_review\|xianyu_board' "$TARGET" | head -40

echo "== 4) 修 sw.js bypass =="
if [ -f "$SW" ]; then
  cp -a "$SW" "${SW}.bak.$(date +%Y%m%d%H%M%S)"
  python3 - <<'PY'
from pathlib import Path
import re
p = Path("/opt/digit-hub/apps/web/sw.js")
t = p.read_text(encoding="utf-8")
need = ["/xianyu/", "/listing-review/", "/channel/", "/takeon/", "/psyche/", "/api/", "/agent-task/"]
# 已有 BYPASS 数组则合并
m = re.search(r'const BYPASS\s*=\s*\[([^\]]*)\]', t)
if m:
    raw = m.group(1)
    have = re.findall(r'"([^"]+)"', raw)
    merged = []
    for x in have + need:
        if x not in merged:
            merged.append(x)
    new_arr = "const BYPASS = [" + ", ".join(f'"{x}"' for x in merged) + "]"
    t = t[: m.start()] + new_arr + t[m.end() :]
    p.write_text(t, encoding="utf-8")
    print("sw.js BYPASS merged:", merged)
elif 'pathname.startsWith("/xianyu/")' in t:
    old = 'if (u.pathname.startsWith("/xianyu/")) return;'
    new = (
        'const BYPASS = ["/xianyu/", "/listing-review/", "/channel/", "/takeon/", "/psyche/", "/api/", "/agent-task/"];\n'
        "    if (BYPASS.some((p) => u.pathname.startsWith(p))) return;"
    )
    if old in t:
        t = t.replace(old, new, 1)
    else:
        t2, n = re.subn(
            r'if\s*\(\s*u\.pathname\.startsWith\(\s*"/xianyu/"\s*\)\s*\)\s*return\s*;',
            new,
            t,
            count=1,
        )
        if n == 0:
            raise SystemExit("sw.js 未找到 xianyu bypass 行，请手改")
        t = t2
    p.write_text(t, encoding="utf-8")
    print("sw.js patched with BYPASS")
else:
    print("WARN: sw.js 无已知 bypass 模式，请手改加入 /channel/")
PY
  grep -n 'channel\|listing-review\|BYPASS\|xianyu' "$SW" | head -15
else
  echo "WARN: 无 $SW"
fi

echo "== 5) nginx -t && reload =="
nginx -t
systemctl reload nginx

echo "== 6) 验收 =="
sleep 1
echo "--- local :8080 /channel/ ---"
curl -sI http://127.0.0.1:8080/channel/ | head -15 || true
curl -s http://127.0.0.1:8080/channel/ | grep -oE '<title>[^<]+</title>|增量商品库' | head -5
echo "--- public /channel/ ---"
curl -sI https://monitor.xhs365.cn/channel/ | head -20 || true
curl -s https://monitor.xhs365.cn/channel/ | grep -oE '<title>[^<]+</title>|增量商品库|心象测' | head -5
echo "--- public /listing-review/ ---"
curl -s https://monitor.xhs365.cn/listing-review/ | grep -oE '<title>[^<]+</title>|闲鱼|心象测|筛选' | head -5
echo "--- public /takeon/ ---"
curl -sI https://monitor.xhs365.cn/takeon/ | tr -d '\r' | grep -iE 'HTTP/|X-Takeon-Board' | head -5 || true
curl -s https://monitor.xhs365.cn/takeon/ | grep -oE '<title>[^<]+</title>|takeon|跟品|心象测|密码' | head -5
echo "DONE"
