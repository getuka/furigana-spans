# furigana-spans

日本語文を入力し、ルビ文字列を挿入せずに **構造化された解析結果** を返すためのライブラリです。

## 設計方針

- 主解析は `SudachiPy + SudachiDict` を使用
- 戻り値は `RubyAnalysis` dataclass
- 文字列レンダリングは別責務
- ユーザ辞書は補助的 override / candidate injection
- 同形異読は「候補列挙」と「候補選択」を分離

## インストール

```bash
pip install sudachipy sudachidict_core
pip install -e .
```

Git リポジトリから直接入れる場合:

```bash
pip install git+https://github.com/getuka/furigana-spans.git
```

## 使用例

```python
from furigana_spans import AnalyzerConfig, RubyAnalyzer

config = AnalyzerConfig(
    dictionary="core",
    split_mode="C",
    reading_script="hiragana",
)

analyzer = RubyAnalyzer(config)
analysis = analyzer.analyze("日本橋に行く")

print(analysis)
```

## ユーザ辞書

JSON または JSONL をサポートします。

### JSON 配列

```json
[
  {"surface": "日本橋", "reading": "にほんばし"},
  {"surface": "重粒子線", "reading": "じゅうりゅうしせん"}
]
```

### JSONL

```jsonl
{"surface": "日本橋", "reading": "にほんばし"}
{"surface": "重粒子線", "reading": "じゅうりゅうしせん"}
```

設定例:

```python
config = AnalyzerConfig(
    enable_user_dictionary=True,
    user_dictionary_paths=("./user_dict.json",),
)
```

## 数助詞ルール

初版では以下を優先的に処理します。

- 人
- 日
- 本
- 匹
- 杯
- 分
- 回
- 階
- 冊
- 枚
- 個
- 年
- 歳

対象は次の 2 パターンです。

- `3人`, `20歳` のような単一 token
- `3` + `人`, `二十` + `歳` のような連続 token

連続 token の場合は、`spans` 側でひとつの複合 span にまとめます。
