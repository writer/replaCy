import pytest
import spacy

from replacy import ReplaceMatcher

nlp = spacy.load("en_core_web_sm")

# They read us the stories they themselves had written.

match_dict = {
    "match-1": {
        "patterns": [
            {"LOWER": {"IN": ["they", "she"]}},
            {"LEMMA": "read", "TEMPLATE_ID": 1},
            {"LOWER": "us"},
            {"LOWER": "the"},
            {"LEMMA": "story", "TEMPLATE_ID": 1},
            {"LOWER": {"IN": ["they", "she"]}},
            {"LOWER": {"IN": ["themselves", "herself"]}},
            {"LEMMA": "have", "OP": "*"},
            {"LEMMA": {"IN": ["write", "made"]}},
        ],
        "suggestions": [
            [
                {"PATTERN_REF": 0},
                {"TEXT": {"IN": ["sing", "give"]}, "FROM_TEMPLATE_ID": 1},
                {"PATTERN_REF": 2},
                {"TEXT": {"IN": ["a", "the", "some"]}},
                {"TEXT": "story", "INFLECTION": "NOUN"},
                {"PATTERN_REF": 5, "REPLACY_OP": "UPPER"},
                {"PATTERN_REF": 6},
                {"TEXT": {"IN": ["write", "made", "create"]}, "INFLECTION": "VBD"},
            ]
        ],
        "test": {"positive": [], "negative": []},
    }
}

output = [
    "They sang us a stories THEY themselves wrote",
    "They sang us a stories THEY themselves made",
    "They sang us a stories THEY themselves created",
    "They gave us a stories THEY themselves wrote",
    "They gave us a stories THEY themselves made",
    "They gave us a stories THEY themselves created",
    "They sang us the story THEY themselves wrote",
    "They sang us the story THEY themselves made",
    "They sang us the story THEY themselves created",
    "They gave us the story THEY themselves wrote",
    "They gave us the story THEY themselves made",
    "They gave us the story THEY themselves created",
]

r_matcher = ReplaceMatcher(
    nlp, match_dict=match_dict, lm_path="./replacy/resources/test.arpa"
)


def test_suggestions():
    spans = r_matcher("They read us the stories they themselves had written.")
    suggestions = spans[0]._.suggestions
    assert all([a == b for a, b in zip(suggestions, output)])
