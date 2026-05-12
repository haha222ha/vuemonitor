import sys
import os
import json
import re
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "docs", "api")


def ensure_output_dir():
    os.makedirs(OUTPUT_DIR, exist_ok=True)


def generate_openapi_spec():
    ensure_output_dir()

    resp = client.get("/openapi.json")
    assert resp.status_code == 200
    schema = resp.json()

    output_path = os.path.join(OUTPUT_DIR, "openapi.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(schema, f, indent=2, ensure_ascii=False)

    print(f"[API Docs] OpenAPI spec written to {output_path}")
    return schema


def generate_markdown_docs(schema: dict):
    ensure_output_dir()

    lines = []
    lines.append("# XHS365 API 文档")
    lines.append("")
    lines.append(f"> 自动生成于 {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    lines.append("")
    lines.append(f"**版本**: {schema.get('info', {}).get('version', 'N/A')}")
    lines.append(f"**描述**: {schema.get('info', {}).get('description', 'N/A')}")
    lines.append("")

    lines.append("## 目录")
    lines.append("")

    tags = {}
    paths = schema.get("paths", {})

    for path, methods in sorted(paths.items()):
        for method, details in methods.items():
            if method in ("parameters", "summary", "description"):
                continue
            tag = (details.get("tags") or ["未分类"])[0]
            if tag not in tags:
                tags[tag] = []
            tags[tag].append((method.upper(), path, details))

    for tag in sorted(tags.keys()):
        lines.append(f"- [{tag}](#{tag.lower().replace(' ', '-')})")

    lines.append("")

    for tag in sorted(tags.keys()):
        lines.append(f"## {tag}")
        lines.append("")

        for method, path, details in sorted(tags[tag], key=lambda x: x[1]):
            summary = details.get("summary", path)
            description = details.get("description", "")

            lines.append(f"### {method} {path}")
            lines.append("")
            lines.append(f"**{summary}**")
            lines.append("")

            if description:
                lines.append(description)
                lines.append("")

            parameters = details.get("parameters", [])
            if parameters:
                lines.append("**参数**:")
                lines.append("")
                lines.append("| 名称 | 位置 | 类型 | 必填 | 描述 |")
                lines.append("|------|------|------|------|------|")
                for param in parameters:
                    name = param.get("name", "")
                    location = param.get("in", "")
                    ptype = param.get("schema", {}).get("type", "string")
                    required = "是" if param.get("required") else "否"
                    desc = param.get("description", "")
                    lines.append(f"| {name} | {location} | {ptype} | {required} | {desc} |")
                lines.append("")

            request_body = details.get("requestBody", {})
            if request_body:
                lines.append("**请求体**:")
                lines.append("")
                content = request_body.get("content", {})
                if "application/json" in content:
                    schema_ref = content["application/json"].get("schema", {})
                    if "$ref" in schema_ref:
                        ref_name = schema_ref["$ref"].split("/")[-1]
                        lines.append(f"类型: `{ref_name}`")
                    lines.append("")
                    lines.append("```json")
                    lines.append(json.dumps(schema_ref, indent=2, ensure_ascii=False))
                    lines.append("```")
                lines.append("")

            responses = details.get("responses", {})
            if responses:
                lines.append("**响应**:")
                lines.append("")
                for status_code, response in sorted(responses.items()):
                    desc = response.get("description", "")
                    lines.append(f"- `{status_code}`: {desc}")
                lines.append("")

            lines.append("---")
            lines.append("")

    output_path = os.path.join(OUTPUT_DIR, "api-reference.md")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"[API Docs] Markdown docs written to {output_path}")


def generate_postman_collection(schema: dict):
    ensure_output_dir()

    collection = {
        "info": {
            "name": "XHS365 API",
            "description": schema.get("info", {}).get("description", ""),
            "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
        },
        "item": [],
        "variable": [
            {"key": "base_url", "value": "http://localhost:8000"},
            {"key": "token", "value": ""},
        ],
    }

    paths = schema.get("paths", {})
    tags_map = {}

    for path, methods in sorted(paths.items()):
        for method, details in methods.items():
            if method in ("parameters", "summary", "description"):
                continue
            tag = (details.get("tags") or ["未分类"])[0]
            if tag not in tags_map:
                tags_map[tag] = []
            tags_map[tag].append((method.upper(), path, details))

    for tag in sorted(tags_map.keys()):
        folder = {"name": tag, "item": []}

        for method, path, details in sorted(tags_map[tag], key=lambda x: x[1]):
            item = {
                "name": details.get("summary", path),
                "request": {
                    "method": method,
                    "header": [
                        {"key": "Authorization", "value": "Bearer {{token}}"},
                        {"key": "Content-Type", "value": "application/json"},
                    ],
                    "url": {
                        "raw": f"{{{{base_url}}}}{path}",
                        "host": ["{{base_url}}"],
                        "path": [seg for seg in path.split("/") if seg],
                    },
                },
            }

            request_body = details.get("requestBody", {})
            if request_body:
                content = request_body.get("content", {})
                if "application/json" in content:
                    example = content["application/json"].get("example", {})
                    schema_ref = content["application/json"].get("schema", {})
                    if not example and "properties" in schema_ref:
                        example = {
                            k: f"<{v.get('type', 'string')}>"
                            for k, v in schema_ref.get("properties", {}).items()
                        }
                    item["request"]["body"] = {
                        "mode": "raw",
                        "raw": json.dumps(example, indent=2, ensure_ascii=False),
                        "options": {"raw": {"language": "json"}},
                    }

            folder["item"].append(item)

        collection["item"].append(folder)

    output_path = os.path.join(OUTPUT_DIR, "postman-collection.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(collection, f, indent=2, ensure_ascii=False)

    print(f"[API Docs] Postman collection written to {output_path}")


def generate_endpoint_summary(schema: dict):
    ensure_output_dir()

    paths = schema.get("paths", {})
    lines = []
    lines.append("# API 端点清单")
    lines.append("")
    lines.append(f"| 方法 | 路径 | 描述 | 认证 |")
    lines.append("|------|------|------|------|")

    for path, methods in sorted(paths.items()):
        for method, details in methods.items():
            if method in ("parameters", "summary", "description"):
                continue
            summary = details.get("summary", "")
            security = details.get("security", [{}])
            requires_auth = "是" if any(security) else "否"
            lines.append(f"| {method.upper()} | `{path}` | {summary} | {requires_auth} |")

    lines.append("")
    lines.append(f"**总计**: {len(lines) - 4} 个端点")

    output_path = os.path.join(OUTPUT_DIR, "endpoints.md")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"[API Docs] Endpoint summary written to {output_path}")


def main():
    print("=" * 60)
    print("XHS365 API 文档自动生成")
    print("=" * 60)

    schema = generate_openapi_spec()
    generate_markdown_docs(schema)
    generate_postman_collection(schema)
    generate_endpoint_summary(schema)

    print("")
    print("=" * 60)
    print("文档生成完成!")
    print(f"输出目录: {OUTPUT_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    main()