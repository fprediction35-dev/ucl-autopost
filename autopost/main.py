"""Daily run: pick today's Champions League fixtures, render a simulation video for each, post to every enabled platform.

python -m autopost.main                    # today's fixtures (in config timezone)
python -m autopost.main --date 2026-11-03  # a specific day
python -m autopost.main --dry-run          # render videos and captions, post nothing
python -m autopost.main --only youtube,x   # limit platforms for this run
"""
import argparse, datetime as dt, json, pathlib, re, subprocess, sys, time, traceback
from zoneinfo import ZoneInfo
from . import captions, hosting
from .platforms import youtube, instagram, tiktok, x

ROOT = pathlib.Path(__file__).resolve().parent.parent
POSTERS = {"youtube": youtube.post, "instagram": instagram.post, "tiktok": tiktok.post, "x": x.post}


def slug(s):
    import unicodedata
    s = "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def pick(fixtures, cfg, elo):
    pri = cfg.get("priority_teams", [])
    def score(f):
        p = 1 if (f["home"] in pri or f["away"] in pri) else 0
        return (-p, -(elo.get(f["home"], 1500) + elo.get(f["away"], 1500)))
    return sorted(fixtures, key=score)[: cfg.get("max_videos_per_day", 4)]


def elo_table():
    html = (ROOT / "sim/index.html").read_text(encoding="utf8")
    data = json.loads(html.split("const DATA=", 1)[1].split(";\n", 1)[0])
    return {k: v["elo"] for k, v in data["teams"].items()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date"); ap.add_argument("--dry-run", action="store_true"); ap.add_argument("--only")
    ap.add_argument("--limit", type=int)
    a = ap.parse_args()
    cfg = json.loads((ROOT / "config.json").read_text(encoding="utf8"))
    day = a.date or dt.datetime.now(ZoneInfo(cfg.get("timezone", "UTC"))).date().isoformat()
    fixtures = [f for f in json.loads((ROOT / "data/fixtures.json").read_text(encoding="utf8")) if f["date"] == day]
    if a.limit:
        cfg["max_videos_per_day"] = a.limit
    todo = pick(fixtures, cfg, elo_table())
    print(f"{day}: {len(fixtures)} fixtures, posting {len(todo)}")
    if not todo:
        return 0
    platforms = [p for p, on in cfg["platforms"].items() if on]
    if a.only:
        platforms = [p for p in platforms if p in a.only.split(",")]
    out = ROOT / "out" / day
    out.mkdir(parents=True, exist_ok=True)
    report, failures = [], 0
    limits = cfg.get("platform_limits", {})
    sent = {p: 0 for p in platforms}
    for n, f in enumerate(todo):
        name = f"{slug(f['home'])}-vs-{slug(f['away'])}"
        video = out / f"{name}.mp4"
        print(f"\n=== {f['home']} vs {f['away']} ===")
        subprocess.run(["node", str(ROOT / "render.js"), "--home", f["home"], "--away", f["away"], "--out", str(video),
                        "--dur", str(cfg.get("duration_seconds", 60)), "--music", cfg.get("music", "hype"),
                        "--handle", cfg.get("handle", "")], check=True)
        info = json.loads(video.with_suffix(".json").read_text())
        cap = captions.build(info, f, cfg)
        (out / f"{name}.captions.json").write_text(json.dumps(cap, ensure_ascii=False, indent=1), encoding="utf8")
        row = {"match": f"{f['home']} vs {f['away']}", "simulated": "-".join(map(str, info["final"])), "posts": {}}
        if a.dry_run:
            row["posts"] = {p: "dry run" for p in platforms}
        else:
            public_url = None
            for p in platforms:
                if p in limits and sent[p] >= limits[p]:
                    row["posts"][p] = "skipped (daily limit)"
                    continue
                try:
                    res = POSTERS[p](str(video), cap[p])
                    row["posts"][p] = res
                    sent[p] += 1
                    print(f"  {p}: {res}")
                except Exception as e:
                    failures += 1
                    row["posts"][p] = f"FAILED: {e}"
                    print(f"  {p}: FAILED {e}")
                    traceback.print_exc()
        report.append(row)
        if not a.dry_run and n < len(todo) - 1:
            time.sleep(60 * cfg.get("post_gap_minutes", 20))
    (out / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf8")
    print("\n" + json.dumps(report, ensure_ascii=False, indent=1))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
