import json
from replacy import ReplaceMatcher
from replacy.db import get_match_dict

with open("replacy/resources/match_dict.json", "r") as f:
    rules = json.load(f)


def test_file_exists():
    assert rules is not None


# spacy 3 requires a new schema
# def test_valid_format():
#     match_dict = get_match_dict()
#     ReplaceMatcher.validate_match_dict(match_dict)
