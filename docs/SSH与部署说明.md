# SSH 密钥与安装包部署说明

## 先分清两件事

| 目的 | 密钥在哪生成 | 公钥加到哪 | 私钥能否给别人 |
|------|-------------|-----------|---------------|
| **服务器 git pull**（拉代码） | 服务器上 | GitHub → Deploy keys | ❌ 绝不能 |
| **本机 scp 上传安装包**（推 277MB exe） | 你的 Windows 电脑 | 服务器 `~/.ssh/authorized_keys` | ❌ 绝不能 |

**私钥永远不要发给 AI、同事或贴到聊天里。**  
只需要把 **公钥**（`.pub` 文件里一行，以 `ssh-ed25519` 开头）加到对应位置。

---

## 方案 A：服务器拉代码（小文件：会员页、配置）

### 1. 服务器上执行

```bash
cd /opt/vuemonitor
git pull origin main   # 若已 clone
bash scripts/server-setup-github-deploy-key.sh
```

### 2. 复制脚本输出的公钥 → GitHub

仓库 **Settings → Deploy keys → Add deploy key**（只读即可）

### 3. 改 remote 并拉代码

```bash
cd /opt/vuemonitor
git remote set-url origin git@github.com-vuemonitor:haha222ha/vuemonitor.git
git fetch origin main && git reset --hard origin/main
bash scripts/host-update.sh
```

### 4. 选品云端会员页

```bash
rsync -a /opt/vuemonitor/xhs-cloud/cloud_deploy/ /opt/xhs-cloud/cloud_deploy/
cd /opt/xhs-cloud && bash cloud_deploy/scripts/host-update.sh
```

---

## 方案 B：本机上传安装包（大文件 exe，不能进 git）

安装包约 277MB，在 `.gitignore` 里，**必须 scp 上传**，不能靠 git pull。

### 1. Windows 上执行

```powershell
cd E:\vuemonitor
powershell -ExecutionPolicy Bypass -File scripts\local-setup-ssh-upload.ps1
```

### 2. 按提示把公钥加到服务器 `authorized_keys`

### 3. 测试

```powershell
ssh xhs365 "echo OK"
```

### 4. 告诉 Cursor「SSH 已配好 Host=xhs365」

会自动执行：

```powershell
py -3.11 scripts/upload_productanalyzer_installer.py --host xhs365
```

---

## 你可以发给 Cursor 的内容

✅ 「公钥已加到 GitHub / 服务器」  
✅ 「ssh xhs365 测试 OK」  
✅ 公钥文本（`.pub` 内容，用于核对）  

❌ 私钥文件、`id_ed25519` 无后缀文件、服务器 root 密码  

---

## 无 SSH 时的备选：手动上传

| 本地 | 服务器路径 |
|------|-----------|
| `deploy/downloads/XHS365-Setup-latest.exe` | `/opt/vuemonitor/deploy/downloads/` 和 `web-user/dist/downloads/` |
| `deploy/downloads/productanalyzer-version.json` | 同上 |
| `xhs-cloud/cloud_deploy/assets/member_portal.html` | `/opt/xhs-cloud/cloud_deploy/assets/` |

```bash
systemctl restart vuemonitor
systemctl restart xhs-cloud-api
```
