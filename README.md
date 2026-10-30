# KOMBO 扭蛋抽獎

羽毛球造型扭蛋機抽獎 app（Streamlit）。支援 IG（API）、FB（貼上留言）、Threads（API）。

## Streamlit Secrets

```toml
APP_PASSWORD = "自己設一組密碼"
FB_PAGE_TOKEN = "KOMBO 粉專的長期權杖"
# 可省略：
THREADS_TOKEN = "Threads 長期權杖"
THREADS_TOKEN_DATE = "2026-10-30"   # 權杖產生的日期，用來算還剩幾天
# IG_USER_ID = "IG 商業帳號 id"
# GRAPH_VERSION = "v23.0"
```

沒有 `FB_PAGE_TOKEN` 時會使用測試留言。

## 檔案
- `app.py`：畫面流程（密碼、抓留言、篩選、抽獎、錄影模式）
- `ig_api.py`：Instagram Graph API
- `threads_api.py`：Threads API（抓回覆、續期權杖）
- `fb_paste.py`：整理從 FB 複製的留言
- `rules.py`：篩選與抽獎規則
- `demo.py`：測試留言
- `gacha.html`：扭蛋機動畫
