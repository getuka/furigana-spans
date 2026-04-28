# furigana-spans

`furigana-spans` は、日本語テキストからルビ候補を抽出し、文字列ではなく構造化データとして返す Python ライブラリです。

主な用途は次のとおりです。

- TTS 前処理で、ルビを付ける span を選ぶ
- 同形異読や数詞 + 助数詞の読みを扱う
- ルビ付与の必要度を `difficulty.score` と `difficulty.reasons` で評価する
- ユーザー辞書、語彙頻度表、専門語辞書で判定を補強する

このライブラリはルビ候補の抽出と評価に特化しています。`<ruby>` などのレンダリングは対象外です。HTML や SSML などへの変換は、呼び出し側で `RubyAnalysis.spans` を使って組み立ててください。

## Contents

- [Requirements](#requirements)
- [Installation](#installation)
- [Quick start](#quick-start)
- [Output schema](#output-schema)
- [AnalyzerConfig](#analyzerconfig)
- [User dictionary](#user-dictionary)
- [Number counter rules](#number-counter-rules)
- [Difficulty scoring](#difficulty-scoring)
- [Vocabulary frequency and domain dictionaries](#vocabulary-frequency-and-domain-dictionaries)
- [Example: selective ruby for TTS](#example-selective-ruby-for-tts)
- [Tests](#tests)

## Requirements

- Python 3.10+
- SudachiPy
- SudachiDict `small`, `core`, `full` のいずれか

## Installation


```bash
pip install git+https://github.com/getuka/furigana-spans.git
```

## Quick start

```python
from furigana_spans import AnalyzerConfig, RubyAnalyzer

analyzer = RubyAnalyzer(
    AnalyzerConfig(
        dictionary="core",
        split_mode="C",
        reading_script="hiragana",
    )
)

analysis = analyzer.analyze("大阪の日本橋に行く")

for span in analysis.spans:
    print(span.surface, span.reading, span.start, span.end)
```

`analysis` は `RubyAnalysis` です。通常は `analysis.spans` を見れば十分です。

```python
analysis.text             # original input text
analysis.normalized_text  # normalized text
analysis.tokens           # token-level results
analysis.spans            # ruby span results
analysis.warnings         # warnings during analysis
analysis.metadata         # additional metadata
```

## Output schema

代表的な `RubySpan` は次のような構造です。

```python
RubySpan(
    surface="日本橋",
    reading="にっぽんばし",
    start=3,
    end=6,
    token_indices=[...],
    source="ambiguity_lexicon",
    candidates=[...],
    difficulty=RubyDifficulty(
        score=0.6175,
        reasons=(
            "ambiguous_reading",
            "resolved_by_context_rule",
            "place_name",
        ),
    ),
)
```

`RubyToken` には Sudachi 由来の token 情報、読み候補、OOV 情報などが入ります。最終的にルビ付与対象を選ぶ用途では、基本的に `RubyAnalysis.spans` を使います。

## AnalyzerConfig

基本設定:

```python
config = AnalyzerConfig(
    dictionary="core",              # small / core / full / compiled dict path
    split_mode="C",                 # A / B / C
    reading_script="hiragana",      # hiragana / katakana
    include_tokens_without_kanji=False,
    enable_number_rules=True,
    enable_ambiguity_resolution=True,
    enable_oov_fallback=True,
    enable_difficulty_scoring=True,
)
```

辞書拡張込みの設定例:

```python
config = AnalyzerConfig(
    dictionary="core",
    split_mode="C",
    reading_script="hiragana",
    enable_user_dictionary=True,
    user_dictionary_paths=("./user_dict.json",),
    enable_frequency_difficulty=True,
    frequency_dictionary_paths=(
        "./data/bccwj_luw_frequency.tsv",
        "./data/bccwj_suw_frequency.tsv",
    ),
    enable_domain_difficulty=True,
    domain_lexicon_paths=("./data/nbdc_domain_terms.tsv",),
)
```

## User dictionary

ユーザー辞書は JSON または JSONL で指定できます。

```python
config = AnalyzerConfig(
    enable_user_dictionary=True,
    user_dictionary_paths=("./user_dict.json",),
)
```

### JSON example

```json
[
  {
    "surface": "日本橋",
    "reading": "にほんばし"
  },
  {
    "surface": "重粒子線",
    "reading": "じゅうりゅうしせん",
    "difficulty_score": 0.82,
    "difficulty_reasons": ["domain_term"],
    "tags": ["medical", "technical_term"]
  },
  {
    "surface": "四月一日",
    "reading": "わたぬき",
    "always_ruby": true,
    "named_entity_type": "person_name",
    "difficulty_reasons": ["rare_name"]
  }
]
```

### JSONL example

```jsonl
{"surface": "日本橋", "reading": "にほんばし"}
{"surface": "重粒子線", "reading": "じゅうりゅうしせん", "difficulty_reasons": ["domain_term"]}
```

### User dictionary fields

| field | meaning |
|---|---|
| `surface` | 表層形 |
| `reading` | 読み |
| `difficulty_score` | 自動 score の下限値。`0.0`–`1.0` |
| `difficulty_reasons` | 追加する difficulty reason |
| `always_ruby` | `true` の場合、`difficulty.score = 1.0` |
| `named_entity_type` | `person_name`, `place_name`, `organization_name`, `product_name`, `work_title`, `rare_name` など |
| `tags` | `domain_term`, `technical_term` などの補助タグ |

## Number counter rules

`enable_number_rules=True` の場合、数詞 + 助数詞を 1 つの span として扱います。

```text
3人    -> さんにん
20歳   -> はたち
8本    -> はっぽん
```

単一 token と連続 token の両方に対応します。

```text
3人
3 + 人
二十 + 歳
```

現在の対象助数詞:

```text
人, 日, 本, 匹, 杯, 分, 回, 階, 冊, 枚, 個, 年, 歳
```

## Difficulty scoring

`enable_difficulty_scoring=True` の場合、`RubyToken` と `RubySpan` に `difficulty` が付きます。

```python
for span in analysis.spans:
    d = span.difficulty
    if d is None:
        continue
    print(span.surface, d.score, d.reasons)
```

`difficulty.score` は `0.0`–`1.0` のルビ必要度です。確率ではありません。`difficulty.reasons` は score の根拠タグです。

score は reason を family ごとに集約し、family 間を Noisy-OR で合成します。同系統のタグ、たとえば `proper_noun + person_name + rare_name` は過剰に加算されません。一方で、`ambiguous_reading + place_name + low_frequency_word` のように別系統の根拠が重なる場合は高くなります。

`always_ruby` は常に `1.0` です。ユーザー辞書の `difficulty_score` は、自動 score の下限として扱われます。

### Ruby target decision example

```python
for span in analysis.spans:
    d = span.difficulty
    if d is None:
        continue

    should_add_ruby = (
        d.score >= 0.6
        or "ambiguous_reading" in d.reasons
        or "number_counter" in d.reasons
        or "irregular_counter_reading" in d.reasons
        or "oov" in d.reasons
        or "fallback_reading" in d.reasons
    )
```

### Difficulty reasons

| reason | meaning |
|---|---|
| `ambiguous_reading` | 複数の読み候補がある |
| `resolved_by_context_rule` | 文脈ルールで読みを選択した |
| `low_candidate_margin` | 上位候補の score 差が小さい |
| `proper_noun` | 固有名詞 |
| `person_name` | 人名 |
| `place_name` | 地名 |
| `organization_name` | 組織名 |
| `product_name` | 製品名・型番 |
| `work_title` | 作品名・タイトル |
| `rare_name` | 難読名・希少名 |
| `number_counter` | 数詞 + 助数詞 |
| `irregular_counter_reading` | `20歳`, `8本` などの特殊読み |
| `oov` | 辞書外語 |
| `fallback_reading` | fallback で読みを作った |
| `long_kanji_compound` | 長い漢字複合語 |
| `alphabetic` | ラテン文字を含む |
| `mixed_script` | 文字種が混在している |
| `user_dictionary` | ユーザー辞書由来 |
| `manual_difficulty_override` | `difficulty_score` が指定された |
| `always_ruby` | 常時ルビ対象 |
| `low_frequency_word` | 頻度表で低頻度 |
| `very_low_frequency_word` | 頻度表で非常に低頻度 |
| `unknown_frequency` | 頻度表にない。既定では無効 |
| `low_frequency_compound` | 頻度表にない長い複合語 |
| `domain_term` | 専門語・ドメイン語 |
| `technical_term` | 科学技術系の専門語 |
| `medical_term` | 医学・生命科学系の専門語 |
| `chemical_term` | 化学系の専門語 |
| `science_term` | 科学技術系の専門語 |
| `computer_term` | 情報・計算機系の専門語 |

## Vocabulary frequency and domain dictionaries

語彙頻度表や専門語辞書を使うと、difficulty score に外部辞書由来の情報を反映できます。

| 目的 | 使う設定 | 主な入力 |
|---|---|---|
| 低頻度語を上げる | `frequency_dictionary_paths` | BCCWJ 語彙表 |
| 専門語を上げる | `domain_lexicon_paths` | NBDC 科学技術用語辞書 |
| 辞書にある長い語を 1 span にまとめる | `enable_lexicon_compound_spans` | BCCWJ / NBDC |

基本フロー:

1. 公式データを `data/` に置く
2. 付属 tool でこのライブラリ用 TSV に変換する
3. `AnalyzerConfig` に変換済み TSV のパスを渡す

辞書データ本体は同梱しません。ライセンスや利用条件は、BCCWJ / NBDC の公式配布元を確認してください。

### Data sources

#### BCCWJ frequency lists

| data | URL |
|---|---|
| 公式ページ | https://clrd.ninjal.ac.jp/bccwj/freq-list.html |
| 長単位語彙表 Version 1.0 | https://repository.ninjal.ac.jp/records/3228 |
| 短単位語彙表 Version 1.0 | https://repository.ninjal.ac.jp/records/3234 |

#### NBDC scientific term dictionaries

| data | URL |
|---|---|
| 公式 README | https://dbarchive.biosciencedbc.jp/data/mecab/LATEST/README.html |
| ダウンロードページ | https://dbarchive.biosciencedbc.jp/data/mecab/ |
| JST シソーラス CSV | https://dbarchive.biosciencedbc.jp/data/mecab/LATEST/mecab_thesaurus.zip |
| J-GLOBAL MeSH CSV | https://dbarchive.biosciencedbc.jp/data/mecab/LATEST/mecab_jstmesh.zip |
| 日化辞 CSV | https://dbarchive.biosciencedbc.jp/data/mecab/LATEST/mecab_nikkaji.zip |

NBDC の MeCab 用 `.dic` は、`domain_lexicon_paths` や Sudachi user dictionary に直接渡す形式ではありません。この README の変換例は CSV 形式の元データを前提にしています。

### Convert BCCWJ to frequency TSV

BCCWJ は語の頻度を見るために使います。一般的な語は低く、珍しい語は高く score に反映されます。

用意する元ファイル:

```text
data/BCCWJ_frequencylist_luw_ver1_0.tsv  # 長単位語彙表データ
data/BCCWJ_frequencylist_suw_ver1_0.tsv  # 短単位語彙表データ
```

変換コマンド:

```bash
python tools/convert_bccwj_frequency.py \
  --input data/BCCWJ_frequencylist_luw_ver1_0.tsv \
  --output data/bccwj_luw_frequency.tsv \
  --encoding utf-8-sig \
  --surface-col lemma \
  --base-form-col lemma \
  --reading-col lForm \
  --pos-col pos \
  --freq-col frequency \
  --rank-col rank \
  --unit luw \
  --source BCCWJ

python tools/convert_bccwj_frequency.py \
  --input data/BCCWJ_frequencylist_suw_ver1_0.tsv \
  --output data/bccwj_suw_frequency.tsv \
  --encoding utf-8-sig \
  --surface-col lemma \
  --base-form-col lemma \
  --reading-col lForm \
  --pos-col pos \
  --freq-col frequency \
  --rank-col rank \
  --unit suw \
  --source BCCWJ
```

出力:

```text
data/bccwj_luw_frequency.tsv
data/bccwj_suw_frequency.tsv
```


### Convert NBDC to domain term TSV

NBDC は「この語は科学技術・医学・化学などの専門語か」を見るために使います。

用意する元ファイル:

```text
data/mecab_thesaurus.csv  # JST シソーラス。まずはこれを使う。
data/mecab_jstmesh.csv    # 医学・生命科学を厚くしたい場合。
data/mecab_nikkaji.csv    # 化学を厚くしたい場合。
```

変換コマンド:

```bash
python tools/convert_nbdc_terms.py \
  --input data/mecab_thesaurus.csv \
  --output data/nbdc_thesaurus_terms.tsv \
  --encoding cp932 \
  --surface-col "Surface form" \
  --base-form-col "Base form" \
  --source-dictionary-col "Source dictionary" \
  --category-code-col "Category code" \
  --headword-flag-col "Headword Flag" \
  --common-word-flag-col "Common word flag 1" \
  --default-tags "technical_term;science_term"

python tools/convert_nbdc_terms.py \
  --input data/mecab_jstmesh.csv \
  --output data/nbdc_jstmesh_terms.tsv \
  --encoding cp932 \
  --surface-col "Surface form" \
  --base-form-col "Base form" \
  --source-dictionary-col "Source dictionary" \
  --category-code-col "Category code" \
  --headword-flag-col "Headword Flag" \
  --common-word-flag-col "Common word flag 1" \
  --default-tags "medical_term"

python tools/convert_nbdc_terms.py \
  --input data/mecab_nikkaji.csv \
  --output data/nbdc_nikkaji_terms.tsv \
  --encoding cp932 \
  --surface-col "Surface form" \
  --base-form-col "Base form" \
  --source-dictionary-col "Source dictionary" \
  --category-code-col "Category code" \
  --headword-flag-col "Headword Flag" \
  --common-word-flag-col "Common word flag 1" \
  --default-tags "chemical_term"
```

3 つをまとめる:

```bash
{
  head -n 1 data/nbdc_thesaurus_terms.tsv
  tail -n +2 data/nbdc_thesaurus_terms.tsv
  tail -n +2 data/nbdc_jstmesh_terms.tsv
  tail -n +2 data/nbdc_nikkaji_terms.tsv
} > data/nbdc_domain_terms.tsv
```

### Load converted dictionaries

```python
from furigana_spans import AnalyzerConfig, RubyAnalyzer

analyzer = RubyAnalyzer(
    AnalyzerConfig(
        enable_frequency_difficulty=True,
        frequency_dictionary_paths=(
            "./data/bccwj_luw_frequency.tsv",
            "./data/bccwj_suw_frequency.tsv",
        ),
        enable_domain_difficulty=True,
        domain_lexicon_paths=("./data/nbdc_domain_terms.tsv",),
    )
)

analysis = analyzer.analyze("重粒子線治療について説明します。")

for span in analysis.spans:
    if span.difficulty is None:
        continue
    print(span.surface, span.reading, span.difficulty.score, span.difficulty.reasons)
```

動作確認:

```bash
python examples/dictionary_difficulty_demo.py
```


### Effect on difficulty score

代表例:

```text
学校                 -> score 0.0    一般語なので上げない
日本橋               -> score 0.6175 同形異読 + 地名
3人                  -> score 0.5275 数詞 + 助数詞
重粒子線             -> score 0.7709 専門語 + 低頻度語
ニューラルネットワーク -> score 0.6150 専門語 + 低頻度語
アスピリン           -> score 0.5600 化学語 + 低頻度語
```

カタカナだけの専門語も span として出したい場合は、`include_tokens_without_kanji=True` を指定します。


### Lexicon-based compound spans

頻度表または専門語辞書に長い語があり、tokenizer がそれを複数 token に分割した場合、既定では連続 token をまとめた `lexicon_compound` span を追加します。

```text
深層 / 強化 / 学習
  -> 深層強化学習
```

`include_tokens_without_kanji=True` の場合は、専門語辞書にあるカタカナ複合語もまとめます。

```text
ニューラル / ネットワーク
  -> ニューラルネットワーク
```

無効化:

```python
config = AnalyzerConfig(enable_lexicon_compound_spans=False)
```

最大 n-gram 長:

```python
config = AnalyzerConfig(lexicon_compound_max_tokens=6)
```

## Example: selective ruby for TTS

```python
from furigana_spans import AnalyzerConfig, RubyAnalyzer

analyzer = RubyAnalyzer(
    AnalyzerConfig(
        enable_user_dictionary=True,
        user_dictionary_paths=("./user_dict.json",),
        enable_frequency_difficulty=True,
        frequency_dictionary_paths=(
            "./data/bccwj_luw_frequency.tsv",
            "./data/bccwj_suw_frequency.tsv",
        ),
        enable_domain_difficulty=True,
        domain_lexicon_paths=("./data/nbdc_domain_terms.tsv",),
    )
)

analysis = analyzer.analyze("重粒子線治療について説明します。")

ruby_targets = []
for span in analysis.spans:
    d = span.difficulty
    if d is None:
        continue
    if d.score >= 0.55 or "domain_term" in d.reasons:
        ruby_targets.append(span)
```
