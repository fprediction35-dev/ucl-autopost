"""After the real match: read the YouTube comments, find who wrote the exact score, and announce them under the
channel's own comment ("I'll reply here with everyone who got it right"). Pinning that comment stays manual
(the YouTube API cannot pin).

python -m autopost.winners            # announce every finished match posted to YouTube in the last days
python -m autopost.winners --dry-run  # show results and winners, write nothing

Real results: this repo's data first (openfootball, data/*.txt), then ESPN's public scoreboard, because the open data
often lags weeks behind. A match is only announced when its result is found for that exact date and both teams.
Done matches are kept in data/winners.json.
"""
import argparse, datetime as dt, json, pathlib, re, sys, unicodedata
from zoneinfo import ZoneInfo
import requests
from . import leagues
from .platforms import youtube

ROOT = pathlib.Path(__file__).resolve().parent.parent
POSTED, DONE = ROOT / "data/posted.json", ROOT / "data/winners.json"
API = youtube.API
ESPN = {"UCL": "uefa.champions", "UEL": "uefa.europa", "UECL": "uefa.europa.conf", "UNL": "uefa.nations",
        "UWCL": "uefa.wchampions", "TR1": "tur.1", "EN1": "eng.1", "ES1": "esp.1", "IT1": "ita.1", "DE1": "ger.1", "FR1": "fra.1"}
SCORE = re.compile(r"(?<!\d)(\d{1,2})\s*[-–—:]\s*(\d{1,2})(?!\d)")

TXT = {
    "en": ("🏆 Real result: {m}. Exact score: {w}", "🏆 Real result: {m}. Nobody got the exact score this time, try the next one ⚽", " and {n} more"),
    "tr": ("🏆 Gerçek skor: {m}. Skoru tam bilenler: {w}", "🏆 Gerçek skor: {m}. Bu sefer kimse tam skoru bilemedi, sıradaki maçta görüşürüz ⚽", " ve {n} kişi daha"),
    "es": ("🏆 Resultado real: {m}. Acertaron el resultado exacto: {w}", "🏆 Resultado real: {m}. Nadie acertó el resultado exacto, ¡a por el siguiente! ⚽", " y {n} más"),
    "it": ("🏆 Risultato reale: {m}. Hanno indovinato: {w}", "🏆 Risultato reale: {m}. Nessuno ha indovinato il risultato esatto, alla prossima ⚽", " e altri {n}"),
    "de": ("🏆 Echtes Ergebnis: {m}. Genau richtig getippt: {w}", "🏆 Echtes Ergebnis: {m}. Diesmal hat niemand genau getippt, beim nächsten Spiel ⚽", " und {n} weitere"),
    "fr": ("🏆 Score réel : {m}. Score exact trouvé par : {w}", "🏆 Score réel : {m}. Personne n'a trouvé le score exact, rendez-vous au prochain ⚽", " et {n} autres"),
}


def words(name):
    s = "".join(c for c in unicodedata.normalize("NFKD", name.lower().replace("ı", "i")) if not unicodedata.combining(c))
    return {w for w in re.split(r"[^a-z0-9]+", s) if len(w) > 2 and w not in ("fc", "cf", "afc", "club", "women", "the")}


def same(ours, theirs):
    """ESPN and openfootball spell clubs differently ("Bayern Munich" / "FC Bayern München"): any shared word decides."""
    return bool(words(ours) & words(theirs))


def from_data(data, f):
    rows = data["matches"] + [r for r in data["nations"] + data["womens"] + data["uefa"] if "gh" in r]
    for r in rows:
        if r.get("comp") == f["comp"] and r["h"] == f["h"] and r["a"] == f["a"] and r["date"] == f["date"] and "gh" in r:
            return r["gh"], r["ga"]


def from_espn(f, names):
    slug = ESPN.get(f["comp"])
    if not slug:
        return None
    d = dt.date.fromisoformat(f["date"])
    for day in (d, d + dt.timedelta(days=1)):  # ESPN dates are US time: late European kick-offs can land on the next day
        r = requests.get(f"https://site.api.espn.com/apis/site/v2/sports/soccer/{slug}/scoreboard",
                         params={"dates": day.strftime("%Y%m%d")}, timeout=30)
        r.raise_for_status()
        for ev in r.json().get("events", []):
            comp = (ev.get("competitions") or [{}])[0]
            if not comp.get("status", ev.get("status", {})).get("type", {}).get("completed"):
                continue
            side = {c.get("homeAway"): c for c in comp.get("competitors", [])}
            if set(side) != {"home", "away"}:
                continue
            tn = lambda c: " ".join(filter(None, [c.get("team", {}).get(k, "") for k in ("displayName", "shortDisplayName", "name")]))
            if all(any(same(n, tn(side[s])) for n in names[s]) for s in ("home", "away")):
                return int(side["home"]["score"]), int(side["away"]["score"])


def comments(tok, vid):
    """all top-level comments, newest first: [(thread id, author channel id, author name, text, published ISO time)]"""
    out, page = [], ""
    for _ in range(10):  # up to 1000 comments
        r = requests.get(f"{API}/commentThreads", headers={"Authorization": f"Bearer {tok}"}, timeout=30, params={
            "part": "snippet", "videoId": vid, "maxResults": 100, "textFormat": "plainText", "pageToken": page})
        youtube._check(r)
        j = r.json()
        for it in j.get("items", []):
            s = it["snippet"]["topLevelComment"]["snippet"]
            out.append((it["id"], s.get("authorChannelId", {}).get("value"), s.get("authorDisplayName", ""), s.get("textOriginal", ""),
                        s.get("publishedAt", "")))
        page = j.get("nextPageToken")
        if not page:
            break
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--days", type=int, default=7, help="look back this many days")
    ap.add_argument("--max", type=int, default=10, help="announcements per run (each reply costs 50 API quota units)")
    a = ap.parse_args()
    cfg = json.loads((ROOT / "config.json").read_text(encoding="utf8"))
    tz = ZoneInfo(cfg.get("timezone", "UTC"))
    today = dt.datetime.now(tz).date()
    posted = json.loads(POSTED.read_text())
    done = json.loads(DONE.read_text()) if DONE.exists() else {}
    todo = []
    for k, v in posted.items():
        link = str(v.get("youtube", ""))
        d = v.get("date", "")
        if k in done or "/shorts/" not in link or not d or not (today - dt.timedelta(days=a.days) <= dt.date.fromisoformat(d) < today):
            continue
        if not a.dry_run and "youtube_at" not in v:
            continue  # posted before the guess-the-score comment existed: nothing was promised there
        todo.append((k, v, link))
    if not todo:
        print("winners: nothing to announce")
        return 0
    data = leagues.build()
    tok = None if a.dry_run else youtube._token()
    me = cfg.get("youtube_channel_id")
    sent = 0
    for k, v, link in todo:
        if sent >= a.max:
            print(f"winners: {a.max} announced, the rest waits for the next run (API quota)")
            break
        # fixture ids are COMP|home key|away key and keys look like "name|COUNTRY"
        parts = k.split("|")
        f = {"comp": parts[0], "h": "|".join(parts[1:3]), "a": "|".join(parts[3:5]), "date": v["date"]}
        disp = lambda key: data["display"].get(key, key.split("|")[0])
        names = {"home": [disp(f["h"]), f["h"].split("|")[0]], "away": [disp(f["a"]), f["a"].split("|")[0]]}
        res = from_data(data, f)
        if res is None:
            try:
                res = from_espn(f, names)
            except Exception as e:
                print(f"  {k}: ESPN lookup failed: {str(e)[:150]}")
        if res is None:
            print(f"  {k}: no result yet")
            continue
        lang = leagues.lang(f)
        T = TXT.get(lang, TXT["en"])
        match = f"{names['home'][0]} {res[0]}-{res[1]} {names['away'][0]}"
        vid = link.rsplit("/", 1)[1].split()[0].split("?")[0]
        if a.dry_run:
            print(f"  {k}: {match} ({link})")
            continue
        try:
            cs = comments(tok, vid)
        except Exception as e:
            print(f"  {k}: comments not readable: {str(e)[:150]}")
            continue
        mine = [c for c in cs if c[1] == me]  # newest first: mine[-1] is the channel's first comment
        # only guesses written before kick-off count (time known for cups, otherwise noon UTC of match day);
        # each viewer's first guess counts, so editing the score later in a new comment does not help
        cutoff = f"{f['date']}T{v.get('time') or '12:00'}"
        guesses = {}
        for tid, author, name, text, at in reversed(cs):
            if author == me or author in guesses or not at or at[:16] >= cutoff:
                continue
            m = SCORE.search(text)
            if m:
                guesses[author] = (name, (int(m.group(1)), int(m.group(2))))
        right = [name for name, g in guesses.values() if g == res]
        if not guesses:
            print(f"  {k}: {match}, no score guesses in the comments")
            done[k] = {"result": f"{res[0]}-{res[1]}", "guesses": 0, "winners": 0}
            continue
        shown = right[:25]
        text = (T[0].format(m=match, w=", ".join(shown)) + (T[2].format(n=len(right) - len(shown)) if len(right) > len(shown) else "")
                if right else T[1].format(m=match))
        h = {"Authorization": f"Bearer {tok}", "Content-Type": "application/json; charset=UTF-8"}
        try:
            if mine:  # reply under the channel's own comment (the one promising this announcement)
                r = requests.post(f"{API}/comments?part=snippet", headers=h, timeout=30,
                                  json={"snippet": {"parentId": mine[-1][0], "textOriginal": text}})
            else:
                r = requests.post(f"{API}/commentThreads?part=snippet", headers=h, timeout=30, json={
                    "snippet": {"videoId": vid, "topLevelComment": {"snippet": {"textOriginal": text}}}})
            youtube._check(r)
        except Exception as e:
            print(f"  {k}: announcement failed: {str(e)[:150]}")
            continue
        done[k] = {"result": f"{res[0]}-{res[1]}", "guesses": len(guesses), "winners": len(right)}
        sent += 1
        print(f"  {k}: {match}, {len(right)}/{len(guesses)} right, announced")
        DONE.write_text(json.dumps(done, ensure_ascii=False, indent=0, sort_keys=True), encoding="utf8")
    if not a.dry_run:
        DONE.write_text(json.dumps(done, ensure_ascii=False, indent=0, sort_keys=True), encoding="utf8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
