import pytest
import spacy

from replacy import default_match_hooks
from replacy.db import get_patterns_test_data

nlp = spacy.load("en_core_web_sm")

examples_list = get_patterns_test_data()


@pytest.mark.parametrize("example", examples_list)
def test_custom_patterns(example):

    hook_name = example["hook_name"]

    if example.get("args", False):
        hook = getattr(default_match_hooks, hook_name)(example["args"])
    elif example.get("kwargs", False):
        hook = getattr(default_match_hooks, hook_name)(**example["kwargs"])
    else:
        hook = getattr(default_match_hooks, hook_name)()

    doc = nlp(example["text"])
    start = example["start"]
    end = example["end"]

    assert hook(doc, start, end) == example["result"], f"{hook_name} should work" + str(example["result"])
