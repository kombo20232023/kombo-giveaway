"""KOMBO 扭蛋抽獎 — Streamlit app"""
import json
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from demo import fake_comments
from ig_api import IGClient, IGError, shortcode_from_url
from rules import draw_winners, eligible

VERSION, BUILD = "v0.4.0", 4
HERE = Path(__file__).parent
TW = timezone(timedelta(hours=8))

st.set_page_config(page_title="KOMBO 扭蛋抽獎", page_icon=str(HERE / "k_logo.png"), layout="centered")


def secret(key, default=None):
    try:
        return st.secrets.get(key, default)
    except Exception:  # 沒有 secrets 檔
        return default


ss = st.session_state
ss.setdefault("mode", "setup")


# ---------- 密碼 ----------
def require_password():
    pw = secret("APP_PASSWORD")
    if not pw:
        st.error("請先在 Streamlit 的 Secrets 設定 APP_PASSWORD。")
        st.stop()
    if ss.get("authed"):
        return
    st.markdown("### KOMBO 扭蛋抽獎")
    with st.form("login"):
        p = st.text_input("密碼", type="password")
        ok = st.form_submit_button("進入", type="primary")
    if ok:
        if secrets.compare_digest(p.encode(), str(pw).encode()):
            ss.authed = True
            st.rerun()
        st.error("密碼不對，再試一次。")
    st.stop()


require_password()

TOKEN = secret("FB_PAGE_TOKEN")
DEMO = not TOKEN


# ---------- 動畫 ----------
def gacha_html(entries, winners, settings) -> str:
    data = {"entries": [{"user": e["user"], "text": e["text"]} for e in entries],
            "winners": winners, "settings": settings}
    js = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    head = ('<meta name="viewport" content="width=device-width, initial-scale=1">'
            f"<script>window.GACHA_DATA={js};</script>")
    return head + (HERE / "gacha.html").read_text(encoding="utf-8")


if ss.mode == "show" and ss.get("draw"):
    d = ss.draw
    # 錄影模式：藏起 Streamlit 的上方列與邊距，畫面只留扭蛋機
    st.markdown("""<style>
    header[data-testid="stHeader"],[data-testid="stToolbar"],[data-testid="stDecoration"],
    [data-testid="stStatusWidget"],footer{display:none!important}
    .block-container{padding:0.25rem 0.25rem 1rem!important;max-width:480px!important}
    </style>""", unsafe_allow_html=True)
    components.html(gacha_html(d["entries"], d["winners"], d["settings"]), height=790, scrolling=False)
    st.caption(f"{d['platform']} · {len(d['entries'])} 則參加 · 抽出時間 {d['at']}")
    with st.expander("得主名單（文字）"):
        lines = [f"{i + 1}. @{d['entries'][w]['user']}：{d['entries'][w]['text']}" for i, w in enumerate(d["winners"])]
        st.code("\n".join(lines), language=None)
    if st.button("回到設定", use_container_width=True):
        ss.mode = "setup"
        st.rerun()
    st.stop()


# ---------- 設定 ----------
st.markdown(f"## KOMBO 扭蛋抽獎\n<span style='color:#5A6B85;font-size:13px'>{VERSION} · BUILD {BUILD}</span>",
            unsafe_allow_html=True)
if DEMO:
    st.info("還沒設定 Meta 權杖，目前使用測試留言。設定好 FB_PAGE_TOKEN 後就會抓真的留言。")

platform = st.radio("平台", ["IG", "FB", "Threads"], horizontal=True, key="platform")
if platform != "IG":
    st.warning("FB 和 Threads 還在接，目前先用 IG。")
    st.stop()

url = st.text_input("IG 貼文連結", key="url", placeholder="https://www.instagram.com/p/……")
if st.button("抓留言", type="primary", use_container_width=True):
    try:
        if DEMO:
            comments = fake_comments(366)
            post = {"caption": "測試貼文", "comments_count": 366}
            own = "kombo_badminton"
        else:
            sc = shortcode_from_url(url)
            if not sc:
                raise IGError("看不懂這個連結，請貼上 IG 貼文或 Reels 的完整網址。")
            client = IGClient(TOKEN, secret("GRAPH_VERSION", "v23.0"), secret("IG_USER_ID"))
            with st.spinner("抓留言中……"):
                own = client.account()["username"]
                post = client.find_media(sc)
                comments = client.comments(post["id"])
        ss.fetched = {"comments": comments, "post": post, "own": own,
                      "at": datetime.now(TW).strftime("%Y/%m/%d %H:%M")}
        ss.exclude = own
        ss.pop("draw", None)
    except IGError as e:
        st.error(str(e))

f = ss.get("fetched")
if not f:
    st.stop()

post, comments = f["post"], f["comments"]
cap = (post.get("caption") or "").replace("\n", " ")
st.markdown(f"**{cap[:40]}{'…' if len(cap) > 40 else ''}**")
st.caption(f"主留言 {len(comments)} 則（貼文上顯示 {post.get('comments_count', '—')} 則，含回覆）· 抓取時間 {f['at']}")
with st.expander("看全部留言"):
    st.dataframe([{"帳號": "@" + c["user"], "留言": c["text"]} for c in comments],
                 use_container_width=True, hide_index=True)

c1, c2 = st.columns(2)
kw = c1.text_input("關鍵字", value="+1", key="kw", help="留空 = 不限")
tags = c2.selectbox("標記人數", [0, 1, 2, 3], key="tags", format_func=lambda n: "不限" if n == 0 else f"至少 {n} 位")
c3, c4 = st.columns(2)
n_win = c3.number_input("投入 K 幣（抽幾位）", 1, 20, 4, key="n_win")
batch = c4.radio("每批紙條", [10, 20, 30], index=1, horizontal=True, key="batch")
with st.expander("進階設定（速度、音效、排除帳號）"):
    paper = st.slider("紙條速度（倍）", 0.5, 1.5, 0.7, 0.1, key="paper")
    opening = st.slider("開蛋速度（倍）", 0.5, 1.5, 0.8, 0.1, key="opening")
    sound = st.toggle("音效", value=True, key="sound")
    exclude = st.text_input("排除帳號", key="exclude")

pool = eligible(comments, kw, tags, exclude)
users = len({c["user"] for c in pool})
secs = round(-(-len(pool) // batch) * 1.05 / paper + 1)
st.markdown(f"符合條件 **{len(pool)}** 則（**{users}** 位）· 投入約 {secs} 秒")

if not pool:
    st.error("沒有符合條件的留言，請調整關鍵字或標記人數。")
    st.stop()
if users < n_win:
    st.error(f"符合條件的只有 {users} 位，請減少抽獎人數。")
    st.stop()

if st.button("抽出得主並進入動畫", type="primary", use_container_width=True):
    ss.draw = {
        "entries": pool,
        "winners": draw_winners(pool, int(n_win)),
        "platform": platform,
        "at": datetime.now(TW).strftime("%Y/%m/%d %H:%M"),
        "settings": {"platform": platform, "kw": kw.strip(), "tags": tags, "winners": int(n_win),
                     "batch": batch, "paperSpeed": paper, "openSpeed": opening, "sound": sound},
    }
    ss.mode = "show"
    st.rerun()
st.caption("得主在按下按鈕時由伺服器的安全亂數抽出（每則留言一次機會，同一帳號只中一次），動畫是把結果演出來。")
