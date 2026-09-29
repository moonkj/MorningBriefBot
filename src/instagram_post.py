"""
GitHub Pages에 올라간 카드 이미지 URL들을 Instagram 캐러셀로 게시.

사전 조건:
  - Instagram 계정이 '프로페셔널(비즈니스/크리에이터)' 계정으로 전환되어 있고,
    Facebook 페이지에 연결되어 있어야 함.
  - Meta Developer 앱에서 발급한 IG_USER_ID / IG_ACCESS_TOKEN이 .env에 있어야 함.
  - 이미지 URL은 공개적으로 접근 가능해야 함 (GitHub Pages).

사용법:
    python src/instagram_post.py --urls https://.../card_01.png https://.../card_02.png --caption "..."
"""
import argparse
import os
import time

import requests
from dotenv import load_dotenv

GRAPH_API_VERSION = "v21.0"
GRAPH_BASE = f"https://graph.facebook.com/{GRAPH_API_VERSION}"


def create_carousel_item(ig_user_id: str, access_token: str, image_url: str) -> str:
    resp = requests.post(
        f"{GRAPH_BASE}/{ig_user_id}/media",
        data={
            "image_url": image_url,
            "is_carousel_item": "true",
            "access_token": access_token,
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["id"]


def create_carousel_container(ig_user_id: str, access_token: str, children_ids: list[str], caption: str) -> str:
    resp = requests.post(
        f"{GRAPH_BASE}/{ig_user_id}/media",
        data={
            "media_type": "CAROUSEL",
            "children": ",".join(children_ids),
            "caption": caption,
            "access_token": access_token,
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["id"]


def wait_until_ready(container_id: str, access_token: str, timeout_s: int = 120) -> None:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        resp = requests.get(
            f"{GRAPH_BASE}/{container_id}",
            params={"fields": "status_code", "access_token": access_token},
            timeout=30,
        )
        resp.raise_for_status()
        status = resp.json().get("status_code")
        if status == "FINISHED":
            return
        if status == "ERROR":
            raise RuntimeError(f"Instagram 컨테이너 처리 실패: {container_id}")
        time.sleep(3)
    raise TimeoutError(f"Instagram 컨테이너가 시간 내에 준비되지 않음: {container_id}")


def publish(ig_user_id: str, access_token: str, creation_id: str) -> str:
    resp = requests.post(
        f"{GRAPH_BASE}/{ig_user_id}/media_publish",
        data={"creation_id": creation_id, "access_token": access_token},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["id"]


def post_carousel(image_urls: list[str], caption: str) -> str:
    load_dotenv()
    ig_user_id = os.environ["IG_USER_ID"]
    access_token = os.environ["IG_ACCESS_TOKEN"]

    if not (2 <= len(image_urls) <= 10):
        raise ValueError(f"캐러셀은 2~10장이어야 합니다 (현재 {len(image_urls)}장)")

    children_ids = [create_carousel_item(ig_user_id, access_token, url) for url in image_urls]
    container_id = create_carousel_container(ig_user_id, access_token, children_ids, caption)
    wait_until_ready(container_id, access_token)
    media_id = publish(ig_user_id, access_token, container_id)
    return media_id


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--urls", nargs="+", required=True, help="공개 접근 가능한 이미지 URL 목록")
    parser.add_argument("--caption", default="")
    args = parser.parse_args()

    media_id = post_carousel(args.urls, args.caption)
    print(f"Instagram 게시 완료: media_id={media_id}")


if __name__ == "__main__":
    main()
