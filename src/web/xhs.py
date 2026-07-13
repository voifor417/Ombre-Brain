"""
web/xhs -- XHS link parsing routes
POST /api/xhs-card   : parse XHS link -> structured note data
GET  /api/parse-xhs  : same, url passed as ?url= query param (WebFetch compatible)
POST /api/xhs-images : batch fetch images -> base64
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

from . import _shared as sh

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
        raw = re.sub(r"\bundefined\b", "null", raw)
        return json.loads(raw)
    except Exception:
        return None


def _parse_note(state: dict[str, Any]) -> dict[str, Any] | None:
    try:
        note = state["noteData"]["data"]["noteData"]

        title = note.get("title", "")
        desc = note.get("desc", "")
        user = note.get("user", {})
        author = user.get("nickName") or user.get("nickname", "")

        images = []
        for img in note.get("imageList", []):
            url = img.get("url") or ""
            if not url:
                info = img.get("infoList", [])
                url = info[0].get("url", "") if info else ""
            if url:
                images.append(url)

        interact = note.get("interactInfo", {})
        liked = interact.get("likedCount", "")
        commented = interact.get("commentCount", "")
        collected = interact.get("collectedCount", "")

        comments_raw = state["noteData"]["data"].get("commentData", {}).get("comments", [])
        comments = []
        for c in comments_raw[:10]:
            u = c.get("user", {})
            comments.append({
                "user": u.get("nickName") or u.get("nickname", ""),
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
        return {"ok": False, "error": "unable to extract page data"}

    note = _parse_note(state)
    if note is None:
        return {"ok": False, "error": "failed to parse note structure"}

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

    @mcp.custom_route("/api/parse-xhs", methods=["GET"])
    async def parse_xhs(request: Request) -> JSONResponse:
        err = sh._require_auth(request)
        if err:
            return err
        url = (request.query_params.get("url") or "").strip()
        if not url:
            return JSONResponse({"ok": False, "error": "missing url"}, status_code=400)
        result = await _fetch_xhs_note(url)
        return JSONResponse(result)

    @mcp.custom_route("/api/xhs-card", methods=["POST"])
    async def xhs_card(request: Request) -> JSONResponse:
        try:
            body = await request.json()
        except Exception:
            return JSONResponse({"ok": False, "error": "request body must be JSON"}, status_code=400)

        url = (body.get("url") or "").strip()
        if not url:
            return JSONResponse({"ok": False, "error": "missing url field"}, status_code=400)

        result = await _fetch_xhs_note(url)
        return JSONResponse(result)

    @mcp.custom_route("/api/xhs-images", methods=["POST"])
    async def xhs_images(request: Request) -> JSONResponse:
        try:
            body = await request.json()
        except Exception:
            return JSONResponse({"ok": False, "error": "request body must be JSON"}, status_code=400)

        urls = body.get("urls") or []
        if not urls:
            return JSONResponse({"ok": False, "error": "missing urls field"}, status_code=400)

        img_headers = {
            **_XHS_HEADERS,
            "Referer": "https://www.xiaohongshu.com/",
        }
        async with httpx.AsyncClient(headers=img_headers, follow_redirects=True, timeout=20) as client:
            tasks = [_fetch_image_b64(client, u) for u in urls]
            images = await asyncio.gather(*tasks)

        return JSONResponse({"ok": True, "images": list(images)})
