from __future__ import annotations

from atlassian import Bitbucket, Confluence, Jira, ServiceDesk
from atlassian.bitbucket.cloud import Cloud as BitbucketCloud

from .settings import BitbucketSettings, ConfluenceSettings, JiraSettings, JsmSettings


def create_jira_client(settings: JiraSettings) -> Jira:
    return Jira(url=settings.url, **settings.client_kwargs())


def create_jsm_client(settings: JsmSettings) -> ServiceDesk:
    return ServiceDesk(url=settings.url, **settings.client_kwargs())


def create_confluence_client(settings: ConfluenceSettings) -> Confluence:
    return Confluence(url=settings.url, **settings.client_kwargs())


def create_bitbucket_client(settings: BitbucketSettings) -> Bitbucket:
    return Bitbucket(url=settings.url, **settings.client_kwargs())


def create_bitbucket_cloud_client(settings: BitbucketSettings) -> BitbucketCloud:
    return BitbucketCloud(url=settings.url, **settings.client_kwargs())
