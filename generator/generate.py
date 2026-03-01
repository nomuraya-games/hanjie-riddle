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
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# 画像サイズ（SNS投稿に適した16:9）
WIDTH = 1200
HEIGHT = 675

# フォント（macOS ヒラギノ角ゴシック W6）
FONT_PATH = "/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc"

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


def load_font(size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(FONT_PATH, size)


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


# 演出名 → 描画関数のマッピング
EFFECT_HANDLERS = {
    "large": draw_effect_large,
    "small": draw_effect_small,
}


def generate_puzzle_image(puzzle: dict, output_dir: Path) -> Path:
    """1問分の画像を生成して保存する"""
    img = Image.new("RGB", (WIDTH, HEIGHT), "white")
    draw = ImageDraw.Draw(img)

    effect = puzzle["effect"]
    text = puzzle["content"]

    if effect in ("red", "blue"):
        draw_effect_color(draw, text, effect)
    elif effect in EFFECT_HANDLERS:
        EFFECT_HANDLERS[effect](draw, text)
    else:
        # フォールバック: 通常サイズで描画
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
        puzzles = json.load(f)

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


if __name__ == "__main__":
    main()
