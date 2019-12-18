# replaCy

## Requirements

- `spacy >= 2.0` (not installed by default, expected nlp object)


## Quick start

```python
from replacy import ReplaceMatcher
import spacy
from replacy.db import get_match_dict

# load custom match_dict, see example in : resources/match_dict.json
match_dict = get_match_dict()

# load nlp spacy model of your choice
nlp = spacy.load("en_core_web_sm")

rmatcher = ReplaceMatcher(nlp, match_dict)

# get inflected suggestions
# look up the first suggestion
span = rmatcher("She extracts revenge.")[0]
>>> span._.suggestions
['exacts']

```