"""篩選留言、抽出得主。"""
import re
import secrets

MENTION = re.compile(r"@[A-Za-z0-9_.]+")


def mention_count(text: str) -> int:
    return len(MENTION.findall(text or ""))


def eligible(comments: list[dict], keyword: str, min_tags: int, exclude: str) -> list[dict]:
    ex = (exclude or "").strip().lstrip("@").lower()
    kw = (keyword or "").strip()
    return [c for c in comments
            if c["user"].lower() != ex
            and (not kw or kw in c["text"])
            and mention_count(c["text"]) >= min_tags]


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
