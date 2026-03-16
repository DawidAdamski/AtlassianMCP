#!/bin/sh
set -eu

case "${MCP_SERVER}" in
  jira)
    CMD="atlassian-mcp-jira"
    ;;
  jsm)
    CMD="atlassian-mcp-jsm"
    ;;
  confluence)
    CMD="atlassian-mcp-confluence"
    ;;
  bitbucket)
    CMD="atlassian-mcp-bitbucket"
    ;;
  *)
    echo "Unsupported MCP_SERVER: ${MCP_SERVER}" >&2
    exit 1
    ;;
esac

ARGS="--transport ${MCP_TRANSPORT}"

if [ "${MCP_TRANSPORT}" != "stdio" ]; then
  ARGS="${ARGS} --host ${MCP_HOST} --port ${MCP_PORT}"
fi

if [ "${MCP_JSON_RESPONSE}" = "true" ]; then
  ARGS="${ARGS} --json-response"
fi

if [ "${MCP_STATELESS_HTTP}" = "true" ]; then
  ARGS="${ARGS} --stateless-http"
fi

if [ -n "${MCP_EXTRA_ARGS}" ]; then
  ARGS="${ARGS} ${MCP_EXTRA_ARGS}"
fi

exec sh -c "${CMD} ${ARGS}"

