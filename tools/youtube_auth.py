"""Run on your own computer once: python tools/youtube_auth.py CLIENT_ID CLIENT_SECRET
Opens Google sign-in, then prints YT_CLIENT_ID / YT_CLIENT_SECRET / YT_REFRESH_TOKEN."""
import http.server, sys, urllib.parse, webbrowser, requests
from _common import save

cid, secret = sys.argv[1], sys.argv[2]
redirect = "http://localhost:8765"
url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode({
    "client_id": cid, "redirect_uri": redirect, "response_type": "code", "access_type": "offline", "prompt": "consent",
    "scope": "https://www.googleapis.com/auth/youtube.upload"})
code = {}


class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        code["v"] = urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query).get("code", [""])[0]
        self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8"); self.end_headers()
        self.wfile.write("Tamam, bu pencereyi kapatabilirsin.".encode())

    def log_message(self, *a):
        pass


print("Tarayıcıda Google girişi açılıyor. Açılmazsa bu adresi aç:\n" + url)
webbrowser.open(url)
srv = http.server.HTTPServer(("localhost", 8765), H)
while not code.get("v"):
    srv.handle_request()
r = requests.post("https://oauth2.googleapis.com/token", data={"code": code["v"], "client_id": cid, "client_secret": secret,
                                                                "redirect_uri": redirect, "grant_type": "authorization_code"})
r.raise_for_status()
save({"YT_CLIENT_ID": cid, "YT_CLIENT_SECRET": secret, "YT_REFRESH_TOKEN": r.json()["refresh_token"]})
