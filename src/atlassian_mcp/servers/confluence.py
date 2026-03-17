from __future__ import annotations

from typing import Annotated, Any

from pydantic import Field

from mcp.server.fastmcp import FastMCP

from ..clients import create_confluence_client
from ..server_cli import main_from_factory
from ..settings import ConfluenceSettings


def _storage_body(value: str) -> dict[str, Any]:
    return {"storage": {"value": value, "representation": "storage"}}


def build_server(settings: ConfluenceSettings, *, json_response: bool = False) -> FastMCP:
    client = create_confluence_client(settings)
    mcp = FastMCP("atlassian-confluence", json_response=json_response)

    @mcp.tool()
    def search_content(
        query: Annotated[str, Field(description="Confluence content query string.")],
        limit: Annotated[int, Field(description="Maximum number of results to return.", ge=1, le=200)] = 25,
    ) -> dict[str, Any]:
        return client.search_content(query, limit=limit)

    @mcp.tool()
    def get_content(
        content_id: Annotated[str, Field(description="Confluence content ID.")],
        expand: Annotated[str | None, Field(description="Optional expand string such as body.storage,version.")] = None,
    ) -> dict[str, Any]:
        kwargs: dict[str, Any] = {}
        if expand:
            kwargs["expand"] = expand
        return client.get_content(content_id, **kwargs)

    @mcp.tool()
    def list_space_pages(
        space_key: Annotated[str, Field(description="Confluence space key.")],
        limit: Annotated[int, Field(description="Maximum number of pages to return.", ge=1, le=200)] = 25,
    ) -> dict[str, Any]:
        pages = []
        for page in client.get_all_pages_from_space(space_key, limit=limit):
            pages.append(page)
            if len(pages) >= limit:
                break
        return {"values": pages}

    @mcp.tool()
    def list_spaces(
        limit: Annotated[int | None, Field(description="Optional limit when supported by the server.")] = 50,
    ) -> dict[str, Any]:
        return client.get_spaces(limit=limit)

    @mcp.tool()
    def get_space_content(
        space_id_or_key: Annotated[str, Field(description="Space key for Server/Data Center or space ID for Cloud.")],
        limit: Annotated[int | None, Field(description="Optional limit parameter.")] = 25,
    ) -> dict[str, Any]:
        return client.get_space_content(space_id_or_key, limit=limit)

    @mcp.tool()
    def create_page(
        space_key: Annotated[str, Field(description="Confluence space key.")],
        title: Annotated[str, Field(description="Page title.")],
        body: Annotated[str, Field(description="Body in Confluence storage format, usually HTML/XML-like markup.")],
        parent_id: Annotated[str | None, Field(description="Optional parent page ID.")] = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "type": "page",
            "title": title,
            "space": {"key": space_key},
            "body": _storage_body(body),
        }
        if parent_id:
            payload["ancestors"] = [{"id": parent_id}]
        return client.create_content(payload)

    @mcp.tool()
    def update_page(
        content_id: Annotated[str, Field(description="Page content ID to update.")],
        body: Annotated[str, Field(description="New body in Confluence storage format.")],
        title: Annotated[str | None, Field(description="Optional replacement title.")] = None,
        version_comment: Annotated[str | None, Field(description="Optional version comment.")] = None,
    ) -> dict[str, Any]:
        current = client.get_content(content_id, expand="version,space")
        payload: dict[str, Any] = {
            "id": str(content_id),
            "type": current.get("type", "page"),
            "title": title or current.get("title"),
            "body": _storage_body(body),
            "version": {"number": int(current["version"]["number"]) + 1},
        }
        if "space" in current and "key" in current["space"]:
            payload["space"] = {"key": current["space"]["key"]}
        if version_comment:
            payload["version"]["message"] = version_comment
        return client.update_content(content_id, payload)

    @mcp.tool()
    def add_page_comment(
        content_id: Annotated[str, Field(description="Page content ID to comment on.")],
        body: Annotated[str, Field(description="Comment body in Confluence storage format.")],
    ) -> dict[str, Any]:
        payload = {
            "type": "comment",
            "container": {"id": content_id, "type": "page"},
            "body": _storage_body(body),
        }
        return client.create_comment(content_id, payload)

    return mcp


def main() -> int:
    return main_from_factory(
        "atlassian-mcp-confluence",
        lambda args: build_server(ConfluenceSettings(), json_response=args.json_response),
    )
