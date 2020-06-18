# replaCy

We found that in multiple projects we had duplicate code for using spaCy’s blazing fast matcher to do the same thing: Match-Replace-Grammaticalize. So we wrote replaCy!

- Match - spaCy’s matcher is great, and lets you match on text, shape, POS, dependency parse, and other features. We extended this with “match hooks”, predicates that get used in the callback function to further refine a match.
- Replace - Not built into spaCy’s matcher syntax, but easily added. You often want to replace a matched word with some other term.
- Grammaticalize - If you match on ”LEMMA”: “dance”, and replace with suggestions: ["sing"], but the actual match is danced, you need to conjugate “sing” appropriately. This is the “killer feature” of replaCy

## Requirements

- `spacy >= 2.0` (not installed by default, but replaCy needs to be instantiated with an `nlp` object)

## Installation

`pip install replacy`

## Quick start

```python
from replacy import ReplaceMatcher
from replacy.db import load_json
import spacy


match_dict = load_json('/path/to/your/match/dict.json')
# load nlp spacy model of your choice
nlp = spacy.load("en_core_web_sm")

rmatcher = ReplaceMatcher(nlp)

# get inflected suggestions
# look up the first suggestion
span = rmatcher("She extracts revenge.")[0]
span._.suggestions
# >>> ['exacts']
```

## Input

ReplaceMatcher accepts both text and spaCy doc.

```python
# text is ok
span = r_matcher("She extracts reverge.")[0]

# doc is ok too
doc = nlp("She extracts reverge.")
span = r_matcher(doc)[0]
```

## Inflection library

ReplaCy uses inflection module underhood. Currently supported inflection libraries:

- [pyInflect](https://github.com/bjascob/pyinflect) - default
- [LemmInflect](https://github.com/bjascob/LemmInflect) - slower, more accurate

```python
# default initialization will load pyInflect
r_matcher = ReplaceMatcher(nlp)

# to use LemmInflect
r_matcher = ReplaceMatcher(nlp, lemmatizer="lemmInflect")
```

## match_dict.json format

Here is a minimal `match_dict.json`:

```json
{
  "extract-revenge": {
    "patterns": [
      {
        "LEMMA": "extract",
        "TEMPLATE_ID": 1
      }
    ],
    "suggestions": [
      [
        {
          "TEXT": "exact",
          "FROM_TEMPLATE_ID": 1
        }
      ]
    ],
    "match_hook": [
      {
        "name": "succeeded_by_phrase",
        "args": "revenge",
        "match_if_predicate_is": true
      }
    ],
    "test": {
      "positive": [
        "And at the same time extract revenge on those he so despises?",
        "Watch as Tampa Bay extracts revenge against his former Los Angeles Rams team."
      ],
      "negative": ["Mother flavours her custards with lemon extract."]
    }
  }
}
```

- The top-level key, `extract-revenge` must be unique (as must any dictionary key). The name is used as a unique identifier, but never shown.

- The inner keys are as follows

  - `patterns` - A list of [spaCy Matcher patterns](https://spacy.io/usage/rule-based-matching#matcher) (actually, a superset of a spaCy matcher pattern), which may look like e.g. `[{"LOWER": "hello"}, {"IS_PUNCT": True}, {"LOWER": "world"}]`. The added syntax which makes it a superset is being able to add `"TEMPLATE_ID": int` to some of the dicts. This labels that part of the match as a template to be inflected, such as a verb to conjugate or a noun to pluralize. In the above example, we label the lemma `extract` as having `TEMPLATE_ID` of `1`.
  - `suggestions` - a list of lists of dicts. The dicts have 1-2 keys:
    - just `"TEXT" (str)`, which will be used in the suggestion,
    - just `"PATTERN_REF" (int)`, which will copy the `PATTERN_REF`'s token from the matched text,
    - both `"TEXT": "sometext"` and `"FROM_TEMPLATE_ID": int`, which will apply the conjugation/pluralization of the `TEMPLATE_ID` with value `int` to `"TEXT"`. In the above example, suggestions is `[[{"TEXT":"exact","FROM_TEMPLATE_ID":1}]]`, which means we will match the conjugation of `exact` to the conjugation of `extracts`, from the step above,
    - both `"PATTERN_REF" (int)` and `"INFLECTION" (str)`, an explicit POS tag. Used when you want to reference the `PATTERN_REF`'s token from the pattern, but conjugate to a different form (so far I have only seen this used for grammar rules). Example: `{"PATTERN_REF": 1, "INFLECTION": "VBN"}` will take the second token from the matched pattern and conjugate it into the past particible.
  - `match_hook` - (despite the singular name) A list of "match hooks". These are Python functions which refine matches. See the following section.
  - `test` - has `positive` and `negative` keys. `positive` is a list of strings which this rule SHOULD match against, `negative` is a list of strings which SHOULD NOT match. Used for testing now, but we have plans to infer rules from this section.
  - (optional) `comment` - a string for other humans to read; ignored by replaCy
  - (optional) `anything` - you can add any extra structure here, and replaCy will attempt to tag matching spans with this information using the spaCy custom extension attributes namespace `span._` ([spaCy docs](https://spacy.io/usage/processing-pipelines#custom-components-attributes)). For example, you can add the key `oogly` with value `"boogly"` for the match `"LOWER": "secret password"`. Then if you call `span = rmatcher("This is the secret password.")[0]`, then `span._.oogly == "boogly"`.
    replaCy tries to be cool about default values with user-defined extensions. If you have a match with the key-value pair `"coolnes": 10`, replaCy will infer that `coolness` is an `int`. When it adds `coolness` to all spaCy spans, it will make it so `span._.coolness` defaults to `0`. This way, you can check all spans for `if span._.coolness > THRESHOLD` and not cause an `AttributeError`. You can change this the way you would change any spaCy custom attribute, e.g.

  ```python
    from spacy.tokens import Span

    Span.set_extension("coolness", default=9000)
  ```

Between match hooks and custom span attributes, replaCy is incredibly powerful, and allows you to control your NLP application's behavior from a single JSON file.

### Match hooks

Match hooks are powerful and somewhat confusing. replaCy provides a starting kit of hooks, but since they are just Python functions, you can supply your own. To see all the built in hooks, see [default_match_hooks.py](https://github.com/Qordobacode/replaCy/blob/master/replacy/default_match_hooks.py). An example is `preceded_by_pos`, which is copied here in full. Notice the signature of the function; if this interests you, see the next subsection, "Hooks Return Predicates".

```python
SpacyMatchPredicate = Callable[[Doc, int, int], bool]

def preceded_by_pos(pos) -> SpacyMatchPredicate:
    if isinstance(pos, list):
        pos_list = pos

        def _preceded_by_pos(doc, start, end):
            bools = [doc[start - 1].pos_ == p for p in pos_list]
            return any(bools)

        return _preceded_by_pos
    elif isinstance(pos, str):
        return lambda doc, start, end: doc[start - 1].pos_ == pos
    else:
        raise ValueError(
            "args of preceded_by_pos should be a string or list of strings"
        )
```

This allows us to put in our `match_dict.json` a hook that effectively says "only do this spaCy match is the preceding POS tag is `pos`, where `pos` is either a string, like `"NOUN"`, or a list such as `["NOUN", "PROPN"]`. Here is the most complicated replaCy match I have written, which demonstrates the use of many hooks:

```json
{
  "require": {
    "patterns": [
      {
        "LEMMA": "require",
        "POS": "VERB",
        "DEP": {
          "NOT_IN": ["amod"]
        },
        "TEMPLATE_ID": 1
      }
    ],
    "suggestions": [
      [
        {
          "TEXT": "need",
          "FROM_TEMPLATE_ID": 1
        }
      ]
    ],
    "match_hook": [
      {
        "name": "succeeded_by_phrase",
        "args": "that",
        "match_if_predicate_is": false
      },
      {
        "name": "succeeded_by_phrase",
        "args": "of",
        "match_if_predicate_is": false
      },
      {
        "name": "preceded_by_dep",
        "args": "auxpass",
        "match_if_predicate_is": false
      },
      {
        "name": "relative_x_is_y",
        "args": ["children", "dep", "csubj"],
        "match_if_predicate_is": false
      }
    ],
    "test": {
      "positive": [
        "Those require more consideration.",
        "Your condition is serious and requires surgery.",
        "I require stimulants to function."
      ],
      "negative": [
        "My pride requires of me that I tell you to piss off.",
        "Is there any required reading?",
        "I am required to tell you that I am a registered Mex offender - I make horrible nachos.",
        "Deciphering the code requires an expert.",
        "Making small models requires manual skill."
      ]
    },
    "comment": "The pattern includes DEP NOT_IN amod because of expresssions like 'required reading' and the relative_x_is_y hook is because this doesn't work for clausal subjects"
  }
}
```

#### Hooks Return Predicates

To be a match hook, a Python function must take 1 or 0 arguments, and return a predicate (function which returns a boolean) with inputs `(doc, start, end)`. If you read about the spaCy Matcher, you will understand why the arguments are `doc, start, end`. The reason match hooks RETURN a predicate, rather than BEING a predicate is for flexibility. It allows us to have `preceded_by_pos` instead of `preceded_by_noun`, `preceded_by_adj`, etc.

The structure of a match hook is:

- `name`, the name of the Python function
- (optional) `args` - the argument of the function. Yes, argument, singular - match hooks take one or zero arguments. If you need more than one argument, have the hook accept a dict or list.
- `match_if_predicate_is` - a boolean which flips the behavior from "if this predicate is true, then match" or "if this predicate is false, then match". This is just to make naming functions easier. For example, we have `preceded_by_pos` as a hook, with `arg: "NOUN"`, and `match_if_predicate_is` set to `true`. This hook is much more sensible than `not_preceded_by_pos`, with args `[every, pos, but, NOUN]`.

To use your own match hooks, instantiate the replace matcher with a module containing them, e.g.

```python
    from replacy import ReplaceMatcher
    from replacy.db import load_json
    import spacy

    # import the module with your hooks
    # the name doesn't matter, it just needs to be a python module
    import my.custom_hooks as ch


    nlp = spacy.load("en_core_web_sm")
    rmatch_dict = load_json("./resources/match_dict.json")
    # pass replaCy your custom hooks here, and then they are usable in your match_dict.json
    rmatcher = ReplaceMatcher(nlp, rmatch_dict, custom_match_hooks=ch)
    span = rmatcher("She excepts her fate.")[0]
    span._.suggestions
    # >>> ['acccepts']
```

#### Context matching

Currently replaCy only supports string-based context using match hooks. The way to do this is by using the match hooks part_of_phrase and sentence_has. The match hook part_of_phrase checks if the matched phrase is part of the given input phrase to the hook, and sentence_has checks whether or not the sentence including the matched phrase contains the word or words given as input. An example would be if you wanted to suggest that the word "apples" be changed to its scientific name, except when it's a Rick and Morty reference. To do this you could use the following:

```json
{
    ...,
    "apples-example": {
        "patterns": [
            {
                "LEMMA": "apple",
                "TEMPLATE_ID": 1
            }
        ],
        "suggestions": [
            [
                {
                    "TEXT": "malus"
                },
                {
                    "TEXT": "domestica",
                    "FROM_TEMPLATE_ID": 1
                }
            ]
        ],
        "match_hook": [
            {
                "name": "part_of_phrase",
                "args": "hungry for apples",
                "match_if_predicate_is": false
            },
            {
                "name": "sentence_has",
                "args": [
                    "rick",
                    "morty",
                    "jerry",
                    "wubba lubba"
                ],
                "match_if_predicate_is": false
            }
        ],
        "comment": "Change apple to its scientific name unless part of a Rick and Morty reference"
    }
}
```

## Testing match_dict (JSON schema validation)

```python
from replacy import ReplaceMatcher
from replacy.db import load_json

match_dict = load_json('/path/to/your/match/dict')
ReplaceMatcher.validate_match_dict(match_dict)
```

## Multiple spaces support

Sometimes text input includes unwated signs, such as:

- non printable unicode signs (see: https://www.soscisurvey.de/tools/view-chars.php)
- non standard whitespaces (see: https://en.wikipedia.org/wiki/Whitespace_character)

ex. `"Here␣is␣a\u180E\u200Bproblem."`

For SpaCy, only most common ascii whitespace `\u0020` is translated as a whitespace spearator.

You might want to project nonstandard signs into whitespaces before processing,

`"Here␣is␣a\u180E\u200Bproblem." -> "Here␣is␣a␣␣problem."`

but getting rid of multiple spaces is not always possible (this would change span char ranges).
Since extra spaces are grouped as one token with propery `IS_SPACE: True`,
patterns in `match_dict` should have extra whitespace tokens:

ex.

```
"patterns": [
                {
                    "LOWER": "a"
                },
                {
                    "IS_SPACE": True, "OP": "?"
                },
                {
                    "LOWER": "problem"
                }
            ]
```

To keep `preceded_by...` and `succeeded_by...` match hooks working, add whitespace tokens before and after each pattern.
In order to automatically add whitespace tokens to all patterns in your `match_dict`, use:

`r_matcher = ReplaceMatcher(nlp, match_dict, allow_multiple_whitespaces=True)`

By default `allow_multiple_whitespaces` is set to `False`.
