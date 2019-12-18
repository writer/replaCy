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
