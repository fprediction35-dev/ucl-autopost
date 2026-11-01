"""English captions for each platform. The final score is never written, so the video keeps its suspense."""
import re, unicodedata

SHORT_DAY = {0: "Mon", 1: "Tue", 2: "Wed", 3: "Thu", 4: "Fri", 5: "Sat", 6: "Sun"}


def tag(name):
    t = unicodedata.normalize("NFKD", name)
    t = "".join(c for c in t if not unicodedata.combining(c))
    return "#" + re.sub(r"[^A-Za-z0-9]", "", t)


def build(info, fx, cfg):
    import datetime as dt
    h, a = info["home"], info["away"]
    ph, pd, pa = (round(x * 100) for x in info["p"])
    d = dt.date.fromisoformat(fx["date"])
    when = f"{SHORT_DAY[d.weekday()]} {d.day} {d.strftime('%b')} {d.year}, {fx['kickoff_cet']} CET"
    tags = [tag(h), tag(a)] + ["#" + x for x in cfg.get("extra_hashtags", [])]
    odds = f"{h} {ph}% · Draw {pd}% · {a} {pa}%"
    disclaimer = "Simulation based on European results since 2011. Not the real match result."

    yt_title = f"{h} vs {a} ⚽ Who wins? Champions League simulation"
    if len(yt_title) > 90:
        yt_title = f"{h} vs {a} ⚽ UCL simulation"
    yt_title += " #Shorts"
    yt_desc = "\n".join([
        f"{h} vs {a} | Champions League matchday {fx['matchday']}",
        f"Real match: {when}",
        f"Model prediction: {odds}",
        "", "Who do you think wins? Drop your score in the comments 👇",
        "", disclaimer, "", " ".join(tags + ["#shorts"]),
    ])
    long = "\n".join([
        f"{h} vs {a} ⚽ Who wins this one?",
        f"Model: {odds}",
        f"Real match: {when}",
        "Comment your prediction 👇",
        "", disclaimer, "", " ".join(tags),
    ])
    x = f"{h} vs {a} ⚽ simulated before kick-off\nModel: {odds}\nWho wins? 👇\n{tag(h)} {tag(a)} #UCL #ChampionsLeague"
    if len(x) > 280:
        x = f"{h} vs {a} ⚽ simulated\n{tag(h)} {tag(a)} #UCL"
    return {
        "youtube": {"title": yt_title[:100], "description": yt_desc[:4900],
                    "tags": [h, a, "Champions League", "UCL", "football simulation", "shorts"]},
        "instagram": long[:2200],
        "tiktok": long[:2200],
        "x": x,
    }
