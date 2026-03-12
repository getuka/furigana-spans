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

print(analysis.to_json())
```

出力例:

```json
{
  "text": "日本橋に行く",
  "normalized_text": "日本橋に行く",
  "tokens": [
    {
      "surface": "日本橋",
      "start": 0,
      "end": 3,
      "pos": ["名詞", "固有名詞", "地名", "一般", "*", "*"],
      "base_form": "日本橋",
      "normalized_form": "日本橋",
      "reading": "にほんばし",
      "pronunciation": "にほんばし",
      "is_oov": false,
      "dictionary_id": 0,
      "candidates": [
        {"reading": "にほんばし", "score": 0.9, "source": "sudachi", "is_selected": true},
        {"reading": "にっぽんばし", "score": 0.6, "source": "ambiguity_lexicon", "is_selected": false}
      ],
      "metadata": {}
    }
  ],
  "spans": [
    {
      "surface": "日本橋",
      "reading": "にほんばし",
      "start": 0,
      "end": 3,
      "token_indices": [0],
      "pos": ["名詞", "固有名詞", "地名", "一般", "*", "*"],
      "normalized_form": "日本橋",
      "source": "ambiguity_resolver",
      "candidates": [
        {"reading": "にほんばし", "score": 0.9, "source": "sudachi", "is_selected": true},
        {"reading": "にっぽんばし", "score": 0.6, "source": "ambiguity_lexicon", "is_selected": false}
      ],
      "metadata": {"span_type": "word"}
    }
  ],
  "warnings": [],
  "metadata": {
    "span_unit": "word",
    "reading_script": "hiragana"
  }
}
```

## 公開 API

```python
from furigana_spans import AnalyzerConfig, RubyAnalyzer
from furigana_spans.schema import ReadingCandidate, RubyAnalysis, RubySpan, RubyToken
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
