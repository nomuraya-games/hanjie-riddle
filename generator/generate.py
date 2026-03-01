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


def main():
    data_path = Path(__file__).parent.parent / "data" / "puzzles.json"
    output_dir = Path(__file__).parent.parent / "output"
    output_dir.mkdir(exist_ok=True)

    # 特定IDのみ生成する場合
    target_id = sys.argv[1] if len(sys.argv) > 1 else None

    with open(data_path, encoding="utf-8") as f:
        puzzles = json.load(f)

    for puzzle in puzzles:
        if target_id and puzzle["id"] != target_id:
            continue
        path = generate_puzzle_image(puzzle, output_dir)
        print(f"生成完了: {path} (答え: {puzzle['answer']})")


if __name__ == "__main__":
    main()
