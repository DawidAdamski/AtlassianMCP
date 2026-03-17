from __future__ import annotations

from typing import Annotated, Any

from pydantic import Field
from requests import HTTPError, Response

from mcp.server.mcpserver import MCPServer

from ..clients import create_jira_client
from ..server_cli import main_from_factory
from ..settings import JiraSettings


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


def _safe_call(operation: str, func: Any) -> dict[str, Any]:
    try:
        return {"ok": True, "operation": operation, "data": _normalize_result(func())}
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
        return details
    except Exception as exc:
        return {
            "ok": False,
            "operation": operation,
            "error_type": type(exc).__name__,
            "message": str(exc),
        }


def build_server(settings: JiraSettings) -> MCPServer:
    client = create_jira_client(settings)
    mcp = MCPServer("atlassian-jira")

    @mcp.tool()
    def ping() -> str:
        """Return a local connectivity check without calling Jira."""
        return "pong"

    @mcp.tool()
    def jira_config_debug() -> dict[str, Any]:
        """Return non-secret Jira MCP configuration visible to the running server."""
        return {
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

    @mcp.tool()
    def jira_myself() -> dict[str, Any]:
        """Return the currently authenticated Jira user."""
        return _safe_call("jira_myself", client.myself)

    @mcp.tool()
    def jira_server_info() -> dict[str, Any]:
        """Return Jira server information."""
        return _safe_call("jira_server_info", client.get_server_info)

    @mcp.tool()
    def list_projects() -> dict[str, Any]:
        """List visible Jira projects."""
        return _safe_call("list_projects", lambda: {"values": client.get_all_projects()})

    @mcp.tool()
    def get_issue(
        issue_key: Annotated[str, Field(description="Issue key or ID, for example PROJ-123.")],
        fields: Annotated[list[str] | None, Field(description="Optional fields to return.")] = None,
        expand: Annotated[str | None, Field(description="Optional expand string.")] = None,
    ) -> dict[str, Any]:
        """Get a Jira issue by key or id."""
        return _safe_call(
            "get_issue",
            lambda: client.issue(issue_key, fields=fields or "*all", expand=expand),
        )

    @mcp.tool()
    def search_issues(
        jql: Annotated[str, Field(description="JQL query.")],
        fields: Annotated[list[str] | None, Field(description="Optional fields to return.")] = None,
        limit: Annotated[int, Field(description="Maximum results to return.", ge=1, le=500)] = 50,
        start: Annotated[int, Field(description="Pagination start offset for non-Cloud Jira.", ge=0)] = 0,
        next_page_token: Annotated[
            str | None,
            Field(description="Pagination token for Jira Cloud enhanced JQL."),
        ] = None,
        expand: Annotated[str | None, Field(description="Optional expand string.")] = None,
    ) -> dict[str, Any]:
        """Search Jira issues using JQL."""
        if settings.cloud:
            return _safe_call(
                "search_issues",
                lambda: client.enhanced_jql(
                    jql=jql,
                    fields=fields or "*all",
                    nextPageToken=next_page_token,
                    limit=limit,
                    expand=expand,
                ),
            )
        return _safe_call(
            "search_issues",
            lambda: client.jql(
                jql=jql,
                fields=fields or "*all",
                start=start,
                limit=limit,
                expand=expand,
            ),
        )

    @mcp.tool()
    def add_issue_comment(
        issue_key: Annotated[str, Field(description="Issue key or ID.")],
        body: Annotated[str, Field(description="Comment body text.")],
    ) -> dict[str, Any]:
        """Add a comment to a Jira issue."""
        return _safe_call("add_issue_comment", lambda: client.issue_add_comment(issue_key, body))

    @mcp.tool()
    def assign_issue(
        issue_key: Annotated[str, Field(description="Issue key or ID.")],
        assignee: Annotated[
            str | None,
            Field(description="Account ID for Cloud or username for Server/Data Center."),
        ] = None,
    ) -> dict[str, Any]:
        """Assign a Jira issue."""
        return _safe_call("assign_issue", lambda: client.assign_issue(issue_key, assignee))

    @mcp.tool()
    def create_issue(
        project_key: Annotated[str, Field(description="Project key.")],
        issue_type: Annotated[str, Field(description="Issue type name.")],
        summary: Annotated[str, Field(description="Issue summary.")],
        description: Annotated[str | None, Field(description="Optional issue description.")] = None,
        fields: Annotated[dict[str, Any] | None, Field(description="Additional Jira fields.")] = None,
    ) -> dict[str, Any]:
        """Create a Jira issue."""
        payload: dict[str, Any] = {
            "project": {"key": project_key},
            "issuetype": {"name": issue_type},
            "summary": summary,
        }
        if description is not None:
            payload["description"] = description
        if fields:
            payload.update(fields)
        return _safe_call("create_issue", lambda: client.create_issue(fields=payload))

    @mcp.tool()
    def update_issue(
        issue_key: Annotated[str, Field(description="Issue key or ID.")],
        fields: Annotated[dict[str, Any], Field(description="Fields payload to send to Jira.")],
        notify_users: Annotated[
            bool,
            Field(description="Whether Jira should notify impacted users."),
        ] = True,
    ) -> dict[str, Any]:
        """Update a Jira issue."""
        return _safe_call(
            "update_issue",
            lambda: client.issue_update(issue_key=issue_key, fields=fields, notify_users=notify_users),
        )

    @mcp.tool()
    def transition_issue(
        issue_key: Annotated[str, Field(description="Issue key or ID.")],
        transition_name: Annotated[str | None, Field(description="Human-readable transition name.")] = None,
        transition_id: Annotated[str | None, Field(description="Explicit transition ID.")] = None,
        comment: Annotated[str | None, Field(description="Optional comment to add after transition.")] = None,
    ) -> dict[str, Any]:
        """Transition a Jira issue."""

        def _transition() -> dict[str, Any]:
            if transition_id:
                result = client.set_issue_status_by_transition_id(issue_key, transition_id)
            elif transition_name:
                result = client.set_issue_status_by_transition_name(issue_key, transition_name)
            else:
                raise ValueError("Set transition_name or transition_id.")
            if comment:
                client.issue_add_comment(issue_key, comment)
            return {"transition": result, "issue": issue_key}

        return _safe_call("transition_issue", _transition)

    @mcp.tool()
    def list_sprints(
        board_id: Annotated[int, Field(description="Agile board ID.")],
        state: Annotated[str | None, Field(description="Optional sprint state filter.")] = None,
        start: Annotated[int, Field(description="Pagination start offset.", ge=0)] = 0,
        limit: Annotated[int, Field(description="Maximum number of sprints to return.", ge=1, le=200)] = 50,
    ) -> dict[str, Any]:
        """List sprints for an agile board."""
        return _safe_call(
            "list_sprints",
            lambda: client.get_all_sprints_from_board(
                board_id=board_id,
                state=state,
                start=start,
                limit=limit,
            ),
        )

    @mcp.tool()
    def get_sprint_issues(
        sprint_id: Annotated[int, Field(description="Sprint ID.")],
        start: Annotated[int, Field(description="Pagination start offset.", ge=0)] = 0,
        limit: Annotated[int, Field(description="Maximum number of issues to return.", ge=1, le=500)] = 50,
    ) -> dict[str, Any]:
        """List issues in a sprint."""
        return _safe_call(
            "get_sprint_issues",
            lambda: client.get_sprint_issues(sprint_id=sprint_id, start=start, limit=limit),
        )

    return mcp


def main() -> int:
    return main_from_factory("atlassian-mcp-jira", lambda args: build_server(JiraSettings()))
