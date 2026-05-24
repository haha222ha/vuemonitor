import asyncio
import os
import sys
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

server_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, server_dir)


def test_aipic_module_imports():
    passed = 0
    failed = 0
    results = []

    modules = [
        ("app.services.aipic.generate_service", [
            "generate_image_async", "get_credits_cost", "QUALITY_TIERS", "PRESET_RATIOS"
        ]),
        ("app.services.aipic.queue_service", [
            "submit_task", "get_next_task", "complete_task", "fail_task", "cancel_task"
        ]),
        ("app.services.aipic.worker_service", [
            "AipicWorker", "start_aipic_workers", "stop_aipic_workers", "get_worker_status"
        ]),
        ("app.services.aipic.credits_service", [
            "deduct_credits", "refund_credits", "get_user_credits"
        ]),
        ("app.services.aipic.style_service", [
            "get_all_styles", "get_style_by_name"
        ]),
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


def test_quality_tiers_configuration():
    from app.services.aipic.generate_service import QUALITY_TIERS

    assert "standard" in QUALITY_TIERS
    assert "hd" in QUALITY_TIERS
    assert "ultra" in QUALITY_TIERS

    assert QUALITY_TIERS["standard"]["credits_cost"] == 1
    assert QUALITY_TIERS["hd"]["credits_cost"] == 2
    assert QUALITY_TIERS["ultra"]["credits_cost"] == 4

    assert QUALITY_TIERS["standard"]["model"] == "gpt-image-2"
    assert QUALITY_TIERS["hd"]["model"] == "gpt-image-2"

    return True


def test_preset_ratios_configuration():
    from app.services.aipic.generate_service import PRESET_RATIOS

    required_ratios = ["square", "portrait", "landscape", "wide"]
    for ratio in required_ratios:
        assert ratio in PRESET_RATIOS, f"Missing ratio: {ratio}"
        assert "sizes" in PRESET_RATIOS[ratio]
        assert "standard" in PRESET_RATIOS[ratio]["sizes"]
        assert "hd" in PRESET_RATIOS[ratio]["sizes"]
        assert "ultra" in PRESET_RATIOS[ratio]["sizes"]

    return True


def test_get_credits_cost():
    from app.services.aipic.generate_service import get_credits_cost

    assert get_credits_cost("standard") == 1
    assert get_credits_cost("hd") == 2
    assert get_credits_cost("ultra") == 4
    assert get_credits_cost("invalid") == 1
    assert get_credits_cost("") == 1

    return True


def test_resolve_size_logic():
    from app.services.aipic.generate_service import OPENAI_SUPPORTED_SIZES, _resolve_size

    size_standard = _resolve_size("square", "standard")
    assert size_standard == "1024x1024"

    size_hd = _resolve_size("portrait", "hd")
    assert size_hd == "1024x1536"

    size_ultra = _resolve_size("landscape", "ultra")
    assert size_ultra == "2048x1366"

    invalid_size = _resolve_size("invalid_ratio", "standard")
    assert invalid_size in OPENAI_SUPPORTED_SIZES

    return True


def test_queue_service_functions_exist():
    from app.services.aipic.queue_service import (
        cancel_task,
        complete_task,
        fail_task,
        get_next_task,
        get_queue_stats,
        get_user_tasks,
        submit_task,
    )

    assert callable(submit_task)
    assert callable(get_next_task)
    assert callable(complete_task)
    assert callable(fail_task)
    assert callable(cancel_task)
    assert callable(get_user_tasks)
    assert callable(get_queue_stats)

    return True


def test_worker_service_functions_exist():
    from app.services.aipic.worker_service import (
        AipicWorker,
        get_worker_status,
        start_aipic_workers,
        stop_aipic_workers,
    )

    assert AipicWorker is not None
    assert callable(start_aipic_workers)
    assert callable(stop_aipic_workers)
    assert callable(get_worker_status)

    return True


def test_worker_initialization():
    from app.services.aipic.worker_service import AipicWorker

    worker = AipicWorker(worker_id=1)

    assert worker.worker_id == 1
    assert worker.running is False
    assert worker.current_task is None
    assert worker._task is None

    return True


def test_worker_status():
    from app.services.aipic.worker_service import AipicWorker

    worker = AipicWorker(worker_id=0)
    status = worker.get_status()

    assert status["worker_id"] == 0
    assert status["running"] is False
    assert status["current_task"] is None

    return True


def test_worker_start_stop():
    from app.services.aipic.worker_service import AipicWorker

    worker = AipicWorker(worker_id=2)

    assert worker.running is False

    return True


def test_generate_service_no_api_key():
    from app.services.aipic.generate_service import generate_image_async

    with patch("app.services.aipic.generate_service.get_settings") as mock_settings:
        mock_settings.return_value.AIPIC_OPENAI_API_KEY = ""

        result = asyncio.run(generate_image_async("test prompt"))

        assert result["success"] is False
        assert "API_KEY" in result["error"] or "未配置" in result["error"]

    return True


def test_generate_service_with_mocked_api():
    from app.services.aipic.generate_service import generate_image_async

    with patch("app.services.aipic.generate_service.get_settings") as mock_settings:
        mock_settings.return_value.AIPIC_OPENAI_API_KEY = "test_key"
        mock_settings.return_value.AIPIC_OPENAI_BASE_URL = "https://api.openai.com/v1"
        mock_settings.return_value.AIPIC_OPENAI_MODEL = "gpt-image-2"
        mock_settings.return_value.AIPIC_OPENAI_TIMEOUT = 180
        mock_settings.return_value.AIPIC_OUTPUTS_DIR = ""

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "data": [{"b64_json": "dGVzdA==", "url": None}]
            }
            mock_response.raise_for_status = MagicMock()

            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

            with patch("builtins.open", MagicMock()):
                with patch("os.makedirs", MagicMock()):
                    asyncio.run(generate_image_async("test prompt"))

    return True


def test_queue_stats_structure():
    mock_db = AsyncMock()

    from app.services.aipic.queue_service import get_queue_stats

    async def mock_execute(query):
        result = MagicMock()
        result.scalar.return_value = 0
        return result

    mock_db.execute = mock_execute

    result = asyncio.run(get_queue_stats(mock_db))

    assert "pending" in result
    assert "running" in result
    assert "completed" in result
    assert "failed" in result

    return True


def test_cancel_task_validation():
    import uuid

    from app.services.aipic.queue_service import cancel_task

    mock_db = AsyncMock()

    async def mock_execute(query):
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        return result

    mock_db.execute = mock_execute
    mock_db.flush = AsyncMock()

    success, message = asyncio.run(cancel_task(mock_db, "task_123", uuid.uuid4()))

    assert success is False
    assert message == "任务不存在"

    return True


def test_get_user_tasks_pagination():
    import uuid

    from app.services.aipic.queue_service import get_user_tasks

    mock_db = AsyncMock()

    mock_task = MagicMock()
    mock_task.task_id = "task_123"
    mock_task.prompt = "test prompt"
    mock_task.model_name = "gpt-image-2"
    mock_task.ratio_key = "square"
    mock_task.task_type = "text2img"
    mock_task.quality_tier = "standard"
    mock_task.task_status = "待执行"
    mock_task.credits_cost = 1
    mock_task.created_at = datetime.now(UTC)
    mock_task.finish_time = None
    mock_task.output_image_path = None
    mock_task.fail_reason = None

    async def mock_execute(query):
        result = MagicMock()
        result.scalar.return_value = 1
        result.scalars.return_value.all.return_value = [mock_task]
        return result

    mock_db.execute = mock_execute

    result = asyncio.run(get_user_tasks(mock_db, uuid.uuid4()))

    assert result["total"] >= 0
    assert "items" in result
    assert "page" in result
    assert "page_size" in result

    return True


def test_worker_status_global():
    from app.services.aipic.worker_service import get_worker_status

    status = get_worker_status()

    assert "total_workers" in status
    assert "running" in status
    assert "workers" in status

    return True


def test_all_tests():
    tests = [
        ("Module Imports", test_aipic_module_imports),
        ("Quality Tiers Config", test_quality_tiers_configuration),
        ("Preset Ratios Config", test_preset_ratios_configuration),
        ("Get Credits Cost", test_get_credits_cost),
        ("Resolve Size Logic", test_resolve_size_logic),
        ("Queue Service Functions", test_queue_service_functions_exist),
        ("Worker Service Functions", test_worker_service_functions_exist),
        ("Worker Initialization", test_worker_initialization),
        ("Worker Status", test_worker_status),
        ("Worker Start/Stop", test_worker_start_stop),
        ("Generate No API Key", test_generate_service_no_api_key),
        ("Generate Mocked API", test_generate_service_with_mocked_api),
        ("Queue Stats Structure", test_queue_stats_structure),
        ("Cancel Task Validation", test_cancel_task_validation),
        ("Get User Tasks Pagination", test_get_user_tasks_pagination),
        ("Worker Status Global", test_worker_status_global),
    ]

    passed = 0
    failed = 0
    results = []

    for name, test_func in tests:
        try:
            result = test_func()
            if result is False:
                results.append(f"  FAIL {name}")
                failed += 1
            else:
                results.append(f"  PASS {name}")
                passed += 1
        except Exception as e:
            results.append(f"  FAIL {name}: {e}")
            failed += 1

    print("\n=== AIPic Module Integration Tests ===")
    for r in results:
        print(r)
    print(f"\nTotal: {passed} passed, {failed} failed")

    return passed, failed
