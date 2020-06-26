import pytest
import spacy

from replacy import ReplaceMatcher
from replacy.db import get_match_dict

nlp = spacy.load("en_core_web_sm")
lm_path = "replacy/resources/test.arpa"

match_dict = get_match_dict()
r_matcher = ReplaceMatcher(nlp, match_dict, lm_path=lm_path)

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


def test_scorer():

    for example in test_examples:
        doc = nlp(example["sent"])
        span = doc[example["span_start"] : example["span_end"]]
        span._.suggestions = example["suggestions"]

        span_sorted = r_matcher.sort_suggestions(doc, [span])[0]
        best_suggestion = span_sorted._.suggestions[0]
        assert example["best_suggestion"] == best_suggestion
