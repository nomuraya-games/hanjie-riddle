"""
判じ絵画像ジェネレータ

目的:
    問題データ（JSON）から判じ絵の出題画像を生成する。
    視覚的な演出（大きさ・色・配置等）と文字/絵を組み合わせて、
    音から別の言葉を連想させる謎解き画像を作る。

出力:
    SNS投稿・ブログ埋め込み用のPNG画像（1200x675, 16:9）
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# 画像サイズ（SNS投稿に適した16:9）
WIDTH = 1200
HEIGHT = 675

# フォント候補（環境変数 HANJIE_FONT_PATH が最優先）
FONT_CANDIDATES = [
    "/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc",
    "/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJKjp-Regular.otf",
]

# 演出ごとのフォントサイズ
EFFECT_FONT_SIZE = {
    "large": 500,
    "small": 60,
    "normal": 200,
}

# 演出ごとのテキスト色
EFFECT_TEXT_COLOR = {
    "large": "#1a1a1a",
    "small": "#1a1a1a",
    "red": "#cc0000",
    "blue": "#0044cc",
    "normal": "#1a1a1a",
}

REQUIRED_FIELDS = {
    "id",
    "content",
    "content_type",
    "effect",
    "effect_params",
    "reading",
    "answer",
    "hint",
    "difficulty",
}
ALLOWED_EFFECTS = set(EFFECT_FONT_SIZE) | {"red", "blue", "half", "top", "bottom", "flip"}
ALLOWED_CONTENT_TYPES = {"text"}
STRICT_READING_PREFIXES = {
    "blue": ("あお",),
    "bottom": ("した",),
}
STRICT_ANSWER_PREFIXES = {
    "blue": ("青",),
    "bottom": ("下",),
}
_RESOLVED_FONT_PATH: str | None = None


def resolve_font_path() -> str:
    global _RESOLVED_FONT_PATH
    if _RESOLVED_FONT_PATH:
        return _RESOLVED_FONT_PATH

    env_font = os.getenv("HANJIE_FONT_PATH")
    if env_font and Path(env_font).exists():
        _RESOLVED_FONT_PATH = env_font
        return _RESOLVED_FONT_PATH

    for candidate in FONT_CANDIDATES:
        if Path(candidate).exists():
            _RESOLVED_FONT_PATH = candidate
            return _RESOLVED_FONT_PATH

    raise FileNotFoundError(
        "日本語フォントが見つかりません。"
        "HANJIE_FONT_PATH にフォントファイルを指定してください。"
    )


def load_font(size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(resolve_font_path(), size)


def validate_puzzles(puzzles: list[dict]) -> None:
    """問題データの最低限の整合性を検証する。"""
    errors: list[str] = []
    seen_ids: set[str] = set()

    for index, puzzle in enumerate(puzzles, start=1):
        if not isinstance(puzzle, dict):
            errors.append(f"{index}件目: dictではありません")
            continue

        puzzle_id = str(puzzle.get("id", f"index-{index}"))
        missing = sorted(REQUIRED_FIELDS - set(puzzle))
        if missing:
            errors.append(f"{puzzle_id}: 必須フィールド不足 {', '.join(missing)}")

        if puzzle_id in seen_ids:
            errors.append(f"{puzzle_id}: id が重複しています")
        seen_ids.add(puzzle_id)

        effect = puzzle.get("effect")
        if effect not in ALLOWED_EFFECTS:
            errors.append(f"{puzzle_id}: 未対応 effect '{effect}'")

        content_type = puzzle.get("content_type")
        if content_type not in ALLOWED_CONTENT_TYPES:
            errors.append(f"{puzzle_id}: 未対応 content_type '{content_type}'")

        effect_params = puzzle.get("effect_params")
        if not isinstance(effect_params, dict):
            errors.append(f"{puzzle_id}: effect_params は object が必要です")

        difficulty = puzzle.get("difficulty")
        if not isinstance(difficulty, int) or not 1 <= difficulty <= 3:
            errors.append(f"{puzzle_id}: difficulty は 1-3 の整数が必要です")

        for key in ("content", "reading", "answer", "hint"):
            value = puzzle.get(key)
            if not isinstance(value, str) or not value.strip():
                errors.append(f"{puzzle_id}: {key} は空でない文字列が必要です")

        reading = puzzle.get("reading")
        if isinstance(reading, str):
            required_reading_prefixes = STRICT_READING_PREFIXES.get(effect)
            if required_reading_prefixes and not reading.startswith(required_reading_prefixes):
                joined = " / ".join(required_reading_prefixes)
                errors.append(
                    f"{puzzle_id}: effect '{effect}' は reading が '{joined}' 始まりである必要があります "
                    f"(現在: '{reading}')"
                )

        answer = puzzle.get("answer")
        if isinstance(answer, str):
            required_answer_prefixes = STRICT_ANSWER_PREFIXES.get(effect)
            if required_answer_prefixes and not answer.startswith(required_answer_prefixes):
                joined = " / ".join(required_answer_prefixes)
                errors.append(
                    f"{puzzle_id}: effect '{effect}' は answer が '{joined}' 始まりである必要があります "
                    f"(現在: '{answer}')"
                )

    if errors:
        lines = "\n".join(f"- {error}" for error in errors)
        raise ValueError(f"問題データ検証エラー:\n{lines}")


def draw_effect_large(draw: ImageDraw.ImageDraw, text: str) -> None:
    """大きい文字を画面いっぱいに描画"""
    font = load_font(EFFECT_FONT_SIZE["large"])
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    x = (WIDTH - text_w) / 2
    y = (HEIGHT - text_h) / 2 - bbox[1]
    draw.text((x, y), text, fill=EFFECT_TEXT_COLOR["large"], font=font)


def draw_effect_small(draw: ImageDraw.ImageDraw, text: str) -> None:
    """小さい文字を画面中央にぽつんと描画"""
    font = load_font(EFFECT_FONT_SIZE["small"])
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    x = (WIDTH - text_w) / 2
    y = (HEIGHT - text_h) / 2 - bbox[1]
    draw.text((x, y), text, fill=EFFECT_TEXT_COLOR["small"], font=font)


def draw_effect_color(draw: ImageDraw.ImageDraw, text: str, color: str) -> None:
    """色付き文字を描画"""
    font = load_font(EFFECT_FONT_SIZE["normal"])
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    x = (WIDTH - text_w) / 2
    y = (HEIGHT - text_h) / 2 - bbox[1]
    draw.text((x, y), text, fill=EFFECT_TEXT_COLOR.get(color, color), font=font)


def draw_effect_half(img: Image.Image, draw: ImageDraw.ImageDraw, text: str) -> None:
    """文字の左半分だけ見える（右半分を白で隠す）"""
    font = load_font(EFFECT_FONT_SIZE["normal"])
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    x = (WIDTH - text_w) / 2
    y = (HEIGHT - text_h) / 2 - bbox[1]
    draw.text((x, y), text, fill="#1a1a1a", font=font)
    # 右半分を白で覆う
    mid_x = WIDTH // 2
    draw.rectangle([(mid_x, 0), (WIDTH, HEIGHT)], fill="white")


def draw_effect_top(draw: ImageDraw.ImageDraw, text: str) -> None:
    """文字を画面上部に配置"""
    font = load_font(EFFECT_FONT_SIZE["normal"])
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    x = (WIDTH - text_w) / 2
    y = 30 - bbox[1]
    draw.text((x, y), text, fill="#1a1a1a", font=font)


def draw_effect_bottom(draw: ImageDraw.ImageDraw, text: str) -> None:
    """文字を画面下部に配置"""
    font = load_font(EFFECT_FONT_SIZE["normal"])
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    x = (WIDTH - text_w) / 2
    y = HEIGHT - text_h - 30 - bbox[1]
    draw.text((x, y), text, fill="#1a1a1a", font=font)


def draw_effect_flip(img: Image.Image, draw: ImageDraw.ImageDraw, text: str) -> None:
    """文字を上下逆さに描画"""
    font = load_font(EFFECT_FONT_SIZE["normal"])
    # 一時画像にテキストを描画してから上下反転して合成
    txt_img = Image.new("RGBA", (WIDTH, HEIGHT), (255, 255, 255, 0))
    txt_draw = ImageDraw.Draw(txt_img)
    bbox = txt_draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    x = (WIDTH - text_w) / 2
    y = (HEIGHT - text_h) / 2 - bbox[1]
    txt_draw.text((x, y), text, fill="#1a1a1a", font=font)
    txt_img = txt_img.transpose(Image.FLIP_TOP_BOTTOM)
    img.paste(txt_img, (0, 0), txt_img)


def generate_puzzle_image(puzzle: dict, output_dir: Path) -> Path:
    """1問分の画像を生成して保存する"""
    img = Image.new("RGB", (WIDTH, HEIGHT), "white")
    draw = ImageDraw.Draw(img)

    effect = puzzle["effect"]
    text = puzzle["content"]

    # 色系の演出
    if effect in ("red", "blue"):
        draw_effect_color(draw, text, effect)
    # サイズ系の演出
    elif effect == "large":
        draw_effect_large(draw, text)
    elif effect == "small":
        draw_effect_small(draw, text)
    # 配置系の演出
    elif effect == "top":
        draw_effect_top(draw, text)
    elif effect == "bottom":
        draw_effect_bottom(draw, text)
    # 変形系の演出（imgも渡す）
    elif effect == "half":
        draw_effect_half(img, draw, text)
    elif effect == "flip":
        draw_effect_flip(img, draw, text)
    else:
        draw_effect_color(draw, text, "normal")

    # 枠線（スライド風）
    draw.rectangle([(2, 2), (WIDTH - 3, HEIGHT - 3)], outline="#333333", width=4)

    output_path = output_dir / f"{puzzle['id']}.png"
    img.save(output_path, "PNG")
    return output_path


def generate_viewer_html(puzzles: list[dict], output_dir: Path) -> Path:
    """問題一覧を表示するHTMLビューアを生成する"""
    cards = ""
    for p in puzzles:
        cards += f"""
      <div class="card">
        <div class="image-wrap">
          <img src="{p['id']}.png" alt="問題 {p['id']}">
        </div>
        <div class="meta">
          <span class="badge">#{p['id']}</span>
          <span class="badge diff-{p['difficulty']}">難易度 {p['difficulty']}</span>
        </div>
        <details>
          <summary>答えを見る</summary>
          <p class="answer">{p['answer']}（{p['reading']}）</p>
          <p class="hint">ヒント: {p['hint']}</p>
        </details>
      </div>"""

    html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>判じ絵なぞなぞ</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: -apple-system, sans-serif; background: #f5f5f5; padding: 2rem; }}
  h1 {{ text-align: center; margin-bottom: 2rem; font-size: 1.8rem; }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(400px, 1fr)); gap: 1.5rem; max-width: 1200px; margin: 0 auto; }}
  .card {{ background: #fff; border-radius: 12px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
  .image-wrap {{ padding: 1rem; background: #fafafa; }}
  .image-wrap img {{ width: 100%; height: auto; display: block; border-radius: 4px; }}
  .meta {{ padding: 0.75rem 1rem 0; display: flex; gap: 0.5rem; }}
  .badge {{ font-size: 0.75rem; padding: 0.2rem 0.6rem; border-radius: 99px; background: #e8e8e8; color: #555; }}
  .diff-1 {{ background: #d4edda; color: #155724; }}
  .diff-2 {{ background: #fff3cd; color: #856404; }}
  .diff-3 {{ background: #f8d7da; color: #721c24; }}
  details {{ padding: 0.75rem 1rem 1rem; }}
  summary {{ cursor: pointer; color: #666; font-size: 0.9rem; }}
  .answer {{ font-size: 1.3rem; font-weight: bold; margin-top: 0.5rem; }}
  .hint {{ font-size: 0.85rem; color: #888; margin-top: 0.3rem; }}
</style>
</head>
<body>
<h1>判じ絵なぞなぞ</h1>
<div class="grid">{cards}
</div>
</body>
</html>"""

    html_path = output_dir / "index.html"
    html_path.write_text(html, encoding="utf-8")
    return html_path


def main():
    data_path = Path(__file__).parent.parent / "data" / "puzzles.json"
    output_dir = Path(__file__).parent.parent / "output"
    output_dir.mkdir(exist_ok=True)

    # 特定IDのみ生成する場合
    target_id = sys.argv[1] if len(sys.argv) > 1 else None

    with open(data_path, encoding="utf-8") as f:
        puzzles = sorted(json.load(f), key=lambda x: x["id"])

    validate_puzzles(puzzles)
    font_path = resolve_font_path()
    print(f"使用フォント: {font_path}", flush=True)

    generated = []
    for puzzle in puzzles:
        if target_id and puzzle["id"] != target_id:
            continue
        path = generate_puzzle_image(puzzle, output_dir)
        generated.append(puzzle)
        print(f"生成完了: {path} (答え: {puzzle['answer']})")

    # HTMLビューア生成（全問題生成時のみ）
    if not target_id:
        html_path = generate_viewer_html(puzzles, output_dir)
        print(f"\nビューア: file://{html_path}")
    elif not generated:
        print(f"指定IDの問題が見つかりません: {target_id}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
