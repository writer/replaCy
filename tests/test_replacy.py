import pytest
import spacy
from replacy import ReplaceMatcher
from replacy.db import get_match_dict
from functional import seq
xfail = pytest.mark.xfail

nlp = spacy.load("en_core_web_sm")

match_dict = get_match_dict()
r_matcher = ReplaceMatcher(nlp, match_dict)

def test_rules_positive():
    for rule_name in r_matcher.match_dict:

        rule_suggestions = []
        for suggestion in r_matcher.match_dict[rule_name]["suggestions"]:
            rule_suggestions.append(" ".join([t["TEXT"] for t in suggestion]))

        test_set = r_matcher.match_dict[rule_name]["test"]
        positive_set = test_set["positive"]

        for positive_sent in positive_set:
            all_suggestions = (
                seq(r_matcher(positive_sent))
                .flat_map(lambda span: span._.suggestions)
                .map(lambda x: x.lower())
                .list()
            )
            assert (
                len(set(rule_suggestions).intersection(set(all_suggestions))) > 0
            ), "should correct"


@xfail(raises=AssertionError)
def test_rules_negative():
    for rule_name in r_matcher.match_dict:

        rule_suggestions = []
        for suggestion in r_matcher.match_dict[rule_name]["suggestions"]:
            rule_suggestions.append(" ".join([t["TEXT"] for t in suggestion]))

        test_set = r_matcher.match_dict[rule_name]["test"]
        negative_set = test_set["negative"]

        for negative_sent in negative_set:
            all_suggestions = (
                seq(r_matcher(negative_sent))
                .flat_map(lambda span: span._.suggestions)
                .map(lambda x: x.lower())
                .list()
            )
            assert (
                len(set(rule_suggestions).intersection(set(all_suggestions))) > 0
            ), "should not correct"


def test_test_completeness():  # sic
    for rule_name in r_matcher.match_dict:
        test_set = r_matcher.match_dict[rule_name]["test"]
        assert (
            len(test_set["positive"]) > 0 and len(test_set["negative"]) > 0
        ), "missing test data"
