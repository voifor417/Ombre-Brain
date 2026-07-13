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


def set_cmd(cmd: str) -> str:
    global _current_cmd
    _current_cmd = cmd
    return cmd


def get_cmd() -> str:
    return _current_cmd


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
