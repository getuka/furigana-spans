"""Basic usage example for furigana-spans."""

from __future__ import annotations

from furigana_spans import AnalyzerConfig, RubyAnalyzer


def main() -> None:
    config = AnalyzerConfig(
        dictionary="core",
        split_mode="C",
        reading_script="hiragana",
    )
    analyzer = RubyAnalyzer(config)
    analysis = analyzer.analyze("静かな雨の朝、湯気の立つコーヒーを片手に窓の外を眺めていると、止まっていた時間が少しずつ動き出すような気がした。")
    for span in analysis.spans:
        print(span)


if __name__ == "__main__":
    main()
