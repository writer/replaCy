import pytest
import replacy.custom_patterns as custom_patterns
import spacy
from replacy.db import get_patterns_test_data

nlp = spacy.load("en_core_web_sm")

examples_list = get_patterns_test_data()


@pytest.mark.parametrize("example", examples_list)
def test_custom_patterns(example):

    hook_name = example["hook_name"]

    if example["args"]:
        hook = getattr(custom_patterns, hook_name)(example["args"])
    else:
        hook = hook = getattr(custom_patterns, hook_name)()

    doc = nlp(example["text"])
    start = example["start"]
    end = example["end"]

    assert hook(doc, start, end) == example["result"], f"{hook_name} should work"
