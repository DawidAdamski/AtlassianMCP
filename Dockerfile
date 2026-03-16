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

RUN pip install --no-cache-dir build uv

COPY pyproject.toml README.md ./
COPY src ./src
COPY docker-entrypoint.sh ./docker-entrypoint.sh

RUN chmod +x /app/docker-entrypoint.sh
RUN python -m build --wheel
RUN pip install --no-cache-dir dist/*.whl

ENTRYPOINT ["/app/docker-entrypoint.sh"]
