"""把從 FB 網頁複製的留言整理成「留言者＋留言內容」。

FB 複製出來每則留言大致是：
    名字
     ·
    （頭號粉絲之類的徽章）
    留言內容
    回覆
    （發送訊息）
    隱藏          ← 粉專管理員才看得到，用來分隔每則留言
"""
import re

BUTTONS = {"回覆", "發送訊息", "隱藏", "已編輯", "讚", "分享", "查看翻譯", "翻譯年糕", "顯示原文", "作者",
           "最相關", "最新", "所有留言", "查看更多留言", "撰寫留言……", "撰寫留言...", "以 KOMBO慷柏體育 的身分留言……"}
BADGES = {"頭號粉絲", "熱衷粉絲", "新成員", "版主", "管理員", "熱門留言者", "追蹤者", "超級粉絲", "活躍成員"}
NOISE = re.compile(r"^(·|\d+\s*(秒|分鐘|小時|天|週|周|個月|年)|\d+|\d+\s*個?讚|查看\s*\d+\s*則回覆|查看(全部|更多).*|\d+\s*則回覆)$")


def _skip(line: str) -> bool:
    return not line or line in BUTTONS or line in BADGES or bool(NOISE.match(line))


def parse_fb(text: str) -> list[dict]:
    lines = [ln.strip() for ln in (text or "").replace("\r", "").split("\n")]
    end = "隱藏" if "隱藏" in lines else "回覆"  # 不是管理員複製的就用「回覆」分隔
    blocks, cur = [], []
    for ln in lines:
        if ln == end:
            blocks.append(cur)
            cur = []
        else:
            cur.append(ln)
    out = []
    for b in blocks:
        keep = [ln for ln in b if not _skip(ln)]
        if not keep:
            continue
        name, body = keep[0], " ".join(keep[1:]).strip()
        out.append({"id": f"fb{len(out)}", "user": name, "text": body, "time": "", "kind": "main", "parent": None})
    return out
