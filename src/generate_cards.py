"""
brief_data.json (Claude가 예약 작업에서 채우는 구조화 데이터) -> 카드뉴스 PNG 이미지들.

사용법:
    python src/generate_cards.py --input data/brief_data.json --outdir docs/2026-09-29
"""
import argparse
import json
import math
import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

CANVAS_W, CANVAS_H = 1080, 1350
MARGIN = 90
FOOTER_TOP = CANVAS_H - 140

BG = "#FCFCFB"
PANEL = "#F3F0E9"
INK = "#2E2C27"
INK_SOFT = "#6B6A63"
INK_GREY = "#B4B3A8"
CLAY = "#C6613F"
CLAY_DARK = "#AE5133"
DOWN_BLUE = "#4C6B8A"
HAIRLINE = "#E4E3DC"

FONT_DIR = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"
FONT_BOLD = FONT_DIR / "malgunbd.ttf"
FONT_REGULAR = FONT_DIR / "malgun.ttf"

_FONT_CACHE: dict[tuple[bool, int], ImageFont.FreeTypeFont] = {}


def load_font(bold: bool, size: int) -> ImageFont.FreeTypeFont:
    key = (bold, size)
    if key not in _FONT_CACHE:
        path = FONT_BOLD if bold else FONT_REGULAR
        if not path.exists():
            raise FileNotFoundError(
                f"한글 폰트를 찾을 수 없습니다: {path}. "
                "Windows의 맑은 고딕 폰트가 필요합니다."
            )
        _FONT_CACHE[key] = ImageFont.truetype(str(path), size)
    return _FONT_CACHE[key]


def trend_color(trend: str | None) -> str:
    return {"up": CLAY, "down": DOWN_BLUE}.get(trend, INK)


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


def text_block_height(lines: list[str], font: ImageFont.FreeTypeFont, line_gap: int) -> int:
    if not lines:
        return 0
    line_h = font.size + line_gap
    return line_h * len(lines) - line_gap


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


def draw_triangle(draw: ImageDraw.ImageDraw, cx: int, cy: int, size: int, direction: str, color: str) -> None:
    if direction == "up":
        pts = [(cx, cy - size), (cx - size, cy + size * 0.7), (cx + size, cy + size * 0.7)]
    else:
        pts = [(cx, cy + size), (cx - size, cy - size * 0.7), (cx + size, cy - size * 0.7)]
    draw.polygon(pts, fill=color)


def draw_sparkline(draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int) -> None:
    """표지 카드 헤드라인 아래에 들어가는 장식용 추세선 (모닝브리프 지형선 오마주)."""
    xs = [x + w * t / 8 for t in range(9)]
    shape = [0.55, 0.5, 0.42, 0.3, 0.18, 0.22, 0.12, 0.2, 0.15]
    ys = [y + h * s for s in shape]
    pts = list(zip(xs, ys))
    draw.line(pts, fill=INK, width=4, joint="curve")
    for i, (px, py) in enumerate(pts):
        if i in (0, 4, 8):
            draw.ellipse([px - 6, py - 6, px + 6, py + 6], fill=INK)
    accent_x, accent_y = pts[4]
    draw.ellipse([accent_x - 9, accent_y - 9, accent_x + 9, accent_y + 9], fill=CLAY)


def make_cover_card(date: str, headline: str, summary_points: list[str]) -> Image.Image:
    img, draw = new_canvas()

    date_font = load_font(False, 30)
    draw.text((MARGIN, 90), date, font=date_font, fill=INK_SOFT)

    draw.rounded_rectangle([(MARGIN, 140), (MARGIN + 90, 146)], radius=3, fill=CLAY)

    headline_font = load_font(True, 64)
    lines = wrap_text(draw, headline, headline_font, CANVAS_W - 2 * MARGIN)
    y = 200
    for line in lines:
        draw.text((MARGIN, y), line, font=headline_font, fill=INK)
        bbox = draw.textbbox((0, 0), line, font=headline_font)
        y += (bbox[3] - bbox[1]) + 22

    y += 20
    draw_sparkline(draw, MARGIN, y, CANVAS_W - 2 * MARGIN, 90)
    y += 150

    draw.line([(MARGIN, y), (CANVAS_W - MARGIN, y)], fill=HAIRLINE, width=2)
    y += 40

    point_font = load_font(False, 34)
    for point in summary_points:
        wrapped = wrap_text(draw, point, point_font, CANVAS_W - 2 * MARGIN - 40)
        draw.ellipse([(MARGIN, y + 14), (MARGIN + 12, y + 26)], fill=CLAY)
        for wline in wrapped:
            draw.text((MARGIN + 34, y), wline, font=point_font, fill=INK_SOFT)
            bbox = draw.textbbox((0, 0), wline, font=point_font)
            y += (bbox[3] - bbox[1]) + 14
        y += 18

    return img


def draw_badge(draw: ImageDraw.ImageDraw, index: int) -> int:
    """번호 칩을 그리고, 칩 바로 아래 y좌표(다음 콘텐츠 시작점)를 반환."""
    chip_size = 64
    x0, y0 = MARGIN, 90
    draw.rounded_rectangle([x0, y0, x0 + chip_size, y0 + chip_size], radius=16, fill=CLAY)
    badge_font = load_font(True, 30)
    text = f"{index:02d}"
    bbox = draw.textbbox((0, 0), text, font=badge_font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(
        (x0 + (chip_size - tw) / 2, y0 + (chip_size - th) / 2 - bbox[1]),
        text, font=badge_font, fill="#FCFCFB",
    )
    return y0 + chip_size


def draw_stat_box(draw: ImageDraw.ImageDraw, top: int, stat: str, stat_label: str, trend: str | None) -> int:
    """큰 수치 하이라이트 박스를 그리고, 박스 아래 y좌표를 반환."""
    color = trend_color(trend)
    stat_font = load_font(True, 92)
    label_font = load_font(False, 30)

    box_left, box_right = MARGIN, CANVAS_W - MARGIN
    pad_y = 44
    stat_bbox = draw.textbbox((0, 0), stat, font=stat_font)
    stat_h = stat_bbox[3] - stat_bbox[1]
    box_height = pad_y * 2 + stat_h + 46
    box_bottom = top + box_height

    draw.rounded_rectangle([box_left, top, box_right, box_bottom], radius=20, fill=PANEL)

    content_x = box_left + 48
    stat_y = top + pad_y - stat_bbox[1]

    if trend in ("up", "down"):
        draw_triangle(draw, content_x + 16, top + box_height // 2, 16, trend, color)
        content_x += 50

    draw.text((content_x, stat_y), stat, font=stat_font, fill=color)
    stat_w = draw.textbbox((0, 0), stat, font=stat_font)[2]
    draw.text(
        (content_x + stat_w + 24, top + box_height // 2 + 6),
        stat_label, font=label_font, fill=INK_SOFT,
    )

    return box_bottom


def make_item_card(index: int, item: dict) -> list[Image.Image]:
    """섹션 항목 하나를 카드 1장 이상으로 렌더링 (본문이 길면 이어지는 카드로 분할)."""
    heading = item["heading"]
    body = item["body"]
    stat = item.get("stat")
    stat_label = item.get("stat_label", "")
    trend = item.get("trend")

    heading_font = load_font(True, 44)
    body_font = load_font(False, 34)

    tmp_img, tmp_draw = new_canvas()
    heading_lines = wrap_text(tmp_draw, heading, heading_font, CANVAS_W - 2 * MARGIN - 90)
    heading_h = text_block_height(heading_lines, heading_font, 16)

    content_top = 90 + 64 + 40 + heading_h + 36
    if stat:
        stat_box_h = 44 * 2 + (load_font(True, 92).getbbox(stat)[3]) + 46
        content_top += stat_box_h + 36

    line_height_est = body_font.size + 20
    max_lines_per_page = max(3, (FOOTER_TOP - content_top - 20) // line_height_est)

    body_lines = wrap_text(tmp_draw, body, body_font, CANVAS_W - 2 * MARGIN)
    pages = paginate_lines(body_lines, max_lines_per_page)

    images = []
    for sub_i, page_lines in enumerate(pages):
        img, draw = new_canvas()

        content_y = draw_badge(draw, index)
        content_y += 26

        heading_display = heading if len(pages) == 1 else f"{heading} ({sub_i + 1}/{len(pages)})"
        h_lines = wrap_text(draw, heading_display, heading_font, CANVAS_W - 2 * MARGIN)
        for hline in h_lines:
            draw.text((MARGIN, content_y), hline, font=heading_font, fill=INK)
            bbox = draw.textbbox((0, 0), hline, font=heading_font)
            content_y += (bbox[3] - bbox[1]) + 16
        content_y += 20

        if stat and sub_i == 0:
            content_y = draw_stat_box(draw, content_y, stat, stat_label, trend) + 36

        for bline in page_lines:
            draw.text((MARGIN, content_y), bline, font=body_font, fill=INK_SOFT)
            bbox = draw.textbbox((0, 0), bline, font=body_font)
            content_y += (bbox[3] - bbox[1]) + 20

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
            cards.extend(make_item_card(index, item))
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
