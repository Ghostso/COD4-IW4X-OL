#!/usr/bin/env python3
"""Call a local idalib-mcp Streamable HTTP tool from the command line."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.request


def read_stdin_arguments() -> str:
    binary = getattr(sys.stdin, "buffer", None)
    if binary is None:
        return sys.stdin.read().removeprefix("\ufeff")
    data = binary.read()
    if data.startswith((b"\xff\xfe", b"\xfe\xff")):
        return data.decode("utf-16")
    return data.decode("utf-8-sig")


def post(url: str, payload: dict, session_id: str | None = None) -> tuple[str | None, str]:
    headers = {
        "Accept": "application/json, text/event-stream",
        "Content-Type": "application/json",
    }
    if session_id:
        headers["Mcp-Session-Id"] = session_id
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        return response.headers.get("Mcp-Session-Id"), response.read().decode("utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--list-tools",
        action="store_true",
        help="List tools exposed by the configured MCP server.",
    )
    parser.add_argument("tool", nargs="?", help="MCP tool name")
    parser.add_argument(
        "arguments",
        nargs="?",
        default="{}",
        help="JSON object, or '-' to read JSON from stdin (recommended in PowerShell)",
    )
    parser.add_argument(
        "--batch",
        action="store_true",
        help="Call one tool for each JSON object in an input array using one MCP session",
    )
    parser.add_argument("--url", default="http://127.0.0.1:8745/mcp")
    args = parser.parse_args()

    if not args.list_tools and not args.tool:
        parser.error("tool is required unless --list-tools is used")

    if args.list_tools and args.batch:
        parser.error("--batch cannot be combined with --list-tools")

    raw_arguments = read_stdin_arguments() if args.arguments == "-" else args.arguments
    tool_arguments = json.loads(raw_arguments)
    if args.batch:
        if not isinstance(tool_arguments, list) or not all(
            isinstance(item, dict) for item in tool_arguments
        ):
            parser.error("batch arguments must decode to an array of JSON objects")
    elif not isinstance(tool_arguments, dict):
        parser.error("arguments must decode to a JSON object")

    session_id, _ = post(
        args.url,
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": "idalib-mcp-cli", "version": "1"},
            },
        },
    )
    post(args.url, {"jsonrpc": "2.0", "method": "notifications/initialized"}, session_id)
    if args.list_tools:
        _, body = post(
            args.url,
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
            session_id,
        )
    elif args.batch:
        batch_results = []
        for index, item_arguments in enumerate(tool_arguments):
            next_session_id, body = post(
                args.url,
                {
                    "jsonrpc": "2.0",
                    "id": index + 2,
                    "method": "tools/call",
                    "params": {"name": args.tool, "arguments": item_arguments},
                },
                session_id,
            )
            if next_session_id:
                session_id = next_session_id
            response = json.loads(body)
            if "error" in response:
                batch_results.append(
                    {"ok": False, "index": index, "error": response["error"]}
                )
                continue

            result = response.get("result", {})
            structured = result.get("structuredContent")
            if structured is not None:
                output = structured
            else:
                output = "\n".join(
                    item.get("text", "")
                    for item in result.get("content", [])
                    if item.get("type") == "text"
                )
            batch_results.append({"ok": True, "index": index, "result": output})

        print(json.dumps({"results": batch_results}, ensure_ascii=False, indent=2))
        return 0 if all(item["ok"] for item in batch_results) else 1
    else:
        _, body = post(
            args.url,
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {"name": args.tool, "arguments": tool_arguments},
            },
            session_id,
        )
    response = json.loads(body)
    if "error" in response:
        print(json.dumps(response["error"], ensure_ascii=False, indent=2))
        return 1

    result = response.get("result", {})
    if args.list_tools:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    structured = result.get("structuredContent")
    if structured is not None:
        print(json.dumps(structured, ensure_ascii=False, indent=2))
        return 0

    for item in result.get("content", []):
        if item.get("type") == "text":
            print(item.get("text", ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
