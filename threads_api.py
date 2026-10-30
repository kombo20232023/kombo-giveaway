"""Threads API：找貼文、抓所有回覆、續期權杖。"""
import re

import requests

HOST = "https://graph.threads.com"
VERSION = "v1.0"


class ThreadsError(Exception):
    """給使用者看的錯誤訊息。"""


def shortcode_from_url(url: str):
    """threads.com/@kombo/post/DAbc123 → DAbc123（threads.net 也可以）。"""
    m = re.search(r"threads\.(?:net|com)/(?:@[^/]+/)?post/([A-Za-z0-9_-]+)", url or "")
    return m.group(1) if m else None


def _friendly(err: dict) -> str:
    code = err.get("code")
    if code == 190:
        return "Threads 權杖過期或無效，請重新產生權杖，更新 Streamlit Secrets 的 THREADS_TOKEN。"
    if code in (10, 200) or (isinstance(code, int) and 200 <= code < 300):
        return "Threads 權杖權限不足，請確認有 threads_basic 和 threads_read_replies。"
    if code in (4, 17, 32, 613):
        return "Threads API 呼叫太頻繁，請等幾分鐘再試。"
    return f"Threads 回傳錯誤：{err.get('message', '')}（代碼 {code}）"


class ThreadsClient:
    def __init__(self, token: str, session=None):
        self.token = token
        self.http = session or requests.Session()

    def _get(self, path_or_url: str, params: dict | None = None) -> dict:
        if path_or_url.startswith("http"):
            url, p = path_or_url, None
        else:
            url = f"{HOST}/{VERSION}/{path_or_url}" if not path_or_url.startswith("refresh") else f"{HOST}/{path_or_url}"
            p = dict(params or {})
            p["access_token"] = self.token
        try:
            r = self.http.get(url, params=p, timeout=20)
            data = r.json()
        except requests.RequestException:
            raise ThreadsError("連不到 Threads，請稍後再試。")
        except ValueError:
            raise ThreadsError("Threads 回傳的資料看不懂，請稍後再試。")
        if isinstance(data, dict) and "error" in data:
            raise ThreadsError(_friendly(data["error"]))
        return data

    def _pages(self, path: str, params: dict, cap: int = 20000):
        """依序拿每一頁，直到沒有下一頁。"""
        d = self._get(path, params)
        got = 0
        while True:
            items = d.get("data", [])
            yield from items
            got += len(items)
            paging = d.get("paging") or {}
            if paging.get("next"):
                d = self._get(paging["next"])
            elif (paging.get("cursors") or {}).get("after") and len(items) >= params.get("limit", 25):
                d = self._get(path, {**params, "after": paging["cursors"]["after"]})
            else:
                return
            if not items or got >= cap:
                return

    def me(self) -> dict:
        d = self._get("me", {"fields": "id,username"})
        return {"id": d.get("id"), "username": d.get("username", "")}

    def find_post(self, shortcode: str, max_items: int = 2000) -> dict:
        for i, m in enumerate(self._pages("me/threads", {"fields": "id,shortcode,permalink,text,timestamp", "limit": 100})):
            if m.get("shortcode") == shortcode or f"/{shortcode}" in (m.get("permalink") or ""):
                return m
            if i >= max_items:
                break
        raise ThreadsError("在 KOMBO 的 Threads 貼文裡找不到這個連結，請確認是自己帳號的貼文。")

    def replies(self, media_id: str) -> list[dict]:
        """這篇底下所有回覆（含回覆的回覆）。直接回覆貼文的算主留言。"""
        out = []
        for c in self._pages(f"{media_id}/conversation",
                             {"fields": "id,text,username,timestamp,replied_to", "reverse": "false", "limit": 100}):
            parent = (c.get("replied_to") or {}).get("id")
            out.append({"id": c.get("id"),
                        # 私人帳號 Threads 不給帳號名稱，用編號分開，避免被當成同一人
                        "user": c.get("username") or f"私人帳號{str(c.get('id', ''))[-4:]}",
                        "text": c.get("text") or "", "time": c.get("timestamp") or "",
                        "kind": "main" if (not parent or parent == media_id) else "reply",
                        "parent": parent, "private": not c.get("username")})
        return out

    def refresh_token(self) -> dict:
        """續期 60 天。權杖要產生超過 24 小時才能續。"""
        d = self._get("refresh_access_token", {"grant_type": "th_refresh_token"})
        if "access_token" not in d:
            raise ThreadsError("續期失敗，請稍後再試。")
        return {"token": d["access_token"], "days": round(int(d.get("expires_in", 0)) / 86400)}
