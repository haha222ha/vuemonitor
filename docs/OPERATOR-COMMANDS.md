# XHS365 运营执行指令（仅授权码 + QQ，不对接支付）

> 永久原则：**不接微信/支付宝/Stripe**。用户付款线下完成 → admin 后台生成授权码 → 用户在「设置」页激活。

---

## 一、每次发版后（服务器，复制一行）

```bash
cd /opt/vuemonitor && sudo chown -R "$(whoami):$(whoami)" "AI互联网信息量化" 2>/dev/null; git fetch origin main && git reset --hard origin/main && bash scripts/host-update.sh
```

成功标志：最后一行附近出现 **API health HTTP 200**。

---

## 二、全量自动验收（服务器，复制一行）

```bash
bash /opt/vuemonitor/scripts/verify_launch.sh
```

可选带 AI 测试（需 `.env` 里已配 `DEEPSEEK_API_KEY`）：

```bash
cd /opt/vuemonitor/server && source .venv/bin/activate && export PYTHONPATH=/opt/vuemonitor/server && RUN_AI=1 bash /opt/vuemonitor/scripts/run_sprints.sh
```

---

## 三、首次或重置管理员（服务器，改密码后执行）

```bash
cd /opt/vuemonitor/server && source .venv/bin/activate && export PYTHONPATH=/opt/vuemonitor/server && python3 ../scripts/seed_admin.py --email admin@xhs365.cn --password '你的强密码'
```

---

## 四、确认客服 QQ 配置（服务器）

```bash
grep '^SUPPORT_' /opt/vuemonitor/server/.env
curl -s https://api.xhs365.cn/api/v1/public/support | python3 -m json.tool
```

应看到 `"qq":"898382699"` 及二维码 URL。若要改 QQ 号：

```bash
cd /opt/vuemonitor && sed -i 's/^SUPPORT_QQ=.*/SUPPORT_QQ=你的QQ号/' server/.env && sudo systemctl restart vuemonitor
```

---

## 五、售卖流程（你每天在用的）

### 5.1 用户侧

1. 打开 https://www.xhs365.cn/register 注册（用户名 + 密码，邮箱可空）
2. 要升级：打开 https://www.xhs365.cn/purchase ，加 QQ 客服
3. 你收款后（微信转账等，**系统外操作**）
4. 用户打开 https://www.xhs365.cn/dashboard/settings → **授权码激活** → 粘贴你发的码

### 5.2 你（管理员）发码

1. 打开 https://admin.xhs365.cn 登录
2. 菜单 **主系统授权码** → **生成授权码**
3. 选套餐：`pro` / `premium` / `enterprise`，填天数、数量
4. 生成后点 **复制全部**，通过 QQ 发给用户
5. 需要存档时点 **导出 CSV**

参考价（可与用户另议）：Pro ¥49/月，Premium ¥149/月，Enterprise 议价。

---

## 六、浏览器手工验收（你本机，约 15 分钟）

逐项打勾：

- [ ] https://www.xhs365.cn/login 能登录
- [ ] https://www.xhs365.cn/purchase 有 QQ 小图，悬停有大图
- [ ] https://www.xhs365.cn/faq 能打开
- [ ] admin 生成 1 个 **Pro** 测试码（30 天）
- [ ] 测试账号在 **设置** 激活后套餐变为 Pro
- [ ] https://api.xhs365.cn/health 返回 healthy

---

## 七、Windows 客户端（可选，开发机执行）

**不要在 2G 服务器上 npm build。**

在 Windows 开发机：

```powershell
cd D:\vuemonitor
git pull origin main
cd client
.\scripts\package-win.ps1
```

将生成的 `deploy\downloads\XHS365-Setup-latest.exe` 提交并 push，再在服务器执行 **第一节** 的 `host-update.sh`。

用户下载页：https://www.xhs365.cn/download  
（无 exe 时会提示联系 QQ，属正常。）

---

## 八、外网快速探测（任意机器）

```bash
curl -sI https://api.xhs365.cn/health | head -3
curl -sI https://www.xhs365.cn/ | head -3
curl -sI https://admin.xhs365.cn/ | head -3
curl -s https://api.xhs365.cn/api/v1/public/support
```

---

## 九、明确不做的事

- 不配置微信支付 / 支付宝 / Stripe
- 不依赖网易 SMTP（验证码走 QQ 客服）
- 不在服务器上 `cd web-user && npm ci`（已用预构建 dist）

---

## 十、出问题先看日志

```bash
sudo journalctl -u vuemonitor -n 50 --no-pager
bash /opt/vuemonitor/scripts/diagnose-api.sh
```
