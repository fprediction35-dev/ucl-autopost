"""Three-way merge of data/posted.json, used when two runs saved it at the same time.

python tools/merge_posted.py BASE MINE THEIRS   # writes the merge to THEIRS

BASE  = posted.json this run started from
MINE  = posted.json this run wrote
THEIRS = posted.json now on the branch (another run pushed in between)
Only what this run changed (MINE vs BASE) is applied on top of THEIRS, so neither run's links get lost.
A real link never gets replaced by a FAILED/skipped marker.
"""
import json, sys

BAD = ("FAILED", "skipped", "dry run", "already")


def real(v):
    return bool(v) and not str(v).startswith(BAD)


def merge(base, mine, theirs):
    out = dict(theirs)
    for k, row in mine.items():
        old = base.get(k, {})
        changed = {f: v for f, v in row.items() if old.get(f) != v}
        if not changed:
            continue
        cur = dict(out.get(k, {}))
        for f, v in changed.items():
            if f in ("at", "date") and f in cur:
                continue  # keep the first time the match was posted
            if real(cur.get(f)) and not real(v):
                continue
            cur[f] = v
        out[k] = cur
    return out


if __name__ == "__main__":
    load = lambda p: json.load(open(p, encoding="utf8"))
    base, mine, theirs = (load(p) for p in sys.argv[1:4])
    with open(sys.argv[3], "w", encoding="utf8") as fh:
        fh.write(json.dumps(merge(base, mine, theirs), ensure_ascii=False, indent=0, sort_keys=True))
