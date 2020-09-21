import pytest
import spacy

from replacy import ReplaceMatcher
from replacy.db import get_match_dict

nlp = spacy.load("en_core_web_sm")
lm_path = "replacy/resources/test.arpa"

match_dict = get_match_dict()
r_matcher = ReplaceMatcher(nlp, match_dict, lm_path=lm_path)

dumb_matcher = ReplaceMatcher(nlp, match_dict, lm_path=None)

test_examples = [
    {
        "sent": "This x a sentence.",
        "span_start": 1,
        "span_end": 2,
        "suggestions": ["are", "were", "is"],
        "best_suggestion": "is",
    },
    {
        "sent": "This is x sentence.",
        "span_start": 2,
        "span_end": 3,
        "suggestions": ["two", "a", "cat"],
        "best_suggestion": "a",
    },
    {
        "sent": "This is a sentences.",
        "span_start": 3,
        "span_end": 4,
        "suggestions": ["sentence", "sentences", "dogs"],
        "best_suggestion": "sentence",
    },
]


@pytest.mark.parametrize("example", test_examples)
def test_scorer(example):
    doc = nlp(example["sent"])
    span = doc[example["span_start"] : example["span_end"]]
    span._.suggestions = example["suggestions"]

    sorted_suggestions = sorted(
        span._.suggestions,
        key=lambda x: r_matcher.scorer.score_suggestion(doc, span, [x]),
    )
    best_suggestion = sorted_suggestions[0]
    assert example["best_suggestion"] == best_suggestion
