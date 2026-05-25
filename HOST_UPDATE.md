# 主机一键更新

每次本地 `git push` 之后，SSH 登录服务器，**复制下面这一行**执行即可（含自动拉代码，首次也可用）：

```bash
cd /opt/vuemonitor && sudo rm -rf client/node_modules 2>/dev/null; git fetch origin main && git reset --hard origin/main && bash scripts/host-update.sh
```

健康检查失败时诊断（复制一行）：

```bash
bash /opt/vuemonitor/scripts/diagnose-api.sh
```

## 配置网易企业邮 SMTP（主机一行）

SSH 登录服务器后，**只改两处**：`SMTP_PASS` 里的授权码、`TEST_TO` 改成你要收测试信的邮箱，然后整行复制执行：

```bash
cd /opt/vuemonitor && git fetch origin main && git reset --hard origin/main && SMTP_PASS='粘贴网易授权码' TEST_TO='你的邮箱@example.com' bash scripts/configure_smtp.sh
```

（脚本默认 **994 + SSL**；阿里云上 587 常被网易断开。）

测试发信：

```bash
bash /opt/vuemonitor/scripts/run-server-cmd.sh /opt/vuemonitor/scripts/test_smtp.py --to 你的邮箱@example.com
```

不想把密码写在命令里：先 `git pull` 后只执行 `bash scripts/configure_smtp.sh`，按提示输入授权码。

测试发信（必须加载 `server/.env`，用下面任一行）：

```bash
bash /opt/vuemonitor/scripts/run-server-cmd.sh /opt/vuemonitor/scripts/test_smtp.py --to 你的邮箱@example.com
```
