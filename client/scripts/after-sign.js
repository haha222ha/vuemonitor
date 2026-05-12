exports.default = async function (context) {
  console.log("[after-sign] 签名后处理...");

  const { appOutDir, packager } = context;
  const platform = packager.platform.name;

  if (platform === "windows") {
    console.log("[after-sign] Windows 签名验证...");
  } else if (platform === "mac") {
    console.log("[after-sign] macOS 签名验证...");
  }

  console.log("[after-sign] 签名后处理完成");
};