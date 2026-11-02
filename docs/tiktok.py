"""TikTok (Content Posting API, Direct Post, FILE_UPLOAD). Until the app passes TikTok's audit, posts are private (SELF_ONLY)."""
import os, time, requests
from .. import secrets_store as S

API = "https://open.tiktokapis.com/v2"


def _token():
    r = requests.post(f"{API}/oauth/token/", headers={"Content-Type": "application/x-www-form-urlencoded"}, data={
        "client_key": S.get("TIKTOK_CLIENT_KEY"), "client_secret": S.get("TIKTOK_CLIENT_SECRET"),
        "grant_type": "refresh_token", "refresh_token": S.get("TIKTOK_REFRESH_TOKEN")}, timeout=30)
    r.raise_for_status()
    j = r.json()
    if "access_token" not in j:
        raise RuntimeError(f"TikTok token refresh failed: {j}")
    if j.get("refresh_token") and j["refresh_token"] != S.get("TIKTOK_REFRESH_TOKEN"):
        S.save("TIKTOK_REFRESH_TOKEN", j["refresh_token"])
    return j["access_token"]


def _ok(r):
    j = r.json()
    if r.status_code >= 400 or j.get("error", {}).get("code") not in (None, "ok"):
        raise RuntimeError(f"TikTok error: {j}")
    return j.get("data", {})


def post(video, caption):
    tok = _token()
    h = {"Authorization": f"Bearer {tok}", "Content-Type": "application/json; charset=UTF-8"}
    info = _ok(requests.post(f"{API}/post/publish/creator_info/query/", headers=h, timeout=30))
    opts = info.get("privacy_level_options", [])
    import json, pathlib
    cfg = json.loads((pathlib.Path(__file__).resolve().parents[2] / "config.json").read_text(encoding="utf8"))
    want = cfg.get("tiktok_privacy", "SELF_ONLY")  # unaudited apps may only post SELF_ONLY
    privacy = want if want in opts else ("SELF_ONLY" if "SELF_ONLY" in opts else (opts[0] if opts else "SELF_ONLY"))
    size = os.path.getsize(video)
    chunk = size if size <= 64 * 1024 * 1024 else 10 * 1024 * 1024
    count = 1 if chunk == size else size // chunk
    init = _ok(requests.post(f"{API}/post/publish/video/init/", headers=h, timeout=60, json={
        "post_info": {"title": caption, "privacy_level": privacy, "disable_comment": False, "disable_duet": False,
                      "disable_stitch": False, "video_cover_timestamp_ms": 4000},
        "source_info": {"source": "FILE_UPLOAD", "video_size": size, "chunk_size": chunk, "total_chunk_count": count}}))
    with open(video, "rb") as f:
        for i in range(count):
            start = i * chunk
            end = size - 1 if i == count - 1 else start + chunk - 1
            f.seek(start)
            body = f.read(end - start + 1)
            u = requests.put(init["upload_url"], data=body, timeout=600, headers={
                "Content-Type": "video/mp4", "Content-Length": str(len(body)), "Content-Range": f"bytes {start}-{end}/{size}"})
            if u.status_code not in (200, 201, 206):
                raise RuntimeError(f"TikTok upload failed: {u.status_code} {u.text[:300]}")
    for _ in range(40):
        time.sleep(15)
        st = _ok(requests.post(f"{API}/post/publish/status/fetch/", headers=h, json={"publish_id": init["publish_id"]}, timeout=30))
        if st.get("status") == "PUBLISH_COMPLETE":
            return f"TikTok post published ({privacy})"
        if st.get("status") == "FAILED":
            raise RuntimeError(f"TikTok publish failed: {st}")
    return f"TikTok upload sent, still processing ({privacy})"
