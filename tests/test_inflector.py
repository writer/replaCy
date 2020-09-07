import pytest

from replacy.inflector import Inflector

inflector = Inflector()

inflector_dataset = [
    {
        "source": "Those are examples.",
        "target": "Those are rabbits.",
        "index": 2,
        "word": "rabbit",
    },
    {
        "source": "Stop avoiding the question.",
        "target": "Stop evading the question.",
        "index": 1,
        "word": "evade",
    },
    {
        "source": "She loves kittens.",
        "target": "She hates kittens.",
        "index": 1,
        "word": "hate",
    },
]


@pytest.mark.parametrize("data", inflector_dataset)
def test_inflector(data):
    assert (
        inflector.insert(data["source"], data["word"], data["index"]) == data["target"]
    ), "should inflect"


"""
Test lemmatization. 
Plural and singular forms of nouns should have common (or at least intersecting) sets of lemmas
Important for max count estimation (see: suggestion.py).

Exceptions to handle separately:
    {
        "plural":"person", 
        "singular": "people"
    },
    {
        "plural": "ox", 
        "singular": "oxen"
    }
"""

irregular_nouns = [
    {
        "plural":"elf", 
        "singular":"elves"
    },
    {
        "plural":"calf", 
        "singular": "calves"
    },
    {
        "plural":"knife", 
        "singular": "knives"
    },
    {
        "plural":"loaf", 
        "singular": "loaves"
    },
    {
        "plural":"shelf", 
        "singular": "shelves"
    },
    {
        "plural":"wolf", 
        "singular": "wolves"
    },
    {
        "plural":"loaf", 
        "singular": "loaves"
    },
    {
        "plural":"man", 
        "singular": "men"
    },
    {
        "plural":"mouse", 
        "singular": "mice"
    },
    {
        "plural":"child", 
        "singular": "children"
    },
    {
        "plural":"foot", 
        "singular": "feet"
    },
    {
        "plural":"goose", 
        "singular": "geese"
    },
    {
        "plural":"tooth", 
        "singular": "teeth"
    },
    {
        "plural":"louse", 
        "singular": "lice"
    },
    {
        "plural":"cactus", 
        "singular": "cacti"
    },
    {
        "plural": "appendix", 
        "singular": "appendices"
    },
    {
        "plural": "cod", 
        "singular": "cods"
    },
    {
        "plural": "shrimp", 
        "singular": "shrimps"
    },
    {
        "plural": "fish", 
        "singular": "fishes"
    },
    {
        "plural": "quail", 
        "singular": "quails"
    }
]

@pytest.mark.parametrize("pair", irregular_nouns)
def test_lemmatization(pair):
    singular_lemmas = set(inflector.get_lemmas(pair["singular"]))
    plural_lemmas = set(inflector.get_lemmas(pair["plural"]))

    assert len(singular_lemmas & plural_lemmas) > 0, "lemmas are different!"