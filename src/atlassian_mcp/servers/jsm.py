from __future__ import annotations

from typing import Annotated, Any

from pydantic import Field

from mcp.server.fastmcp import FastMCP

from ..clients import create_jsm_client
from ..server_cli import main_from_factory
from ..settings import JsmSettings


def build_server(settings: JsmSettings, *, json_response: bool = False) -> FastMCP:
    client = create_jsm_client(settings)
    mcp = FastMCP("atlassian-jsm", json_response=json_response)

    @mcp.tool()
    def list_service_desks() -> dict[str, Any]:
        return {"values": client.get_service_desks()}

    @mcp.tool()
    def list_my_requests() -> dict[str, Any]:
        return {"values": client.get_my_customer_requests()}

    @mcp.tool()
    def get_request(
        issue_id_or_key: Annotated[str, Field(description="Customer request issue key or ID.")],
    ) -> dict[str, Any]:
        return client.get_customer_request(issue_id_or_key)

    @mcp.tool()
    def create_request(
        service_desk_id: Annotated[str, Field(description="Service desk ID.")],
        request_type_id: Annotated[str, Field(description="Request type ID.")],
        summary: Annotated[str | None, Field(description="Summary value for the request when supported.")] = None,
        description: Annotated[str | None, Field(description="Description value for the request when supported.")] = None,
        field_values: Annotated[
            dict[str, Any] | None, Field(description="Additional request field values.")
        ] = None,
        raise_on_behalf_of: Annotated[
            str | None, Field(description="Optional account or user identifier to raise on behalf of.")
        ] = None,
        request_participants: Annotated[
            list[str] | None, Field(description="Optional list of participants.")
        ] = None,
    ) -> dict[str, Any]:
        values = dict(field_values or {})
        if summary is not None:
            values.setdefault("summary", summary)
        if description is not None:
            values.setdefault("description", description)
        return client.create_customer_request(
            service_desk_id=service_desk_id,
            request_type_id=request_type_id,
            values_dict=values,
            raise_on_behalf_of=raise_on_behalf_of,
            request_participants=request_participants,
        )

    @mcp.tool()
    def list_request_transitions(
        issue_id_or_key: Annotated[str, Field(description="Customer request issue key or ID.")],
    ) -> dict[str, Any]:
        return client.get_customer_transitions(issue_id_or_key)

    @mcp.tool()
    def transition_request(
        issue_id_or_key: Annotated[str, Field(description="Customer request issue key or ID.")],
        transition_id: Annotated[str, Field(description="Transition ID to execute.")],
        comment: Annotated[str | None, Field(description="Optional comment to attach with the transition.")] = None,
    ) -> dict[str, Any]:
        return client.perform_transition(issue_id_or_key, transition_id, comment=comment)

    @mcp.tool()
    def add_request_comment(
        issue_id_or_key: Annotated[str, Field(description="Customer request issue key or ID.")],
        body: Annotated[str, Field(description="Comment body.")],
        public: Annotated[bool, Field(description="Whether the comment should be public to the customer.")] = True,
    ) -> dict[str, Any]:
        return client.create_request_comment(issue_id_or_key, body=body, public=public)

    @mcp.tool()
    def list_queues(
        service_desk_id: Annotated[str, Field(description="Service desk ID.")],
        include_count: Annotated[bool, Field(description="Include issue counts in queue results.")] = False,
        start: Annotated[int, Field(description="Pagination start offset.", ge=0)] = 0,
        limit: Annotated[int, Field(description="Maximum number of queues to return.", ge=1, le=200)] = 50,
    ) -> dict[str, Any]:
        return client.get_queues(service_desk_id, include_count=include_count, start=start, limit=limit)

    @mcp.tool()
    def list_queue_issues(
        service_desk_id: Annotated[str, Field(description="Service desk ID.")],
        queue_id: Annotated[str, Field(description="Queue ID.")],
        start: Annotated[int, Field(description="Pagination start offset.", ge=0)] = 0,
        limit: Annotated[int, Field(description="Maximum number of issues to return.", ge=1, le=200)] = 50,
    ) -> dict[str, Any]:
        return client.get_issues_in_queue(service_desk_id, queue_id, start=start, limit=limit)

    return mcp


def main() -> int:
    return main_from_factory(
        "atlassian-mcp-jsm",
        lambda args: build_server(JsmSettings(), json_response=args.json_response),
    )
