"""Dictionary-backed difficulty scoring demo.

Run from the project root after creating the normalized dictionaries:

    python examples/dictionary_difficulty_demo.py
"""

from __future__ import annotations

from pathlib import Path

from furigana_spans import AnalyzerConfig, RubyAnalyzer

ROOT = Path(__file__).resolve().parents[1]
FREQUENCY_PATHS = (
    ROOT / "data" / "bccwj_luw_frequency.tsv",
    ROOT / "data" / "bccwj_suw_frequency.tsv",
)
DOMAIN_PATH = ROOT / "data" / "nbdc_domain_terms.tsv"

TEXTS = (
    "今日は学校で友達と昼ご飯を食べた。",
    "大阪の日本橋にある店へ3人で行く。",
    "音声合成モデルの評価にニューラルネットワークを使う。",
    "重粒子線治療について説明します。",
    "BRCA1遺伝子とタンパク質発現を解析した。",
    "アスピリンとクロロホルムの性質を比較した。",
)


def main() -> None:
    _require_dictionaries()

    analyzer = RubyAnalyzer(
        AnalyzerConfig(
            include_tokens_without_kanji=True,
            enable_frequency_difficulty=True,
            frequency_dictionary_paths=tuple(str(path) for path in FREQUENCY_PATHS),
            enable_domain_difficulty=True,
            domain_lexicon_paths=(str(DOMAIN_PATH),),
        )
    )

    print("解析開始")
    for text in TEXTS:
        print(f"\n{text}")
        analysis = analyzer.analyze(text)
        for span in analysis.spans:
            difficulty = span.difficulty
            if difficulty is None or difficulty.score < 0.2:
                continue
            reasons = ", ".join(difficulty.reasons) or "-"
            print(
                f"  {span.surface}\t{span.reading}\t"
                f"score={difficulty.score:.4f}\t{reasons}"
            )


def _require_dictionaries() -> None:
    missing = [path for path in (*FREQUENCY_PATHS, DOMAIN_PATH) if not path.exists()]
    if not missing:
        return
    missing_text = "\n".join(f"  - {path}" for path in missing)
    raise SystemExit(
        "Normalized dictionary files are missing. "
        "Create them with the README conversion commands first:\n"
        f"{missing_text}"
    )


if __name__ == "__main__":
    main()
