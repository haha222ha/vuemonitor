#!/usr/bin/env python3
"""
API Documentation Generator
Generates OpenAPI specifications and alternative documentation formats.

Usage:
    python scripts/generate_api_docs.py --format openapi --output ./docs/api/
    python scripts/generate_api_docs.py --format redoc --output ./docs/redoc.html
    python scripts/generate_api_docs.py --format all --output ./docs/
"""
import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "server"))


def get_openapi_spec():
    from fastapi.openapi.utils import get_openapi

    from app.main import app

    return get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )


def generate_openapi_json(output_path: str):
    spec = get_openapi_spec()
    output_file = Path(output_path) / "openapi.json"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(spec, f, indent=2, ensure_ascii=False)
    print(f"Generated OpenAPI JSON: {output_file}")
    return output_file


def generate_openapi_yaml(output_path: str):
    try:
        import yaml
    except ImportError:
        print("PyYAML not installed. Run: pip install pyyaml")
        return None

    spec = get_openapi_spec()
    output_file = Path(output_path) / "openapi.yaml"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        yaml.dump(spec, f, default_flow_style=False, allow_unicode=True)
    print(f"Generated OpenAPI YAML: {output_file}")
    return output_file


def generate_redoc_html(output_path: str):
    spec = get_openapi_spec()
    spec_url = "./openapi.json"

    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>VueMonitor API Documentation</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@300;400;700&display=swap" rel="stylesheet">
    <style>
        body {{
            margin: 0;
            padding: 0;
        }}
    </style>
</head>
<body>
    <redoc spec-url='{spec_url}'></redoc>
    <script src="https://cdn.jsdelivr.net/npm/redoc@next/bundles/redoc.standalone.js"></script>
</body>
</html>
"""

    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"Generated ReDoc HTML: {output_file}")
    return output_file


def generateSwaggerHtml(output_path: str):
    spec = get_openapi_spec()
    spec_url = "./openapi.json"

    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>VueMonitor API - Swagger UI</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css">
</head>
<body>
    <div id="swagger-ui"></div>
    <script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
    <script>
        window.onload = function() {{
            SwaggerUIBuilders.preset
            SwaggerUIBundle({{
                url: "{spec_url}",
                dom_id: '#swagger-ui',
                presets: [
                    SwaggerUIBundle.presets.apis,
                    SwaggerUIBundle.SwaggerUIStandalonePreset
                ],
                layout: "BaseLayout",
                deepLinking: true
            }})
        }}
    </script>
</body>
</html>
"""

    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"Generated Swagger UI HTML: {output_file}")
    return output_file


def generate_postman_collection(output_path: str):
    spec = get_openapi_spec()

    postman_collection = {
        "info": {
            "name": spec.get("info", {}).get("title", "VueMonitor API"),
            "description": spec.get("info", {}).get("description", ""),
            "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
        },
        "item": []
    }

    paths = spec.get("paths", {})

    for path, methods in paths.items():
        for method, details in methods.items():
            if method.upper() in ["GET", "POST", "PUT", "PATCH", "DELETE"]:
                item = {
                    "name": details.get("summary", f"{method.upper()} {path}"),
                    "request": {
                        "method": method.upper(),
                        "header": [],
                        "url": {
                            "raw": "{{base_url}}" + path,
                            "host": ["{{base_url}}"],
                            "path": path.split("/")[1:]
                        }
                    }
                }

                if details.get("requestBody"):
                    item["request"]["body"] = {
                        "mode": "raw",
                        "raw": json.dumps(details["requestBody"].get("content", {}).get("application/json", {}).get("example", {}), indent=2)
                    }

                postman_collection["item"].append(item)

    output_file = Path(output_path) / "postman_collection.json"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(postman_collection, f, indent=2, ensure_ascii=False)
    print(f"Generated Postman Collection: {output_file}")
    return output_file


def generate_api_usage_examples(output_path: str):
    spec = get_openapi_spec()
    paths = spec.get("paths", {})

    examples = []
    examples.append("# VueMonitor API Usage Examples\n")

    for path, methods in paths.items():
        for method, details in methods.items():
            if method.upper() in ["GET", "POST", "PUT", "PATCH", "DELETE"]:
                summary = details.get("summary", f"{method.upper()} {path}")
                description = details.get("description", "")
                tags = details.get("tags", [])

                examples.append(f"## {summary}\n")
                examples.append(f"**Endpoint:** `{method.upper()} {path}`\n")
                if tags:
                    examples.append(f"**Tags:** {', '.join(tags)}\n")
                if description:
                    examples.append(f"**Description:** {description}\n")

                examples.append(f"\n```bash\n# cURL example\ncurl -X {method.upper()} https://api.xhs365.cn{path} \\\n  -H \"Authorization: Bearer $ACCESS_TOKEN\" \\\n  -H \"Content-Type: application/json\"\n```\n\n")

    output_file = Path(output_path) / "API_USAGE_EXAMPLES.md"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        f.writelines(examples)
    print(f"Generated API Usage Examples: {output_file}")
    return output_file


def main():
    parser = argparse.ArgumentParser(description="Generate API Documentation")
    parser.add_argument("--format", "-f", choices=["openapi", "yaml", "redoc", "swagger", "postman", "examples", "all"],
                        default="all", help="Documentation format to generate")
    parser.add_argument("--output", "-o", default="./docs", help="Output directory")

    args = parser.parse_args()

    if args.format == "all":
        generate_openapi_json(args.output)
        generate_openapi_yaml(args.output)
        generate_redoc_html(args.output)
        generateSwaggerHtml(args.output)
        generate_postman_collection(args.output)
        generate_api_usage_examples(args.output)
    elif args.format == "openapi":
        generate_openapi_json(args.output)
    elif args.format == "yaml":
        generate_openapi_yaml(args.output)
    elif args.format == "redoc":
        generate_redoc_html(args.output)
    elif args.format == "swagger":
        generateSwaggerHtml(args.output)
    elif args.format == "postman":
        generate_postman_collection(args.output)
    elif args.format == "examples":
        generate_api_usage_examples(args.output)

    print("\nDocumentation generation complete!")


if __name__ == "__main__":
    main()
