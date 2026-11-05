"""Daily run: pick upcoming fixtures (European cups, Süper Lig, big 5 leagues), render a simulation video for each,
post to every enabled platform within its daily cap.

python -m autopost.main                    # fixtures from tomorrow (config timezone) over the next few days
python -m autopost.main --date 2026-11-05  # window starts on this day
python -m autopost.main --dry-run          # render videos and captions, post nothing
python -m autopost.main --only youtube,x   # limit platforms for this run (ignores daily caps)
python -m autopost.main --comps UEL,UECL   # limit competitions
python -m autopost.main --exclude youtube  # daily run without youtube (youtube has its own evening slot)
python -m autopost.main --only youtube --backfill  # post already-posted matches that are missing a youtube link
"""
import zlib, argparse, concurrent.futures as cf, datetime as dt, json, pathlib, re, subprocess, sys, time, traceback
from zoneinfo import ZoneInfo
from . import captions, leagues, teams
from .i18n import OVERLAY
from .platforms import youtube, instagram, tiktok, x

ROOT = pathlib.Path(__file__).resolve().parent.parent
POSTED = ROOT / "data/posted.json"
POSTERS = {"youtube": youtube.post, "instagram": instagram.post, "tiktok": tiktok.post, "x": x.post}


def slug(s):
    import unicodedata
    s = "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def fid(f):
    return f"{f['comp']}|{f['h']}|{f['a']}"


def uefa_matchday(data, comp, date):
    weeks = sorted({dt.date.fromisoformat(r["date"]).isocalendar()[:2] for r in data["uefa"] if r["comp"] == comp})
    wk = dt.date.fromisoformat(date).isocalendar()[:2]
    return weeks.index(wk) + 1 if wk in weeks else None


def order(fixtures, data, cfg):
    big = set(cfg.get("priority_teams", []))
    elo = lambda k: data["teams"].get(k, {}).get("elo", 1450)
    def score(f):
        tier = 2 if (f["h"] in big or f["a"] in big) else 1 if (f["h"].endswith("|TUR") or f["a"].endswith("|TUR")) else 0
        # soonest day first, so every match goes out before kick-off; within a day Turkish clubs, then the strongest pairings
        return (f["date"], -tier, -(elo(f["h"]) + elo(f["a"])))
    return sorted(fixtures, key=score)


def prepare(f, data, out, cfg):
    comp = f["comp"]
    lang = leagues.COMPS[comp]["lang"]
    m = data["model"]
    ti = {k: teams.info(f[k[0]], f[k]) for k in ("home", "away")}
    f["home"], f["away"] = ti["home"]["name"], ti["away"]["name"]
    meta = {"model": {"a": m["intercept"].get(comp, m["a"]), "b": m["b"], "hfa": m["hfa"]}}
    for k in ("home", "away"):
        t = data["teams"].get(f[k[0]], {})
        meta[k] = dict(ti[k], elo=t.get("elo", 1450), n=t.get("n", 0), last=[])
    name = f"{comp.lower()}-{slug(f['home'])}-vs-{slug(f['away'])}"
    setup = out / f"{name}.setup.json"
    setup.write_text(json.dumps({"meta": meta, "lang": OVERLAY[lang], "seed": zlib.crc32(f"{fid(f)}|{f['date']}".encode())}, ensure_ascii=False), encoding="utf8")
    return name, setup


def render(f, name, setup, out, cfg):
    video = out / f"{name}.mp4"
    if not (video.exists() and video.with_suffix(".json").exists()):
        r = subprocess.run(["node", str(ROOT / "render.js"), "--home", f["home"], "--away", f["away"], "--out", str(video),
                            "--dur", str(cfg.get("duration_seconds", 60)), "--music", cfg.get("music", "hype"),
                            "--handle", cfg.get("handle", ""), "--meta", str(setup)], capture_output=True, text=True)
        if r.returncode:
            raise RuntimeError(f"render failed: {r.stderr[-800:]}")
    return video, json.loads(video.with_suffix(".json").read_text())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date"); ap.add_argument("--dry-run", action="store_true"); ap.add_argument("--only")
    ap.add_argument("--limit", type=int, help="max videos for this run")
    ap.add_argument("--skip", type=int, default=0, help="skip the first N matches")
    ap.add_argument("--gap", type=float, help="minutes between matches (overrides config)")
    ap.add_argument("--days", type=int, help="window length in days (overrides config)")
    ap.add_argument("--comps", help="comma-separated competition codes, e.g. UEL,UECL,TR1")
    ap.add_argument("--workers", type=int, help="parallel renders")
    ap.add_argument("--exclude", help="comma-separated platforms to leave out of this run (daily caps and posted.json still apply)")
    ap.add_argument("--backfill", action="store_true",
                    help="with --only: post matches already in posted.json that have no link yet for those platforms")
    a = ap.parse_args()
    cfg = json.loads((ROOT / "config.json").read_text(encoding="utf8"))
    tz = ZoneInfo(cfg.get("timezone", "UTC"))
    start = dt.date.fromisoformat(a.date) if a.date else dt.datetime.now(tz).date() + dt.timedelta(days=1)
    days = a.days or cfg.get("window_days", 3)
    end = start + dt.timedelta(days=days - 1)

    data = leagues.build()
    posted = json.loads(POSTED.read_text()) if POSTED.exists() else {}
    if a.backfill and not a.only:
        sys.exit("--backfill needs --only, e.g. --only youtube")
    has = lambda f, p: str(posted.get(fid(f), {}).get(p, "")).startswith("http")
    if a.backfill:
        fx = [f for f in leagues.fixtures(data, start.isoformat(), end.isoformat())
              if fid(f) in posted and not all(has(f, p) for p in a.only.split(","))]
    else:
        fx = [f for f in leagues.fixtures(data, start.isoformat(), end.isoformat()) if fid(f) not in posted]
    if a.comps:
        fx = [f for f in fx if f["comp"] in a.comps.split(",")]
    for f in fx:
        if f["comp"] in ("UCL", "UEL", "UECL"):
            f["matchday"] = uefa_matchday(data, f["comp"], f["date"])

    platforms = [p for p, on in cfg["platforms"].items() if on]
    if a.only:
        platforms = [p for p in a.only.split(",") if p in POSTERS]
    if a.exclude:
        platforms = [p for p in platforms if p not in a.exclude.split(",")]
    limits = {} if a.only and not a.backfill else {p: cfg.get("platform_limits", {}).get(p, 999) for p in platforms}
    n = a.limit or max([limits.get(p, cfg.get("max_videos_per_day", 20)) for p in platforms] or [cfg.get("max_videos_per_day", 20)])
    todo = order(fx, data, cfg)[a.skip:a.skip + n]
    print(f"{start}..{end}: {len(fx)} unposted fixtures, making {len(todo)} videos for {', '.join(platforms) or 'nothing'}")
    for f in todo:
        print(f"  {f['date']} {f['comp']:5} {f['home']} vs {f['away']}")
    if not todo:
        return 0

    out = ROOT / "out" / start.isoformat()
    out.mkdir(parents=True, exist_ok=True)
    jobs = [(f, *prepare(f, data, out, cfg)) for f in todo]
    pool = cf.ThreadPoolExecutor(a.workers or cfg.get("render_workers", 3))
    futures = [pool.submit(render, f, name, setup, out, cfg) for f, name, setup in jobs]

    report, failures = [], 0
    sent = {p: 0 for p in platforms}
    strikes = {p: 0 for p in platforms}
    gap = 60 * (a.gap if a.gap is not None else cfg.get("post_gap_minutes", 6))
    last_post = 0.0
    for (f, name, setup), fut in zip(jobs, futures):
        print(f"\n=== {f['comp']} {f['home']} vs {f['away']} ===", flush=True)
        try:
            video, info = fut.result()
        except Exception as e:
            failures += 1
            print(f"  render FAILED: {e}")
            report.append({"match": f"{f['home']} vs {f['away']}", "comp": f["comp"], "error": str(e)})
            continue
        cap = captions.build(info, f, cfg)
        (out / f"{name}.captions.json").write_text(json.dumps(cap, ensure_ascii=False, indent=1), encoding="utf8")
        row = {"match": f"{f['home']} vs {f['away']}", "comp": f["comp"], "date": f["date"],
               "simulated": "-".join(map(str, info["final"])), "posts": {}}
        if a.dry_run:
            row["posts"] = {p: "dry run" for p in platforms}
        else:
            wait = gap - (time.time() - last_post)
            if last_post and wait > 0:
                time.sleep(wait)
            last_post = time.time()
            for p in platforms:
                if a.backfill and has(f, p):
                    row["posts"][p] = "already posted"; continue
                if sent[p] >= limits.get(p, 999):
                    row["posts"][p] = "skipped (daily limit)"; continue
                if strikes[p] >= 2:
                    row["posts"][p] = "skipped (platform failing)"; continue
                try:
                    res = POSTERS[p](str(video), cap[p])
                    row["posts"][p] = res; sent[p] += 1; strikes[p] = 0
                    print(f"  {p}: {res}", flush=True)
                except Exception as e:
                    if any(k in str(e) for k in ("uploadLimitExceeded", "quotaExceeded")):
                        # the platform's own daily limit: stop using it for this run, not an error
                        row["posts"][p] = f"skipped (platform daily limit)"; strikes[p] = 99
                        print(f"  {p}: daily limit reached, skipping it for the rest of this run", flush=True)
                        continue
                    failures += 1; strikes[p] += 1
                    row["posts"][p] = f"FAILED: {e}"
                    print(f"  {p}: FAILED {e}", flush=True)
                    traceback.print_exc()
            # manual single-platform tests (--only) do not mark a match as done for the daily run
            if not a.only and any(not str(v).startswith(("FAILED", "skipped")) for v in row["posts"].values()):
                posted[fid(f)] = {"date": f["date"], "at": dt.datetime.now(tz).isoformat(timespec="minutes"), **row["posts"]}
                POSTED.write_text(json.dumps(posted, ensure_ascii=False, indent=0, sort_keys=True), encoding="utf8")
            elif a.backfill:
                new = {p: v for p, v in row["posts"].items() if str(v).startswith("http")}
                if new:
                    posted[fid(f)].update(new)
                    POSTED.write_text(json.dumps(posted, ensure_ascii=False, indent=0, sort_keys=True), encoding="utf8")
        report.append(row)
    pool.shutdown()
    (out / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf8")
    print("\n" + json.dumps(report, ensure_ascii=False, indent=1))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
