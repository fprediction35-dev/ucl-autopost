"""Captions for each platform, in the competition's language. The final score is never written, so the video keeps its suspense."""
import datetime as dt, re, unicodedata, zlib
from .i18n import TXT, COMP_NAME, COMP_TAGS, GENERIC_TAGS
from .leagues import COMPS


def tag(name):
    t = unicodedata.normalize("NFKD", name)
    t = "".join(c for c in t if not unicodedata.combining(c))
    return "#" + re.sub(r"[^A-Za-z0-9]", "", t)


def build(info, fx, cfg):
    comp = fx["comp"]
    lang = COMPS[comp]["lang"]
    L = TXT[lang]
    h, a = info["home"], info["away"]
    ph, pd, pa = (round(x * 100) for x in info["p"])
    cname = COMP_NAME[comp]
    d = dt.date.fromisoformat(fx["date"])
    stage = (f"{L['lp']} · " if comp in ("UCL", "UEL", "UECL") else "") + (f"{L['md']} {fx['matchday']}" if fx.get("matchday") else "")
    # league dates in the open data are provisional, so only European cup fixtures get a kick-off time
    when = f"{L['days'][d.weekday()]} {d.day} {L['months'][d.month - 1]} {d.year}, {fx['time']} CET" if fx.get("time") else None
    ctags = ["#" + t for t in COMP_TAGS[comp]]
    tags = [tag(h), tag(a)] + ctags + ["#" + t for t in GENERIC_TAGS[lang]]
    odds = f"{h} {ph}% · {L['draw']} {pd}% · {a} {pa}%"
    cta = L["ctas"][zlib.crc32(f"{h}{a}{fx['date']}".encode()) % len(L["ctas"])]
    head = f"{h} vs {a} | {cname}" + (f" · {stage}" if stage else "")

    yt_title = f"{h} vs {a} ⚽ {L['who']} {cname} {L['sim']}"
    if len(yt_title) > 90:
        yt_title = f"{h} vs {a} ⚽ {L['who']}"
    yt_title += " #Shorts"
    lines = [head] + ([f"{L['real']}: {when}"] if when else []) + [f"{L['model']}: {odds}"]
    yt_desc = "\n".join(lines + ["", cta, "", L["disc"], "", " ".join(tags + ["#shorts"])])
    long = "\n".join([f"{h} vs {a} ⚽ {L['who']}", f"{cname}" + (f" · {stage}" if stage else ""), f"{L['model']}: {odds}"]
                     + ([f"{L['real']}: {when}"] if when else []) + [cta, "", L["disc"], "", " ".join(tags)])
    # X: no engagement asks (X's creator rewards penalise them)
    x = f"{h} vs {a} ⚽ {L['simulated']}\n{L['model']}: {odds}\n{tag(h)} {tag(a)} " + " ".join(ctags)
    if len(x) > 280:
        x = f"{h} vs {a} ⚽ {L['simulated']}\n{tag(h)} {tag(a)} {ctags[0]}"
    return {
        "youtube": {"title": yt_title[:100], "description": yt_desc[:4900],
                    "tags": [h, a, cname] + COMP_TAGS[comp] + GENERIC_TAGS[lang] + ["shorts"]},
        "instagram": long[:2200],
        "tiktok": long[:2200],
        "x": x,
    }
