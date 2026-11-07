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


API = "https://www.googleapis.com/youtube/v3"
_playlists = {}


def _playlist(tok, title):
    """id of the channel's public playlist with this title, created on first use."""
    h = {"Authorization": f"Bearer {tok}"}
    if not _playlists:
        page = ""
        while True:
            r = requests.get(f"{API}/playlists", headers=h, timeout=30,
                             params={"part": "snippet", "mine": "true", "maxResults": 50, "pageToken": page})
            _check(r)
            j = r.json()
            for it in j.get("items", []):
                _playlists[it["snippet"]["title"]] = it["id"]
            page = j.get("nextPageToken")
            if not page:
                break
        _playlists.setdefault("", "")  # marks the channel's playlists as listed for this run
    if title not in _playlists:
        r = requests.post(f"{API}/playlists?part=snippet,status", headers=h, timeout=30, json={
            "snippet": {"title": title, "description": f"{title}: every match simulated before kick-off."},
            "status": {"privacyStatus": "public"}})
        _check(r)
        _playlists[title] = r.json()["id"]
    return _playlists[title]


def _extras(tok, vid, cap):
    """League playlist and a channel comment. Best effort: needs the youtube.force-ssl scope (tools/youtube_auth.py);
    a failure here never fails the upload."""
    h = {"Authorization": f"Bearer {tok}", "Content-Type": "application/json; charset=UTF-8"}
    if cap.get("playlist"):
        try:
            pl = _playlist(tok, cap["playlist"])
            _check(requests.post(f"{API}/playlistItems?part=snippet", headers=h, timeout=30, json={
                "snippet": {"playlistId": pl, "resourceId": {"kind": "youtube#video", "videoId": vid}}}))
        except Exception as e:
            print(f"  youtube: playlist skipped: {e}", flush=True)
    if cap.get("comment"):
        try:
            _check(requests.post(f"{API}/commentThreads?part=snippet", headers=h, timeout=30, json={
                "snippet": {"videoId": vid, "topLevelComment": {"snippet": {"textOriginal": cap["comment"]}}}}))
        except Exception as e:
            print(f"  youtube: comment skipped: {e}", flush=True)


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
    _extras(tok, v["id"], cap)
    status = v.get("status", {}).get("privacyStatus")
    note = "" if status == "public" else f" (uploaded as {status}: the Google API project may need an audit before uploads can be public)"
    return f"https://youtube.com/shorts/{v['id']}{note}"
