import json

import pytest
import spacy
from replacy import ReplaceMatcher
from replacy.db import get_match_dict

nlp = spacy.load("en_core_web_sm")

with open("replacy/resources/match_dict.json", "r") as md:
    match_dict = json.load(md)
    r_matcher = ReplaceMatcher(nlp, match_dict)

r_matcher.match_dict.update(
    {
        "sometest": {
            "patterns": [{"LOWER": "sometest"}],
            "suggestions": [[{"TEXT": "this part isn't the point"}]],
            "test": {"positive": ["positive test"], "negative": ["negative test"]},
            "comment": "this is an example comment",
            "description": 'The expression is "make do".',
            "category": "R:VERB",
            "yo": "yoyo",
            "whoa": ["it's", "a", "list"],
            "damn": {"a dict": "too?"},
            "nice": 69,
            "also_nice": 6.9,
            "meh": True,
        }
    }
)
new_matcher = ReplaceMatcher(nlp, r_matcher.match_dict)
matched_span = new_matcher("sometest")[0]
no_match_span = new_matcher("I will extract revenge")[0]


def test_custom_properties_string():
    assert no_match_span._.yo == "", "automatically infers string types"


def test_custom_properties_list():
    assert no_match_span._.whoa == [], "automatically infers list types"


def test_custom_properties_dict():
    assert no_match_span._.damn == {}, "automatically infers dict types"


def test_custom_properties_int():
    assert no_match_span._.nice == 0, "automatically infers int types"


def test_custom_properties_float():
    assert no_match_span._.also_nice == 0.0, "automatically infers float types"


def test_custom_properties_bool():
    assert no_match_span._.meh == False, "automatically infers bool types"
