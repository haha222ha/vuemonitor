const fs = require("fs");
const path = require("path");

exports.default = async function (context) {
  console.log("[after-pack] 打包后处理...");

  const appOutDir = context.appOutDir;
  const packager = context.packager;
  const platform = packager.platform.name;

  if (platform === "windows") {
    const versionPath = path.join(appOutDir, "version");
    fs.writeFileSync(versionPath, packager.appInfo.version, "utf-8");
    console.log(`[after-pack] 写入版本文件: ${packager.appInfo.version}`);
  }

  const buildResources = path.join(appOutDir, "build");
  if (fs.existsSync(buildResources)) {
    const files = fs.readdirSync(buildResources);
    console.log(`[after-pack] 构建资源: ${files.join(", ")}`);
  }

  console.log("[after-pack] 打包后处理完成");
};