import { z } from "zod";

const XHSNoteSchema = z.object({
  platform: z.literal("xhs"),
  platform_product_id: z.string().min(1),
  product_name: z.string().min(1).max(500),
  shop_name: z.string().optional().nullable(),
  category: z.string().optional().nullable(),
  image_url: z.string().url().optional().nullable().or(z.literal("")),
  product_url: z.string().optional().nullable(),
  price: z.number().nonnegative().optional().nullable(),
  original_price: z.number().nonnegative().optional().nullable(),
  sales_count: z.number().int().nonnegative().optional().nullable(),
  monthly_sales: z.number().int().nonnegative().optional().nullable(),
  rating: z.number().min(0).max(5).optional().nullable(),
  review_count: z.number().int().nonnegative().optional().nullable(),
  favorite_count: z.number().int().nonnegative().optional().nullable(),
  stock_status: z.string().optional().nullable(),
  description: z.string().optional().nullable(),
  publish_date: z.string().optional().nullable(),
  fans_count: z.number().int().nonnegative().optional().nullable(),
  note_count: z.number().int().nonnegative().optional().nullable(),
  targetType: z.enum(["note", "user"]).optional().nullable(),
});

export type NormalizedXHSData = z.infer<typeof XHSNoteSchema>;

export interface NormalizationResult {
  success: boolean;
  data: NormalizedXHSData | null;
  errors: string[];
  warnings: string[];
  qualityScore: number;
}

const XHS_FIELD_ALIASES: Record<string, string> = {
  note_id: "platform_product_id",
  noteId: "platform_product_id",
  title: "product_name",
  display_title: "product_name",
  desc: "description",
  nickname: "shop_name",
  author_name: "shop_name",
  liked_count: "favorite_count",
  likes: "favorite_count",
  collected_count: "sales_count",
  collects: "sales_count",
  comment_count: "review_count",
  comments: "review_count",
  cover_url: "image_url",
  coverUrl: "image_url",
  tags: "category",
  hash_tags: "category",
  publish_time: "publish_date",
  publishTime: "publish_date",
  fans: "fans_count",
  followers: "fans_count",
  notes: "note_count",
};

export class Normalizer {
  normalize(raw: Record<string, unknown>): NormalizationResult {
    const errors: string[] = [];
    const warnings: string[] = [];

    const mapped = this.mapFields(raw, warnings);

    this.cleanValues(mapped, warnings);

    if (!mapped.platform) {
      mapped.platform = "xhs";
    }

    const parseResult = XHSNoteSchema.safeParse(mapped);

    if (!parseResult.success) {
      const fieldErrors = parseResult.error.errors.map(
        (e) => `${e.path.join(".")}: ${e.message}`
      );
      errors.push(...fieldErrors);
    }

    const qualityScore = this.calculateQualityScore(mapped, errors, warnings);

    return {
      success: errors.length === 0,
      data: errors.length === 0 ? (parseResult.success ? parseResult.data : null) : null,
      errors,
      warnings,
      qualityScore,
    };
  }

  private mapFields(raw: Record<string, unknown>, warnings: string[]): Record<string, unknown> {
    const result: Record<string, unknown> = { ...raw };

    for (const [alias, canonical] of Object.entries(XHS_FIELD_ALIASES)) {
      if (result[alias] !== undefined && result[canonical] === undefined) {
        result[canonical] = result[alias];
        delete result[alias];
      }
    }

    return result;
  }

  private cleanValues(data: Record<string, unknown>, warnings: string[]): void {
    if (typeof data.product_name === "string") {
      data.product_name = data.product_name.trim().substring(0, 500);
      if (!data.product_name) {
        data.product_name = "小红书商品";
        warnings.push("标题为空，使用默认名称");
      }
    }

    if (typeof data.price === "string") {
      const cleaned = data.price.replace(/[^\d.]/g, "");
      const parsed = parseFloat(cleaned);
      if (!isNaN(parsed) && parsed >= 0) {
        data.price = parsed;
      } else {
        warnings.push(`价格格式异常: "${data.price}"`);
        data.price = null;
      }
    }

    if (typeof data.sales_count === "string") {
      data.sales_count = this.parseCountString(data.sales_count as string);
      if (data.sales_count === null) {
        warnings.push(`收藏数格式异常`);
      }
    }

    if (typeof data.review_count === "string") {
      data.review_count = this.parseCountString(data.review_count as string);
    }

    if (typeof data.favorite_count === "string") {
      data.favorite_count = this.parseCountString(data.favorite_count as string);
    }

    if (typeof data.fans_count === "string") {
      data.fans_count = this.parseCountString(data.fans_count as string);
    }

    if (typeof data.note_count === "string") {
      data.note_count = this.parseCountString(data.note_count as string);
    }

    if (typeof data.category === "string") {
      data.category = data.category.trim();
    }

    if (data.image_url && typeof data.image_url === "string" && data.image_url.startsWith("//")) {
      data.image_url = "https:" + data.image_url;
    }

    if (typeof data.description === "string") {
      data.description = data.description.trim().substring(0, 1000);
    }
  }

  private parseCountString(val: string): number | null {
    if (!val) return null;
    const trimmed = val.trim();

    if (trimmed.endsWith("万+")) {
      const num = parseFloat(trimmed.slice(0, -2));
      return isNaN(num) ? null : Math.round(num * 10000);
    }
    if (trimmed.endsWith("万") || trimmed.endsWith("w") || trimmed.endsWith("W")) {
      const num = parseFloat(trimmed.slice(0, -1));
      return isNaN(num) ? null : Math.round(num * 10000);
    }
    if (trimmed.endsWith("+")) {
      const num = parseInt(trimmed.slice(0, -1));
      return isNaN(num) ? null : num;
    }
    if (trimmed.endsWith("k") || trimmed.endsWith("K")) {
      const num = parseFloat(trimmed.slice(0, -1));
      return isNaN(num) ? null : Math.round(num * 1000);
    }

    const num = parseInt(trimmed.replace(/,/g, ""));
    return isNaN(num) ? null : num;
  }

  private calculateQualityScore(data: Record<string, unknown>, errors: string[], warnings: string[]): number {
    let score = 100;

    const criticalFields = ["platform_product_id", "product_name"];
    for (const field of criticalFields) {
      if (data[field] === undefined || data[field] === null || data[field] === "") {
        score -= 25;
      }
    }

    const importantFields = ["shop_name", "image_url", "favorite_count", "review_count"];
    for (const field of importantFields) {
      if (data[field] === undefined || data[field] === null) {
        score -= 8;
      }
    }

    const secondaryFields = ["category", "description", "sales_count", "publish_date"];
    for (const field of secondaryFields) {
      if (data[field] === undefined || data[field] === null) {
        score -= 3;
      }
    }

    score -= errors.length * 10;
    score -= warnings.length * 3;

    return Math.max(0, Math.min(100, score));
  }
}

export const normalizer = new Normalizer();
