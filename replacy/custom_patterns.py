"""
This module contains predicates which influence what counts as a match
If the predicate (function) returns True, the match will be ignored
"""
import operator

from typing import List, Union


def compose(f, g):
    return lambda doc, start, end: f(g(doc, start, end))


def neg(f):
    # function negatin, ex. neg(preceeded_by_pos(pos))
    return compose(operator.not_, f)


def succeeded_by_phrase(phrase: Union[str, List[str]]):
    if isinstance(phrase, list):
        phrase_list = phrase

        def _succeeded_by_phrase(doc, start, end):
            bools = [doc[end:].text.lower().startswith(p.lower()) for p in phrase_list]
            return any(bools)

        return _succeeded_by_phrase
    elif isinstance(phrase, str):
        return lambda doc, start, end: doc[end:].text.lower().startswith(phrase.lower())
    else:
        raise ValueError(
            "args of succeeded_by_phrase should be a string or list of strings"
        )


def preceeded_by_phrase(phrase):
    return lambda doc, start, end: doc[:start].text.lower().endswith(phrase.lower())


def succeeded_by_pos(pos):
    return lambda doc, start, end: doc[end].pos_ == pos


def preceeded_by_pos(pos):
    return lambda doc, start, end: doc[start - 1].pos_ == pos


def succeeded_by_dep(dep):
    return lambda doc, start, end: doc[end].dep_ == dep


def preceeded_by_dep(dep):
    return lambda doc, start, end: doc[start - 1].dep_ == dep


def surrounded_by_phrase(phrase):
    def _surrounded_by_hook(doc, start, end):
        preceeds = doc[:start].text.lower().endswith(phrase.lower())
        follows = doc[end:].text.lower().startswith(phrase.lower())
        return preceeds and follows

    return _surrounded_by_hook
