from __future__ import annotations

import time

from starlette.requests import Request
from starlette.responses import JSONResponse

from . import _shared as sh

_TOY_TOKEN = "xiaokeechoes"
# 死人开关：非stop指令超过此秒数未刷新，GET一律返回stop。
# 防止控制端窗口中断后设备无人喊停一直运行（2026-07-18真实事故）。
_CMD_TTL_SECONDS = 600
_current_cmd: str = ""
_cmd_set_at: float = 0.0


def _check_token(request: Request) -> bool:
    header = request.headers.get("x-toy-token", "")
    query = request.query_params.get("token", "")
    return header == _TOY_TOKEN or query == _TOY_TOKEN


def set_cmd(cmd: str) -> str:
    global _current_cmd, _cmd_set_at
    _current_cmd = cmd
    _cmd_set_at = time.monotonic()
    return cmd


def get_cmd() -> str:
    global _current_cmd
    if _current_cmd and _current_cmd != "stop":
        if time.monotonic() - _cmd_set_at > _CMD_TTL_SECONDS:
            _current_cmd = "stop"
    return _current_cmd


def register(mcp) -> None:

    @mcp.custom_route("/api/toy/command", methods=["GET"])
    async def toy_command_get(request: Request) -> JSONResponse:
        if not _check_token(request):
            return JSONResponse({"error": "unauthorized"}, status_code=401)
        return JSONResponse({"cmd": get_cmd()})

    @mcp.custom_route("/api/toy/command", methods=["POST"])
    async def toy_command_post(request: Request) -> JSONResponse:
        if not _check_token(request):
            return JSONResponse({"error": "unauthorized"}, status_code=401)
        try:
            body = await request.json()
        except Exception:
            return JSONResponse({"error": "invalid json"}, status_code=400)
        cmd = str(body.get("cmd", "") or "")
        set_cmd(cmd)
        return JSONResponse({"ok": True, "cmd": cmd})
