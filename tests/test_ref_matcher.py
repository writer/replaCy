import pytest
import spacy

from replacy import ReplaceMatcher

nlp = spacy.load("en_core_web_sm")

match_dict = {
    "match-1": {
        "patterns": [
            {"POS": {"NOT_IN": ["ADJ"]}, "OP": "*"},
            {"POS": "ADJ", "OP": "*"},
            {"POS": "NOUN"},
            {"LEMMA": "be", "TEMPLATE_ID": 1},
            {"LEMMA": "deliver"},
            {"IS_PUNCT": False, "OP": "*"},
            {"IS_PUNCT": True},
        ],
        "suggestions": [
            [
                {"TEXT": "A"},
                {"TEXT": "delivery"},
                {"TEXT": "of"},
                {"PATTERN_REF": 1},
                {"PATTERN_REF": 2},
                {"TEXT": "be", "FROM_TEMPLATE_ID": 1},
                {"TEXT": "made"},
                {"PATTERN_REF": -2},
                {"PATTERN_REF": -1},
            ]
        ],
        "test": {"positive": [], "negative": []},
    },
    "match-2": {
        "patterns": [
            {"TEXT": "I"},
            {"POS": "VERB",},
            {"POS": "DET", "OP": "?"},
            {"TEXT": "dog"},
            {"POS": "DET"},
            {"POS": "ADJ", "OP": "*"},
            {"POS": "NOUN"},
        ],
        "suggestions": [
            [
                {"PATTERN_REF": 0},
                {"PATTERN_REF": 1},
                {"PATTERN_REF": 4},
                {"PATTERN_REF": 5},
                {"PATTERN_REF": 6},
                {"TEXT": "to"},
                {"PATTERN_REF": 2},
                {"PATTERN_REF": 3},
            ]
        ],
        "test": {"positive": [], "negative": []},
    },
}

r_matcher = ReplaceMatcher(nlp, match_dict)

sents = [
    "The fresh juicy sandwiches were delivered to everyone at the shop before lunchtime.",
    "Looks like I fed the dog some popcorn.",
]

suggestions = [
    "A delivery of fresh juicy sandwiches was made to everyone at the shop before lunchtime .",
    "I fed some popcorn to the dog",
]


def test_refs():
    for sent, sugg in zip(sents, suggestions):
        span = r_matcher(sent)
        print(span[0])
        print(span[0]._.suggestions[0])
        assert span[0]._.suggestions[0] == sugg
