"""Minimal OAuth 1.0a (HMAC-SHA1) signer for requests. JSON and multipart bodies are not part of the signature."""
import base64, hashlib, hmac, secrets, time, urllib.parse
import requests


def _q(s):
    return urllib.parse.quote(str(s), safe="~-._")


class OAuth1(requests.auth.AuthBase):
    def __init__(self, ck, cs, tk, ts):
        self.ck, self.cs, self.tk, self.ts = ck, cs, tk, ts

    def __call__(self, r):
        url = urllib.parse.urlsplit(r.url)
        base_url = f"{url.scheme}://{url.netloc}{url.path}"
        params = urllib.parse.parse_qsl(url.query, keep_blank_values=True)
        ctype = r.headers.get("Content-Type", "")
        if r.body and ctype.startswith("application/x-www-form-urlencoded"):
            body = r.body.decode() if isinstance(r.body, bytes) else r.body
            params += urllib.parse.parse_qsl(body, keep_blank_values=True)
        oa = {"oauth_consumer_key": self.ck, "oauth_nonce": secrets.token_hex(16), "oauth_signature_method": "HMAC-SHA1",
              "oauth_timestamp": str(int(time.time())), "oauth_token": self.tk, "oauth_version": "1.0"}
        allp = sorted((_q(k), _q(v)) for k, v in params + list(oa.items()))
        base = "&".join([r.method.upper(), _q(base_url), _q("&".join(f"{k}={v}" for k, v in allp))])
        key = f"{_q(self.cs)}&{_q(self.ts)}"
        oa["oauth_signature"] = base64.b64encode(hmac.new(key.encode(), base.encode(), hashlib.sha1).digest()).decode()
        r.headers["Authorization"] = "OAuth " + ", ".join(f'{_q(k)}="{_q(v)}"' for k, v in sorted(oa.items()))
        return r
