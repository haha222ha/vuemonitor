export type Platform = "xhs" | "douyin" | "taobao" | "jd" | "pdd" | string;

export const PLATFORM_LABELS: Record<Platform, string> = {
  xhs: "小红书",
  douyin: "抖音",
  taobao: "淘宝",
  jd: "京东",
  pdd: "拼多多",
};

export const PLATFORM_LIST: Platform[] = ["xhs", "douyin", "taobao", "jd", "pdd"];

export const PLATFORM_ADAPTER_FILES: Record<Platform, string> = {
  xhs: "xiaohongshu",
  douyin: "douyin",
  taobao: "taobao",
  jd: "jd",
  pdd: "pdd",
};
