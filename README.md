# Atlassian MCP

Focused MCP servers for Atlassian products built with Python and `uv`.

## Scope

This repository exposes multiple small MCP servers instead of one oversized server:

- `atlassian-mcp-jira`
- `atlassian-mcp-jsm`
- `atlassian-mcp-confluence`
- `atlassian-mcp-bitbucket`

The goal is to keep each server in the `6-10` tool range so clients can enable only the product surface they need.

## Install

```powershell
uv venv
uv pip install -e .
```

## Run

Default transport is `stdio`.

```powershell
uv run atlassian-mcp-jira
uv run atlassian-mcp-jsm
uv run atlassian-mcp-confluence
uv run atlassian-mcp-bitbucket
```

To expose HTTP transport instead:

```powershell
uv run atlassian-mcp-jira --transport streamable-http --port 8000
```

## Configuration

Each server uses product-specific environment variables:

- Jira: `ATLASSIAN_JIRA_*`
- JSM: `ATLASSIAN_JSM_*`
- Confluence: `ATLASSIAN_CONFLUENCE_*`
- Bitbucket: `ATLASSIAN_BITBUCKET_*`

Shared variable names per product:

- `URL`
- `USERNAME`
- `PASSWORD`
- `TOKEN`
- `CLOUD`
- `VERIFY_SSL`
- `TIMEOUT`

Authentication rules:

- Use `TOKEN` for Atlassian Cloud whenever possible.
- Use `USERNAME` + `PASSWORD` for Data Center / Server where needed.
- `TOKEN` or `USERNAME` + `PASSWORD` must be set.

Example:

```powershell
$env:ATLASSIAN_JIRA_URL="https://your-site.atlassian.net"
$env:ATLASSIAN_JIRA_USERNAME="you@example.com"
$env:ATLASSIAN_JIRA_TOKEN="your-api-token"
$env:ATLASSIAN_JIRA_CLOUD="true"
uv run atlassian-mcp-jira
```

## Documentation

Tool documentation is generated from MCP tool schemas:

```powershell
uv run atlassian-mcp-export-docs
```

Generated files are written to `docs/generated/`.

## Docker

Build locally:

```powershell
docker build -t atlassian-mcp .
```

Run the Jira server over streamable HTTP:

```powershell
docker run --rm -p 8000:8000 `
  -e MCP_SERVER=jira `
  -e MCP_TRANSPORT=streamable-http `
  -e MCP_JSON_RESPONSE=true `
  -e ATLASSIAN_JIRA_URL="https://your-site.atlassian.net" `
  -e ATLASSIAN_JIRA_USERNAME="you@example.com" `
  -e ATLASSIAN_JIRA_TOKEN="your-api-token" `
  -e ATLASSIAN_JIRA_CLOUD=true `
  atlassian-mcp
```

Supported `MCP_SERVER` values:

- `jira`
- `jsm`
- `confluence`
- `bitbucket`

The GitHub Actions workflow in `.github/workflows/docker.yml` builds the image on pull requests and pushes it to GHCR on `main` and version tags.
