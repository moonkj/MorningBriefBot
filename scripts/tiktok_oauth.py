"""
TikTok 본인 계정용 access token을 처음 한 번 발급받기 위한 헬퍼.
로컬에서 임시 웹서버를 띄워 OAuth redirect를 받은 뒤 토큰으로 교환한다.

사전 준비:
  - TikTok Developer 콘솔에서 앱을 만들고 Content Posting API를 추가
  - 앱 설정의 Redirect URI에 정확히 http://localhost:8787/callback 를 등록
  - 아래 CLIENT_KEY / CLIENT_SECRET을 본인 앱 값으로 교체 (또는 환경변수로 전달)

사용법:
    python scripts/tiktok_oauth.py
    (브라우저가 열리면 본인 TikTok 계정으로 로그인/동의 -> 터미널에 토큰 출력)
"""
import http.server
import os
import urllib.parse
import webbrowser

import requests
from dotenv import load_dotenv

REDIRECT_URI = "http://localhost:8787/callback"
SCOPES = "user.info.basic,video.publish"
AUTH_URL = "https://www.tiktok.com/v2/auth/authorize/"
TOKEN_URL = "https://open.tiktokapis.com/v2/oauth/token/"

_received_code: dict[str, str] = {}


class CallbackHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        code = params.get("code", [None])[0]
        if code:
            _received_code["code"] = code
            self.send_response(200)
            self.end_headers()
            self.wfile.write("인증 완료. 이 창을 닫고 터미널을 확인하세요.".encode("utf-8"))
        else:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"code parameter missing")

    def log_message(self, format: str, *args) -> None:
        pass


def main() -> None:
    load_dotenv()
    client_key = os.environ["TIKTOK_CLIENT_KEY"]
    client_secret = os.environ["TIKTOK_CLIENT_SECRET"]

    auth_params = {
        "client_key": client_key,
        "scope": SCOPES,
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
        "state": "morning-brief-bot",
    }
    url = f"{AUTH_URL}?{urllib.parse.urlencode(auth_params)}"
    print(f"브라우저에서 아래 URL을 열어 로그인/동의하세요 (자동으로 열립니다):\n{url}\n")
    webbrowser.open(url)

    server = http.server.HTTPServer(("localhost", 8787), CallbackHandler)
    while "code" not in _received_code:
        server.handle_request()

    code = _received_code["code"]
    resp = requests.post(
        TOKEN_URL,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={
            "client_key": client_key,
            "client_secret": client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": REDIRECT_URI,
        },
        timeout=30,
    )
    resp.raise_for_status()
    print("\n토큰 발급 완료. 아래 값을 .env 의 TIKTOK_ACCESS_TOKEN 에 넣으세요:\n")
    print(resp.json())


if __name__ == "__main__":
    main()
