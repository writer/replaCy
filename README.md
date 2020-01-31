# replaCy

We found that in multiple projects we had duplicate code for using spaCy’s blazing fast matcher to do the same thing: Match-Replace-Grammaticalize. So we wrote replaCy!

* Match - spaCy’s matcher is great, and lets you match on text, shape, POS, dependency parse, and other features. We extended this with “match hooks”,  predicates that get used in the callback function to further refine a match.

* Replace - Not built into spaCy’s matcher syntax, but easily added. You often want to replace a matched word with some other term.

* Grammaticalize - If you match on ”LEMMA”: “dance”, and replace with suggestions: ["sing"], but the actual match is danced, you need to conjugate “sing” appropriately. This is the “killer feature” of replaCy

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

## Testing match_dict (json schema validation)

```python
from replacy import ReplaceMatcher
from replacy.db import load_json

match_dict = load_json('/path/to/your/match/dict')
ReplaceMatcher.validate_match_dict(match_dict)
```
