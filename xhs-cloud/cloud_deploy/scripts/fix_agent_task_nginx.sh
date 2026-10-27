#!/usr/bin/env bash
# 云主机一键：挂上 /agent-task nginx 反代 + 修 sw.js（防心象测劫持）
# 必须插进「真正生效」的 monitor 配置（通常已有 listing_review 的那份）
# 用法: sudo bash /opt/xhs-cloud/cloud_deploy/scripts/fix_agent_task_nginx.sh
set -euo pipefail

SNIP_SRC="/opt/xhs-cloud/cloud_deploy/deploy/snippets/agent_task.conf"
SNIP_DST="/etc/nginx/snippets/agent_task.conf"
SW="/opt/digit-hub/apps/web/sw.js"
INC_LINE='    include /etc/nginx/snippets/agent_task.conf;'

echo "== 1) 安装 snippet =="
[ -f "$SNIP_SRC" ] || { echo "缺少 $SNIP_SRC"; exit 1; }
cp -a "$SNIP_SRC" "$SNIP_DST"
echo "ok $SNIP_DST"

echo "== 2) 收集 monitor.xhs365.cn 真实配置文件（解析软链） =="
declare -A SEEN=()
TARGETS=()
while IFS= read -r f; do
  [ -z "$f" ] && continue
  real=$(readlink -f "$f" 2>/dev/null || echo "$f")
  [ -n "${SEEN[$real]:-}" ] && continue
  SEEN[$real]=1
  TARGETS+=("$real")
done < <(grep -Rl 'server_name.*monitor\.xhs365\.cn' /etc/nginx 2>/dev/null || true)

if [ ${#TARGETS[@]} -eq 0 ]; then
  echo "未找到 monitor.xhs365.cn server"
  exit 1
fi
printf '候选真实路径:\n'
for f in "${TARGETS[@]}"; do
  flags=""
  grep -q 'listing_review.conf' "$f" 2>/dev/null && flags="$flags [has-listing_review]"
  grep -q 'xianyu_board.conf' "$f" 2>/dev/null && flags="$flags [has-xianyu]"
  grep -q 'digit-hub\|try_files' "$f" 2>/dev/null && flags="$flags [spa-ish]"
  grep -q 'agent_task.conf' "$f" 2>/dev/null && flags="$flags [has-agent_task]"
  echo "  $f$flags"
done

pick_score() {
  local f="$1" s=0
  grep -q 'listing_review.conf' "$f" 2>/dev/null && s=$((s + 100))
  grep -q 'xianyu_board.conf' "$f" 2>/dev/null && s=$((s + 50))
  grep -q 'digit-hub\|try_files' "$f" 2>/dev/null && s=$((s + 40))
  [[ "$f" == *"/conf.d/"* ]] && s=$((s + 20))
  [[ "$f" == *"/sites-enabled/"* ]] && s=$((s + 10))
  [[ "$f" == *"/sites-available/"* ]] && s=$((s - 30))
  echo "$s"
}

echo "== 3) 按优先级插入 include（可插多份，避免挂到被 ignore 的重复 server） =="
# 先按分数排序，高分优先；但对所有「含 listing_review 或 spa-ish」的文件都确保有 include
SORTED=()
while IFS= read -r line; do
  SORTED+=("${line#*$'\t'}")
done < <(
  for f in "${TARGETS[@]}"; do
    printf '%s\t%s\n' "$(pick_score "$f")" "$f"
  done | sort -nr
)

patched=0
for f in "${SORTED[@]}"; do
  need=0
  grep -q 'listing_review.conf\|xianyu_board.conf\|digit-hub\|try_files' "$f" 2>/dev/null && need=1
  # 若只有一份候选，也必须改
  [ ${#SORTED[@]} -eq 1 ] && need=1
  # 最高分那份一定改
  [ "$f" = "${SORTED[0]}" ] && need=1
  [ "$need" -eq 0 ] && continue

  if grep -q 'snippets/agent_task.conf' "$f"; then
    echo "skip (already): $f"
    continue
  fi
  cp -a "$f" "${f}.bak.$(date +%Y%m%d%H%M%S)"
  if grep -q 'snippets/listing_review.conf' "$f"; then
    sed -i '/snippets\/listing_review.conf/a\    include /etc/nginx/snippets/agent_task.conf;' "$f"
    echo "patched after listing_review: $f"
  elif grep -q 'snippets/xianyu_board.conf' "$f"; then
    sed -i '/snippets\/xianyu_board.conf/a\    include /etc/nginx/snippets/agent_task.conf;' "$f"
    echo "patched after xianyu_board: $f"
  else
    # 插在第一个 location / 或 try_files 之前更稳；找不到则 server_name 后
    if grep -q 'location[[:space:]]\+/' "$f"; then
      # 在第一个 location 前插入
      awk -v line="$INC_LINE" '
        BEGIN{done=0}
        /^[[:space:]]*location[[:space:]]+\// && done==0 {
          print line
          done=1
        }
        {print}
      ' "$f" > "${f}.new"
      mv "${f}.new" "$f"
      echo "patched before location /: $f"
    else
      awk -v line="$INC_LINE" '
        BEGIN{done=0}
        /server_name[[:space:]]+monitor\.xhs365\.cn/ && done==0 {
          print
          getline
          print
          print line
          done=1
          next
        }
        {print}
      ' "$f" > "${f}.new"
      mv "${f}.new" "$f"
      echo "patched near server_name: $f"
    fi
  fi
  patched=$((patched + 1))
done

if [ "$patched" -eq 0 ]; then
  echo "WARN: 没有新插入（可能都已有）。继续验收。"
fi

echo "== 当前 include 分布 =="
grep -Rn 'agent_task.conf\|listing_review.conf' /etc/nginx/conf.d /etc/nginx/sites-enabled /etc/nginx/sites-available 2>/dev/null | head -40 || true

echo "== 4) 修 sw.js bypass =="
if [ -f "$SW" ]; then
  cp -a "$SW" "${SW}.bak.$(date +%Y%m%d%H%M%S)"
  if grep -q 'agent-task' "$SW"; then
    echo "sw.js 已含 agent-task"
  else
    python3 - <<'PY'
from pathlib import Path
import re
p = Path("/opt/digit-hub/apps/web/sw.js")
t = p.read_text(encoding="utf-8")
m = re.search(r'const BYPASS\s*=\s*\[([^\]]*)\]', t)
if m:
    inner = m.group(1)
    if "/agent-task/" in inner:
        print("BYPASS already has agent-task")
    else:
        new_inner = inner.rstrip()
        if new_inner and not new_inner.rstrip().endswith(","):
            new_inner = new_inner.rstrip() + ", "
        new_inner = new_inner + '"/agent-task/"'
        t = t[: m.start(1)] + new_inner + t[m.end(1) :]
        p.write_text(t, encoding="utf-8")
        print("sw.js BYPASS appended /agent-task/")
else:
    print("WARN: no BYPASS array")
PY
  fi
  grep -n 'agent-task\|BYPASS' "$SW" | head -10
else
  echo "WARN: 无 $SW"
fi

echo "== 5) nginx -t && reload =="
nginx -t
systemctl reload nginx

echo "== 6) 验收 =="
sleep 1
echo "--- local GET :8080 ---"
curl -s -o /dev/null -w "local_GET=%{http_code}\n" http://127.0.0.1:8080/agent-task/
curl -s http://127.0.0.1:8080/agent-task/ | grep -oE '<title>[^<]+</title>' | head -2
echo "--- public ---"
curl -sI https://monitor.xhs365.cn/agent-task/ | grep -iE 'HTTP/|X-Agent-Task|content-type|server:' || true
curl -s -o /dev/null -w "public_GET=%{http_code}\n" https://monitor.xhs365.cn/agent-task/
echo "--- public title ---"
curl -s https://monitor.xhs365.cn/agent-task/ | grep -oE '<title>[^<]+</title>' | head -3
echo "--- listing-review对照 ---"
curl -s https://monitor.xhs365.cn/listing-review/ | grep -oE '<title>[^<]+</title>' | head -2
curl -sI https://monitor.xhs365.cn/listing-review/ | grep -i X-Listing || true
echo "DONE"
