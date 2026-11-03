"""YouTube Shorts upload (YouTube Data API v3, resumable upload)."""
import os, requests
from .. import secrets_store as S


def _check(r):
    """raise_for_status, but keep Google's error reason (e.g. uploadLimitExceeded, quotaExceeded) in the message."""
    if not r.ok:
        try:
            err = r.json().get("error", {})
            reasons = ",".join(e.get("reason", "") for e in err.get("errors", [])) or err.get("status", "")
            detail = f"{reasons}: {err.get('message', '')}".strip(": ")
        except Exception:
            detail = r.text[:300]
        raise requests.HTTPError(f"{r.status_code} {detail}", response=r)


def _token():
    r = requests.post("https://oauth2.googleapis.com/token", data={
        "client_id": S.get("YT_CLIENT_ID"), "client_secret": S.get("YT_CLIENT_SECRET"),
        "refresh_token": S.get("YT_REFRESH_TOKEN"), "grant_type": "refresh_token"}, timeout=30)
    r.raise_for_status()
    return r.json()["access_token"]


def post(video, cap):
    tok = _token()
    size = os.path.getsize(video)
    meta = {"snippet": {"title": cap["title"], "description": cap["description"], "tags": cap["tags"], "categoryId": "17"},
            "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False}}
    r = requests.post("https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status",
                      headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json; charset=UTF-8",
                               "X-Upload-Content-Type": "video/mp4", "X-Upload-Content-Length": str(size)},
                      json=meta, timeout=60)
    _check(r)
    with open(video, "rb") as f:
        up = requests.put(r.headers["Location"], data=f, headers={"Authorization": f"Bearer {tok}", "Content-Type": "video/mp4",
                                                                   "Content-Length": str(size)}, timeout=900)
    _check(up)
    v = up.json()
    status = v.get("status", {}).get("privacyStatus")
    note = "" if status == "public" else f" (uploaded as {status}: the Google API project may need an audit before uploads can be public)"
    return f"https://youtube.com/shorts/{v['id']}{note}"
