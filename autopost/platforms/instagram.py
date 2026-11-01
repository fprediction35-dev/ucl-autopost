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


def post(video, caption):
    tok = S.get("IG_ACCESS_TOKEN")
    ig = _ig_id()
    c = requests.post(f"{GRAPH}/{ig}/media", timeout=60, data={
        "media_type": "REELS", "upload_type": "resumable", "caption": caption,
        "share_to_feed": "true", "access_token": tok})
    if not c.ok:
        raise RuntimeError(f"Instagram container failed: {c.status_code} {c.text[:400]}")
    cid = c.json()["id"]
    size = os.path.getsize(video)
    with open(video, "rb") as f:
        up = requests.post(f"https://rupload.facebook.com/ig-api-upload/{VER}/{cid}", data=f, timeout=900, headers={
            "Authorization": f"OAuth {tok}", "offset": "0", "file_size": str(size)})
    if not up.ok:
        raise RuntimeError(f"Instagram upload failed: {up.status_code} {up.text[:400]}")
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
