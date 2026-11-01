"""X (Twitter) post with video. API v2 chunked media upload + POST /2/tweets, OAuth 1.0a user context."""
import os, time, requests
from ..oauth1 import OAuth1
from .. import secrets_store as S

API = "https://api.x.com/2"
SEG = 4 * 1024 * 1024


def post(video, text):
    auth = OAuth1(S.get("X_API_KEY"), S.get("X_API_SECRET"), S.get("X_ACCESS_TOKEN"), S.get("X_ACCESS_SECRET"))
    size = os.path.getsize(video)
    r = requests.post(f"{API}/media/upload/initialize", auth=auth, timeout=60,
                      json={"media_type": "video/mp4", "total_bytes": size, "media_category": "tweet_video"})
    if not r.ok:
        raise RuntimeError(f"X init failed: {r.status_code} {r.text[:300]}")
    mid = r.json()["data"]["id"]
    with open(video, "rb") as f:
        i = 0
        while True:
            chunk = f.read(SEG)
            if not chunk:
                break
            a = requests.post(f"{API}/media/upload/{mid}/append", auth=auth, timeout=300,
                              data={"segment_index": str(i)}, files={"media": ("chunk", chunk, "application/octet-stream")})
            if not a.ok:
                raise RuntimeError(f"X append failed: {a.status_code} {a.text[:300]}")
            i += 1
    fin = requests.post(f"{API}/media/upload/{mid}/finalize", auth=auth, timeout=60)
    if not fin.ok:
        raise RuntimeError(f"X finalize failed: {fin.status_code} {fin.text[:300]}")
    proc = fin.json().get("data", {}).get("processing_info")
    while proc and proc.get("state") in ("pending", "in_progress"):
        time.sleep(proc.get("check_after_secs", 5))
        st = requests.get(f"{API}/media/upload", auth=auth, params={"command": "STATUS", "media_id": mid}, timeout=30)
        proc = st.json().get("data", {}).get("processing_info")
    if proc and proc.get("state") == "failed":
        raise RuntimeError(f"X video processing failed: {proc}")
    t = requests.post(f"{API}/tweets", auth=auth, json={"text": text, "media": {"media_ids": [mid]}}, timeout=60)
    if not t.ok:
        raise RuntimeError(f"X post failed: {t.status_code} {t.text[:300]}")
    return f"https://x.com/i/status/{t.json()['data']['id']}"
