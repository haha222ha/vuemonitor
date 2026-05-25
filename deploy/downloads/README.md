# 客户端安装包目录

将 Windows 安装包放到此目录后，用户可通过：

- `https://www.xhs365.cn/downloads/XHS365-Setup-latest.exe`

## 开发机构建

```powershell
cd D:\vuemonitor\client
.\scripts\package-win.ps1
```

会复制到 `deploy/downloads/XHS365-Setup-latest.exe`。

## 生产机

`host-update.sh` 会同步到 `web-user/dist/downloads/`。  
若使用仓库内 `nginx/nginx.conf`，另有 `alias /opt/vuemonitor/deploy/downloads/`。

API `GET /api/v1/public/downloads` 会检测文件是否存在并返回 `installer_available`。
