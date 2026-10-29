"""KOMBO 扭蛋抽獎 — Streamlit app"""
import json
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from demo import fake_comments
from ig_api import IGClient, IGError, shortcode_from_url
from rules import draw_winners, selected

VERSION, BUILD = "v0.5.0", 6
HERE = Path(__file__).parent
TW = timezone(timedelta(hours=8))

st.set_page_config(page_title="KOMBO 抽獎活動", page_icon=str(HERE / "k_logo.png"), layout="centered")


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
st.markdown(f"## KOMBO 抽獎活動 - KD 半筒 \n<span style='color:#5A6B85;font-size:13px'>{VERSION} · BUILD {BUILD}</span>",
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
        ss.overrides = {}
        ss.ed_ver = ss.get("ed_ver", 0) + 1
        ss.pop("draw", None)
    except IGError as e:
        st.error(str(e))

f = ss.get("fetched")
if not f:
    st.stop()


def fmt_time(t: str) -> str:
    try:
        return datetime.strptime(t, "%Y-%m-%dT%H:%M:%S%z").astimezone(TW).strftime("%m/%d %H:%M")
    except (ValueError, TypeError):
        return ""


post, comments = f["post"], f["comments"]
mains = sum(c.get("kind", "main") == "main" for c in comments)
cap = (post.get("caption") or "").replace("\n", " ")
st.markdown(f"**{cap[:40]}{'…' if len(cap) > 40 else ''}**")
shown = post.get("comments_count")
st.caption(f"共抓到 {len(comments)} 則：主留言 {mains}、回覆 {len(comments) - mains}"
           f"（IG 上顯示 {shown if shown is not None else '—'} 則）· 抓取時間 {f['at']}")
if isinstance(shown, int) and shown > len(comments):
    st.caption(f"有 {shown - len(comments)} 則抓不到，通常是被 IG 自動隱藏或已刪除的留言。")

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

# ---------- 參加名單（自動預設 + 手動勾選） ----------
ss.setdefault("overrides", {})
ss.setdefault("ed_ver", 0)
flags = selected(comments, kw, tags, exclude, ss.overrides)
pool = [c for c, ok in zip(comments, flags) if ok]
users = len({c["user"] for c in pool})
secs = round(-(-len(pool) // batch) * 1.05 / paper + 1) if pool else 0

st.markdown("#### 參加名單")
st.markdown(f"已勾選 **{len(pool)}** 則（**{users}** 位）· 沒勾 {len(comments) - len(pool)} 則 · 投入約 {secs} 秒")
st.caption("符合關鍵字、標記人數的會自動打勾，KOMBO 自己的留言不勾。可以直接點「參加」欄位手動調整，手動改過的會一直保留。")
v1, v2 = st.columns(2)
view = v1.radio("顯示", ["全部", "已勾選", "沒勾選"], horizontal=True, key="view")
q = v2.text_input("搜尋帳號或留言", key="q").strip().lower()

rows = []
for c, ok in zip(comments, flags):
    if (view == "已勾選" and not ok) or (view == "沒勾選" and ok):
        continue
    if q and q not in (c["user"] + " " + c["text"]).lower():
        continue
    rows.append({"參加": ok, "帳號": "@" + c["user"], "留言": c["text"],
                 "類型": "回覆" if c.get("kind") == "reply" else "主留言",
                 "手動": "已手動" if c["id"] in ss.overrides else "", "時間": fmt_time(c.get("time")), "id": c["id"]})
df = pd.DataFrame(rows, columns=["參加", "帳號", "留言", "類型", "手動", "時間", "id"])
edited = st.data_editor(
    df, key=f"ed{ss.ed_ver}-{view}-{q}", hide_index=True, use_container_width=True,
    height=min(430, 40 + 35 * max(len(df), 1)),
    column_order=["參加", "帳號", "留言", "類型", "手動", "時間"],
    column_config={"參加": st.column_config.CheckboxColumn("參加", width="small"),
                   "留言": st.column_config.TextColumn("留言", width="large")},
    disabled=["帳號", "留言", "類型", "手動", "時間", "id"])
if len(df):
    changed = [i for i in range(len(df)) if bool(edited.iloc[i]["參加"]) != bool(df.iloc[i]["參加"])]
    if changed:
        for i in changed:
            ss.overrides[df.iloc[i]["id"]] = bool(edited.iloc[i]["參加"])
        ss.ed_ver += 1
        st.rerun()
if ss.overrides and st.button(f"清除手動調整（{len(ss.overrides)} 則），全部恢復自動勾選"):
    ss.overrides = {}
    ss.ed_ver += 1
    st.rerun()

if not pool:
    st.error("沒有勾選任何留言，請調整關鍵字、標記人數，或在名單裡手動勾選。")
    st.stop()
if users < n_win:
    st.error(f"勾選的只有 {users} 位，請減少抽獎人數。")
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
st.caption("只有打勾的留言會進扭蛋機。得主在按下按鈕時由伺服器的安全亂數抽出（每則留言一次機會，同一帳號只中一次），動畫是把結果演出來。")
