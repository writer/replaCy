import json
import os
from typing import Any, Dict, List, Union

here = os.path.abspath(os.path.dirname(__file__))


def _load_list(paths: List[str]) -> dict:
    content: Dict[str, Any] = {}
    for p in paths:
        with open(p) as h:
            t = json.load(h)
            content.update(t)
    return content


def load_json(path_or_dir: Union[str, List[str]]) -> dict:
    path_error = (
        "replacy.db.load_json expects a valid path to a json file, "
        "a list of (valid) paths to json files, "
        "or the (valid) path to a directory with json files"
        f", but received {path_or_dir}"
    )
    if type(path_or_dir) == str:
        json_path = str(path_or_dir)  # make mypy happy
        if (
            os.path.exists(json_path)
            and os.path.isfile(json_path)
            and json_path[-5:] == ".json"
        ):
            with open(json_path) as h:
                content = json.load(h)
        elif os.path.isdir(json_path):
            paths = [
                os.path.join(json_path, f)
                for f in os.listdir(json_path)
                if f.endswith(".json")
            ]
            content = _load_list(paths)
        else:
            raise ValueError(path_error)
    elif type(path_or_dir) == list:
        paths = list(path_or_dir)  # for mypy
        content = _load_list(paths)
    else:
        raise TypeError(path_error)
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


def load_lm(model_path):
    import kenlm
    return kenlm.Model(model_path)
