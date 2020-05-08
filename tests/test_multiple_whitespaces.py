import pytest
import spacy
from replacy import ReplaceMatcher
from replacy.db import get_match_dict
from functional import seq

nlp = spacy.load("en_core_web_sm")

# minimal match dict with many whitespaces
match_dict = {
    "extract-revenge": {
        "patterns": [
            {
                "LEMMA": "extract",
                "TEMPLATE_ID": 1
            }
        ],
        "suggestions": [
            [
                {
                    "TEXT": "exact",
                    "FROM_TEMPLATE_ID": 1
                }
            ]
        ],
        "match_hook": [
            {
                "name": "succeeded_by_phrase",
                "args": "revenge",
                "match_if_predicate_is": True
            }
        ],
        "test": {
            "positive": [
                "And at the same time extract revenge on those he so despises?", # 0
                "Watch as Tampa Bay extracts  revenge against his former Los Angeles Rams team.", # 1
                "In fact, the farmer was so mean to this young man he determined to extract   revenge.", # 2
                "And at the same time extract          revenge on the whites he so despises?", # 10 sic
            ],
            "negative": [
                "Mother flavours her custards with lemon extract."
            ]
        }
    }
}

r_matcher = ReplaceMatcher(nlp, match_dict, allow_multiple_whitespaces=True)

def test_multiple_whites():
    sents = match_dict["extract-revenge"]["test"]["positive"]
    for sent in sents:
        assert len(r_matcher(sent)), "Should correct with multiple whitespaces"

        suggestion = r_matcher(sent)[0].text.strip()
        assert "extract" in suggestion, "Should correct with multiple whitespaces"
