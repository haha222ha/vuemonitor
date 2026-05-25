import { describe, it, expect } from "vitest";
import { parseURL, parseBatchInput, detectPlatformFromInput, PLATFORM_ICONS, PLATFORM_COLORS } from "../../utils/urlParser";

describe("parseURL", () => {
  it("解析小红书商品链接", () => {
    const result = parseURL("https://www.xiaohongshu.com/explore/650a1b2c3d4e5f6a7b8c9d0e");
    expect(result).toEqual({
      platform: "xhs",
      targetType: "product_id",
      targetId: "650a1b2c3d4e5f6a7b8c9d0e",
      originalUrl: "https://www.xiaohongshu.com/explore/650a1b2c3d4e5f6a7b8c9d0e",
    });
  });

  it("解析小红书 discovery 链接", () => {
    const result = parseURL("https://www.xiaohongshu.com/discovery/item/650a1b2c3d4e5f6a7b8c9d0e");
    expect(result?.platform).toBe("xhs");
    expect(result?.targetType).toBe("product_id");
  });

  it("解析小红书用户主页", () => {
    const result = parseURL("https://www.xiaohongshu.com/user/profile/5a1b2c3d4e5f6a7b8c9d0e1f");
    expect(result).toEqual({
      platform: "xhs",
      targetType: "shop_id",
      targetId: "5a1b2c3d4e5f6a7b8c9d0e1f",
      originalUrl: expect.any(String),
    });
  });

  it("解析淘宝商品链接", () => {
    const result = parseURL("https://item.taobao.com/item.htm?id=123456789012");
    expect(result).toEqual({
      platform: "taobao",
      targetType: "product_id",
      targetId: "123456789012",
      originalUrl: expect.any(String),
    });
  });

  it("解析天猫商品链接", () => {
    const result = parseURL("https://detail.tmall.com/item.htm?id=987654321098");
    expect(result?.platform).toBe("taobao");
    expect(result?.targetId).toBe("987654321098");
  });

  it("解析京东商品链接", () => {
    const result = parseURL("https://item.jd.com/12345678.html");
    expect(result).toEqual({
      platform: "jd",
      targetType: "product_id",
      targetId: "12345678",
      originalUrl: expect.any(String),
    });
  });

  it("解析抖音视频链接", () => {
    const result = parseURL("https://www.douyin.com/video/7123456789012345678");
    expect(result).toEqual({
      platform: "douyin",
      targetType: "product_id",
      targetId: "7123456789012345678",
      originalUrl: expect.any(String),
    });
  });

  it("解析拼多多商品链接", () => {
    const result = parseURL("https://mobile.yangkeduo.com/goods.html?goods_id=123456789");
    expect(result).toEqual({
      platform: "pdd",
      targetType: "product_id",
      targetId: "123456789",
      originalUrl: expect.any(String),
    });
  });

  it("空输入返回 null", () => {
    expect(parseURL("")).toBeNull();
    expect(parseURL("   ")).toBeNull();
  });

  it("不支持的URL返回 null", () => {
    expect(parseURL("https://www.google.com/search?q=test")).toBeNull();
    expect(parseURL("not-a-url")).toBeNull();
  });
});

describe("parseBatchInput", () => {
  it("按换行分割多个URL", () => {
    const input = [
      "https://www.xiaohongshu.com/explore/650a1b2c3d4e5f6a7b8c9d0e",
      "https://item.jd.com/12345678.html",
    ].join("\n");

    const results = parseBatchInput(input);
    expect(results).toHaveLength(2);
    expect(results[0].platform).toBe("xhs");
    expect(results[1].platform).toBe("jd");
  });

  it("按逗号分割", () => {
    const input = "https://www.xiaohongshu.com/explore/abc123,https://item.jd.com/12345.html";
    const results = parseBatchInput(input);
    expect(results).toHaveLength(2);
  });

  it("按中文逗号分割", () => {
    const input = "https://www.xiaohongshu.com/explore/abc123，https://item.jd.com/12345.html";
    const results = parseBatchInput(input);
    expect(results).toHaveLength(2);
  });

  it("忽略空行", () => {
    const input = "\n\nhttps://www.xiaohongshu.com/explore/abc123\n\n";
    const results = parseBatchInput(input);
    expect(results).toHaveLength(1);
  });

  it("空输入返回空数组", () => {
    expect(parseBatchInput("")).toEqual([]);
    expect(parseBatchInput("   \n  ")).toEqual([]);
  });
});

describe("detectPlatformFromInput", () => {
  it("从URL检测小红书", () => {
    expect(detectPlatformFromInput("https://xiaohongshu.com/explore/abc")).toBe("xhs");
  });

  it("从关键词检测抖音", () => {
    expect(detectPlatformFromInput("抖音热门商品")).toBe("douyin");
  });

  it("从关键词检测淘宝", () => {
    expect(detectPlatformFromInput("淘宝好物推荐")).toBe("taobao");
  });

  it("从关键词检测京东", () => {
    expect(detectPlatformFromInput("京东自营")).toBe("jd");
  });

  it("从关键词检测拼多多", () => {
    expect(detectPlatformFromInput("拼多多百亿补贴")).toBe("pdd");
  });

  it("无法识别时返回空字符串", () => {
    expect(detectPlatformFromInput("随便一段文字")).toBe("");
  });
});

describe("PLATFORM_ICONS 和 PLATFORM_COLORS", () => {
  it("所有平台都有图标", () => {
    const platforms = ["xhs", "douyin", "taobao", "jd", "pdd"];
    for (const p of platforms) {
      expect(PLATFORM_ICONS[p]).toBeDefined();
    }
  });

  it("所有平台都有颜色", () => {
    const platforms = ["xhs", "douyin", "taobao", "jd", "pdd"];
    for (const p of platforms) {
      expect(PLATFORM_COLORS[p]).toMatch(/^#[0-9a-f]{6}$/i);
    }
  });
});
