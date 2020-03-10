import json

import pytest
import spacy
from replacy import ReplaceMatcher
from replacy.db import get_match_dict

nlp = spacy.load("en_core_web_sm")

with open("replacy/resources/match_dict.json", "r") as md:
    match_dict = json.load(md)
    r_matcher = ReplaceMatcher(nlp, match_dict)


# @TODO this should be more clear
# also, if the match_dict.json changes, this test breaks
# maybe we should build the match dict from a python dict, like in test_custom_props?
def test_part_of_compound():
    pos = "Our immediate requirement is extra staff."
    neg = "There is a residency requirement for obtaining citizenship."
    p_span = r_matcher(pos)[0]
    n_span = r_matcher(neg)
    assert p_span.text == "requirement", "part_of_compound hook should work"
    assert (
        len(n_span) == 0
    ), "part_of_compound working means not matching when part of compound"


def test_list_suc_pos():
    pos = r_matcher("She does a dance.")[0]
    assert pos._.suggestions == ["makes"]


def test_list_suc_pos_no():
    neg = r_matcher("I do fun things")
    assert len(neg) == 0


# @TODO test the rest of the functions in custom_patterns.py
