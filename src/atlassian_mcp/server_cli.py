from __future__ import annotations

import argparse
from collections.abc import Callable
from typing import Any

def build_arg_parser(server_name: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog=server_name)
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse", "streamable-http"],
        default="stdio",
        help="Transport to use for the MCP server.",
    )
    parser.add_argument("--host", default="127.0.0.1", help="HTTP host for SSE or Streamable HTTP transports.")
    parser.add_argument("--port", type=int, default=8000, help="HTTP port for SSE or Streamable HTTP transports.")
    parser.add_argument(
        "--json-response",
        action="store_true",
        help="Use JSON responses instead of SSE streams for streamable HTTP.",
    )
    parser.add_argument(
        "--stateless-http",
        action="store_true",
        help="Enable stateless HTTP mode for streamable HTTP transport.",
    )
    return parser


def run_server(server: Any, args: argparse.Namespace) -> int:
    if args.transport == "stdio":
        server.run(transport="stdio")
        return 0

    if args.transport == "sse":
        server.run(transport="sse", host=args.host, port=args.port)
        return 0

    server.run(
        transport="streamable-http",
        host=args.host,
        port=args.port,
        json_response=args.json_response,
        stateless_http=args.stateless_http,
    )
    return 0


def main_from_factory(
    server_name: str,
    factory: Callable[[argparse.Namespace], Any],
) -> int:
    parser = build_arg_parser(server_name)
    args = parser.parse_args()
    server = factory(args)
    return run_server(server, args)
