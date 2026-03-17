FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV MCP_SERVER=jira
ENV MCP_TRANSPORT=stdio
ENV MCP_HOST=0.0.0.0
ENV MCP_PORT=8000
ENV MCP_JSON_RESPONSE=false
ENV MCP_STATELESS_HTTP=false
ENV MCP_EXTRA_ARGS=

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml README.md ./
COPY src ./src
COPY python-sdk ./python-sdk
COPY atlassian-python-api ./atlassian-python-api
COPY docker-entrypoint.sh ./docker-entrypoint.sh

RUN chmod +x /app/docker-entrypoint.sh
RUN uv pip install --system ./python-sdk ./atlassian-python-api
RUN uv pip install --system .

ENTRYPOINT ["/app/docker-entrypoint.sh"]
