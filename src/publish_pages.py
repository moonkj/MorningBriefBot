"""
docs/<date>/ 에 생성된 카드 이미지를 git commit+push 하고,
GitHub Pages에서 실제로 열릴 때까지 기다린 뒤 공개 URL 목록을 돌려준다.

사용법:
    python src/publish_pages.py --dir docs/2026-09-29
"""
import argparse
import os
import subprocess
import time
from pathlib import Path

import requests
from dotenv import load_dotenv


def run(cmd: list[str], cwd: Path) -> None:
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"명령 실패: {' '.join(cmd)}\n{result.stdout}\n{result.stderr}")


def commit_and_push(repo_root: Path, rel_dir: str) -> None:
    run(["git", "add", rel_dir], repo_root)
    result = subprocess.run(
        ["git", "diff", "--cached", "--quiet"], cwd=repo_root
    )
    if result.returncode == 0:
        print("변경 사항 없음 (이미 커밋됨)")
        return
    run(["git", "commit", "-m", f"카드뉴스 이미지: {rel_dir}"], repo_root)
    run(["git", "push"], repo_root)


def wait_until_live(url: str, timeout_s: int = 300, interval_s: int = 5) -> None:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                return
        except requests.RequestException:
            pass
        time.sleep(interval_s)
    raise TimeoutError(f"GitHub Pages가 시간 내에 반영되지 않음: {url}")


def build_urls(rel_dir: str, image_names: list[str]) -> list[str]:
    load_dotenv()
    username = os.environ["GITHUB_USERNAME"]
    repo = os.environ["GITHUB_REPO"]
    base = f"https://{username}.github.io/{repo}/{rel_dir}"
    return [f"{base}/{name}" for name in image_names]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", required=True, help="repo 루트 기준 상대 경로, 예: docs/2026-09-29")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    rel_dir = args.dir.replace("\\", "/")
    abs_dir = repo_root / rel_dir

    image_names = sorted(p.name for p in abs_dir.glob("*.png"))
    if not image_names:
        raise SystemExit(f"이미지가 없습니다: {abs_dir}")

    commit_and_push(repo_root, rel_dir)

    urls = build_urls(rel_dir, image_names)
    print("생성된 URL 목록 (GitHub Pages 반영 대기 중)...")
    for url in urls:
        wait_until_live(url)
        print(f"  준비됨: {url}")

    print("\n".join(urls))


if __name__ == "__main__":
    main()
