"""Reads credentials from environment variables and saves refreshed tokens back.

On GitHub Actions, refreshed tokens (Instagram, TikTok) are written back to the repository's
Actions secrets with the GitHub API, using the GH_PAT secret. Locally they go to .tokens.json.
"""
import base64, json, os, pathlib, requests

LOCAL = pathlib.Path(__file__).resolve().parent.parent / ".tokens.json"


def get(name, required=True):
    val = os.environ.get(name)
    if not val and LOCAL.exists():
        val = json.loads(LOCAL.read_text()).get(name)
    if required and not val:
        raise RuntimeError(f"Missing credential: {name}")
    return val


def save(name, value):
    os.environ[name] = value
    repo, pat = os.environ.get("GITHUB_REPOSITORY"), os.environ.get("GH_PAT")
    if repo and pat:
        from nacl import encoding, public
        h = {"Authorization": f"Bearer {pat}", "Accept": "application/vnd.github+json"}
        key = requests.get(f"https://api.github.com/repos/{repo}/actions/secrets/public-key", headers=h, timeout=30)
        key.raise_for_status()
        k = key.json()
        box = public.SealedBox(public.PublicKey(k["key"].encode(), encoding.Base64Encoder()))
        enc = base64.b64encode(box.encrypt(value.encode())).decode()
        r = requests.put(f"https://api.github.com/repos/{repo}/actions/secrets/{name}", headers=h,
                         json={"encrypted_value": enc, "key_id": k["key_id"]}, timeout=30)
        r.raise_for_status()
        print(f"  saved refreshed {name} to GitHub secrets")
    else:
        data = json.loads(LOCAL.read_text()) if LOCAL.exists() else {}
        data[name] = value
        LOCAL.write_text(json.dumps(data, indent=1))
        print(f"  saved refreshed {name} to {LOCAL.name}")
