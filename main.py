import hashlib
import os

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response

app = FastAPI()

EMAIL = "24f2005862@ds.study.iitm.ac.in"
PROTOCOL_VERSION = "2025-03-26"

TOOLS = [
    {
        "name": "solve_challenge",
        "description": "Solve the current exam challenge from HTTP request headers.",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    }
]


def rpc_result(request_id, result):
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "result": result
    }


def rpc_error(request_id, code, message):
    return JSONResponse({
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {"code": code, "message": message}
    })


@app.get("/")
async def health():
    return {"status": "ok", "service": "live-mcp"}


@app.post("/mcp")
async def mcp(request: Request):
    body = await request.json()
    method = body.get("method")
    request_id = body.get("id")
    params = body.get("params") or {}

    # MCP notifications do not receive a JSON-RPC response.
    if method == "notifications/initialized":
        return Response(status_code=202)

    if method == "initialize":
        requested_version = params.get(
            "protocolVersion", PROTOCOL_VERSION
        )
        return JSONResponse(
            rpc_result(request_id, {
                "protocolVersion": requested_version,
                "capabilities": {"tools": {}},
                "serverInfo": {
                    "name": "live-challenge-mcp",
                    "version": "1.0.0"
                }
            }),
            headers={"MCP-Protocol-Version": requested_version}
        )

    if method == "ping":
        return JSONResponse(rpc_result(request_id, {}))

    if method == "tools/list":
        return JSONResponse(rpc_result(request_id, {"tools": TOOLS}))

    if method == "tools/call":
        tool_name = params.get("name")

        if tool_name != "solve_challenge":
            return rpc_error(request_id, -32602, "Unknown tool")

        # Read the fresh challenge from THIS HTTP request's headers.
        challenge = request.headers.get("x-exam-challenge")

        if challenge is None:
            return rpc_error(
                request_id, -32602, "Missing X-Exam-Challenge header"
            )

        if len(challenge) != 32 or any(
            c not in "0123456789abcdef" for c in challenge
        ):
            return rpc_error(
                request_id, -32602, "Invalid challenge header"
            )

        answer = hashlib.sha256(
            f"{challenge}:{EMAIL.strip().lower()}".encode("utf-8")
        ).hexdigest()[:16]

        return JSONResponse(
            rpc_result(request_id, {
                "content": [{"type": "text", "text": answer}],
                "isError": False
            })
        )

    if request_id is None:
        return Response(status_code=202)

    return rpc_error(request_id, -32601, "Method not found")
