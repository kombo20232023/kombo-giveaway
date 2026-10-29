"""還沒設定 Meta 權杖時用的測試留言。"""
import random

GOOD = ["+1 想要 {m}", "+1 跟 {m} 一起打球", "+1 好想中 {m} {m}", "+1 KOMBO 練習球讚", "+1 拜託讓我中一次",
        "+1 {m} 快來", "+1 週末球隊用 {m}", "+1 想要一桶 {m}", "+1 必備！", "+1 我要我要 {m} {m}", "+1 抽我抽我",
        "+1 打球必備 {m}", "+1 祝我好運", "+1 謝謝 KOMBO {m}", "+1 想試試新球 {m} {m}", "+1 羽球人必抽",
        "+1 我們球隊每週都打，想要試試看 KOMBO 的比賽球 {m} {m}", "+1 {m} {m} {m} 一起來"]
BAD = ["請問多少錢？", "好漂亮", "已分享", "怎麼買", "好想要喔", "可以寄外島嗎", "{m} 你看"]
SYL = ["amy", "ben", "coco", "dan", "eva", "gogo", "hana", "ivy", "jj", "kai", "lulu", "mia", "nini", "ping",
       "ray", "sam", "tina", "vic", "wen", "yuyu", "zoe", "chen", "lin", "wang", "huang", "liu", "tsai", "momo"]
SUF = ["_bd", ".smash", "_shuttle", "88", "921", "_tw", ".play", "_k", "", "_badminton", ".c", "66"]


def fake_comments(n: int = 366, own: str = "kombo_badminton", seed: int = 20261030) -> list[dict]:
    r = random.Random(seed + n)
    users = set()
    while len(users) < max(12, round(n * 0.72)):
        users.add(r.choice(SYL) + r.choice(SUF) + (str(r.randint(10, 99)) if r.random() < .25 else ""))
    users = sorted(users)

    def fill(t):
        while "{m}" in t:
            t = t.replace("{m}", "@" + r.choice(SYL) + r.choice(["", "_", ".k", "88"]), 1)
        return t

    nb = round(n * 0.033)
    out = [{"user": r.choice(users), "text": fill(r.choice(GOOD))} for _ in range(n - 2 - nb)]
    out += [{"user": r.choice(users), "text": fill(r.choice(BAD))} for _ in range(nb)]
    out += [{"user": own, "text": "+1 謝謝大家參加！"}, {"user": own, "text": "+1 開獎時間見貼文說明"}]
    r.shuffle(out)
    for i, c in enumerate(out):
        c["id"], c["time"], c["kind"], c["parent"] = f"m{i}", "", "main", None
    # 回覆：KOMBO 自己的感謝回覆，以及參加者在別人留言底下回覆參加
    replies = []
    for k in range(round(n * 0.19)):
        p = r.choice(out)
        if k % 5 < 3:
            replies.append({"user": own, "text": r.choice(["謝謝參加！", "祝你好運～", "收到！"])})
        else:
            replies.append({"user": r.choice(users), "text": fill(r.choice(GOOD))})
        replies[-1].update(id=f"r{k}", time="", kind="reply", parent=p["id"])
    return out + replies
