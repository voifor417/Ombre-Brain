"""
web/toy -- BLE toy control relay
GET  /api/toy/command          : toy.html polls this (x-toy-token header or ?token=)
POST /api/toy/command          : set command via JSON body (x-toy-token header or ?token=)
GET  /api/toy/set?cmd=s3&token=xiaokeechoes : set command via query params (WebFetch-compatible)
"""

from __future__ import annotations

from starlette.requests import Request
from starlette.responses import JSONResponse

from . import _shared as sh

_TOY_TOKEN = "xiaokeechoes"
_current_cmd: str = ""


def _check_token(request: Request) -> bool:
    header = request.headers.get("x-toy-token", "")
    query = request.query_params.get("token", "")
    return header == _TOY_TOKEN or query == _TOY_TOKEN


def register(mcp) -> None:

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
        err = sh._require_auth(request)
        if err:
            return err
        cmd = str(request.query_params.get("cmd", "") or "")
        _current_cmd = cmd
        return JSONResponse({"ok": True, "cmd": _current_cmd})
