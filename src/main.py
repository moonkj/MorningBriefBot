"""
전체 파이프라인 오케스트레이터.
data/brief_data.json 을 읽어서:
  1) 카드뉴스 이미지 생성 (docs/<date>/card_XX.png)
  2) git commit + push, GitHub Pages URL 준비 대기
  3) Instagram 캐러셀 게시
  4) TikTok 포토 게시

사용법:
    python src/main.py --input data/brief_data.json
"""
import argparse
import json
import re
from datetime import date
from pathlib import Path

from generate_cards import generate
from instagram_post import post_carousel
from publish_pages import build_urls, commit_and_push, wait_until_live
from tiktok_post import post_photo_carousel

REPO_ROOT = Path(__file__).resolve().parent.parent


def slugify_date(raw_date: str) -> str:
    match = re.search(r"(\d{4})\D+(\d{1,2})\D+(\d{1,2})", raw_date)
    if match:
        y, m, d = match.groups()
        return f"{int(y):04d}-{int(m):02d}-{int(d):02d}"
    return date.today().isoformat()


def build_caption(data: dict) -> str:
    lines = [data["headline"], ""]
    lines.extend(f"- {p}" for p in data.get("summary_points", []))
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/brief_data.json")
    parser.add_argument(
        "--session", choices=["us", "kr"], required=True,
        help="us: 오전 7시 미국장 브리프, kr: 오후 5시 국내장 브리프 (같은 날짜 폴더 충돌 방지용)",
    )
    parser.add_argument("--skip-instagram", action="store_true")
    parser.add_argument("--skip-tiktok", action="store_true")
    args = parser.parse_args()

    input_path = Path(args.input)
    data = json.loads(input_path.read_text(encoding="utf-8"))

    day_slug = slugify_date(data["date"])
    rel_dir = f"docs/{day_slug}-{args.session}"
    outdir = REPO_ROOT / rel_dir

    print(f"[1/4] 카드 이미지 생성 -> {rel_dir}")
    card_paths = generate(input_path, outdir)
    image_names = [p.name for p in card_paths]

    print("[2/4] git commit + push, GitHub Pages 대기")
    commit_and_push(REPO_ROOT, rel_dir)
    urls = build_urls(rel_dir, image_names)
    for url in urls:
        wait_until_live(url)
    print(f"  URL {len(urls)}개 준비 완료")

    caption = build_caption(data)

    if not args.skip_instagram:
        print("[3/4] Instagram 게시")
        ig_urls = urls[:10]
        media_id = post_carousel(ig_urls, caption)
        print(f"  완료: media_id={media_id}")
    else:
        print("[3/4] Instagram 게시 건너뜀 (--skip-instagram)")

    if not args.skip_tiktok:
        print("[4/4] TikTok 게시")
        tk_urls = urls[:10]
        result = post_photo_carousel(tk_urls, title=data["headline"], description=caption)
        print(f"  완료: {result}")
    else:
        print("[4/4] TikTok 게시 건너뜀 (--skip-tiktok)")


if __name__ == "__main__":
    main()
