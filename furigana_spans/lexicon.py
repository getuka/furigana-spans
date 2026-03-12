"""Built-in ambiguity lexicon and rule profiles."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AmbiguityProfile:
    """Context profile for a homographic reading candidate."""

    surface: str
    reading: str
    positive_keywords: tuple[str, ...] = ()
    negative_keywords: tuple[str, ...] = ()
    base_score: float = 0.55


BUILTIN_AMBIGUITY_PROFILES: tuple[AmbiguityProfile, ...] = (
    AmbiguityProfile(
        surface="日本橋",
        reading="にほんばし",
        positive_keywords=("東京", "中央区", "三越前", "室町", "銀座", "コレド"),
        negative_keywords=("大阪", "難波", "でんでんタウン", "オタロード", "堺筋"),
        base_score=0.6,
    ),
    AmbiguityProfile(
        surface="日本橋",
        reading="にっぽんばし",
        positive_keywords=("大阪", "難波", "でんでんタウン", "オタロード", "堺筋", "ミナミ"),
        negative_keywords=("東京", "中央区", "三越前", "室町", "銀座", "コレド"),
        base_score=0.6,
    ),
    AmbiguityProfile(
        surface="人気",
        reading="にんき",
        positive_keywords=("商品", "作品", "上昇", "話題", "ランキング", "俳優", "店"),
        negative_keywords=("ない", "少ない", "静か", "気配"),
        base_score=0.6,
    ),
    AmbiguityProfile(
        surface="人気",
        reading="ひとけ",
        positive_keywords=("ない", "少ない", "静か", "気配", "路地"),
        negative_keywords=("商品", "作品", "上昇", "話題", "ランキング"),
        base_score=0.55,
    ),
    AmbiguityProfile(
        surface="上手",
        reading="じょうず",
        positive_keywords=("歌", "料理", "絵", "演奏", "下手"),
        negative_keywords=("投げる", "位置", "手前"),
        base_score=0.6,
    ),
    AmbiguityProfile(
        surface="上手",
        reading="うわて",
        positive_keywords=("投げる", "位置", "手前", "下手", "役者"),
        negative_keywords=("歌", "料理", "絵", "演奏"),
        base_score=0.55,
    ),
    AmbiguityProfile(
        surface="明日",
        reading="あした",
        positive_keywords=("行く", "来る", "休み", "会う"),
        negative_keywords=("以降", "現在", "今日"),
        base_score=0.58,
    ),
    AmbiguityProfile(
        surface="明日",
        reading="あす",
        positive_keywords=("発表", "発送", "締切", "予定", "午前"),
        negative_keywords=("会う", "遊ぶ", "休み"),
        base_score=0.52,
    ),
    AmbiguityProfile(
        surface="市場",
        reading="しじょう",
        positive_keywords=("株", "証券", "成長", "拡大", "経済", "動向"),
        negative_keywords=("魚", "青果", "豊洲", "朝市"),
        base_score=0.58,
    ),
    AmbiguityProfile(
        surface="市場",
        reading="いちば",
        positive_keywords=("魚", "青果", "豊洲", "朝市", "買う"),
        negative_keywords=("株", "証券", "経済", "動向"),
        base_score=0.55,
    ),
)
