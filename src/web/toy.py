"""
toy.py — 玩具控制信号桥
GET  /api/toy/command  — Python 脚本轮询，取出并清除当前指令
POST /api/toy/command  — 写入新指令（由小克通过 WebFetch 调用）
"""
from starlette.requests import Request
from starlette.responses import JSONResponse

_pending_command: str = ""


def register(mcp) -> None:
    @mcp.custom_route("/api/toy/command", methods=["GET", "POST"])
    async def toy_command(request: Request) -> JSONResponse:
        global _pending_command
        if request.method == "POST":
            try:
                body = await request.json()
            except Exception:
                return JSONResponse({"ok": False, "error": "invalid json"}, status_code=400)
            _pending_command = body.get("cmd", "")
            return JSONResponse({"ok": True, "cmd": _pending_command})
        else:
            cmd = _pending_command
            _pending_command = ""
            return JSONResponse({"cmd": cmd})
