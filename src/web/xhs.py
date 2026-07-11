"""
web/xhs — 小红书链接解析路由
POST /api/xhs-card   : 解析 XHS 链接 → 笔记结构化数据
POST /api/xhs-images : 批量拉取图片 → base64
"""

from __future__ import annotations

import asyncio
import base64
import json
import re
from typing import Any

import httpx
from starlette.requests import Request
from starlette.responses import JSONResponse

_MOBILE_UA = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
)

_XHS_HEADERS = {
    "User-Agent": _MOBILE_UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Referer": "https://www.xiaohongshu.com/",
}


def _extract_initial_state(html: str) -> dict[str, Any] | None:
    m = re.search(r"window\.__INITIAL_STATE__\s*=\s*(\{.*?\})(?:\s*</script>|;)", html, re.DOTALL)
    if not m:
        return None
    try:
        raw = m.group(1)
        # XHS sometimes uses undefined; replace with null
        raw = re.sub(r"\bundefined\b", "null", raw)
        return json.loads(raw)
    except Exception:
        return None


def _parse_note(state: dict[str, Any]) -> dict[str, Any] | None:
    try:
        note_detail = (
            state.get("note", {})
            .get("noteDetailMap", {})
        )
        if not note_detail:
            return None
        note_id = next(iter(note_detail))
        note = note_detail[note_id].get("note", {})

        title = note.get("title", "")
        desc = note.get("desc", "")
        author = note.get("user", {}).get("nickname", "")

        image_list = note.get("imageList", [])
        images = []
        for img in image_list:
            url = (
                img.get("urlDefault")
                or img.get("url")
                or (img.get("infoList") or [{}])[0].get("url", "")
            )
            if url:
                images.append(url)

        interact = note.get("interactInfo", {})
        liked = interact.get("likedCount", "")
        commented = interact.get("commentCount", "")
        collected = interact.get("collectedCount", "")

        comments_raw = state.get("comment", {}).get("comments", [])
        comments = []
        for c in comments_raw[:10]:
            comments.append({
                "user": c.get("userInfo", {}).get("nickname", ""),
                "content": c.get("content", ""),
                "ipLocation": c.get("ipLocation", ""),
            })

        return {
            "title": title,
            "author": author,
            "desc": desc,
            "images": images,
            "imageCount": len(images),
            "likedCount": liked,
            "commentCount": commented,
            "collectedCount": collected,
            "comments": comments,
        }
    except Exception:
        return None


async def _fetch_xhs_note(url: str) -> dict[str, Any]:
    # Handle short links (xhslink.com) → follow redirect
    async with httpx.AsyncClient(
        headers=_XHS_HEADERS,
        follow_redirects=True,
        timeout=15,
    ) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        html = resp.text

    state = _extract_initial_state(html)
    if state is None:
        return {"ok": False, "error": "无法提取页面数据，可能需要登录或链接已失效"}

    note = _parse_note(state)
    if note is None:
        return {"ok": False, "error": "解析笔记结构失败"}

    return {"ok": True, "note": note}


async def _fetch_image_b64(client: httpx.AsyncClient, img_url: str) -> dict[str, Any]:
    try:
        resp = await client.get(img_url)
        resp.raise_for_status()
        mime = resp.headers.get("content-type", "image/jpeg").split(";")[0].strip()
        b64 = base64.b64encode(resp.content).decode()
        return {"url": img_url, "base64": b64, "mime": mime}
    except Exception as e:
        return {"url": img_url, "base64": None, "mime": None, "error": str(e)}


def register(mcp) -> None:

    @mcp.custom_route("/api/xhs-card", methods=["POST"])
    async def xhs_card(request: Request) -> JSONResponse:
        try:
            body = await request.json()
        except Exception:
            return JSONResponse({"ok": False, "error": "请求体必须是 JSON"}, status_code=400)

        url = (body.get("url") or "").strip()
        if not url:
            return JSONResponse({"ok": False, "error": "缺少 url 字段"}, status_code=400)

        result = await _fetch_xhs_note(url)
        return JSONResponse(result)

    @mcp.custom_route("/api/xhs-images", methods=["POST"])
    async def xhs_images(request: Request) -> JSONResponse:
        try:
            body = await request.json()
        except Exception:
            return JSONResponse({"ok": False, "error": "请求体必须是 JSON"}, status_code=400)

        urls = body.get("urls") or []
        if not urls:
            return JSONResponse({"ok": False, "error": "缺少 urls 字段"}, status_code=400)

        img_headers = {
            **_XHS_HEADERS,
            "Referer": "https://www.xiaohongshu.com/",
        }
        async with httpx.AsyncClient(headers=img_headers, follow_redirects=True, timeout=20) as client:
            tasks = [_fetch_image_b64(client, u) for u in urls]
            images = await asyncio.gather(*tasks)

        return JSONResponse({"ok": True, "images": list(images)})
