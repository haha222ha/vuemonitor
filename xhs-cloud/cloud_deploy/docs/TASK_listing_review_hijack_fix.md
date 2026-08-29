# 修复任务书：/listing-review/ 被心象测劫持

> **给执行 Agent 直接照做。** 模式对齐已修好的 `/xianyu/board/`。  
> 验收站：https://monitor.xhs365.cn/listing-review/  
> 对照：https://monitor.xhs365.cn/xianyu/board/  
> 本机仓库权威：`D:\vuemonitor\xhs-cloud\cloud_deploy\`（push 后主机 pull）

---

## 0. 现象

- 打开 `/listing-review/` 标题是「心象测」，页面空白/不对。
- 有时 Ctrl+F5 短暂正确，普通刷新又变心象测。
- 公网 `GET /listing-review/` 直接返回心象测 SPA HTML（~1711B，`title=心象测`）。
- **结论：服务端 nginx 已把该路径指到心象测；不只是浏览器缓存。**

## 1. 根因（两层，必须都修）

### A. nginx（主因）

`monitor.xhs365.cn` 上心象测 SPA 有 catch-all / `try_files`。  
`/listing-review/` 没有独立的 `^~` location → 落到心象测 `index.html`。  
与此前 `/xianyu/board/` 误挂心象测同类。

### B. Service Worker（次因，必修）

云上文件：`/opt/digit-hub/apps/web/sw.js`  
当前只排除 `/xianyu/`：

```js
if (u.pathname.startsWith("/xianyu/")) return;
```

未排除 `/listing-review/` → nginx 修好后旧 SW 仍可能劫持。

---

## 2. 修复目标

| 检查 | 期望 |
|---|---|
| `curl -sI https://monitor.xhs365.cn/listing-review/` | 200；**有** `X-Listing-Review`；**不是**心象测 |
| `curl -s …/listing-review/ \| head` | 标题含「闲鱼选品」或「云端人工筛选」 |
| `curl -s …/sw.js \| grep listing-review` | 有 bypass |
| 普通 F5 / 新标签 | 可进，不必依赖 Ctrl+F5 |

---

## 3. 架构说明（执行前必读）

筛选台 **业务已在 xhs-cloud-api（127.0.0.1:8080）**：

| 路径 | 作用 |
|---|---|
| `GET /listing-review/` | 密码门 |
| `POST /listing-review/login` | 设 cookie |
| `GET /listing-review/app/` | 筛选 UI（`assets/listing_review_cloud.html`） |
| `/api/v1/listing-review/*` | 批次 API |
| `/api/v1/sync/listing-*` | 本机推送 / 领任务 |

静态资源仓库路径：

- `xhs-cloud/cloud_deploy/assets/listing_review_cloud.html`
- `xhs-cloud/cloud_deploy/assets/listing_review_cloud/index.html`
- nginx 片段模板：`xhs-cloud/cloud_deploy/deploy/snippets/listing_review.conf`

**推荐方案（与现网代码一致，优先做这个）**：  
`location ^~ /listing-review/` → `proxy_pass http://127.0.0.1:8080`（xhs-cloud-api），  
**禁止**落到心象测 root 的 `try_files`。

**备选（完全对齐闲鱼静态目录）**：  
`alias /opt/xhs-cloud/data/listing_review/current/` + 另开 `^~` 把 `/listing-review/login` 与 `/api/v1/listing-review/` 反代到 `:8080`。  
若只挂静态、不反代 login/API，密码门会坏。

闲鱼对照（勿破坏）：

```bash
grep -n xianyu_board /etc/nginx/conf.d/monitor.xhs365.cn.conf
cat /etc/nginx/snippets/xianyu_board.conf
# 闲鱼 API → 8902；snippet 路径常为 /opt/xhs-cloud/data/xianyu_board/repo/
```

---

## 4. 执行步骤（按顺序）

### Step 1 — 勘察

```bash
sudo find /opt /var/www -iname '*listing*review*' 2>/dev/null | head -50
sudo ls -la /opt/xhs-cloud/cloud_deploy/assets/listing_review_cloud* 2>/dev/null
sudo ls -la /opt/xhs-cloud/data/ 2>/dev/null
sudo grep -RIn 'listing-review\|xianyu_board\|digit-hub\|try_files' /etc/nginx/ 2>/dev/null | head -60
curl -sI http://127.0.0.1:8080/listing-review/ | head -15
curl -s http://127.0.0.1:8080/listing-review/ | head -15
```

期望本机 `:8080` 已是正确密码门（标题「闲鱼选品 · 云端人工筛选」）。若 8080 正确、公网错误 → **纯 nginx 路由问题**。

若主机 `cloud_deploy` 缺文件：先 pull vuemonitor（`0284e904` 起含 listing-review），再 rsync 到 `/opt/xhs-cloud`。

### Step 2 — 写 nginx snippet（完整 tee，禁止 sed 插行）

```bash
sudo cp -a /etc/nginx/snippets/listing_review.conf /etc/nginx/snippets/listing_review.conf.bak.$(date +%Y%m%d%H%M%S) 2>/dev/null || true

sudo tee /etc/nginx/snippets/listing_review.conf >/dev/null <<'EOF'
# 小红书→闲鱼筛选台 — 禁止落到心象测 SPA
# 业务在 xhs-cloud-api :8080

location = /listing-review {
    return 301 /listing-review/;
}

location ^~ /listing-review/ {
    proxy_pass http://127.0.0.1:8080;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_read_timeout 120s;
    add_header Cache-Control "no-store, no-cache, must-revalidate" always;
    add_header X-Listing-Review "1" always;
}

# API 双保险（若根域 /api 曾被 SPA 抢）
location ^~ /api/v1/listing-review/ {
    proxy_pass http://127.0.0.1:8080;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    add_header X-Listing-Review "api" always;
}
EOF
```

在 **monitor.xhs365.cn** 的 `server {}` 里、**心象测 catch-all / try_files 之前** 增加：

```nginx
include /etc/nginx/snippets/listing_review.conf;
```

参考闲鱼 include 行位置，紧挨着放：

```bash
grep -n 'xianyu_board\|include.*snippet' /etc/nginx/conf.d/monitor.xhs365.cn.conf
```

然后：

```bash
sudo nginx -t && sudo systemctl reload nginx
```

`-t` 失败 → 立刻恢复 `.bak`，不要 reload。

**禁止**：`try_files $uri /index.html` 指到心象测 root。  
**禁止**：覆盖 `/etc/nginx/snippets/xianyu_board.conf`。

#### 若坚持纯静态（备选）

```bash
sudo mkdir -p /opt/xhs-cloud/data/listing_review/current
sudo cp -a /opt/xhs-cloud/cloud_deploy/assets/listing_review_cloud/index.html \
  /opt/xhs-cloud/data/listing_review/current/index.html
# alias 仅服务静态；login + /api/v1/listing-review/ 仍必须 ^~ 反代 :8080
```

### Step 3 — 扩展 sw.js 排除列表

```bash
sudo cp -a /opt/digit-hub/apps/web/sw.js /opt/digit-hub/apps/web/sw.js.bak.$(date +%Y%m%d%H%M%S)
sudo grep -n 'xianyu\|pathname.startsWith' /opt/digit-hub/apps/web/sw.js | head -20
```

把：

```js
if (u.pathname.startsWith("/xianyu/")) return;
```

改成：

```js
const BYPASS = ["/xianyu/", "/listing-review/", "/psyche/", "/api/"];
if (BYPASS.some((p) => u.pathname.startsWith(p))) return;
```

验收：

```bash
curl -s https://monitor.xhs365.cn/sw.js | grep -E 'listing-review|BYPASS|xianyu'
```

### Step 4 — HTML 入口卸敌对 SW

仓库 HTML 已含 `killHostileSW`（与闲鱼同款）。确认云上文件有该脚本：

```bash
grep -n killHostileSW /opt/xhs-cloud/cloud_deploy/assets/listing_review_cloud.html
grep -n killHostileSW /opt/xhs-cloud/cloud_deploy/assets/listing_review_cloud/index.html
```

若缺失：从 git pull / rsync 同步后再 `systemctl restart xhs-cloud-api`。

脚本内容（须在 `<head>` 最前）：

```html
<script>
(function killHostileSW(){
  try {
    if ("serviceWorker" in navigator) {
      navigator.serviceWorker.getRegistrations().then(function(rs){
        rs.forEach(function(r){ r.unregister(); });
      }).catch(function(){});
    }
    if (window.caches && caches.keys) {
      caches.keys().then(function(keys){
        keys.forEach(function(k){ caches.delete(k); });
      }).catch(function(){});
    }
  } catch (e) {}
})();
</script>
```

### Step 5 — 验收

```bash
curl -sI https://monitor.xhs365.cn/listing-review/ | head -n 20
curl -s https://monitor.xhs365.cn/listing-review/ | head -n 25
curl -s https://monitor.xhs365.cn/sw.js | grep listing-review
```

期望：

- 响应头含 `X-Listing-Review: 1`（或 `static`）
- `Cache-Control: no-store...`
- HTML **不是** `<title>心象测</title>`
- 含「闲鱼选品」或「云端人工筛选」或密码表单

浏览器（用户侧一次）：

1. 打开 `/listing-review/` → Ctrl+F5 一次  
2. 再普通 F5 / 新标签 → 不再是心象测  

---

## 5. 禁止事项

- 不要对 `/listing-review/` 使用 `try_files … /index.html` 指到心象测 root  
- 不要用超长交互式 git 要账号；缺文件用已 push 的 vuemonitor + rsync  
- 不要一次改光所有 nginx site；只动 `monitor.xhs365.cn` + 新 snippet  
- 不要覆盖已修好的 `xianyu_board.conf`（闲鱼 API→8902）  
- 改完必须 `nginx -t` 成功再 reload；失败立刻回滚 snippet 备份  

---

## 6. 对照表

| 项 | 闲鱼 `/xianyu/board/` | listing-review |
|---|---|---|
| 内容根 | `/opt/xhs-cloud/data/xianyu_board/repo/` | **推荐**反代 `:8080`；备选 `data/listing_review/current/` |
| nginx | `^~` + 无 SPA try_files | 同左 + `X-Listing-Review` |
| 响应头 | `X-Xianyu-Board` | `X-Listing-Review` |
| sw.js | skip `/xianyu/` | 追加 `/listing-review/` |
| HTML | killHostileSW | 同款 |
| API | 8902 | `:8080` 的 listing-review / sync listing-* |

闲鱼仓库：https://github.com/haha222ha/xianyu-advisor-board  
云上 SW：`/opt/digit-hub/apps/web/sw.js`

---

## 7. 一句话

先把 nginx 把 `/listing-review/` 从心象测 SPA 摘出来挂到 **xhs-cloud-api:8080**（或真实静态目录），再让 `/sw.js` 与页面入口都不再劫持该路径。只清浏览器不够——当前公网 HTML 已经是心象测壳子。
