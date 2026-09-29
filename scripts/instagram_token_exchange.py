"""
Graph API Explorer에서 받은 단기(short-lived) 사용자 토큰을 60일짜리 장기 토큰으로 교환.

사용법:
    python scripts/instagram_token_exchange.py --short-token EAAB...
"""
import argparse
import os

import requests
from dotenv import load_dotenv

GRAPH_BASE = "https://graph.facebook.com/v21.0"


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser()
    parser.add_argument("--short-token", required=True)
    args = parser.parse_args()

    resp = requests.get(
        f"{GRAPH_BASE}/oauth/access_token",
        params={
            "grant_type": "fb_exchange_token",
            "client_id": os.environ["META_APP_ID"],
            "client_secret": os.environ["META_APP_SECRET"],
            "fb_exchange_token": args.short_token,
        },
        timeout=30,
    )
    resp.raise_for_status()
    body = resp.json()
    print("장기 토큰 발급 완료 (만료: 약 60일). .env 의 IG_ACCESS_TOKEN 에 넣으세요:\n")
    print(body["access_token"])


if __name__ == "__main__":
    main()
