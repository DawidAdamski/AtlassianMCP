from __future__ import annotations

from typing import Annotated, Any

from pydantic import Field
from requests import HTTPError

from mcp.server.fastmcp import FastMCP

from ..clients import create_jira_client
from ..server_cli import main_from_factory
from ..settings import JiraSettings


def _safe_call(operation: str, func: Any) -> dict[str, Any]:
    try:
        result = func()
        return {"ok": True, "operation": operation, "data": result}
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


def build_server(settings: JiraSettings, *, json_response: bool = False) -> FastMCP:
    client = create_jira_client(settings)
    mcp = FastMCP("atlassian-jira", json_response=json_response)

    @mcp.tool()
    def search_issues(
        jql: Annotated[str, Field(description="JQL query used to search for issues.")],
        fields: Annotated[list[str] | None, Field(description="Optional list of fields to return.")] = None,
        limit: Annotated[int | None, Field(description="Maximum number of results to return.", ge=1, le=200)] = 50,
        start: Annotated[int, Field(description="Pagination start offset for Jira Server/Data Center.", ge=0)] = 0,
        next_page_token: Annotated[
            str | None, Field(description="Pagination token for Jira Cloud enhanced JQL.")
        ] = None,
        expand: Annotated[str | None, Field(description="Comma-separated expand values.")] = None,
    ) -> dict[str, Any]:
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
            lambda: client.jql(jql=jql, fields=fields or "*all", start=start, limit=limit, expand=expand),
        )

    @mcp.tool()
    def get_issue(
        issue_key: Annotated[str, Field(description="Issue key or ID, for example PROJ-123.")],
        fields: Annotated[list[str] | None, Field(description="Optional list of fields to return.")] = None,
        expand: Annotated[str | None, Field(description="Optional expand string.")] = None,
    ) -> dict[str, Any]:
        return _safe_call("get_issue", lambda: client.issue(issue_key, fields=fields or "*all", expand=expand))

    @mcp.tool()
    def create_issue(
        project_key: Annotated[str, Field(description="Project key where the issue should be created.")],
        issue_type: Annotated[str, Field(description="Issue type name, for example Story or Task.")],
        summary: Annotated[str, Field(description="Issue summary.")],
        description: Annotated[str | None, Field(description="Optional issue description.")] = None,
        fields: Annotated[dict[str, Any] | None, Field(description="Additional Jira fields to merge into the payload.")] = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "project": {"key": project_key},
            "issuetype": {"name": issue_type},
            "summary": summary,
        }
        if description:
            payload["description"] = description
        if fields:
            payload.update(fields)
        return _safe_call("create_issue", lambda: client.create_issue(fields=payload))

    @mcp.tool()
    def update_issue(
        issue_key: Annotated[str, Field(description="Issue key or ID to update.")],
        fields: Annotated[dict[str, Any], Field(description="Fields payload to send to Jira.")],
        notify_users: Annotated[bool, Field(description="Whether Jira should notify impacted users.")] = True,
    ) -> dict[str, Any]:
        return _safe_call(
            "update_issue",
            lambda: client.issue_update(issue_key=issue_key, fields=fields, notify_users=notify_users),
        )

    @mcp.tool()
    def transition_issue(
        issue_key: Annotated[str, Field(description="Issue key or ID to transition.")],
        transition_name: Annotated[
            str | None, Field(description="Human-readable transition name, for example Done.")
        ] = None,
        transition_id: Annotated[str | None, Field(description="Explicit transition ID.")] = None,
        comment: Annotated[str | None, Field(description="Optional comment to add after transition.")] = None,
    ) -> dict[str, Any]:
        def _run() -> dict[str, Any]:
            if transition_id:
                result = client.set_issue_status_by_transition_id(issue_key, transition_id)
            elif transition_name:
                result = client.set_issue_status_by_transition_name(issue_key, transition_name)
            else:
                raise ValueError("Set transition_name or transition_id.")
            if comment:
                client.issue_add_comment(issue_key, comment)
            return {"transition": result, "issue": issue_key}

        return _safe_call("transition_issue", _run)

    @mcp.tool()
    def add_issue_comment(
        issue_key: Annotated[str, Field(description="Issue key or ID to comment on.")],
        body: Annotated[str, Field(description="Comment body text.")],
    ) -> dict[str, Any]:
        return _safe_call("add_issue_comment", lambda: client.issue_add_comment(issue_key, body))

    @mcp.tool()
    def assign_issue(
        issue_key: Annotated[str, Field(description="Issue key or ID to assign.")],
        assignee: Annotated[
            str | None,
            Field(description="Account ID for Cloud or username for Server/Data Center. Use null to unassign."),
        ] = None,
    ) -> dict[str, Any]:
        return _safe_call("assign_issue", lambda: client.assign_issue(issue_key, assignee))

    @mcp.tool()
    def jira_myself() -> dict[str, Any]:
        return _safe_call("jira_myself", client.myself)

    @mcp.tool()
    def jira_server_info() -> dict[str, Any]:
        return _safe_call("jira_server_info", client.get_server_info)

    @mcp.tool()
    def list_projects() -> dict[str, Any]:
        return _safe_call("list_projects", lambda: {"values": client.get_all_projects()})

    @mcp.tool()
    def list_sprints(
        board_id: Annotated[int, Field(description="Agile board ID.")],
        state: Annotated[
            str | None, Field(description="Optional sprint state filter, e.g. active,future,closed.")
        ] = None,
        start: Annotated[int, Field(description="Pagination start offset.", ge=0)] = 0,
        limit: Annotated[int, Field(description="Maximum number of sprints to return.", ge=1, le=200)] = 50,
    ) -> dict[str, Any]:
        return _safe_call(
            "list_sprints",
            lambda: client.get_all_sprints_from_board(board_id=board_id, state=state, start=start, limit=limit),
        )

    @mcp.tool()
    def get_sprint_issues(
        sprint_id: Annotated[int, Field(description="Sprint ID.")],
        start: Annotated[int, Field(description="Pagination start offset.", ge=0)] = 0,
        limit: Annotated[int, Field(description="Maximum number of issues to return.", ge=1, le=200)] = 50,
    ) -> dict[str, Any]:
        return _safe_call(
            "get_sprint_issues",
            lambda: client.get_sprint_issues(sprint_id=sprint_id, start=start, limit=limit),
        )

    return mcp


def main() -> int:
    return main_from_factory(
        "atlassian-mcp-jira",
        lambda args: build_server(JiraSettings(), json_response=args.json_response),
    )
