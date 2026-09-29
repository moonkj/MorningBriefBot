"""
brief_data.json (Claude가 예약 작업에서 채우는 구조화 데이터) -> 카드뉴스 PNG 이미지들.

사용법:
    python src/generate_cards.py --input data/brief_data.json --outdir docs/2026-09-29
"""
import argparse
import json
import os
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

CANVAS_W, CANVAS_H = 1080, 1350
MARGIN = 90

BG = "#FCFCFB"
INK = "#2E2C27"
INK_SOFT = "#6B6A63"
INK_GREY = "#B4B3A8"
CLAY = "#C6613F"
HAIRLINE = "#E4E3DC"

FONT_DIR = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"
FONT_BOLD = FONT_DIR / "malgunbd.ttf"
FONT_REGULAR = FONT_DIR / "malgun.ttf"


def load_font(bold: bool, size: int) -> ImageFont.FreeTypeFont:
    path = FONT_BOLD if bold else FONT_REGULAR
    if not path.exists():
        raise FileNotFoundError(
            f"한글 폰트를 찾을 수 없습니다: {path}. "
            "Windows의 맑은 고딕 폰트가 필요합니다."
        )
    return ImageFont.truetype(str(path), size)


def wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    """단어(어절) 단위로 줄바꿈하되, 픽셀 폭 기준으로 정확히 맞춘다."""
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        bbox = draw.textbbox((0, 0), candidate, font=font)
        if bbox[2] - bbox[0] <= max_width or not current:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def paginate_lines(lines: list[str], max_lines_per_page: int) -> list[list[str]]:
    if not lines:
        return [[]]
    return [lines[i:i + max_lines_per_page] for i in range(0, len(lines), max_lines_per_page)]


def new_canvas() -> tuple[Image.Image, ImageDraw.ImageDraw]:
    img = Image.new("RGB", (CANVAS_W, CANVAS_H), BG)
    return img, ImageDraw.Draw(img)


def draw_footer(draw: ImageDraw.ImageDraw, page: int, total: int, brand_handle: str) -> None:
    font = load_font(False, 26)
    draw.line([(MARGIN, CANVAS_H - 110), (CANVAS_W - MARGIN, CANVAS_H - 110)], fill=HAIRLINE, width=2)
    draw.text((MARGIN, CANVAS_H - 80), brand_handle, font=font, fill=INK_SOFT)
    page_text = f"{page} / {total}"
    bbox = draw.textbbox((0, 0), page_text, font=font)
    w = bbox[2] - bbox[0]
    draw.text((CANVAS_W - MARGIN - w, CANVAS_H - 80), page_text, font=font, fill=INK_GREY)


def make_cover_card(date: str, headline: str, summary_points: list[str]) -> Image.Image:
    img, draw = new_canvas()

    date_font = load_font(False, 30)
    draw.text((MARGIN, 100), date, font=date_font, fill=INK_SOFT)

    draw.line([(MARGIN, 160), (MARGIN + 90, 160)], fill=CLAY, width=6)

    headline_font = load_font(True, 66)
    lines = wrap_text(draw, headline, headline_font, CANVAS_W - 2 * MARGIN)
    y = 230
    for line in lines:
        draw.text((MARGIN, y), line, font=headline_font, fill=INK)
        bbox = draw.textbbox((0, 0), line, font=headline_font)
        y += (bbox[3] - bbox[1]) + 26

    y += 50
    point_font = load_font(False, 34)
    for point in summary_points:
        draw.ellipse([(MARGIN, y + 14), (MARGIN + 10, y + 24)], fill=CLAY)
        wrapped = wrap_text(draw, point, point_font, CANVAS_W - 2 * MARGIN - 40)
        for i, wline in enumerate(wrapped):
            draw.text((MARGIN + 34, y), wline, font=point_font, fill=INK_SOFT)
            bbox = draw.textbbox((0, 0), wline, font=point_font)
            y += (bbox[3] - bbox[1]) + 14
        y += 16

    return img


def make_item_card(index: int, heading: str, body: str, page_no: int, page_total: int) -> list[Image.Image]:
    """섹션 항목 하나를 카드 1장 이상으로 렌더링 (본문이 길면 이어지는 카드로 분할)."""
    heading_font = load_font(True, 46)
    body_font = load_font(False, 36)

    tmp_img, tmp_draw = new_canvas()
    content_top = 260
    footer_top = CANVAS_H - 140
    line_height_est = body_font.size + 20
    max_lines_per_page = max(3, (footer_top - content_top - 90) // line_height_est)

    body_lines = wrap_text(tmp_draw, body, body_font, CANVAS_W - 2 * MARGIN)
    pages = paginate_lines(body_lines, max_lines_per_page)

    images = []
    for sub_i, page_lines in enumerate(pages):
        img, draw = new_canvas()

        badge_text = f"{index:02d}"
        badge_font = load_font(True, 34)
        draw.text((MARGIN, 100), badge_text, font=badge_font, fill=CLAY)
        draw.line([(MARGIN, 150), (CANVAS_W - MARGIN, 150)], fill=HAIRLINE, width=2)

        heading_display = heading if len(pages) == 1 else f"{heading} ({sub_i + 1}/{len(pages)})"
        heading_lines = wrap_text(draw, heading_display, heading_font, CANVAS_W - 2 * MARGIN)
        y = 190
        for hline in heading_lines:
            draw.text((MARGIN, y), hline, font=heading_font, fill=INK)
            bbox = draw.textbbox((0, 0), hline, font=heading_font)
            y += (bbox[3] - bbox[1]) + 18

        y = content_top
        for bline in page_lines:
            draw.text((MARGIN, y), bline, font=body_font, fill=INK_SOFT)
            bbox = draw.textbbox((0, 0), bline, font=body_font)
            y += (bbox[3] - bbox[1]) + 20

        images.append(img)
    return images


def generate(input_path: Path, outdir: Path, brand_handle: str) -> list[Path]:
    data = json.loads(input_path.read_text(encoding="utf-8"))
    outdir.mkdir(parents=True, exist_ok=True)

    cards: list[Image.Image] = [
        make_cover_card(data["date"], data["headline"], data.get("summary_points", []))
    ]

    index = 1
    for section in data.get("sections", []):
        for item in section.get("items", []):
            cards.extend(make_item_card(index, item["heading"], item["body"], 0, 0))
            index += 1

    total = len(cards)
    paths: list[Path] = []
    for i, card in enumerate(cards, start=1):
        draw = ImageDraw.Draw(card)
        draw_footer(draw, i, total, brand_handle)
        path = outdir / f"card_{i:02d}.png"
        card.save(path, "PNG")
        paths.append(path)

    return paths


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/brief_data.json")
    parser.add_argument("--outdir", required=True)
    parser.add_argument("--brand-handle", default=os.environ.get("BRAND_HANDLE", "@morning_brief"))
    args = parser.parse_args()

    paths = generate(Path(args.input), Path(args.outdir), args.brand_handle)
    print(f"생성된 카드 {len(paths)}장:")
    for p in paths:
        print(f"  {p}")


if __name__ == "__main__":
    main()
