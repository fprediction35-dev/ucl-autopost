"""Instagram Reels (Instagram API with Instagram Login). Instagram fetches the video from a public URL."""
import time, requests
from .. import secrets_store as S

VER = "v23.0"
BASE = f"https://graph.instagram.com/{VER}"


def _refresh():
    tok = S.get("IG_ACCESS_TOKEN")
    r = requests.get("https://graph.instagram.com/refresh_access_token",
                     params={"grant_type": "ig_refresh_token", "access_token": tok}, timeout=30)
    if r.ok and r.json().get("access_token") and r.json()["access_token"] != tok:
        S.save("IG_ACCESS_TOKEN", r.json()["access_token"])
        return r.json()["access_token"]
    return tok


def post(video_url, caption):
    tok = _refresh()
    me = requests.get(f"{BASE}/me", params={"fields": "user_id,username", "access_token": tok}, timeout=30)
    me.raise_for_status()
    uid = me.json()["user_id"]
    c = requests.post(f"{BASE}/{uid}/media", data={"media_type": "REELS", "video_url": video_url, "caption": caption,
                                                   "share_to_feed": "true", "access_token": tok}, timeout=60)
    c.raise_for_status()
    cid = c.json()["id"]
    for _ in range(40):  # up to ~10 minutes
        time.sleep(15)
        st = requests.get(f"{BASE}/{cid}", params={"fields": "status_code,status", "access_token": tok}, timeout=30).json()
        if st.get("status_code") == "FINISHED":
            break
        if st.get("status_code") in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"Instagram processing failed: {st}")
    else:
        raise RuntimeError("Instagram processing timed out")
    p = requests.post(f"{BASE}/{uid}/media_publish", data={"creation_id": cid, "access_token": tok}, timeout=60)
    p.raise_for_status()
    mid = p.json()["id"]
    link = requests.get(f"{BASE}/{mid}", params={"fields": "permalink", "access_token": tok}, timeout=30).json().get("permalink")
    return link or f"instagram media {mid}"
