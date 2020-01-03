# replaCy

## Requirements

- `spacy >= 2.0` (not installed by default, expected nlp object)

## Installation

`pip install replacy`

## Quick start

```python
from replacy import ReplaceMatcher
import spacy


# load nlp spacy model of your choice
nlp = spacy.load("en_core_web_sm")

rmatcher = ReplaceMatcher(nlp)

# get inflected suggestions
# look up the first suggestion
span = rmatcher("She extracts revenge.")[0]
span._.suggestions
# >>> ['exacts']
```
