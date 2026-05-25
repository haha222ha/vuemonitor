import { describe, it, expect } from "vitest";
import { Normalizer } from "./normalizer";

describe("Normalizer", () => {
  const normalizer = new Normalizer();

  it("maps XHS field aliases and validates note payload", () => {
    const result = normalizer.normalize({
      noteId: "note-123",
      display_title: "测试笔记标题",
      liked_count: "1200",
      comment_count: 88,
      cover_url: "https://example.com/cover.jpg",
    });

    expect(result.success).toBe(true);
    expect(result.data).toMatchObject({
      platform: "xhs",
      platform_product_id: "note-123",
      product_name: "测试笔记标题",
      favorite_count: 1200,
      review_count: 88,
      image_url: "https://example.com/cover.jpg",
    });
    expect(result.qualityScore).toBeGreaterThan(0);
  });

  it("rejects payload missing required fields", () => {
    const result = normalizer.normalize({
      title: "只有标题没有ID",
    });

    expect(result.success).toBe(false);
    expect(result.data).toBeNull();
    expect(result.errors.length).toBeGreaterThan(0);
  });

  it("coerces price strings with currency symbols", () => {
    const result = normalizer.normalize({
      platform_product_id: "g-1",
      product_name: "商品A",
      price: "¥99.5",
    });

    expect(result.success).toBe(true);
    expect(result.data?.price).toBe(99.5);
  });
});
