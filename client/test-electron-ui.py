from playwright.sync_api import sync_playwright
import os

SCREENSHOTS_DIR = r"d:\vuemonitor\client\test-screenshots"
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(viewport={"width": 1280, "height": 800})
    page = context.new_page()

    page.goto("http://127.0.0.1:5173/")
    page.evaluate("localStorage.setItem('access_token', 'test_fake_token_for_ui_testing')")

    def handle_route(route):
        if route.request.resource_type in ["document", "stylesheet", "script", "image", "font"]:
            route.continue_()
        else:
            route.fulfill(status=200, content_type="application/json", body='{"data":{}}')

    page.route("**/api/**", handle_route)

    print("=" * 60)
    print("1. 测试登录页 - 注册按钮可见性")
    print("=" * 60)
    page.goto("http://127.0.0.1:5173/#/login")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(1000)
    page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "01_login_page.png"), full_page=True)

    register_btn = page.locator("text=立即注册")
    if register_btn.count() > 0:
        btn_box = register_btn.bounding_box()
        print(f"  [OK] 注册按钮找到: 位置={btn_box}")
    else:
        print("  [FAIL] 注册按钮未找到!")

    print()
    print("=" * 60)
    print("2. 测试注册对话框")
    print("=" * 60)
    register_btn.click()
    page.wait_for_timeout(500)

    dialog = page.locator(".el-dialog")
    if dialog.count() > 0:
        print("  [OK] 注册对话框已打开")
        page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "02_register_dialog.png"), full_page=True)

        dialog_register_btn = dialog.locator("button:has-text('注册')")
        if dialog_register_btn.count() > 0:
            reg_btn_box = dialog_register_btn.bounding_box()
            print(f"  [OK] 对话框内注册按钮可见: {reg_btn_box}")
        else:
            print("  [FAIL] 对话框内注册按钮不可见")

        close_btn = dialog.locator(".el-dialog__headerbtn")
        if close_btn.count() > 0:
            close_btn.click()
            page.wait_for_timeout(300)
    else:
        print("  [FAIL] 注册对话框未打开")

    print()
    print("=" * 60)
    print("3. 直接进入主界面 - 测试侧边栏宽度")
    print("=" * 60)
    page.evaluate("localStorage.setItem('access_token', 'test_fake_token_for_ui_testing')")
    page.goto("http://127.0.0.1:5173/#/dashboard")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(2000)
    page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "03_main_layout.png"), full_page=True)

    sidebar = page.locator(".sidebar")
    if sidebar.count() == 0:
        sidebar = page.locator("aside")

    if sidebar.count() > 0:
        sidebar_box = sidebar.first.bounding_box()
        print(f"  侧边栏宽度: {sidebar_box['width']}px")

        if sidebar_box["width"] <= 210:
            print(f"  [OK] 侧边栏宽度正常 ({sidebar_box['width']}px <= 210px)")
        else:
            print(f"  [WARN] 侧边栏偏宽 ({sidebar_box['width']}px)")
    else:
        print("  [INFO] 侧边栏元素未找到，尝试获取页面内容")
        body_text = page.locator("body").inner_text()
        print(f"  页面内容: {body_text[:200]}")

    content_area = page.locator(".app-layout__content")
    if content_area.count() > 0 and sidebar.count() > 0:
        content_box = content_area.bounding_box()
        sidebar_box = sidebar.first.bounding_box()
        print(f"  内容区宽度: {content_box['width']}px")
        total = sidebar_box["width"] + content_box["width"]
        sidebar_ratio = sidebar_box["width"] / total * 100
        print(f"  侧边栏占比: {sidebar_ratio:.1f}%")
        if sidebar_ratio < 20:
            print(f"  [OK] 侧边栏占比合理 ({sidebar_ratio:.1f}%)")
        else:
            print(f"  [WARN] 侧边栏占比偏高 ({sidebar_ratio:.1f}%)")

    print()
    print("=" * 60)
    print("4. 测试侧边栏折叠/展开")
    print("=" * 60)
    logo_area = page.locator(".sidebar__logo")
    if logo_area.count() > 0:
        logo_area.click()
        page.wait_for_timeout(500)
        page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "04_sidebar_collapsed.png"), full_page=True)

        if sidebar.count() > 0:
            sidebar_box_after = sidebar.first.bounding_box()
            print(f"  折叠后侧边栏宽度: {sidebar_box_after['width']}px")
            if sidebar_box_after["width"] <= 70:
                print(f"  [OK] 折叠后宽度正常 ({sidebar_box_after['width']}px)")
            else:
                print(f"  [WARN] 折叠后宽度偏大 ({sidebar_box_after['width']}px)")

        logo_area.click()
        page.wait_for_timeout(300)

    print()
    print("=" * 60)
    print("5. 窗口宽度 1024px 模拟 Electron 默认窗口")
    print("=" * 60)
    page.set_viewport_size({"width": 1024, "height": 700})
    page.wait_for_timeout(500)
    page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "05_narrow_window.png"), full_page=True)

    if sidebar.count() > 0:
        sidebar_box_narrow = sidebar.first.bounding_box()
        print(f"  窄窗口侧边栏宽度: {sidebar_box_narrow['width']}px")
        if content_area.count() > 0:
            content_box_narrow = content_area.bounding_box()
            print(f"  窄窗口内容区宽度: {content_box_narrow['width']}px")
            total_narrow = sidebar_box_narrow["width"] + content_box_narrow["width"]
            ratio_narrow = sidebar_box_narrow["width"] / total_narrow * 100
            print(f"  窄窗口侧边栏占比: {ratio_narrow:.1f}%")
            if ratio_narrow < 25:
                print(f"  [OK] 窄窗口下侧边栏占比合理 ({ratio_narrow:.1f}%)")
            else:
                print(f"  [WARN] 窄窗口下侧边栏占比偏高 ({ratio_narrow:.1f}%)")

    print()
    print("=" * 60)
    print("测试完成！截图保存在:", SCREENSHOTS_DIR)
    print("=" * 60)

    browser.close()
