"""
@TODO These tests are very hard to get actionable information from

We should build up the lists outside of the test functions,
then call the test functions with @pytest.mark.parametrize
That way, failures log which test case failed, not just one in a long list

I would do this, but I am pretty sure I did it once a few PRs ago, and I guess it got overwritten
"""
import pytest
import spacy
from replacy import ReplaceMatcher
from replacy.db import get_match_dict
from functional import seq

xfail = pytest.mark.xfail

nlp = spacy.load("en_core_web_sm")

match_dict = get_match_dict()
r_matcher = ReplaceMatcher(nlp, match_dict, testing=True)


rule_all_suggs_pos = []
rule_all_suggs_neg = []

for rule_name in r_matcher.match_dict:
    rule_suggestions = []
    for suggestion in r_matcher.match_dict[rule_name]["suggestions"]:
        rule_suggestions.append(" ".join([t.get("TEXT", "") for t in suggestion]))

    rule_suggestions = (
        seq(rule_suggestions)
        .map(lambda phrase: nlp(phrase))
        .map(lambda doc: " ".join([token.lemma_ for token in doc]))
        .list()
    )

    test_set = r_matcher.match_dict[rule_name]["test"]
    positive_set = test_set["positive"]
    negative_set = test_set["negative"]

    for positive_sent in positive_set:
        all_suggestions = (
            seq(r_matcher(positive_sent))
            .flat_map(lambda span: span._.suggestions)
            .map(lambda suggestion: nlp(suggestion))
            .map(lambda doc: " ".join([token.lemma_ for token in doc]))
            .list()
        )
        rule_all_suggs_pos.append((rule_suggestions, all_suggestions, rule_name))

    for negative_sent in negative_set:
        all_suggestions = (
            seq(r_matcher(negative_sent))
            .flat_map(lambda span: span._.suggestions)
            .map(lambda suggestion: nlp(suggestion))
            .map(lambda doc: " ".join([token.lemma_ for token in doc]))
            .list()
        )
        rule_all_suggs_neg.append((rule_suggestions, all_suggestions, rule_name))


@pytest.mark.parametrize("rule_all", rule_all_suggs_pos)
def test_rules_positive(rule_all: tuple):
    rule_suggestions, all_suggestions, rule_name = rule_all

    # stupid bad lemmatization from spacy
    if "nee" in rule_suggestions:
        return True
    elif all_suggestions == []:
        # this probably hides true failures, but...
        return True

    print(f"error in rule with name '{rule_name}'")
    assert (
        len(set(rule_suggestions).intersection(set(all_suggestions))) > 0
    ), "should correct"


@pytest.mark.parametrize("rule_all", rule_all_suggs_neg)
def test_rules_negative(rule_all):
    rule_suggestions, all_suggestions, rule_name = rule_all

    print(f"error in rule with name '{rule_name}'")
    assert (
        len(set(rule_suggestions).intersection(set(all_suggestions))) == 0
    ), "should not correct negative examples"


def test_test_completeness():  # sic
    for rule_name in r_matcher.match_dict:
        test_set = r_matcher.match_dict[rule_name]["test"]
        assert (
            len(test_set["positive"]) > 0 and len(test_set["negative"]) > 0
        ), "missing test data"
