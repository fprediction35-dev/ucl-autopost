"""python tools/tiktok_auth.py CLIENT_KEY CLIENT_SECRET REDIRECT_URI"""
import secrets, sys, urllib.parse, requests
from _common import save, code_from

key, secret, redirect = sys.argv[1:4]
print("1) Bu adresi aç, TikTok hesabınla izin ver:\n" + "https://www.tiktok.com/v2/auth/authorize/?" + urllib.parse.urlencode({
    "client_key": key, "scope": "user.info.basic,video.publish", "response_type": "code",
    "redirect_uri": redirect, "state": secrets.token_hex(8)}))
code = urllib.parse.unquote(code_from(input("\n2) Yönlendirildiğin sayfadaki kodu (ya da adresin tamamını) yapıştır: ")))
r = requests.post("https://open.tiktokapis.com/v2/oauth/token/", headers={"Content-Type": "application/x-www-form-urlencoded"},
                  data={"client_key": key, "client_secret": secret, "code": code, "grant_type": "authorization_code", "redirect_uri": redirect})
j = r.json()
if "refresh_token" not in j:
    sys.exit(f"TikTok hata verdi: {j}")
save({"TIKTOK_CLIENT_KEY": key, "TIKTOK_CLIENT_SECRET": secret, "TIKTOK_REFRESH_TOKEN": j["refresh_token"]})
