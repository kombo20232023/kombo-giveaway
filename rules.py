"""篩選留言、抽出得主。"""
import re
import secrets
import unicodedata

MENTION = re.compile(r"@[A-Za-z0-9_.]+")
# 「打球囉！」去掉關鍵字後剩下的語助詞、標點，不算是標記的名字
FILLER = set("囉嘍咯嚕了啦鴨喔哦呀啊吧耶唷～~!！?？.。,，、:：;；「」『』\"'()（）[]【】<>《》 \t-_")


def mention_count(text: str) -> int:
    return len(MENTION.findall(text or ""))


def tag_key(c: dict, keyword: str, platform: str) -> str:
    """這則留言標記了誰。IG 用 @帳號；FB 沒有 @，用去掉關鍵字和語助詞後剩下的字。"""
    if platform != "FB":
        return " ".join(sorted({m.lower() for m in MENTION.findall(c["text"])}))
    t = c["text"].replace(keyword, "") if keyword else c["text"]
    rest = []
    for ch in t:
        if ch in FILLER or unicodedata.category(ch) in ("So", "Sk", "Mn", "Cf", "Zs") or ord(ch) >= 0x1F000:
            continue
        rest.append(ch.lower())
    return "".join(rest)


def auto_flags(comments: list[dict], keyword: str = "", exclude: str = "", min_tags: int = 0,
               need_tag: bool = False, dedupe: bool = True, platform: str = "IG") -> list[tuple[bool, str]]:
    """每則留言的自動判斷：(要不要勾, 不勾的原因)。重複標記時，最早的那則算數。"""
    ex = (exclude or "").strip().lstrip("@").lower()
    kw = (keyword or "").strip()
    order = sorted(range(len(comments)), key=lambda i: (comments[i].get("time") or "", i))
    seen, res = set(), [(True, "")] * len(comments)
    for i in order:
        c = comments[i]
        if ex and c["user"].lower() == ex:
            res[i] = (False, "KOMBO 自己的留言")
        elif kw and kw not in c["text"]:
            res[i] = (False, "沒有關鍵字")
        elif platform != "FB" and mention_count(c["text"]) < min_tags:
            res[i] = (False, f"標記不到 {min_tags} 位")
        else:
            key = tag_key(c, kw, platform)
            if platform == "FB" and need_tag and not key:
                res[i] = (False, "沒標記朋友")
            elif dedupe and key and (c["user"].lower(), key) in seen:
                res[i] = (False, "重複標記同一位朋友")
            else:
                seen.add((c["user"].lower(), key))
                res[i] = (True, "")
    return res


def selected(comments: list[dict], flags: list[tuple[bool, str]], overrides: dict) -> list[bool]:
    """最後要不要參加：手動改過的以手動為準，其他照自動判斷。"""
    return [overrides.get(c["id"], ok) for c, (ok, _) in zip(comments, flags)]


def draw_winners(entries: list[dict], n: int, rng=None) -> list[int]:
    """每則留言一次機會；同一人只會中一次。回傳 entries 的索引。"""
    rng = rng or secrets.SystemRandom()
    pool = list(range(len(entries)))
    picked = []
    while pool and len(picked) < n:
        i = pool[rng.randrange(len(pool))]
        picked.append(i)
        user = entries[i]["user"]
        pool = [j for j in pool if entries[j]["user"] != user]
    return picked
