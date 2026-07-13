"""
web/toy -- BLE toy control relay
GET  /api/toy/command          : toy.html polls this (x-toy-token header)
POST /api/toy/command          : set command via JSON body (x-toy-token header)
GET  /api/toy/set?cmd=s3&token=xiaokeechoes : set command via query params (WebFetch-compatible)
GET  /toy                      : serve toy.html control page
"""

from __future__ import annotations

import os
from starlette.requests import Request
from starlette.responses import Response, JSONResponse

_TOY_TOKEN = "xiaokeechoes"
_current_cmd: str = ""


def _check_token(request: Request) -> bool:
    header = request.headers.get("x-toy-token", "")
    query = request.query_params.get("token", "")
    return header == _TOY_TOKEN or query == _TOY_TOKEN


def register(mcp) -> None:
    from . import _shared as sh

    @mcp.custom_route("/api/toy/command", methods=["GET"])
    async def toy_command_get(request: Request) -> JSONResponse:
        if not _check_token(request):
            return JSONResponse({"error": "unauthorized"}, status_code=401)
        return JSONResponse({"cmd": _current_cmd})

    @mcp.custom_route("/api/toy/command", methods=["POST"])
    async def toy_command_post(request: Request) -> JSONResponse:
        global _current_cmd
        if not _check_token(request):
            return JSONResponse({"error": "unauthorized"}, status_code=401)
        try:
            body = await request.json()
        except Exception:
            return JSONResponse({"error": "invalid json"}, status_code=400)
        cmd = str(body.get("cmd", "") or "")
        _current_cmd = cmd
        return JSONResponse({"ok": True, "cmd": _current_cmd})

    @mcp.custom_route("/api/toy/set", methods=["GET"])
    async def toy_set_get(request: Request) -> JSONResponse:
        global _current_cmd
        if not _check_token(request):
            return JSONResponse({"error": "unauthorized"}, status_code=401)
        cmd = str(request.query_params.get("cmd", "") or "")
        _current_cmd = cmd
        return JSONResponse({"ok": True, "cmd": _current_cmd})
