# 主机一键更新

每次本地 `git push` 之后，SSH 登录服务器，**复制下面这一行**执行即可（含自动拉代码，首次也可用）：

```bash
cd /opt/vuemonitor && sudo rm -rf client/node_modules/.vite 2>/dev/null; git fetch origin main && git reset --hard origin/main && bash scripts/host-update.sh
```
