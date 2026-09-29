"""
GitHub Pages에 올라간 카드 이미지 URL들을 TikTok 포토(캐러셀) 게시물로 업로드.

사전 조건:
  - TikTok Developer 앱에 Content Posting API 스코프(video.publish 등)가 추가되어 있고,
    본인 TikTok 계정으로 OAuth 인가를 받아 TIKTOK_ACCESS_TOKEN을 발급받아야 함.
  - 앱이 아직 심사(App Review)를 통과하지 않았다면 privacy_level은 SELF_ONLY만 가능
    (본인 계정에서만 보이는 비공개/초안 상태).
  - source.PULL_FROM_URL을 쓰려면 TikTok Developer 콘솔에서 이미지가 호스팅되는
    도메인(GitHub Pages 도메인)의 소유권을 사전에 검증해야 함.

사용법:
    python src/tiktok_post.py --urls https://.../card_01.png https://.../card_02.png --title "..."
"""
import argparse
import os
import time

import requests
from dotenv import load_dotenv

API_BASE = "https://open.tiktokapis.com/v2"


def init_photo_post(access_token: str, image_urls: list[str], title: str, description: str, privacy_level: str) -> str:
    resp = requests.post(
        f"{API_BASE}/post/publish/content/init/",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json; charset=UTF-8",
        },
        json={
            "post_info": {
                "title": title,
                "description": description,
                "privacy_level": privacy_level,
                "disable_comment": False,
            },
            "source_info": {
                "source": "PULL_FROM_URL",
                "photo_cover_index": 0,
                "photo_images": image_urls,
            },
            "post_mode": "DIRECT_POST",
            "media_type": "PHOTO",
        },
        timeout=30,
    )
    resp.raise_for_status()
    body = resp.json()
    if body.get("error", {}).get("code") not in (None, "ok"):
        raise RuntimeError(f"TikTok init 실패: {body['error']}")
    return body["data"]["publish_id"]


def poll_status(access_token: str, publish_id: str, timeout_s: int = 120) -> dict:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        resp = requests.post(
            f"{API_BASE}/post/publish/status/fetch/",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json; charset=UTF-8",
            },
            json={"publish_id": publish_id},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()["data"]
        status = data.get("status")
        if status in ("PUBLISH_COMPLETE", "FAILED"):
            return data
        time.sleep(3)
    raise TimeoutError(f"TikTok 게시 상태 확인 시간 초과: {publish_id}")


def post_photo_carousel(image_urls: list[str], title: str, description: str = "") -> dict:
    load_dotenv()
    access_token = os.environ["TIKTOK_ACCESS_TOKEN"]
    privacy_level = os.environ.get("TIKTOK_PRIVACY_LEVEL", "SELF_ONLY")

    publish_id = init_photo_post(access_token, image_urls, title, description, privacy_level)
    result = poll_status(access_token, publish_id)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--urls", nargs="+", required=True, help="공개 접근 가능한 이미지 URL 목록")
    parser.add_argument("--title", required=True)
    parser.add_argument("--description", default="")
    args = parser.parse_args()

    result = post_photo_carousel(args.urls, args.title, args.description)
    print(f"TikTok 게시 결과: {result}")


if __name__ == "__main__":
    main()
