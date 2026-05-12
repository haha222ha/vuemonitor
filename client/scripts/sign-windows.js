const { execSync } = require("child_process");
const path = require("path");

exports.default = async function (configuration) {
  const { path: filePath, name } = configuration;

  console.log(`[sign-windows] 签名文件: ${name || path.basename(filePath)}`);

  const certFile = process.env.WIN_CERTIFICATE_FILE;
  const certPassword = process.env.WIN_CERTIFICATE_PASSWORD;

  if (!certFile || !certPassword) {
    console.log("[sign-windows] 未配置签名证书，跳过代码签名");
    return;
  }

  try {
    const signtoolPath = "signtool.exe";
    const cmd = [
      `"${signtoolPath}"`,
      "sign",
      "/fd", "SHA256",
      "/f", `"${certFile}"`,
      "/p", `"${certPassword}"`,
      "/tr", "http://timestamp.digicert.com",
      "/td", "SHA256",
      "/v",
      `"${filePath}"`,
    ].join(" ");

    execSync(cmd, { stdio: "inherit" });
    console.log(`[sign-windows] 签名成功: ${name || path.basename(filePath)}`);
  } catch (err) {
    console.error(`[sign-windows] 签名失败: ${err.message}`);
    throw err;
  }
};