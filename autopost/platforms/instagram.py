"""Instagram Reels via the Instagram API with Unified login (Facebook Login for Business).

Uses a system-user access token (never expires) from the business portfolio and the
Instagram account ID from config.json ("instagram_user_id"). The video file is sent
directly with Meta's resumable upload, so no public video URL is needed.
"""
import json, os, pathlib, time, requests
from .. import secrets_store as S

VER = "v23.0"
GRAPH = f"https://graph.facebook.com/{VER}"


def _ig_id():
    cfg = json.loads((pathlib.Path(__file__).resolve().parents[2] / "config.json").read_text(encoding="utf8"))
    ig = str(cfg.get("instagram_user_id") or os.environ.get("IG_USER_ID") or "").strip()
    if not ig:
        raise RuntimeError("instagram_user_id is missing in config.json")
    return ig


def _container(ig, tok, fields, tags):
    """Create the Reels container, tagging the clubs' accounts; if Instagram refuses the tags, post without them."""
    if tags:
        c = requests.post(f"{GRAPH}/{ig}/media", timeout=60, data=dict(fields, access_token=tok,
                          user_tags=json.dumps([{"username": u} for u in tags])))
        if c.ok:
            return c
        print(f"  instagram: tags {tags} refused ({c.status_code} {c.text[:200]}), posting without them", flush=True)
    return requests.post(f"{GRAPH}/{ig}/media", timeout=60, data=dict(fields, access_token=tok))


def post(video, caption):
    tags = []
    if isinstance(caption, dict):
        caption, tags = caption["caption"], caption.get("user_tags", [])
    tok = S.get("IG_ACCESS_TOKEN")
    ig = _ig_id()
    c = _container(ig, tok, {"media_type": "REELS", "upload_type": "resumable", "caption": caption, "share_to_feed": "true"}, tags)
    if not c.ok:
        raise RuntimeError(f"Instagram container failed: {c.status_code} {c.text[:400]}")
    cid = c.json()["id"]
    size = os.path.getsize(video)
    rup = f"https://rupload.facebook.com/ig-api-upload/{VER}/{cid}"
    with open(video, "rb") as f:
        body = f.read()
    up = requests.post(rup, data=body, timeout=900, headers={
        "Authorization": f"OAuth {tok}", "offset": "0", "file_size": str(size),
        "Content-Type": "application/octet-stream"})
    if not up.ok:
        # Fallback: classic Reels upload where Meta downloads the file from a public URL.
        # GitHub release links redirect to a signed storage URL; Meta needs the final URL.
        print(f"  instagram: direct upload refused ({up.status_code} {up.text[:200]}), trying public URL")
        from .. import hosting
        import datetime as dt
        url = hosting.publish(video, dt.date.today().isoformat())
        r = requests.head(url, allow_redirects=False, timeout=30)
        final = r.headers.get("Location", url)
        c = _container(ig, tok, {"media_type": "REELS", "video_url": final, "caption": caption, "share_to_feed": "true"}, tags)
        if not c.ok:
            raise RuntimeError(f"Instagram container (URL) failed: {c.status_code} {c.text[:400]}")
        cid = c.json()["id"]
    for _ in range(40):  # up to ~10 minutes of processing
        time.sleep(15)
        st = requests.get(f"{GRAPH}/{cid}", params={"fields": "status_code,status", "access_token": tok}, timeout=30).json()
        if st.get("status_code") == "FINISHED":
            break
        if st.get("status_code") in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"Instagram processing failed: {st}")
    else:
        raise RuntimeError("Instagram processing timed out")
    p = requests.post(f"{GRAPH}/{ig}/media_publish", data={"creation_id": cid, "access_token": tok}, timeout=60)
    if not p.ok:
        raise RuntimeError(f"Instagram publish failed: {p.status_code} {p.text[:400]}")
    mid = p.json()["id"]
    link = requests.get(f"{GRAPH}/{mid}", params={"fields": "permalink", "access_token": tok}, timeout=30).json().get("permalink")
    return link or f"instagram media {mid}"
