import asyncio
import json
import sys
import os

server_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, server_dir)


def test_imports():
    passed = 0
    failed = 0
    results = []

    modules = [
        ("app.ai.providers", ["ANALYSIS_PROMPTS", "get_provider", "get_available_providers", "AIProvider", "DeepSeekProvider", "OpenAIProvider"]),
        ("app.ai.service", ["AIService", "_GATE_KEY_MAP"]),
        ("shared.constants.feature_gates", ["PLAN_HIERARCHY", "PLAN_LIMITS", "PLAN_FEATURES_MAP", "is_plan_sufficient"]),
        ("shared.constants.error_codes", ["ERROR_CODES"]),
        ("app.config", ["get_settings", "Settings"]),
    ]

    for module_name, expected_attrs in modules:
        try:
            mod = __import__(module_name, fromlist=expected_attrs)
            missing = [a for a in expected_attrs if not hasattr(mod, a)]
            if missing:
                results.append(f"  FAIL {module_name}: missing attrs {missing}")
                failed += 1
            else:
                results.append(f"  PASS {module_name}")
                passed += 1
        except Exception as e:
            results.append(f"  FAIL {module_name}: {e}")
            failed += 1

    return passed, failed, results


def test_analysis_prompts():
    passed = 0
    failed = 0
    results = []

    from app.ai.providers import ANALYSIS_PROMPTS

    required_types = ["basic_analysis", "trend_score", "prediction", "risk_warning", "competitor_analysis", "product_selection", "report", "product_optimization"]

    for at in required_types:
        if at in ANALYSIS_PROMPTS:
            config = ANALYSIS_PROMPTS[at]
            has_system = "system" in config and len(config["system"]) > 10
            has_template = "template" in config and "{data}" in config["template"]
            if has_system and has_template:
                results.append(f"  PASS prompt[{at}]: system+template OK")
                passed += 1
            else:
                results.append(f"  FAIL prompt[{at}]: system={has_system}, template={has_template}")
                failed += 1
        else:
            results.append(f"  FAIL prompt[{at}]: NOT FOUND")
            failed += 1

    return passed, failed, results


def test_gate_key_map():
    passed = 0
    failed = 0
    results = []

    from app.ai.service import _GATE_KEY_MAP

    for analysis_type in ["basic_analysis", "trend_score", "prediction", "risk_warning", "competitor_analysis", "product_selection", "report", "product_optimization"]:
        if analysis_type in _GATE_KEY_MAP:
            gate_key = _GATE_KEY_MAP[analysis_type]
            if gate_key.startswith("gate:ai:"):
                results.append(f"  PASS gate_map[{analysis_type}] = {gate_key}")
                passed += 1
            else:
                results.append(f"  FAIL gate_map[{analysis_type}]: invalid format {gate_key}")
                failed += 1
        else:
            results.append(f"  FAIL gate_map[{analysis_type}]: NOT FOUND")
            failed += 1

    return passed, failed, results


def test_plan_hierarchy():
    passed = 0
    failed = 0
    results = []

    from shared.constants.feature_gates import PLAN_HIERARCHY, PLAN_LIMITS, is_plan_sufficient

    if list(PLAN_HIERARCHY.keys()) == ["free", "pro", "premium", "enterprise"]:
        results.append("  PASS PLAN_HIERARCHY keys correct")
        passed += 1
    else:
        results.append(f"  FAIL PLAN_HIERARCHY keys: {list(PLAN_HIERARCHY.keys())}")
        failed += 1

    for plan in PLAN_HIERARCHY:
        if plan in PLAN_LIMITS:
            limits = PLAN_LIMITS[plan]
            required_keys = ["maxProducts", "aiCallsPerDay", "dailyCollectLimit"]
            if all(k in limits for k in required_keys):
                results.append(f"  PASS PLAN_LIMITS[{plan}]: has required keys")
                passed += 1
            else:
                results.append(f"  FAIL PLAN_LIMITS[{plan}]: missing keys")
                failed += 1
        else:
            results.append(f"  FAIL PLAN_LIMITS[{plan}]: NOT FOUND")
            failed += 1

    if is_plan_sufficient("pro", "free"):
        results.append("  PASS is_plan_sufficient(pro, free) = True")
        passed += 1
    else:
        results.append("  FAIL is_plan_sufficient(pro, free) should be True")
        failed += 1

    if not is_plan_sufficient("free", "pro"):
        results.append("  PASS is_plan_sufficient(free, pro) = False")
        passed += 1
    else:
        results.append("  FAIL is_plan_sufficient(free, pro) should be False")
        failed += 1

    return passed, failed, results


def test_error_codes():
    passed = 0
    failed = 0
    results = []

    from shared.constants.error_codes import ERROR_CODES

    required_codes = ["SUCCESS", "BAD_REQUEST", "NOT_FOUND", "GATE_FEATURE_UNAUTHORIZED", "GATE_QUOTA_EXCEEDED", "GATE_PLAN_INSUFFICIENT", "AI_SERVICE_ERROR", "AI_PROVIDER_UNAVAILABLE", "LICENSE_INVALID"]
    for code in required_codes:
        if code in ERROR_CODES:
            results.append(f"  PASS ERROR_CODES[{code}] = {ERROR_CODES[code]}")
            passed += 1
        else:
            results.append(f"  FAIL ERROR_CODES[{code}]: NOT FOUND")
            failed += 1

    return passed, failed, results


def test_rule_based_analysis():
    passed = 0
    failed = 0
    results = []

    try:
        from app.ai.service import AIService

        class MockProduct:
            product_name = "测试商品A"
            platform = "xhs"
            shop_name = "测试店铺"
            category = "美妆"

        class MockFeature:
            price = 99.9
            sales_count = 500
            monthly_sales = 200
            rating = 4.5
            review_count = 80
            favorite_count = 1200
            collected_at = None

        svc = AIService.__new__(AIService)
        svc.db = None
        svc.gate = None

        product = MockProduct()
        features = [MockFeature()]

        for at in ["basic_analysis", "trend_score", "prediction", "risk_warning", "competitor_analysis", "product_selection"]:
            result = svc._rule_based_analysis(product, features, at)
            if isinstance(result, dict) and "note_name" in result:
                results.append(f"  PASS rule_based[{at}]: returns dict with note_name")
                passed += 1
            elif isinstance(result, dict):
                results.append(f"  PASS rule_based[{at}]: returns dict (no note_name)")
                passed += 1
            else:
                results.append(f"  FAIL rule_based[{at}]: unexpected type {type(result)}")
                failed += 1

        empty_result = svc._rule_based_analysis(product, [], "basic_analysis")
        if empty_result.get("confidence") == 0:
            results.append("  PASS rule_based[empty features]: returns low confidence")
            passed += 1
        else:
            results.append(f"  FAIL rule_based[empty features]: {empty_result}")
            failed += 1

    except Exception as e:
        results.append(f"  FAIL rule_based_analysis: {e}")
        failed += 3

    return passed, failed, results


def test_report_prompt_builder():
    passed = 0
    failed = 0
    results = []

    try:
        from app.ai.service import AIService

        svc = AIService.__new__(AIService)
        svc.db = None
        svc.gate = None

        sample_data = [
            {"product_name": "商品A", "platform": "xhs", "shop_name": "店铺1", "category": "美妆", "features": [{"price": 99, "sales_count": 500}]}
        ]

        for rt in ["product", "category", "trend", "risk"]:
            prompt = svc._build_report_prompt(rt, sample_data)
            has_system = "system" in prompt and len(prompt["system"]) > 20
            has_prompt = "prompt" in prompt and len(prompt["prompt"]) > 50
            if has_system and has_prompt:
                results.append(f"  PASS report_prompt[{rt}]: system+prompt OK")
                passed += 1
            else:
                results.append(f"  FAIL report_prompt[{rt}]: system={has_system}, prompt={has_prompt}")
                failed += 1

    except Exception as e:
        results.append(f"  FAIL report_prompt_builder: {e}")
        failed += 4

    return passed, failed, results


def test_api_route_structure():
    passed = 0
    failed = 0
    results = []

    try:
        from app.api.ai import router

        routes = {}
        for r in router.routes:
            path = r.path
            methods = list(r.methods) if r.methods else []
            if path in routes:
                routes[path].extend(methods)
            else:
                routes[path] = methods

        expected_routes = {
            "/ai/status": ["GET"],
            "/ai/analyze": ["POST"],
            "/ai/report": ["POST"],
            "/ai/analyses": ["GET"],
            "/ai/reports": ["GET"],
            "/ai/reports/{report_id}": ["GET", "DELETE"],
            "/ai/analyses/{analysis_id}": ["DELETE"],
        }

        for path, methods in expected_routes.items():
            if path in routes:
                for method in methods:
                    if method in routes[path]:
                        results.append(f"  PASS route {method} {path}")
                        passed += 1
                    else:
                        results.append(f"  FAIL route {method} {path}: method not found, have {routes[path]}")
                        failed += 1
            else:
                results.append(f"  FAIL route {path}: NOT FOUND, available: {list(routes.keys())}")
                failed += len(methods)

    except Exception as e:
        results.append(f"  FAIL api_route_structure: {e}")
        failed += 10

    return passed, failed, results


def main():
    print("=" * 60)
    print("P7-A-2 AI模块端到端验证")
    print("=" * 60)

    total_passed = 0
    total_failed = 0

    tests = [
        ("模块导入验证", test_imports),
        ("分析提示词验证", test_analysis_prompts),
        ("Feature Gate映射验证", test_gate_key_map),
        ("套餐层级验证", test_plan_hierarchy),
        ("错误码验证", test_error_codes),
        ("规则引擎分析验证", test_rule_based_analysis),
        ("报告提示词构建验证", test_report_prompt_builder),
        ("API路由结构验证", test_api_route_structure),
    ]

    for name, test_fn in tests:
        print(f"\n--- {name} ---")
        p, f, results = test_fn()
        for r in results:
            print(r)
        total_passed += p
        total_failed += f

    print("\n" + "=" * 60)
    print(f"验证结果: {total_passed} PASSED, {total_failed} FAILED, {total_passed + total_failed} TOTAL")
    print("=" * 60)

    if total_failed > 0:
        print("\n❌ 存在失败项，请检查上方输出")
        sys.exit(1)
    else:
        print("\n✅ 全部验证通过！AI模块代码完整性验证成功")
        sys.exit(0)


if __name__ == "__main__":
    main()
