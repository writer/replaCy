from typing import Any, Dict, List, Tuple

import pytest
import spacy
from replacy import ReplaceMatcher
from replacy.db import get_match_dict
from functional import seq

xfail = pytest.mark.xfail

nlp = spacy.load("en_core_web_sm")

match_dict = get_match_dict()
r_matcher = ReplaceMatcher(nlp, match_dict)


def generate_cases(
    match_dict: Dict[str, Any]
) -> Tuple[List[Tuple[str, str]], List[Tuple[str, str]]]:
    positives: List[Tuple[str, str]] = []
    negatives: List[Tuple[str, str]] = []
    for rule_name in match_dict:
        test_set = match_dict[rule_name]["test"]
        positive_cases = test_set["positive"]
        negative_cases = test_set["negative"]
        for positive_sent in positive_cases:
            positives.append((rule_name, positive_sent))
        for negative_sent in negative_cases:
            negatives.append((rule_name, negative_sent))
    return positives, negatives


positive_cases, negative_cases = generate_cases(r_matcher.match_dict)


@pytest.mark.parametrize("match_name,positive_sent", positive_cases)
def test_positive(match_name: str, positive_sent: str):
    spans = r_matcher(positive_sent)
    spans_from_this_rule = list(filter(lambda s: s._.match_name == match_name, spans))
    print(match_name, positive_sent)
    assert len(spans_from_this_rule) > 0, "Positive case should trigger rule"


@pytest.mark.parametrize("match_name,negative_sent", negative_cases)
def test_rules_negative(match_name: str, negative_sent: str):
    spans = r_matcher(negative_sent)
    spans_from_this_rule = list(filter(lambda s: s._.match_name == match_name, spans))
    print(match_name, negative_sent)
    assert len(spans_from_this_rule) == 0, "Negative case should NOT trigger rule"


def test_test_completeness():  # sic
    for rule_name in r_matcher.match_dict:
        test_set = r_matcher.match_dict[rule_name]["test"]
        assert (
            len(test_set["positive"]) > 0 and len(test_set["negative"]) > 0
        ), "missing test data"
