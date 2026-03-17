from __future__ import annotations

from typing import Annotated, Any

from pydantic import Field

from mcp.server.fastmcp import FastMCP

from ..clients import create_bitbucket_client, create_bitbucket_cloud_client
from ..server_cli import main_from_factory
from ..settings import BitbucketSettings


def build_server(settings: BitbucketSettings) -> FastMCP:
    client = create_bitbucket_client(settings)
    cloud_client = create_bitbucket_cloud_client(settings) if settings.cloud else None

    mcp = FastMCP("atlassian-bitbucket")

    @mcp.tool()
    def list_repositories(
        scope: Annotated[
            str,
            Field(description="Workspace for Bitbucket Cloud or project key for Bitbucket Server/Data Center."),
        ],
        limit: Annotated[int, Field(description="Maximum number of repositories to return.", ge=1, le=200)] = 25,
        query: Annotated[str | None, Field(description="Optional query filter for Cloud.")] = None,
        role: Annotated[str | None, Field(description="Optional role filter for Cloud.")] = None,
    ) -> dict[str, Any]:
        if settings.cloud:
            values = cloud_client.get_repositories(scope, role=role, query=query)[:limit]
            return {"values": values}
        repos = []
        for repo in client.repo_list(scope, start=0, limit=limit):
            repos.append(repo)
            if len(repos) >= limit:
                break
        return {"values": repos}

    @mcp.tool()
    def get_repository(
        scope: Annotated[
            str,
            Field(description="Workspace for Bitbucket Cloud or project key for Bitbucket Server/Data Center."),
        ],
        repository_slug: Annotated[str, Field(description="Repository slug.")],
    ) -> dict[str, Any]:
        if settings.cloud:
            repo = cloud_client.repositories.get(scope, repository_slug)
            return repo.data
        return client.get_repo(scope, repository_slug)

    @mcp.tool()
    def list_branches(
        scope: Annotated[
            str,
            Field(description="Workspace for Bitbucket Cloud or project key for Bitbucket Server/Data Center."),
        ],
        repository_slug: Annotated[str, Field(description="Repository slug.")],
        filter_text: Annotated[str | None, Field(description="Optional branch filter.")] = None,
        limit: Annotated[int, Field(description="Maximum number of branches to return.", ge=1, le=200)] = 25,
    ) -> dict[str, Any]:
        if settings.cloud:
            repo = cloud_client.repositories.get(scope, repository_slug)
            values = [branch.data for branch in repo.branches.each(q=filter_text, pagelen=limit)]
            return {"values": values[:limit]}
        values = []
        for branch in client.get_branches(scope, repository_slug, filter=filter_text, limit=limit):
            values.append(branch)
            if len(values) >= limit:
                break
        return {"values": values}

    @mcp.tool()
    def list_pull_requests(
        scope: Annotated[
            str,
            Field(description="Workspace for Bitbucket Cloud or project key for Bitbucket Server/Data Center."),
        ],
        repository_slug: Annotated[str, Field(description="Repository slug.")],
        state: Annotated[str | None, Field(description="PR state filter where supported.")] = "OPEN",
        limit: Annotated[int, Field(description="Maximum number of pull requests to return.", ge=1, le=200)] = 25,
    ) -> dict[str, Any]:
        if settings.cloud:
            repo = cloud_client.repositories.get(scope, repository_slug)
            query = None if state is None else f'state="{state.lower()}"'
            values = [pr.data for pr in repo.pullrequests.each(q=query)]
            return {"values": values[:limit]}
        values = []
        for pr in client.get_pull_requests(scope, repository_slug, state=state or "OPEN", limit=limit):
            values.append(pr)
            if len(values) >= limit:
                break
        return {"values": values}

    @mcp.tool()
    def get_pull_request(
        scope: Annotated[
            str,
            Field(description="Workspace for Bitbucket Cloud or project key for Bitbucket Server/Data Center."),
        ],
        repository_slug: Annotated[str, Field(description="Repository slug.")],
        pull_request_id: Annotated[int, Field(description="Pull request ID.", ge=1)],
    ) -> dict[str, Any]:
        if settings.cloud:
            repo = cloud_client.repositories.get(scope, repository_slug)
            return repo.pullrequests.get(pull_request_id).data
        return client.get_pull_request(scope, repository_slug, pull_request_id)

    @mcp.tool()
    def create_pull_request(
        scope: Annotated[
            str,
            Field(description="Workspace for Bitbucket Cloud or source project key for Bitbucket Server/Data Center."),
        ],
        repository_slug: Annotated[str, Field(description="Repository slug.")],
        title: Annotated[str, Field(description="Pull request title.")],
        source_branch: Annotated[str, Field(description="Source branch name or ref.")],
        destination_branch: Annotated[str, Field(description="Destination branch name or ref.")],
        description: Annotated[str | None, Field(description="Optional pull request description.")] = None,
        destination_scope: Annotated[
            str | None,
            Field(description="Optional destination project key for Server/Data Center. Defaults to scope."),
        ] = None,
    ) -> dict[str, Any]:
        if settings.cloud:
            repo = cloud_client.repositories.get(scope, repository_slug)
            return repo.pullrequests.create(
                title=title,
                source_branch=source_branch,
                destination_branch=destination_branch,
                description=description,
            ).data
        return client.open_pull_request(
            source_project=scope,
            source_repo=repository_slug,
            dest_project=destination_scope or scope,
            dest_repo=repository_slug,
            source_branch=source_branch,
            destination_branch=destination_branch,
            title=title,
            description=description or "",
        )

    @mcp.tool()
    def list_commits(
        scope: Annotated[
            str,
            Field(description="Workspace for Bitbucket Cloud or project key for Bitbucket Server/Data Center."),
        ],
        repository_slug: Annotated[str, Field(description="Repository slug.")],
        ref: Annotated[str | None, Field(description="Top ref or commit to query from.")] = None,
        limit: Annotated[int, Field(description="Maximum number of commits to return.", ge=1, le=200)] = 25,
    ) -> dict[str, Any]:
        if settings.cloud:
            repo = cloud_client.repositories.get(scope, repository_slug)
            values = [commit.data for commit in repo.commits.each(top=ref)]
            return {"values": values[:limit]}
        values = []
        for commit in client.get_commits(scope, repository_slug, hash_newest=ref, limit=limit):
            values.append(commit)
            if len(values) >= limit:
                break
        return {"values": values}

    @mcp.tool()
    def list_pipelines(
        workspace: Annotated[str, Field(description="Bitbucket Cloud workspace.")],
        repository_slug: Annotated[str, Field(description="Repository slug.")],
        limit: Annotated[int, Field(description="Maximum number of pipelines to return.", ge=1, le=100)] = 10,
    ) -> dict[str, Any]:
        if not settings.cloud:
            raise ValueError("Pipeline tools are only supported for Bitbucket Cloud.")
        return {"values": client.get_pipelines(workspace, repository_slug, number=limit)}

    @mcp.tool()
    def get_pipeline_steps(
        workspace: Annotated[str, Field(description="Bitbucket Cloud workspace.")],
        repository_slug: Annotated[str, Field(description="Repository slug.")],
        pipeline_uuid: Annotated[str, Field(description="Pipeline UUID including braces when required.")],
    ) -> dict[str, Any]:
        if not settings.cloud:
            raise ValueError("Pipeline tools are only supported for Bitbucket Cloud.")
        return {"values": client.get_pipeline_steps(workspace, repository_slug, pipeline_uuid)}

    return mcp


def main() -> int:
    return main_from_factory("atlassian-mcp-bitbucket", lambda: build_server(BitbucketSettings()))
