import json, pathlib, urllib.parse

OUT = pathlib.Path(__file__).resolve().parent.parent / ".tokens.json"


def save(values):
    data = json.loads(OUT.read_text()) if OUT.exists() else {}
    data.update(values)
    OUT.write_text(json.dumps(data, indent=1))
    print(f"\nSaved to {OUT.name}. Add each of these as a GitHub Actions secret (Settings > Secrets and variables > Actions):")
    for k, v in values.items():
        print(f"  {k} = {v}")


def code_from(pasted):
    pasted = pasted.strip()
    if pasted.startswith("http"):
        q = urllib.parse.parse_qs(urllib.parse.urlsplit(pasted).query)
        pasted = q.get("code", [""])[0]
    return pasted.split("#")[0]
