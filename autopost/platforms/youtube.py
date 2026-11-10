"""YouTube Shorts upload (YouTube Data API v3, resumable upload)."""
import os, time, requests
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
            for i in range(3):  # a just-created playlist can answer 409 SERVICE_UNAVAILABLE for a few seconds
                r = requests.post(f"{API}/playlistItems?part=snippet", headers=h, timeout=30, json={
                    "snippet": {"playlistId": pl, "resourceId": {"kind": "youtube#video", "videoId": vid}}})
                if r.ok or r.status_code not in (409, 500, 503) or i == 2:
                    break
                time.sleep(5)
            _check(r)
        except Exception as e:
            print(f"  youtube: playlist skipped: {e}", flush=True)
    if cap.get("comment"):
        try:
            _check(requests.post(f"{API}/commentThreads?part=snippet", headers=h, timeout=30, json={
                "snippet": {"videoId": vid, "topLevelComment": {"snippet": {"textOriginal": cap["comment"]}}}}))
        except Exception as e:
            print(f"  youtube: comment skipped: {e}", flush=True)


_channel_ok = []


def _check_channel(tok):
    """Refuse to upload unless the token belongs to the channel named in config.json (youtube_channel). A reconnect
    that picks another channel of the same Google account would otherwise post there silently."""
    if _channel_ok:
        return
    import json, pathlib
    cfg = json.loads((pathlib.Path(__file__).resolve().parents[2] / "config.json").read_text(encoding="utf8"))
    want, want_id = cfg.get("youtube_channel"), cfg.get("youtube_channel_id")
    r = requests.get(f"{API}/channels", headers={"Authorization": f"Bearer {tok}"}, timeout=30,
                     params={"part": "snippet", "mine": "true"})
    _check(r)
    got = [(it["id"], it["snippet"]["title"]) for it in r.json().get("items", [])]
    ok = [c for c in got if c[0] == want_id] if want_id else [c for c in got if c[1] == want]
    if not ok:
        # "wrong YouTube channel" is matched in main.py: the run stops using YouTube instead of retrying
        raise RuntimeError(f"wrong YouTube channel: connected to {[t for _, t in got] or 'none'}, expected '{want}'. "
                           f"Run 'Connect YouTube' again and pick '{want}' on Google's channel chooser.")
    print(f"  youtube: channel check ok: {ok[0][1]} ({ok[0][0]})", flush=True)
    _channel_ok.append(True)


def _sent_bytes(session, tok, size):
    """Ask the resumable session how much it has. Returns the video resource when the upload is already complete,
    otherwise the byte offset to resume from."""
    r = requests.put(session, headers={"Authorization": f"Bearer {tok}", "Content-Length": "0",
                                       "Content-Range": f"bytes */{size}"}, timeout=60)
    if r.status_code in (200, 201):
        return r.json()
    if r.status_code != 308:
        _check(r)
        raise requests.HTTPError(f"{r.status_code} unexpected resumable status", response=r)
    rng = r.headers.get("Range")  # "bytes=0-12345"; absent when nothing arrived yet
    return int(rng.split("-")[1]) + 1 if rng else 0


def _send(session, tok, video, size, tries=4):
    """PUT the file to the resumable session. A dropped connection (SSL EOF, reset, timeout) resumes from the byte
    YouTube last stored instead of failing, so the same video is never left half-uploaded or uploaded twice."""
    start = 0
    for attempt in range(tries):
        try:
            with open(video, "rb") as f:
                f.seek(start)
                h = {"Authorization": f"Bearer {tok}", "Content-Type": "video/mp4", "Content-Length": str(size - start)}
                if start:
                    h["Content-Range"] = f"bytes {start}-{size - 1}/{size}"
                up = requests.put(session, data=f, headers=h, timeout=900)
            if up.status_code in (500, 502, 503, 504) and attempt < tries - 1:
                raise requests.ConnectionError(f"{up.status_code} from upload server")
            _check(up)
            return up.json()
        except (requests.ConnectionError, requests.Timeout) as e:
            if attempt == tries - 1:
                raise
            wait = 5 * 2 ** attempt
            print(f"  youtube: upload interrupted ({str(e)[:120]}), resuming in {wait}s", flush=True)
            time.sleep(wait)
            for _ in range(3):
                try:
                    got = _sent_bytes(session, tok, size)
                    break
                except (requests.ConnectionError, requests.Timeout):
                    time.sleep(wait)
            else:
                continue  # status query kept failing: retry the PUT from the last known offset
            if isinstance(got, dict):
                return got
            start = got
            print(f"  youtube: resuming at {start}/{size} bytes", flush=True)


def post(video, cap):
    tok = _token()
    _check_channel(tok)
    size = os.path.getsize(video)
    meta = {"snippet": {"title": cap["title"], "description": cap["description"], "tags": cap["tags"], "categoryId": "17"},
            "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False}}
    r = requests.post("https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status",
                      headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json; charset=UTF-8",
                               "X-Upload-Content-Type": "video/mp4", "X-Upload-Content-Length": str(size)},
                      json=meta, timeout=60)
    _check(r)
    v = _send(r.headers["Location"], tok, video, size)
    _extras(tok, v["id"], cap)
    status = v.get("status", {}).get("privacyStatus")
    note = "" if status == "public" else f" (uploaded as {status}: the Google API project may need an audit before uploads can be public)"
    return f"https://youtube.com/shorts/{v['id']}{note}"
