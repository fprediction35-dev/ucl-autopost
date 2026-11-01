"""python tools/instagram_auth.py APP_ID APP_SECRET REDIRECT_URI
REDIRECT_URI is your GitHub Pages callback, e.g. https://USER.github.io/ucl-autopost/callback.html"""
import sys, urllib.parse, requests
from _common import save, code_from

app_id, secret, redirect = sys.argv[1:4]
print("1) Bu adresi aç, Instagram hesabınla izin ver:\n" + "https://www.instagram.com/oauth/authorize?" + urllib.parse.urlencode({
    "client_id": app_id, "redirect_uri": redirect, "response_type": "code",
    "scope": "instagram_business_basic,instagram_business_content_publish"}))
code = code_from(input("\n2) Yönlendirildiğin sayfadaki kodu (ya da adresin tamamını) yapıştır: "))
r = requests.post("https://api.instagram.com/oauth/access_token", data={"client_id": app_id, "client_secret": secret,
                  "grant_type": "authorization_code", "redirect_uri": redirect, "code": code})
r.raise_for_status()
short = r.json()["access_token"]
l = requests.get("https://graph.instagram.com/access_token", params={"grant_type": "ig_exchange_token", "client_secret": secret, "access_token": short})
l.raise_for_status()
save({"IG_ACCESS_TOKEN": l.json()["access_token"]})
