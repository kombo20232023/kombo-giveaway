"""篩選留言、抽出得主。"""
import re
import secrets

MENTION = re.compile(r"@[A-Za-z0-9_.]+")


def mention_count(text: str) -> int:
    return len(MENTION.findall(text or ""))


def auto_ok(c: dict, keyword: str, min_tags: int, exclude: str) -> bool:
    """自動預設要不要勾：不是自己的帳號、有關鍵字、標記人數夠。"""
    ex = (exclude or "").strip().lstrip("@").lower()
    kw = (keyword or "").strip()
    return (c["user"].lower() != ex
            and (not kw or kw in c["text"])
            and mention_count(c["text"]) >= min_tags)


def eligible(comments: list[dict], keyword: str, min_tags: int, exclude: str) -> list[dict]:
    return [c for c in comments if auto_ok(c, keyword, min_tags, exclude)]


def selected(comments: list[dict], keyword: str, min_tags: int, exclude: str, overrides: dict) -> list[bool]:
    """每則留言最後要不要參加：手動改過的以手動為準，其他照自動規則。"""
    return [overrides.get(c["id"], auto_ok(c, keyword, min_tags, exclude)) for c in comments]


def draw_winners(entries: list[dict], n: int, rng=None) -> list[int]:
    """每則留言一次機會；同一帳號只會中一次。回傳 entries 的索引。"""
    rng = rng or secrets.SystemRandom()
    pool = list(range(len(entries)))
    picked = []
    while pool and len(picked) < n:
        i = pool[rng.randrange(len(pool))]
        picked.append(i)
        user = entries[i]["user"]
        pool = [j for j in pool if entries[j]["user"] != user]
    return picked
