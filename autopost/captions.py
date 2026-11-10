"""Captions for each platform, in the competition's language. The final score is never written, so the video keeps its suspense."""
import datetime as dt, json, pathlib, re, unicodedata, zlib
from .i18n import TXT, COMP_NAME, COMP_TAGS, GENERIC_TAGS
from .leagues import COMPS, lang as fixture_lang


def tag(name):
    t = unicodedata.normalize("NFKD", name)
    t = "".join(c for c in t if not unicodedata.combining(c))
    return "#" + re.sub(r"[^A-Za-z0-9]", "", t)


HANDLES = json.loads((pathlib.Path(__file__).resolve().parent.parent / "data/instagram_handles.json").read_text(encoding="utf8"))


def build(info, fx, cfg):
    comp = fx["comp"]
    lang = fixture_lang(fx)
    L = TXT[lang]
    h, a = info["home"], info["away"]
    if comp == "UWCL":  # the video shows short club names; titles and captions say "Barcelona Women" (what people search)
        from .leagues import WOMENS, w_key
        full = {w_key(n): t["full"] for n, t in WOMENS.items()}
        h, a = full.get(fx["h"], h), full.get(fx["a"], a)
    ph, pd, pa = (round(x * 100) for x in info["p"])
    cname = COMP_NAME[comp]
    if comp == "UNL" and lang == "tr":
        cname = "UEFA Uluslar Ligi"
    d = dt.date.fromisoformat(fx["date"])
    stage = (f"{L['lp']} · " if comp in ("UCL", "UEL", "UECL", "UWCL") else "") + (f"{L['md']} {fx['matchday']}" if fx.get("matchday") else "")
    if comp == "UNL" and fx.get("group"):  # e.g. "League A · Group 1 · Matchday 5"
        g = fx["group"]
        grp = f"{g[0]} Ligi · {g[1:]}. Grup" if lang == "tr" else f"League {g[0]} · Group {g[1:]}"
        stage = grp + (f" · {stage}" if stage else "")
    # league dates in the open data are provisional, so only European cup fixtures get a kick-off time
    when = f"{L['days'][d.weekday()]} {d.day} {L['months'][d.month - 1]} {d.year}, {fx['time']} CET" if fx.get("time") else None
    if when and lang == "tr":  # Turkish viewers get Istanbul time (TSİ)
        from zoneinfo import ZoneInfo
        k = dt.datetime.fromisoformat(f"{fx['date']}T{fx['time']}").replace(tzinfo=ZoneInfo("Europe/Paris")).astimezone(ZoneInfo("Europe/Istanbul"))
        when = f"{L['days'][k.weekday()]} {k.day} {L['months'][k.month - 1]} {k.year}, {k:%H:%M} TSİ"
    ctags = ["#" + t for t in COMP_TAGS[comp]] + (["#UluslarLigi", "#BizimÇocuklar"] if comp == "UNL" and lang == "tr" else [])
    tags = [tag(h), tag(a)] + ctags + ["#" + t for t in GENERIC_TAGS[lang]]
    odds = f"{h} {ph}% · {L['draw']} {pd}% · {a} {pa}%"
    cta = L["ctas"][zlib.crc32(f"{h}{a}{fx['date']}".encode()) % len(L["ctas"])]
    head = f"{h} vs {a} | {cname}" + (f" · {stage}" if stage else "")

    # "Prediction" first: ~40% of YouTube views come from search ("X vs Y prediction")
    yt_title = f"{h} vs {a} {L['pred']} ⚽ {L['who']} {cname} {L['sim']}"
    if len(yt_title) > 90:
        yt_title = f"{h} vs {a} {L['pred']} ⚽ {cname}"
    if len(yt_title) > 90:
        yt_title = f"{h} vs {a} {L['pred']} ⚽"
    yt_title += " #Shorts"
    lines = [head] + ([f"{L['real']}: {when}"] if when else []) + [f"{L['model']}: {odds}"]
    yt_desc = "\n".join(lines + ["", cta, "", L["disc"], "", " ".join(tags + ["#shorts"])])
    long = "\n".join([f"{h} vs {a} {L['pred']} ⚽ {L['who']}", f"{cname}" + (f" · {stage}" if stage else ""), f"{L['model']}: {odds}"]
                     + ([f"{L['real']}: {when}"] if when else []) + [cta, "", L["disc"], "", " ".join(tags)])
    # X: no engagement asks (X's creator rewards penalise them)
    x = f"{h} vs {a} ⚽ {L['simulated']}\n{L['model']}: {odds}\n{tag(h)} {tag(a)} " + " ".join(ctags)
    if len(x) > 280:
        x = f"{h} vs {a} ⚽ {L['simulated']}\n{tag(h)} {tag(a)} {ctags[0]}"
    return {
        "youtube": {"title": yt_title[:100], "description": yt_desc[:4900], "comment": L["comment"],
                    # one playlist per competition, in the competition's own language
                    "playlist": TXT[COMPS[comp]["lang"]]["playlist"].format(c=COMP_NAME[comp]),
                    "tags": [h, a, cname] + COMP_TAGS[comp] + GENERIC_TAGS[lang] + ["shorts"]},
        # Reels: the clubs' official accounts are tagged on the video when we know them
        "instagram": {"caption": long[:2200], "user_tags": [HANDLES[k] for k in (fx.get("h"), fx.get("a")) if k in HANDLES]},
        "tiktok": long[:2200],
        "x": x,
    }
