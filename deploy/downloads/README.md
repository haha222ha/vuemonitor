# 客户端安装包目录

将 Windows 安装包放到此目录后，用户可通过：

- `https://www.xhs365.cn/downloads/XHS365-Setup-latest.exe`
- `https://xhs365.cn/downloads/productanalyzer-version.json`（ProductAnalyzer 会员工具版本清单）
- `https://xhs365.cn/download`（下载页，读取 API `/api/v1/public/downloads`）

## 上传 ProductAnalyzer 安装包到生产机

```powershell
# 1. 复制安装包（示例）
Copy-Item "E:\...\ProductAnalyzer_Setup_20260706.exe" deploy\downloads\XHS365-Setup-latest.exe

# 2. 需已配置 SSH 密钥登录 root@47.239.181.111
cd E:\vuemonitor
py -3.11 scripts/upload_productanalyzer_installer.py
```

同步内容：安装包、版本 json、会员页 `member_portal.html`（含 PC 客户端下载入口）。

## 开发机构建（旧 XHS365 Electron 客户端）

```powershell
cd D:\vuemonitor\client
.\scripts\package-win.ps1
```

会复制到 `deploy/downloads/XHS365-Setup-latest.exe`。

## 生产机

`host-update.sh` 会同步到 `web-user/dist/downloads/`。  
若使用仓库内 `nginx/nginx.conf`，另有 `alias /opt/vuemonitor/deploy/downloads/`。

API `GET /api/v1/public/downloads` 会检测文件是否存在并返回 `installer_available`。
