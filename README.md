# hanjie-riddle

判じ絵なぞなぞジェネレータ。

## 判じ絵とは

視覚的な演出（大きさ・色・配置など）と描かれた文字・絵を組み合わせて、音から別の言葉を連想する謎解き。

### 例

| 見た目 | 内容 | 音 | 答え |
|--------|------|----|------|
| **大きい** | 豆 | だい + ず | 大豆 |
| **小さい** | 柿 | しょう + かき | 消火器 |

## 仕組み

- 問題データ（JSON）から画像を自動生成
- Pillow でPNGを出力
- SNS（X等）で出題、ブログ（はてな/note）で解説

## 構成

```
hanjie-riddle/
├── data/          # 問題データ（JSON）
├── generator/     # 画像生成スクリプト
└── output/        # 生成画像・HTMLビューア
```

## 実行

```bash
uv run python generator/generate.py
```

特定IDのみ生成する場合:

```bash
uv run python generator/generate.py 010
```

フォントを明示したい場合:

```bash
HANJIE_FONT_PATH=/path/to/font.ttf uv run python generator/generate.py
```

## 品質ルール（厳格）

- `effect=blue` の問題は `reading` が `あお` 始まり、`answer` が `青` 始まりであること
- `effect=bottom` の問題は `reading` が `した` 始まり、`answer` が `下` 始まりであること
- ルール違反の問題データがある場合、生成時にエラーで停止
