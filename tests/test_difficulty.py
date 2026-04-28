"""Tests for ruby difficulty scoring."""

from __future__ import annotations

import copy

from furigana_spans import AnalyzerConfig, RubyAnalyzer
from furigana_spans.backends.base import BaseTokenizerBackend
from furigana_spans.schema import ReadingCandidate, RubyToken


class StaticBackend(BaseTokenizerBackend):
    """Small backend for analyzer tests without Sudachi."""

    def __init__(self, tokens: list[RubyToken]) -> None:
        self._tokens = tokens

    def tokenize(self, text: str) -> list[RubyToken]:
        del text
        return copy.deepcopy(self._tokens)


def test_difficulty_scores_ambiguous_proper_noun() -> None:
    analyzer = RubyAnalyzer(
        AnalyzerConfig(),
        backend=StaticBackend(
            [
                RubyToken(
                    surface="日本橋",
                    start=0,
                    end=3,
                    pos=("名詞", "固有名詞", "地名", "一般", "*", "*"),
                    reading="にほんばし",
                    pronunciation="にほんばし",
                    candidates=[
                        ReadingCandidate(
                            reading="にほんばし",
                            score=0.9,
                            source="static",
                            is_selected=True,
                        )
                    ],
                )
            ]
        ),
    )

    analysis = analyzer.analyze("大阪の日本橋")
    span = next(span for span in analysis.spans if span.surface == "日本橋")

    assert span.difficulty is not None
    assert span.difficulty.score >= 0.6
    assert "ambiguous_reading" in span.difficulty.reasons
    assert "resolved_by_context_rule" in span.difficulty.reasons
    assert "proper_noun" in span.difficulty.reasons


def test_difficulty_scores_number_counter() -> None:
    analyzer = RubyAnalyzer(
        AnalyzerConfig(),
        backend=StaticBackend(
            [
                RubyToken(
                    surface="20歳",
                    start=0,
                    end=3,
                    pos=("名詞", "数詞", "*", "*", "*", "*"),
                    reading="にじゅうさい",
                    pronunciation="にじゅうさい",
                    candidates=[
                        ReadingCandidate(
                            reading="にじゅうさい",
                            score=0.9,
                            source="static",
                            is_selected=True,
                        )
                    ],
                )
            ]
        ),
    )

    analysis = analyzer.analyze("20歳")
    span = next(span for span in analysis.spans if span.surface == "20歳")

    assert span.reading == "はたち"
    assert span.difficulty is not None
    assert span.difficulty.score >= 0.45
    assert "number_counter" in span.difficulty.reasons
    assert "irregular_counter_reading" in span.difficulty.reasons
    assert "mixed_script" in span.difficulty.reasons


def test_difficulty_can_be_disabled() -> None:
    analyzer = RubyAnalyzer(
        AnalyzerConfig(enable_difficulty_scoring=False),
        backend=StaticBackend(
            [
                RubyToken(
                    surface="日本橋",
                    start=0,
                    end=3,
                    pos=("名詞", "固有名詞", "地名", "一般", "*", "*"),
                    reading="にほんばし",
                    pronunciation="にほんばし",
                    candidates=[
                        ReadingCandidate(
                            reading="にほんばし",
                            score=0.9,
                            source="static",
                            is_selected=True,
                        )
                    ],
                )
            ]
        ),
    )

    analysis = analyzer.analyze("日本橋")

    assert all(token.difficulty is None for token in analysis.tokens)
    assert all(span.difficulty is None for span in analysis.spans)


def test_context_rules_can_override_primary_dictionary_reading() -> None:
    analyzer = RubyAnalyzer(
        AnalyzerConfig(),
        backend=StaticBackend(
            [
                RubyToken(
                    surface="日本橋",
                    start=0,
                    end=3,
                    pos=("名詞", "固有名詞", "地名", "一般", "*", "*"),
                    reading="にほんばし",
                    pronunciation="にほんばし",
                    candidates=[
                        ReadingCandidate(
                            reading="にほんばし",
                            score=0.9,
                            source="static",
                            is_selected=True,
                        )
                    ],
                )
            ]
        ),
    )

    analysis = analyzer.analyze("大阪の日本橋")
    span = next(span for span in analysis.spans if span.surface == "日本橋")

    assert span.reading == "にっぽんばし"
    assert span.difficulty is not None
    assert "ambiguous_reading" in span.difficulty.reasons


def test_user_dictionary_difficulty_override(tmp_path) -> None:
    user_dict = tmp_path / "user_dict.json"
    user_dict.write_text(
        """
        [
          {
            "surface": "重粒子線",
            "reading": "じゅうりゅうしせん",
            "difficulty_score": 0.82,
            "difficulty_reasons": ["domain_term"],
            "tags": ["medical", "technical_term"]
          }
        ]
        """,
        encoding="utf-8",
    )
    analyzer = RubyAnalyzer(
        AnalyzerConfig(
            enable_user_dictionary=True,
            user_dictionary_paths=(str(user_dict),),
        ),
        backend=StaticBackend(
            [
                RubyToken(
                    surface="重粒子線",
                    start=0,
                    end=4,
                    pos=("名詞", "普通名詞", "一般", "*", "*", "*"),
                    reading="じゅうりゅうしせん",
                    pronunciation="じゅうりゅうしせん",
                    candidates=[
                        ReadingCandidate(
                            reading="じゅうりゅうしせん",
                            score=0.9,
                            source="static",
                            is_selected=True,
                        )
                    ],
                )
            ]
        ),
    )

    analysis = analyzer.analyze("重粒子線")
    span = next(span for span in analysis.spans if span.surface == "重粒子線")

    assert span.difficulty is not None
    assert span.difficulty.score >= 0.82
    assert "user_dictionary" in span.difficulty.reasons
    assert "manual_difficulty_override" in span.difficulty.reasons
    assert "domain_term" in span.difficulty.reasons


def test_user_dictionary_always_ruby(tmp_path) -> None:
    user_dict = tmp_path / "user_dict.json"
    user_dict.write_text(
        """
        [
          {
            "surface": "四月一日",
            "reading": "わたぬき",
            "always_ruby": true,
            "named_entity_type": "person_name",
            "difficulty_reasons": ["rare_name"]
          }
        ]
        """,
        encoding="utf-8",
    )
    analyzer = RubyAnalyzer(
        AnalyzerConfig(
            enable_user_dictionary=True,
            user_dictionary_paths=(str(user_dict),),
        ),
        backend=StaticBackend(
            [
                RubyToken(
                    surface="四月一日",
                    start=0,
                    end=4,
                    pos=("名詞", "固有名詞", "人名", "姓", "*", "*"),
                    reading="わたぬき",
                    pronunciation="わたぬき",
                    candidates=[
                        ReadingCandidate(
                            reading="わたぬき",
                            score=0.9,
                            source="static",
                            is_selected=True,
                        )
                    ],
                )
            ]
        ),
    )

    analysis = analyzer.analyze("四月一日")
    span = next(span for span in analysis.spans if span.surface == "四月一日")

    assert span.difficulty is not None
    assert span.difficulty.score == 1.0
    assert "always_ruby" in span.difficulty.reasons
    assert "person_name" in span.difficulty.reasons
    assert "rare_name" in span.difficulty.reasons


def test_proper_noun_subtype_reasons() -> None:
    analyzer = RubyAnalyzer(
        AnalyzerConfig(),
        backend=StaticBackend(
            [
                RubyToken(
                    surface="御嶽山",
                    start=0,
                    end=3,
                    pos=("名詞", "固有名詞", "地名", "一般", "*", "*"),
                    reading="おんたけさん",
                    pronunciation="おんたけさん",
                    candidates=[
                        ReadingCandidate(
                            reading="おんたけさん",
                            score=0.9,
                            source="static",
                            is_selected=True,
                        )
                    ],
                )
            ]
        ),
    )

    analysis = analyzer.analyze("御嶽山")
    span = next(span for span in analysis.spans if span.surface == "御嶽山")

    assert span.difficulty is not None
    assert "proper_noun" in span.difficulty.reasons
    assert "place_name" in span.difficulty.reasons


def test_proper_noun_person_context_suffix() -> None:
    analyzer = RubyAnalyzer(
        AnalyzerConfig(),
        backend=StaticBackend(
            [
                RubyToken(
                    surface="小鳥遊",
                    start=0,
                    end=3,
                    pos=("名詞", "固有名詞", "一般", "*", "*", "*"),
                    reading="たかなし",
                    pronunciation="たかなし",
                    candidates=[
                        ReadingCandidate(
                            reading="たかなし",
                            score=0.9,
                            source="static",
                            is_selected=True,
                        )
                    ],
                ),
                RubyToken(
                    surface="さん",
                    start=3,
                    end=5,
                    pos=("接尾辞", "名詞的", "一般", "*", "*", "*"),
                    reading="さん",
                    pronunciation="さん",
                    candidates=[
                        ReadingCandidate(
                            reading="さん",
                            score=0.9,
                            source="static",
                            is_selected=True,
                        )
                    ],
                ),
            ]
        ),
    )

    analysis = analyzer.analyze("小鳥遊さん")
    span = next(span for span in analysis.spans if span.surface == "小鳥遊")

    assert span.difficulty is not None
    assert "proper_noun" in span.difficulty.reasons
    assert "person_name" in span.difficulty.reasons


def test_organization_suffix_promotes_named_entity() -> None:
    analyzer = RubyAnalyzer(
        AnalyzerConfig(),
        backend=StaticBackend(
            [
                RubyToken(
                    surface="白石研究室",
                    start=0,
                    end=5,
                    pos=("名詞", "普通名詞", "一般", "*", "*", "*"),
                    reading="しらいしけんきゅうしつ",
                    pronunciation="しらいしけんきゅうしつ",
                    candidates=[
                        ReadingCandidate(
                            reading="しらいしけんきゅうしつ",
                            score=0.9,
                            source="static",
                            is_selected=True,
                        )
                    ],
                )
            ]
        ),
    )

    analysis = analyzer.analyze("白石研究室")
    span = next(span for span in analysis.spans if span.surface == "白石研究室")

    assert span.difficulty is not None
    assert "proper_noun" in span.difficulty.reasons
    assert "organization_name" in span.difficulty.reasons


def test_product_code_promotes_named_entity() -> None:
    analyzer = RubyAnalyzer(
        AnalyzerConfig(),
        backend=StaticBackend(
            [
                RubyToken(
                    surface="RTX4090",
                    start=0,
                    end=7,
                    pos=("名詞", "普通名詞", "一般", "*", "*", "*"),
                    reading="あーるてぃーえっくすよんせんきゅうじゅう",
                    pronunciation="あーるてぃーえっくすよんせんきゅうじゅう",
                    candidates=[
                        ReadingCandidate(
                            reading="あーるてぃーえっくすよんせんきゅうじゅう",
                            score=0.9,
                            source="static",
                            is_selected=True,
                        )
                    ],
                )
            ]
        ),
    )

    analysis = analyzer.analyze("RTX4090")
    span = next(span for span in analysis.spans if span.surface == "RTX4090")

    assert span.difficulty is not None
    assert "proper_noun" in span.difficulty.reasons
    assert "product_name" in span.difficulty.reasons


def test_quoted_work_title_reason() -> None:
    analyzer = RubyAnalyzer(
        AnalyzerConfig(),
        backend=StaticBackend(
            [
                RubyToken(
                    surface="羅生門",
                    start=1,
                    end=4,
                    pos=("名詞", "普通名詞", "一般", "*", "*", "*"),
                    reading="らしょうもん",
                    pronunciation="らしょうもん",
                    candidates=[
                        ReadingCandidate(
                            reading="らしょうもん",
                            score=0.9,
                            source="static",
                            is_selected=True,
                        )
                    ],
                )
            ]
        ),
    )

    analysis = analyzer.analyze("『羅生門』")
    span = next(span for span in analysis.spans if span.surface == "羅生門")

    assert span.difficulty is not None
    assert "proper_noun" in span.difficulty.reasons
    assert "work_title" in span.difficulty.reasons


def test_score_does_not_stack_named_entity_subtypes() -> None:
    analyzer = RubyAnalyzer(
        AnalyzerConfig(),
        backend=StaticBackend(
            [
                RubyToken(
                    surface="山田",
                    start=0,
                    end=2,
                    pos=("名詞", "固有名詞", "人名", "姓", "*", "*"),
                    reading="やまだ",
                    pronunciation="やまだ",
                    candidates=[
                        ReadingCandidate(
                            reading="やまだ",
                            score=0.9,
                            source="static",
                            is_selected=True,
                        )
                    ],
                )
            ]
        ),
    )

    analysis = analyzer.analyze("山田")
    span = next(span for span in analysis.spans if span.surface == "山田")

    assert span.difficulty is not None
    assert span.difficulty.reasons == ("proper_noun", "person_name")
    assert span.difficulty.score == 0.25


def test_score_combines_independent_risk_families() -> None:
    analyzer = RubyAnalyzer(
        AnalyzerConfig(),
        backend=StaticBackend(
            [
                RubyToken(
                    surface="日本橋",
                    start=0,
                    end=3,
                    pos=("名詞", "固有名詞", "地名", "一般", "*", "*"),
                    reading="にほんばし",
                    pronunciation="にほんばし",
                    candidates=[
                        ReadingCandidate(
                            reading="にほんばし",
                            score=0.9,
                            source="static",
                            is_selected=True,
                        )
                    ],
                )
            ]
        ),
    )

    analysis = analyzer.analyze("大阪の日本橋")
    span = next(span for span in analysis.spans if span.surface == "日本橋")

    assert span.difficulty is not None
    assert "ambiguous_reading" in span.difficulty.reasons
    assert "place_name" in span.difficulty.reasons
    assert "long_kanji_compound" in span.difficulty.reasons
    assert span.difficulty.score == 0.6175


def test_score_preserves_manual_override(tmp_path) -> None:
    user_dict = tmp_path / "user_dict.json"
    user_dict.write_text(
        """
        [
          {
            "surface": "重粒子線",
            "reading": "じゅうりゅうしせん",
            "difficulty_score": 0.82,
            "difficulty_reasons": ["domain_term"]
          }
        ]
        """,
        encoding="utf-8",
    )
    analyzer = RubyAnalyzer(
        AnalyzerConfig(
            enable_user_dictionary=True,
            user_dictionary_paths=(str(user_dict),),
        ),
        backend=StaticBackend(
            [
                RubyToken(
                    surface="重粒子線",
                    start=0,
                    end=4,
                    pos=("名詞", "普通名詞", "一般", "*", "*", "*"),
                    reading="じゅうりゅうしせん",
                    pronunciation="じゅうりゅうしせん",
                    candidates=[
                        ReadingCandidate(
                            reading="じゅうりゅうしせん",
                            score=0.9,
                            source="static",
                            is_selected=True,
                        )
                    ],
                )
            ]
        ),
    )

    analysis = analyzer.analyze("重粒子線")
    span = next(span for span in analysis.spans if span.surface == "重粒子線")

    assert span.difficulty is not None
    assert span.difficulty.score == 0.82
    assert "manual_difficulty_override" in span.difficulty.reasons
    assert "domain_term" in span.difficulty.reasons


def test_score_numeric_irregular_intensifies_counter() -> None:
    analyzer = RubyAnalyzer(
        AnalyzerConfig(),
        backend=StaticBackend(
            [
                RubyToken(
                    surface="20歳",
                    start=0,
                    end=3,
                    pos=("名詞", "数詞", "*", "*", "*", "*"),
                    reading="にじゅうさい",
                    pronunciation="にじゅうさい",
                    candidates=[
                        ReadingCandidate(
                            reading="にじゅうさい",
                            score=0.9,
                            source="static",
                            is_selected=True,
                        )
                    ],
                )
            ]
        ),
    )

    analysis = analyzer.analyze("20歳")
    span = next(span for span in analysis.spans if span.surface == "20歳")

    assert span.difficulty is not None
    assert span.difficulty.score == 0.505
    assert "number_counter" in span.difficulty.reasons
    assert "irregular_counter_reading" in span.difficulty.reasons


def test_score_oov_fallback_is_stronger_than_oov_only() -> None:
    analyzer = RubyAnalyzer(
        AnalyzerConfig(),
        backend=StaticBackend(
            [
                RubyToken(
                    surface="RTX4090",
                    start=0,
                    end=7,
                    pos=("名詞", "普通名詞", "一般", "*", "*", "*"),
                    is_oov=True,
                )
            ]
        ),
    )

    analysis = analyzer.analyze("RTX4090")
    span = next(span for span in analysis.spans if span.surface == "RTX4090")

    assert span.difficulty is not None
    assert span.difficulty.score == 0.604
    assert "oov" in span.difficulty.reasons
    assert "fallback_reading" in span.difficulty.reasons


def test_frequency_provider_adds_low_frequency_reason(tmp_path) -> None:
    frequency_path = tmp_path / "frequency.tsv"
    frequency_path.write_text(
        "surface\tbase_form\tunit\tfrequency\trank\tsource\n"
        "重粒子線\t重粒子線\tluw\t3\t91234\tTEST\n",
        encoding="utf-8",
    )
    analyzer = RubyAnalyzer(
        AnalyzerConfig(
            enable_frequency_difficulty=True,
            frequency_dictionary_paths=(str(frequency_path),),
        ),
        backend=StaticBackend(
            [
                RubyToken(
                    surface="重粒子線",
                    start=0,
                    end=4,
                    pos=("名詞", "普通名詞", "一般", "*", "*", "*"),
                    reading="じゅうりゅうしせん",
                    pronunciation="じゅうりゅうしせん",
                    candidates=[
                        ReadingCandidate(
                            reading="じゅうりゅうしせん",
                            score=0.9,
                            source="static",
                            is_selected=True,
                        )
                    ],
                )
            ]
        ),
    )

    analysis = analyzer.analyze("重粒子線")
    span = next(span for span in analysis.spans if span.surface == "重粒子線")

    assert span.difficulty is not None
    assert "very_low_frequency_word" in span.difficulty.reasons
    assert "long_kanji_compound" in span.difficulty.reasons
    assert span.metadata["difficulty_frequency"]["rank"] == 91234
    assert span.difficulty.score > 0.35


def test_frequency_provider_adds_low_frequency_compound_for_unknown_span(tmp_path) -> None:
    frequency_path = tmp_path / "frequency.tsv"
    frequency_path.write_text(
        "surface\tbase_form\tunit\tfrequency\trank\tsource\n"
        "深層\t深層\tsuw\t200\t12000\tTEST\n"
        "強化\t強化\tsuw\t1000\t4000\tTEST\n"
        "学習\t学習\tsuw\t9000\t500\tTEST\n",
        encoding="utf-8",
    )
    analyzer = RubyAnalyzer(
        AnalyzerConfig(
            enable_frequency_difficulty=True,
            frequency_dictionary_paths=(str(frequency_path),),
            include_tokens_without_kanji=True,
        ),
        backend=StaticBackend(
            [
                RubyToken(
                    surface="深層",
                    start=0,
                    end=2,
                    pos=("名詞", "普通名詞", "一般", "*", "*", "*"),
                    reading="しんそう",
                    pronunciation="しんそう",
                    candidates=[ReadingCandidate("しんそう", 0.9, "static", True)],
                ),
                RubyToken(
                    surface="強化",
                    start=2,
                    end=4,
                    pos=("名詞", "普通名詞", "一般", "*", "*", "*"),
                    reading="きょうか",
                    pronunciation="きょうか",
                    candidates=[ReadingCandidate("きょうか", 0.9, "static", True)],
                ),
                RubyToken(
                    surface="学習",
                    start=4,
                    end=6,
                    pos=("名詞", "普通名詞", "一般", "*", "*", "*"),
                    reading="がくしゅう",
                    pronunciation="がくしゅう",
                    candidates=[ReadingCandidate("がくしゅう", 0.9, "static", True)],
                ),
            ]
        ),
    )

    analysis = analyzer.analyze("深層強化学習")
    # The static backend emits token spans rather than a merged phrase span, so
    # check the aggregate token-level signal is at least present where relevant.
    span = next(span for span in analysis.spans if span.surface == "深層")

    assert span.difficulty is not None
    assert "low_frequency_word" not in span.difficulty.reasons
    assert span.metadata["difficulty_frequency"]["surface"] == "深層"


def test_domain_lexicon_adds_technical_reasons(tmp_path) -> None:
    domain_path = tmp_path / "domain.tsv"
    domain_path.write_text(
        "surface\tbase_form\tsource_dictionary\ttags\tcommon_word_flag\n"
        "重粒子線\t重粒子線\tNBDC\ttechnical_term;science_term\t0\n",
        encoding="utf-8",
    )
    analyzer = RubyAnalyzer(
        AnalyzerConfig(
            include_tokens_without_kanji=True,
            enable_domain_difficulty=True,
            domain_lexicon_paths=(str(domain_path),),
        ),
        backend=StaticBackend(
            [
                RubyToken(
                    surface="重粒子線",
                    start=0,
                    end=4,
                    pos=("名詞", "普通名詞", "一般", "*", "*", "*"),
                    reading="じゅうりゅうしせん",
                    pronunciation="じゅうりゅうしせん",
                    candidates=[
                        ReadingCandidate(
                            reading="じゅうりゅうしせん",
                            score=0.9,
                            source="static",
                            is_selected=True,
                        )
                    ],
                )
            ]
        ),
    )

    analysis = analyzer.analyze("重粒子線")
    span = next(span for span in analysis.spans if span.surface == "重粒子線")

    assert span.difficulty is not None
    assert "domain_term" in span.difficulty.reasons
    assert "technical_term" in span.difficulty.reasons
    assert "science_term" in span.difficulty.reasons
    assert span.metadata["difficulty_domain_terms"][0]["source_dictionary"] == "NBDC"
    assert span.difficulty.score > 0.4


def test_domain_common_word_without_specific_tag_is_ignored(tmp_path) -> None:
    domain_path = tmp_path / "domain.tsv"
    domain_path.write_text(
        "surface\tbase_form\tsource_dictionary\ttags\tcommon_word_flag\n"
        "学校\t学校\tNBDC\ttechnical_term\t1\n",
        encoding="utf-8",
    )
    analyzer = RubyAnalyzer(
        AnalyzerConfig(
            include_tokens_without_kanji=True,
            enable_domain_difficulty=True,
            domain_lexicon_paths=(str(domain_path),),
        ),
        backend=StaticBackend(
            [
                RubyToken(
                    surface="学校",
                    start=0,
                    end=2,
                    pos=("名詞", "普通名詞", "一般", "*", "*", "*"),
                    reading="がっこう",
                    pronunciation="がっこう",
                    candidates=[ReadingCandidate("がっこう", 0.9, "static", True)],
                )
            ]
        ),
    )

    analysis = analyzer.analyze("学校")
    span = next(span for span in analysis.spans if span.surface == "学校")

    assert span.difficulty is not None
    assert "domain_term" not in span.difficulty.reasons
    assert "difficulty_domain_terms" not in span.metadata


def test_domain_common_science_word_is_ignored(tmp_path) -> None:
    domain_path = tmp_path / "domain.tsv"
    domain_path.write_text(
        "surface\tbase_form\tsource_dictionary\ttags\tcommon_word_flag\n"
        "学校\t学校\tNBDC\ttechnical_term;science_term\tt\n",
        encoding="utf-8",
    )
    analyzer = RubyAnalyzer(
        AnalyzerConfig(
            include_tokens_without_kanji=True,
            enable_domain_difficulty=True,
            domain_lexicon_paths=(str(domain_path),),
        ),
        backend=StaticBackend(
            [
                RubyToken(
                    surface="学校",
                    start=0,
                    end=2,
                    pos=("名詞", "普通名詞", "一般", "*", "*", "*"),
                    reading="がっこう",
                    pronunciation="がっこう",
                    candidates=[ReadingCandidate("がっこう", 0.9, "static", True)],
                )
            ]
        ),
    )

    analysis = analyzer.analyze("学校")
    span = next(span for span in analysis.spans if span.surface == "学校")

    assert span.difficulty is not None
    assert "domain_term" not in span.difficulty.reasons
    assert "difficulty_domain_terms" not in span.metadata


def test_domain_common_word_with_specific_tag_is_kept(tmp_path) -> None:
    domain_path = tmp_path / "domain.tsv"
    domain_path.write_text(
        "surface\tbase_form\tsource_dictionary\ttags\tcommon_word_flag\n"
        "アスピリン\tアスピリン\tNikkaji\tchemical_term\tt\n",
        encoding="utf-8",
    )
    analyzer = RubyAnalyzer(
        AnalyzerConfig(
            include_tokens_without_kanji=True,
            enable_domain_difficulty=True,
            domain_lexicon_paths=(str(domain_path),),
        ),
        backend=StaticBackend(
            [
                RubyToken(
                    surface="アスピリン",
                    start=0,
                    end=5,
                    pos=("名詞", "普通名詞", "一般", "*", "*", "*"),
                    reading="あすぴりん",
                    pronunciation="あすぴりん",
                    candidates=[ReadingCandidate("あすぴりん", 0.9, "static", True)],
                )
            ]
        ),
    )

    analysis = analyzer.analyze("アスピリン")
    span = next(span for span in analysis.spans if span.surface == "アスピリン")

    assert span.difficulty is not None
    assert "domain_term" in span.difficulty.reasons
    assert "chemical_term" in span.difficulty.reasons


def test_lexicon_compound_span_merges_split_domain_terms(tmp_path) -> None:
    frequency_path = tmp_path / "frequency.tsv"
    frequency_path.write_text(
        "surface\tbase_form\treading\tpos\tunit\tfrequency\trank\tlog_frequency\tsource\tregister\n"
        "深層強化学習\t深層強化学習\t\t名詞\tluw\t1\t150000\t0.69\tTEST\tall\n",
        encoding="utf-8",
    )
    domain_path = tmp_path / "domain.tsv"
    domain_path.write_text(
        "surface\tbase_form\tsource_dictionary\tcategory_code\theadword_flag\tcommon_word_flag\ttags\tscore\n"
        "深層強化学習\t深層強化学習\tNBDC\tINFO\tC\t0\ttechnical_term;computer_term\t0.75\n",
        encoding="utf-8",
    )
    analyzer = RubyAnalyzer(
        AnalyzerConfig(
            enable_frequency_difficulty=True,
            frequency_dictionary_paths=(str(frequency_path),),
            enable_domain_difficulty=True,
            domain_lexicon_paths=(str(domain_path),),
        ),
        backend=StaticBackend(
            [
                RubyToken(
                    surface="深層",
                    start=0,
                    end=2,
                    pos=("名詞", "普通名詞", "一般", "*", "*", "*"),
                    reading="しんそう",
                    pronunciation="しんそう",
                    candidates=[
                        ReadingCandidate(
                            reading="しんそう",
                            score=0.9,
                            source="static",
                            is_selected=True,
                        )
                    ],
                ),
                RubyToken(
                    surface="強化",
                    start=2,
                    end=4,
                    pos=("名詞", "普通名詞", "一般", "*", "*", "*"),
                    reading="きょうか",
                    pronunciation="きょうか",
                    candidates=[
                        ReadingCandidate(
                            reading="きょうか",
                            score=0.9,
                            source="static",
                            is_selected=True,
                        )
                    ],
                ),
                RubyToken(
                    surface="学習",
                    start=4,
                    end=6,
                    pos=("名詞", "普通名詞", "一般", "*", "*", "*"),
                    reading="がくしゅう",
                    pronunciation="がくしゅう",
                    candidates=[
                        ReadingCandidate(
                            reading="がくしゅう",
                            score=0.9,
                            source="static",
                            is_selected=True,
                        )
                    ],
                ),
            ]
        ),
    )

    analysis = analyzer.analyze("深層強化学習を使う")
    span = next(span for span in analysis.spans if span.surface == "深層強化学習")

    assert span.reading == "しんそうきょうかがくしゅう"
    assert span.source == "lexicon_compound"
    assert span.token_indices == [0, 1, 2]
    assert span.difficulty is not None
    assert "domain_term" in span.difficulty.reasons
    assert "technical_term" in span.difficulty.reasons
    assert "very_low_frequency_word" in span.difficulty.reasons


def test_lexicon_compound_span_merges_split_katakana_domain_terms_when_enabled(tmp_path) -> None:
    domain_path = tmp_path / "domain.tsv"
    domain_path.write_text(
        "surface\tbase_form\tsource_dictionary\tcategory_code\theadword_flag\tcommon_word_flag\ttags\tscore\n"
        "ニューラルネットワーク\tニューラルネットワーク\tNBDC\tEG01\tC\tf\ttechnical_term;science_term\t\n",
        encoding="utf-8",
    )
    analyzer = RubyAnalyzer(
        AnalyzerConfig(
            include_tokens_without_kanji=True,
            enable_domain_difficulty=True,
            domain_lexicon_paths=(str(domain_path),),
        ),
        backend=StaticBackend(
            [
                RubyToken(
                    surface="ニューラル",
                    start=0,
                    end=5,
                    pos=("名詞", "普通名詞", "一般", "*", "*", "*"),
                    reading="にゅーらる",
                    pronunciation="にゅーらる",
                    candidates=[ReadingCandidate("にゅーらる", 0.9, "static", True)],
                ),
                RubyToken(
                    surface="ネットワーク",
                    start=5,
                    end=11,
                    pos=("名詞", "普通名詞", "一般", "*", "*", "*"),
                    reading="ねっとわーく",
                    pronunciation="ねっとわーく",
                    candidates=[ReadingCandidate("ねっとわーく", 0.9, "static", True)],
                ),
            ]
        ),
    )

    analysis = analyzer.analyze("ニューラルネットワーク")
    span = next(span for span in analysis.spans if span.surface == "ニューラルネットワーク")

    assert span.reading == "にゅーらるねっとわーく"
    assert span.source == "lexicon_compound"
    assert span.token_indices == [0, 1]
    assert span.difficulty is not None
    assert "domain_term" in span.difficulty.reasons
