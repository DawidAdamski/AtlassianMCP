from __future__ import annotations

import argparse
import asyncio
import json
from typing import Any

import mcp.server.stdio
from mcp import types
from mcp.server import Server, ServerRequestContext
from requests import HTTPError, Response

from ..clients import create_jira_client
from ..settings import JiraSettings


def _dump_text(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True, default=str)


def _normalize_result(result: Any) -> Any:
    if isinstance(result, Response):
        try:
            return result.json()
        except Exception:
            return {
                "status_code": result.status_code,
                "reason": result.reason,
                "text": result.text,
                "url": result.url,
            }
    return result


def _safe_call(operation: str, func: Any) -> str:
    try:
        return _dump_text({"ok": True, "operation": operation, "data": _normalize_result(func())})
    except HTTPError as exc:
        response = exc.response
        details: dict[str, Any] = {
            "ok": False,
            "operation": operation,
            "error_type": "http_error",
            "message": str(exc),
        }
        if response is not None:
            details["status_code"] = response.status_code
            details["reason"] = response.reason
            details["url"] = response.url
            details["request_id"] = response.headers.get("X-AREQUESTID") or response.headers.get("x-arequestid")
            try:
                details["response"] = response.json()
            except Exception:
                details["response_text"] = response.text
        return _dump_text(details)
    except Exception as exc:
        return _dump_text(
            {
                "ok": False,
                "operation": operation,
                "error_type": type(exc).__name__,
                "message": str(exc),
            }
        )


def _text_result(text: str, *, is_error: bool = False) -> types.CallToolResult:
    return types.CallToolResult(content=[types.TextContent(type="text", text=text)], is_error=is_error)


def _tool(
    name: str,
    description: str,
    properties: dict[str, Any] | None = None,
    required: list[str] | None = None,
) -> types.Tool:
    schema: dict[str, Any] = {"type": "object", "properties": properties or {}}
    if required:
        schema["required"] = required
    return types.Tool(name=name, description=description, input_schema=schema)


def build_server(settings: JiraSettings) -> Server:
    client = create_jira_client(settings)

    tools = [
        _tool("ping", "Return a local connectivity check without calling Jira."),
        _tool("jira_config_debug", "Return non-secret Jira MCP configuration visible to the running container."),
        _tool("jira_myself", "Return the currently authenticated Jira user."),
        _tool("jira_server_info", "Return Jira server information."),
        _tool("list_projects", "List visible Jira projects."),
        _tool(
            "get_issue",
            "Get a Jira issue by key or id.",
            {
                "issue_key": {"type": "string", "description": "Issue key or ID, for example PROJ-123."},
                "fields": {"type": "array", "items": {"type": "string"}, "description": "Optional fields to return."},
                "expand": {"type": "string", "description": "Optional expand string."},
            },
            ["issue_key"],
        ),
        _tool(
            "search_issues",
            "Search Jira issues using JQL.",
            {
                "jql": {"type": "string", "description": "JQL query."},
                "fields": {"type": "array", "items": {"type": "string"}, "description": "Optional fields to return."},
                "limit": {"type": "integer", "description": "Maximum results to return."},
                "start": {"type": "integer", "description": "Pagination start offset."},
                "next_page_token": {"type": "string", "description": "Pagination token for Jira Cloud."},
                "expand": {"type": "string", "description": "Optional expand string."},
            },
            ["jql"],
        ),
        _tool(
            "add_issue_comment",
            "Add a comment to a Jira issue.",
            {
                "issue_key": {"type": "string", "description": "Issue key or ID."},
                "body": {"type": "string", "description": "Comment body text."},
            },
            ["issue_key", "body"],
        ),
        _tool(
            "assign_issue",
            "Assign a Jira issue.",
            {
                "issue_key": {"type": "string", "description": "Issue key or ID."},
                "assignee": {
                    "type": "string",
                    "description": "Account ID for Cloud or username for Server/Data Center.",
                },
            },
            ["issue_key"],
        ),
        _tool(
            "create_issue",
            "Create a Jira issue.",
            {
                "project_key": {"type": "string", "description": "Project key."},
                "issue_type": {"type": "string", "description": "Issue type name."},
                "summary": {"type": "string", "description": "Issue summary."},
                "description": {"type": "string", "description": "Optional issue description."},
                "fields": {"type": "object", "description": "Additional Jira fields."},
            },
            ["project_key", "issue_type", "summary"],
        ),
        _tool(
            "update_issue",
            "Update a Jira issue.",
            {
                "issue_key": {"type": "string", "description": "Issue key or ID."},
                "fields": {"type": "object", "description": "Fields payload to send to Jira."},
                "notify_users": {"type": "boolean", "description": "Whether Jira should notify impacted users."},
            },
            ["issue_key", "fields"],
        ),
        _tool(
            "transition_issue",
            "Transition a Jira issue.",
            {
                "issue_key": {"type": "string", "description": "Issue key or ID."},
                "transition_name": {"type": "string", "description": "Human-readable transition name."},
                "transition_id": {"type": "string", "description": "Explicit transition ID."},
                "comment": {"type": "string", "description": "Optional comment to add after transition."},
            },
            ["issue_key"],
        ),
        _tool(
            "list_sprints",
            "List sprints for an agile board.",
            {
                "board_id": {"type": "integer", "description": "Agile board ID."},
                "state": {"type": "string", "description": "Optional sprint state filter."},
                "start": {"type": "integer", "description": "Pagination start offset."},
                "limit": {"type": "integer", "description": "Maximum number of sprints to return."},
            },
            ["board_id"],
        ),
        _tool(
            "get_sprint_issues",
            "List issues in a sprint.",
            {
                "sprint_id": {"type": "integer", "description": "Sprint ID."},
                "start": {"type": "integer", "description": "Pagination start offset."},
                "limit": {"type": "integer", "description": "Maximum number of issues to return."},
            },
            ["sprint_id"],
        ),
    ]

    async def handle_list_tools(
        ctx: ServerRequestContext, params: types.PaginatedRequestParams | None
    ) -> types.ListToolsResult:
        return types.ListToolsResult(tools=tools)

    async def handle_call_tool(ctx: ServerRequestContext, params: types.CallToolRequestParams) -> types.CallToolResult:
        arguments = params.arguments or {}
        name = params.name

        if name == "ping":
            return _text_result("pong")

        if name == "jira_config_debug":
            return _text_result(
                _dump_text(
                    {
                        "ok": True,
                        "server": "atlassian-jira",
                        "config": {
                            "url": settings.url,
                            "cloud": settings.cloud,
                            "timeout": settings.timeout,
                            "verify_ssl": settings.verify_ssl,
                            "has_username": bool(settings.username),
                            "has_password": settings.password is not None,
                            "has_token": settings.token is not None,
                        },
                    }
                )
            )

        if name == "jira_myself":
            return _text_result(_safe_call("jira_myself", client.myself))

        if name == "jira_server_info":
            return _text_result(_safe_call("jira_server_info", client.get_server_info))

        if name == "list_projects":
            return _text_result(_safe_call("list_projects", lambda: {"values": client.get_all_projects()}))

        if name == "get_issue":
            return _text_result(
                _safe_call(
                    "get_issue",
                    lambda: client.issue(
                        arguments["issue_key"],
                        fields=arguments.get("fields") or "*all",
                        expand=arguments.get("expand"),
                    ),
                )
            )

        if name == "search_issues":
            if settings.cloud:
                return _text_result(
                    _safe_call(
                        "search_issues",
                        lambda: client.enhanced_jql(
                            jql=arguments["jql"],
                            fields=arguments.get("fields") or "*all",
                            nextPageToken=arguments.get("next_page_token"),
                            limit=arguments.get("limit", 50),
                            expand=arguments.get("expand"),
                        ),
                    )
                )
            return _text_result(
                _safe_call(
                    "search_issues",
                    lambda: client.jql(
                        jql=arguments["jql"],
                        fields=arguments.get("fields") or "*all",
                        start=arguments.get("start", 0),
                        limit=arguments.get("limit", 50),
                        expand=arguments.get("expand"),
                    ),
                )
            )

        if name == "add_issue_comment":
            return _text_result(
                _safe_call("add_issue_comment", lambda: client.issue_add_comment(arguments["issue_key"], arguments["body"]))
            )

        if name == "assign_issue":
            return _text_result(
                _safe_call("assign_issue", lambda: client.assign_issue(arguments["issue_key"], arguments.get("assignee")))
            )

        if name == "create_issue":
            payload: dict[str, Any] = {
                "project": {"key": arguments["project_key"]},
                "issuetype": {"name": arguments["issue_type"]},
                "summary": arguments["summary"],
            }
            if arguments.get("description"):
                payload["description"] = arguments["description"]
            if arguments.get("fields"):
                payload.update(arguments["fields"])
            return _text_result(_safe_call("create_issue", lambda: client.create_issue(fields=payload)))

        if name == "update_issue":
            return _text_result(
                _safe_call(
                    "update_issue",
                    lambda: client.issue_update(
                        issue_key=arguments["issue_key"],
                        fields=arguments["fields"],
                        notify_users=arguments.get("notify_users", True),
                    ),
                )
            )

        if name == "transition_issue":
            def _transition() -> dict[str, Any]:
                if arguments.get("transition_id"):
                    result = client.set_issue_status_by_transition_id(arguments["issue_key"], arguments["transition_id"])
                elif arguments.get("transition_name"):
                    result = client.set_issue_status_by_transition_name(arguments["issue_key"], arguments["transition_name"])
                else:
                    raise ValueError("Set transition_name or transition_id.")
                if arguments.get("comment"):
                    client.issue_add_comment(arguments["issue_key"], arguments["comment"])
                return {"transition": result, "issue": arguments["issue_key"]}

            return _text_result(_safe_call("transition_issue", _transition))

        if name == "list_sprints":
            return _text_result(
                _safe_call(
                    "list_sprints",
                    lambda: client.get_all_sprints_from_board(
                        board_id=arguments["board_id"],
                        state=arguments.get("state"),
                        start=arguments.get("start", 0),
                        limit=arguments.get("limit", 50),
                    ),
                )
            )

        if name == "get_sprint_issues":
            return _text_result(
                _safe_call(
                    "get_sprint_issues",
                    lambda: client.get_sprint_issues(
                        sprint_id=arguments["sprint_id"],
                        start=arguments.get("start", 0),
                        limit=arguments.get("limit", 50),
                    ),
                )
            )

        return _text_result(f"Unknown tool: {name}", is_error=True)

    return Server(
        "atlassian-jira",
        on_list_tools=handle_list_tools,
        on_call_tool=handle_call_tool,
    )


async def _run_stdio() -> None:
    server = build_server(JiraSettings())
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


def main() -> int:
    parser = argparse.ArgumentParser(prog="atlassian-mcp-jira")
    parser.add_argument("--transport", choices=["stdio"], default="stdio")
    parser.parse_args()
    asyncio.run(_run_stdio())
    return 0
