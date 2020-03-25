import json
import os

here = os.path.abspath(os.path.dirname(__file__))


def load_json(json_path):
    with open(json_path) as h:
        content = json.load(h)
    return content


def get_forms_lookup(forms_path="resources/forms_lookup.json"):
    matches_path = os.path.join(here, forms_path)
    return load_json(matches_path)


def get_match_dict(match_path="resources/match_dict.json"):
    matches_path = os.path.join(here, match_path)
    return load_json(matches_path)

def get_match_dict_schema(schema_path="resources/match_dict_schema.json"):
    full_schema_path = os.path.join(here, schema_path)
    return load_json(full_schema_path)

def get_patterns_test_data(data_path="resources/patterns_test_data.json"):
    test_data_path = os.path.join(here, data_path)
    return load_json(test_data_path)