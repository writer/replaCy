from typing import List

import pytest
import spacy
from spacy.tokens import Span
from spacy.util import filter_spans

from replacy import ReplaceMatcher
from replacy.suggestion import Suggestion

nlp = spacy.load("en_core_web_sm")

match_dict = {
    "hyuck": {
        "patterns": [{"LOWER": "hyuck"}],
        "suggestions": [[{"TEXT": "ha"}]],
        "test": {"positive": [], "negative": []},
    },
    "hyuck-hyuck": {
        "patterns": [{"LOWER": "hyuck"}, {"LOWER": "hyuck"}],
        "suggestions": [[{"TEXT": "haha"}]],
        "test": {"positive": [], "negative": []},
    },
}


def test_default_pipe():
    replaCy = ReplaceMatcher(nlp, match_dict)
    assert replaCy.pipe_names == ["sorter", "filter", "joiner"]


class NewComponent:
    gibberish = "jknasdkjna"

    def __init__(self, name="garbler"):
        self.name = name

    def __call__(self, spans: List[Span]):
        for s in spans:
            s._.suggestions = [[Suggestion(text=self.gibberish, max_count=1, id=69)]]


garbler = NewComponent()


def test_add_pipe_first():
    replaCy = ReplaceMatcher(nlp, match_dict)
    replaCy.add_pipe(garbler, first=True)
    assert replaCy.pipe_names == ["garbler", "sorter", "filter", "joiner"]


def test_add_pipe_last():
    replaCy = ReplaceMatcher(nlp, match_dict)
    replaCy.add_pipe(garbler, last=True)
    assert replaCy.pipe_names == ["sorter", "filter", "joiner", "garbler"]


def test_add_pipe_before():
    replaCy = ReplaceMatcher(nlp, match_dict)
    replaCy.add_pipe(garbler, before="joiner")
    assert replaCy.pipe_names == ["sorter", "filter", "garbler", "joiner"]


def test_add_pipe_after():
    replaCy = ReplaceMatcher(nlp, match_dict)
    replaCy.add_pipe(garbler, after="filter")
    assert replaCy.pipe_names == ["sorter", "filter", "garbler", "joiner"]


def test_component_added_after_filter_is_called():
    replaCy = ReplaceMatcher(nlp, match_dict)
    replaCy.add_pipe(garbler, after="filter")
    spans = replaCy("hyuck, that's funny")
    assert spans[0]._.suggestions[0] == NewComponent.gibberish


class FilterSpans:
    name = "filterSpans"

    def __init__(self):
        pass

    def __call__(self, spans):
        filtered = filter_spans(spans)
        for i, s in enumerate(spans):
            if s not in filtered:
                del spans[i]


def test_span_filter_component():
    replaCy = ReplaceMatcher(nlp, match_dict)
    spans = replaCy("hyuck hyuck")
    assert (
        len(spans) == 3
    ), "without span overlap filtering there are three spans (one for each hyuck, and one for both)"
    filterSpans = FilterSpans()
    replaCy.add_pipe(filterSpans, before="joiner")
    spans = replaCy("hyuck hyuck")
    assert len(spans) == 1, "with span overlap filtering there is only one span"
