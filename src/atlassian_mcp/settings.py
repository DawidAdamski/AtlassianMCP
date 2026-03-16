from __future__ import annotations

from typing import Any

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AtlassianSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_nested_delimiter="__",
        extra="ignore",
    )

    url: str
    username: str | None = None
    password: SecretStr | None = None
    token: SecretStr | None = None
    cloud: bool = False
    verify_ssl: bool = True
    timeout: int = 75

    @model_validator(mode="after")
    def validate_auth(self) -> "AtlassianSettings":
        if self.token is None and not (self.username and self.password):
            raise ValueError("Set TOKEN or USERNAME + PASSWORD for Atlassian authentication.")
        return self

    def client_kwargs(self) -> dict[str, Any]:
        kwargs: dict[str, Any] = {
            "timeout": self.timeout,
            "verify_ssl": self.verify_ssl,
            "advanced_mode": True,
            "backoff_and_retry": True,
            "cloud": self.cloud,
        }
        if self.token is not None:
            kwargs["token"] = self.token.get_secret_value()
        else:
            kwargs["username"] = self.username
            kwargs["password"] = self.password.get_secret_value() if self.password is not None else None
        return kwargs


class JiraSettings(AtlassianSettings):
    model_config = SettingsConfigDict(
        env_prefix="ATLASSIAN_JIRA_",
        env_file=".env",
        env_nested_delimiter="__",
        extra="ignore",
    )

    @classmethod
    def example(cls) -> "JiraSettings":
        return cls.model_construct(
            url="https://example.atlassian.net",
            username="jira@example.com",
            token=SecretStr("example-token"),
            cloud=True,
            verify_ssl=True,
            timeout=75,
        )


class JsmSettings(AtlassianSettings):
    model_config = SettingsConfigDict(
        env_prefix="ATLASSIAN_JSM_",
        env_file=".env",
        env_nested_delimiter="__",
        extra="ignore",
    )

    @classmethod
    def example(cls) -> "JsmSettings":
        return cls.model_construct(
            url="https://example.atlassian.net",
            username="jsm@example.com",
            token=SecretStr("example-token"),
            cloud=True,
            verify_ssl=True,
            timeout=75,
        )


class ConfluenceSettings(AtlassianSettings):
    model_config = SettingsConfigDict(
        env_prefix="ATLASSIAN_CONFLUENCE_",
        env_file=".env",
        env_nested_delimiter="__",
        extra="ignore",
    )

    @classmethod
    def example(cls) -> "ConfluenceSettings":
        return cls.model_construct(
            url="https://example.atlassian.net/wiki",
            username="confluence@example.com",
            token=SecretStr("example-token"),
            cloud=True,
            verify_ssl=True,
            timeout=75,
        )


class BitbucketSettings(AtlassianSettings):
    model_config = SettingsConfigDict(
        env_prefix="ATLASSIAN_BITBUCKET_",
        env_file=".env",
        env_nested_delimiter="__",
        extra="ignore",
    )

    @classmethod
    def example(cls) -> "BitbucketSettings":
        return cls.model_construct(
            url="https://api.bitbucket.org",
            username="bitbucket@example.com",
            token=SecretStr("example-token"),
            cloud=True,
            verify_ssl=True,
            timeout=75,
        )
