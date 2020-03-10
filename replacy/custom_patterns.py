"""
This module contains predicates which influence what counts as a match
If the predicate (function) returns True, the match will be ignored
"""
import operator
from typing import Callable

from spacy.tokens.doc import Doc


SpacyMatchPredicate = Callable[[Doc, int, int], bool]


def compose(f, g):
    return lambda doc, start, end: f(g(doc, start, end))


def neg(f):
    # function negation, ex. neg(preceeded_by_pos(pos))
    return compose(operator.not_, f)


def succeeded_by_phrase(phrase) -> SpacyMatchPredicate:
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


def preceded_by_phrase(phrase) -> SpacyMatchPredicate:
    if isinstance(phrase, list):
        phrase_list = phrase

        def _preceded_by_phrase(doc, start, end):
            bools = [doc[end:].text.lower().endswith(p.lower()) for p in phrase_list]
            return any(bools)

        return _preceded_by_phrase
    elif isinstance(phrase, str):
        return lambda doc, start, end: doc[:start].text.lower().endswith(phrase.lower())
    else:
        raise ValueError(
            "args of preceded_by_phrase should be a string or list of strings"
        )


def succeeded_by_pos(pos) -> SpacyMatchPredicate:
    if isinstance(pos, list):
        pos_list = pos

        def _succeeded_by_pos(doc, start, end):
            bools = [doc[end].pos_ == p for p in pos_list]
            return any(bools)

        return _succeeded_by_pos
    elif isinstance(pos, str):
        return lambda doc, start, end: doc[end].pos_ == pos
    else:
        raise ValueError(
            "args of succeeded_by_pos should be a string or list of strings"
        )


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


def succeeded_by_dep(dep) -> SpacyMatchPredicate:
    if isinstance(dep, list):
        dep_list = dep

        def _succeeded_by_dep(doc, start, end):
            bools = [doc[end].dep_ == d for d in dep_list]
            return any(bools)

        return _succeeded_by_dep
    elif isinstance(dep, str):
        return lambda doc, start, end: doc[end].dep_ == dep
    else:
        raise ValueError(
            "args of succeeded_by_dep should be a string or list of strings"
        )


def preceded_by_dep(dep) -> SpacyMatchPredicate:
    if isinstance(dep, list):
        dep_list = dep

        def _preceded_by_dep(doc, start, end):
            bools = [doc[start - 1].dep_ == d for d in dep_list]
            return any(bools)

        return _preceded_by_dep
    elif isinstance(dep, str):
        return lambda doc, start, end: doc[start - 1].dep_ == dep
    else:
        raise ValueError(
            "args of preceded_by_dep should be a string or list of strings"
        )


def surrounded_by_phrase(phrase) -> SpacyMatchPredicate:
    def _surrounded_by_hook(doc, start, end):
        preceeds = doc[:start].text.lower().endswith(phrase.lower())
        follows = doc[end:].text.lower().startswith(phrase.lower())
        return preceeds and follows

    return _surrounded_by_hook


def part_of_compound() -> SpacyMatchPredicate:
    def _word_is_part_of_compound_hook(doc, start, end):
        head = doc[start]
        is_compound = head.dep_ == "compound"
        is_part_of_compound = any(
            [t.dep_ == "compound" and t.head == head for t in doc]
        )
        return is_compound or is_part_of_compound

    return _word_is_part_of_compound_hook


# for compatibilty with a previous version with spelling errors
# point incorrectly spelled versions to correct versions
# eventually deprecate these
preceeded_by_phrase = preceded_by_phrase
preceeded_by_pos = preceded_by_pos
preceeded_by_dep = preceded_by_dep
