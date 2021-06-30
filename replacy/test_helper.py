import unittest
from typing import Any, Dict, List, Tuple

import spacy

from replacy import ReplaceMatcher
from replacy.db import get_match_dict


class MatchDictTestHelper(unittest.TestCase):

    @staticmethod
    def generate_cases(match_dict: Dict[str, Any]) -> Tuple[List[Tuple[str, str]], List[Tuple[str, str]]]:
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

    @classmethod
    def setUpClass(cls):
        nlp = spacy.load("en_core_web_sm")
        match_dict = get_match_dict()
        cls.r_matcher = ReplaceMatcher(nlp, match_dict)
        cls.positive_cases, cls.negative_cases = MatchDictTestHelper.generate_cases(match_dict)

    def test_positive(self):
        for (match_name, positive_sent) in self.positive_cases:
            spans = self.r_matcher(positive_sent)
            spans_from_this_rule = list(filter(lambda s: s._.match_name == match_name, spans))
            print(match_name, positive_sent)
            assert len(spans_from_this_rule) > 0, "Positive case should trigger rule"

    def test_negative(self):
        for (match_name, negative_sent) in self.negative_cases:
            spans = self.r_matcher(negative_sent)
            spans_from_this_rule = list(filter(lambda s: s._.match_name == match_name, spans))
            print(match_name, negative_sent)
            assert len(spans_from_this_rule) == 0, "Negative case should NOT trigger rule"
