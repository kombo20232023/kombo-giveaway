"""Instagram Graph API（透過 Facebook 登入）：找貼文、抓主留言。"""
import re

import requests

GRAPH = "https://graph.facebook.com"


class IGError(Exception):
    """給使用者看的錯誤訊息。"""


def shortcode_from_url(url: str):
    """從 IG 貼文 / Reels 連結取出 shortcode，例如 /p/DewQRDrqKcS/ → DewQRDrqKcS。"""
    m = re.search(r"instagram\.com/(?:[^/?#]+/)?(?:p|reel|reels|tv)/([A-Za-z0-9_-]+)", url or "")
    return m.group(1) if m else None


def _friendly(err: dict) -> str:
    code = err.get("code")
    msg = err.get("message", "")
    if code == 190:
        return "Meta 權杖過期或無效，請到 Streamlit Secrets 更新 FB_PAGE_TOKEN。"
    if code in (10, 200) or (isinstance(code, int) and 200 <= code < 300):
        return ("權杖權限不足，請確認有勾選 instagram_basic、instagram_manage_comments、"
                "pages_show_list、pages_read_engagement。")
    if code in (4, 17, 32, 613):
        return "Meta API 呼叫太頻繁，請等幾分鐘再試。"
    return f"Meta 回傳錯誤：{msg}（代碼 {code}）"


class IGClient:
    def __init__(self, token: str, version: str = "v23.0", ig_user_id: str | None = None, session=None):
        self.token = token
        self.version = version
        self.ig_user_id = ig_user_id
        self.http = session or requests.Session()

    def _get(self, path_or_url: str, params: dict | None = None) -> dict:
        if path_or_url.startswith("http"):
            url, p = path_or_url, None  # paging.next 已經帶好參數和權杖
        else:
            url = f"{GRAPH}/{self.version}/{path_or_url}"
            p = dict(params or {})
            p["access_token"] = self.token
        try:
            r = self.http.get(url, params=p, timeout=20)
            data = r.json()
        except requests.RequestException:
            raise IGError("連不到 Meta，請稍後再試。")
        except ValueError:
            raise IGError("Meta 回傳的資料看不懂，請稍後再試。")
        if isinstance(data, dict) and "error" in data:
            raise IGError(_friendly(data["error"]))
        return data

    def account(self) -> dict:
        """回傳 {'id': IG 商業帳號 id, 'username': 帳號名稱}。"""
        if self.ig_user_id:
            d = self._get(self.ig_user_id, {"fields": "id,username"})
            return {"id": d["id"], "username": d.get("username", "")}
        # 粉專權杖：/me 就是粉專
        me = self._get("me", {"fields": "id,name,instagram_business_account{id,username}"})
        iba = me.get("instagram_business_account")
        if iba:
            self.ig_user_id = iba["id"]
            return {"id": iba["id"], "username": iba.get("username", "")}
        # 使用者權杖：從管理的粉專裡找有連 IG 的
        pages = self._get("me/accounts", {"fields": "name,instagram_business_account{id,username}"})
        for pg in pages.get("data", []):
            iba = pg.get("instagram_business_account")
            if iba:
                self.ig_user_id = iba["id"]
                return {"id": iba["id"], "username": iba.get("username", "")}
        raise IGError("找不到連結到粉專的 IG 商業帳號，請確認 IG 已切換成商業帳號並連結 KOMBO 粉專。")

    def find_media(self, shortcode: str, max_pages: int = 40) -> dict:
        if not self.ig_user_id:
            self.account()
        nxt = None
        for _ in range(max_pages):
            d = self._get(nxt) if nxt else self._get(
                f"{self.ig_user_id}/media",
                {"fields": "id,shortcode,permalink,caption,timestamp,comments_count", "limit": 50})
            for m in d.get("data", []):
                if m.get("shortcode") == shortcode or f"/{shortcode}" in (m.get("permalink") or ""):
                    return m
            nxt = (d.get("paging") or {}).get("next")
            if not nxt:
                break
        raise IGError("在 KOMBO 的 IG 貼文裡找不到這個連結，請確認是自己帳號的貼文。")

    def comments(self, media_id: str, cap: int = 20000) -> list[dict]:
        """主留言和底下的回覆都抓。每筆有 kind = main / reply。"""
        def row(c, kind, parent=None):
            return {"id": c.get("id"), "user": c.get("username") or "（未知帳號）", "text": c.get("text") or "",
                    "time": c.get("timestamp") or "", "kind": kind, "parent": parent}

        out, nxt = [], None
        while True:
            d = self._get(nxt) if nxt else self._get(
                f"{media_id}/comments",
                {"fields": "id,text,username,timestamp,replies.limit(50){id,text,username,timestamp}", "limit": 50})
            for c in d.get("data", []):
                out.append(row(c, "main"))
                rep = c.get("replies") or {}
                while True:
                    out.extend(row(r, "reply", c.get("id")) for r in rep.get("data", []))
                    rn = (rep.get("paging") or {}).get("next")
                    if not rn or len(out) >= cap:
                        break
                    rep = self._get(rn)
            nxt = (d.get("paging") or {}).get("next")
            if not nxt or len(out) >= cap:
                return out
