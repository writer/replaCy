import json
import os

here = os.path.abspath(os.path.dirname(__file__))


def load_json(json_path):
    with open(json_path) as h:
        content = json.load(h)
    return content


def get_forms_dict():
    matches_path = os.path.join(here, "resources/forms_dict.json")
    return load_json(matches_path)


def get_match_dict():
    matches_path = os.path.join(here, "resources/match_dict.json")
    return load_json(matches_path)
