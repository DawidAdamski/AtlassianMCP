from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import anyio

from .servers.bitbucket import build_server as build_bitbucket_server
from .servers.confluence import build_server as build_confluence_server
from .servers.jira import build_server as build_jira_server
from .servers.jsm import build_server as build_jsm_server
from .settings import BitbucketSettings, ConfluenceSettings, JiraSettings, JsmSettings


def _schema_type(spec: dict[str, Any]) -> str:
    if "type" in spec and isinstance(spec["type"], str):
        return spec["type"]
    if "anyOf" in spec:
        return " | ".join(_schema_type(option) for option in spec["anyOf"])
    if "items" in spec:
        return f"array[{_schema_type(spec['items'])}]"
    return "object"


def _render_properties(schema: dict[str, Any]) -> str:
    properties = schema.get("properties", {})
    required = set(schema.get("required", []))
    if not properties:
        return "_No arguments._\n"

    lines = [
        "| Argument | Type | Required | Description |",
        "| --- | --- | --- | --- |",
    ]
    for name, spec in properties.items():
        arg_type = _schema_type(spec)
        description = spec.get("description", "").replace("\n", " ").strip()
        lines.append(f"| `{name}` | `{arg_type}` | `{'yes' if name in required else 'no'}` | {description} |")
    return "\n".join(lines) + "\n"


async def _export() -> None:
    output_dir = Path("docs/generated")
    output_dir.mkdir(parents=True, exist_ok=True)

    registry = [
        ("jira", build_jira_server(JiraSettings.example())),
        ("jsm", build_jsm_server(JsmSettings.example())),
        ("confluence", build_confluence_server(ConfluenceSettings.example())),
        ("bitbucket", build_bitbucket_server(BitbucketSettings.example())),
    ]

    index_lines = ["# Generated Tool Docs", ""]

    for name, server in registry:
        tools = await server.list_tools()
        doc_lines = [f"# {name.capitalize()} MCP Tools", ""]
        index_lines.append(f"- [{name}](./{name}.md)")
        for tool in tools:
            doc_lines.append(f"## `{tool.name}`")
            doc_lines.append("")
            if tool.description:
                doc_lines.append(tool.description)
                doc_lines.append("")
            doc_lines.append("### Arguments")
            doc_lines.append("")
            doc_lines.append(_render_properties(tool.input_schema))
            if tool.output_schema:
                doc_lines.append("### Output Schema")
                doc_lines.append("")
                doc_lines.append("```json")
                doc_lines.append(json.dumps(tool.output_schema, indent=2))
                doc_lines.append("```")
                doc_lines.append("")
        (output_dir / f"{name}.md").write_text("\n".join(doc_lines), encoding="utf-8")

    (output_dir / "README.md").write_text("\n".join(index_lines) + "\n", encoding="utf-8")


def main() -> int:
    anyio.run(_export)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
