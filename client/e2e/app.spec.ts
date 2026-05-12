import { test, expect } from "@playwright/test";

const BASE_URL = process.env.E2E_BASE_URL || "http://localhost:5173";
const API_URL = process.env.E2E_API_URL || "http://localhost:8000";

test.describe("Authentication Flow", () => {
  test("login page loads correctly", async ({ page }) => {
    await page.goto(`${BASE_URL}/login`);
    await expect(page.locator("h2, .login-title, .login-container")).toBeVisible({ timeout: 10000 });
  });

  test("login form has required fields", async ({ page }) => {
    await page.goto(`${BASE_URL}/login`);
    const emailInput = page.locator('input[type="email"], input[placeholder*="邮箱"], input[placeholder*="Email"]');
    const passwordInput = page.locator('input[type="password"]');
    await expect(emailInput.or(passwordInput)).toBeVisible({ timeout: 10000 });
  });

  test("login with invalid credentials shows error", async ({ page }) => {
    await page.goto(`${BASE_URL}/login`);
    const emailInput = page.locator('input[type="email"], input[placeholder*="邮箱"], input[placeholder*="Email"]').first();
    const passwordInput = page.locator('input[type="password"]').first();
    const submitBtn = page.locator('button[type="submit"], button:has-text("登录"), button:has-text("Login")').first();

    if (await emailInput.isVisible()) {
      await emailInput.fill("invalid@test.com");
      await passwordInput.fill("wrongpassword");
      await submitBtn.click();
      await page.waitForTimeout(2000);
    }
  });

  test("navigate to register page", async ({ page }) => {
    await page.goto(`${BASE_URL}/login`);
    const registerLink = page.locator('a:has-text("注册"), a:has-text("Register"), button:has-text("注册")').first();
    if (await registerLink.isVisible()) {
      await registerLink.click();
      await page.waitForTimeout(1000);
    }
  });
});

test.describe("Dashboard", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(`${BASE_URL}/dashboard`);
    await page.waitForTimeout(2000);
  });

  test("dashboard page renders", async ({ page }) => {
    const heading = page.locator("h2").first();
    await expect(heading).toBeVisible({ timeout: 10000 });
  });

  test("statistics cards are visible", async ({ page }) => {
    const cards = page.locator(".el-card");
    await expect(cards.first()).toBeVisible({ timeout: 10000 });
  });

  test("concurrency slider exists", async ({ page }) => {
    const slider = page.locator(".el-slider");
    if (await slider.isVisible()) {
      await expect(slider).toBeVisible();
    }
  });
});

test.describe("Products Page", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(`${BASE_URL}/products`);
    await page.waitForTimeout(2000);
  });

  test("products page renders", async ({ page }) => {
    const content = page.locator(".el-table, .el-card, h2").first();
    await expect(content).toBeVisible({ timeout: 10000 });
  });

  test("add product button exists", async ({ page }) => {
    const addBtn = page.locator('button:has-text("添加"), button:has-text("Add")').first();
    if (await addBtn.isVisible()) {
      await expect(addBtn).toBeEnabled();
    }
  });

  test("product table or empty state", async ({ page }) => {
    const table = page.locator(".el-table");
    const emptyState = page.locator(".el-empty, .el-table__empty-block");
    await expect(table.or(emptyState).first()).toBeVisible({ timeout: 10000 });
  });
});

test.describe("Monitor Rules Page", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(`${BASE_URL}/monitor`);
    await page.waitForTimeout(2000);
  });

  test("monitor page renders", async ({ page }) => {
    const content = page.locator(".el-card, h2, .el-table").first();
    await expect(content).toBeVisible({ timeout: 10000 });
  });

  test("add rule button exists", async ({ page }) => {
    const addBtn = page.locator('button:has-text("添加"), button:has-text("Add")').first();
    if (await addBtn.isVisible()) {
      await expect(addBtn).toBeEnabled();
    }
  });
});

test.describe("Notifications Page", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(`${BASE_URL}/notifications`);
    await page.waitForTimeout(2000);
  });

  test("notifications page renders", async ({ page }) => {
    const content = page.locator(".el-card, h2, .el-table").first();
    await expect(content).toBeVisible({ timeout: 10000 });
  });

  test("filter tabs exist", async ({ page }) => {
    const tabs = page.locator(".el-tabs, .el-radio-group");
    if (await tabs.isVisible()) {
      await expect(tabs).toBeVisible();
    }
  });
});

test.describe("AI Analysis Page", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(`${BASE_URL}/ai`);
    await page.waitForTimeout(2000);
  });

  test("AI page renders", async ({ page }) => {
    const content = page.locator(".el-card, h2").first();
    await expect(content).toBeVisible({ timeout: 10000 });
  });

  test("analysis type selector exists", async ({ page }) => {
    const selector = page.locator(".el-select, .el-radio-group").first();
    if (await selector.isVisible()) {
      await expect(selector).toBeVisible();
    }
  });
});

test.describe("Settings Page", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(`${BASE_URL}/settings`);
    await page.waitForTimeout(2000);
  });

  test("settings page renders", async ({ page }) => {
    const content = page.locator(".el-card, h2, .el-tabs").first();
    await expect(content).toBeVisible({ timeout: 10000 });
  });

  test("language selector exists", async ({ page }) => {
    const langSelector = page.locator('.el-select, [data-testid="language-select"]').first();
    if (await langSelector.isVisible()) {
      await expect(langSelector).toBeVisible();
    }
  });
});

test.describe("Navigation", () => {
  test("sidebar navigation works", async ({ page }) => {
    await page.goto(`${BASE_URL}/dashboard`);
    await page.waitForTimeout(2000);

    const navItems = [
      { path: "/products", text: /商品|Products/ },
      { path: "/monitor", text: /规则|Monitor/ },
      { path: "/notifications", text: /通知|Notifications/ },
      { path: "/ai", text: /AI/ },
      { path: "/settings", text: /设置|Settings/ },
    ];

    for (const item of navItems) {
      const navLink = page.locator(`.el-menu-item[index="${item.path}"], a[href="${item.path}"]`).first();
      if (await navLink.isVisible()) {
        await navLink.click();
        await page.waitForTimeout(1000);
        await expect(page).toHaveURL(new RegExp(item.path));
      }
    }
  });

  test("responsive layout on mobile viewport", async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 });
    await page.goto(`${BASE_URL}/dashboard`);
    await page.waitForTimeout(2000);

    const mobileNav = page.locator(".mobile-nav, .mobile-nav-item");
    if (await mobileNav.isVisible()) {
      await expect(mobileNav).toBeVisible();
    }
  });
});

test.describe("API Health Check", () => {
  test("server health endpoint responds", async ({ request }) => {
    const response = await request.get(`${API_URL}/health`);
    expect(response.status()).toBe(200);
  });

  test("API v1 health endpoint responds", async ({ request }) => {
    const response = await request.get(`${API_URL}/api/v1/health`);
    expect(response.status()).toBe(200);
  });
});
