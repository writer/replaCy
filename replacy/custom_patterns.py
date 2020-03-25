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


def relative_x_is_y(arglist) -> SpacyMatchPredicate:
    """
    Written because I wanted to not match the verb `require` if its subject was clausal
    aka if it had a child with child.dep_ == 'csubj'
    So I will match_if_hook_is: false
    e.g. usage looks like
        {
            "name": "relative_x_is_y",
            "args": [
                "children",
                "dep",
                "csubj"
            ],
            "match_if_predicate_is": false
        }
    And this can be read as "if any children of the matched pattern have
    child.dep_ == csubj, then don't match"
    """
    # custom patterns have to take one value as an arg, so destructure
    children_or_ancestors, pos_or_dep, value = arglist

    # asserting that values are acceptable lets us template them in
    assert children_or_ancestors == "children" or children_or_ancestors == "ancestors"
    assert pos_or_dep == "pos" or pos_or_dep == "dep"

    def _relatives_x_is_y(doc, start, end):
        if end - start != 1:
            # This only works if a single Token is matched,
            # not a Span
            print(
                "replaCy match rule relative_x_is_y should only be used "
                "on single token patterns, not for matching spans"
            )
            return False
        matched_token = doc[start]
        relatives = getattr(matched_token, children_or_ancestors, [])
        for rel in relatives:
            v = getattr(rel, f"{pos_or_dep}_", False)
            if v == value:
                return True
        return False

    return _relatives_x_is_y


def succeeded_by_num() -> SpacyMatchPredicate:
    return lambda doc, start, end: doc[end].like_num or doc[end].pos_ == "NUM" or doc[end].is_digit


def succeeded_by_currency() -> SpacyMatchPredicate:
    return lambda doc, start, end: doc[end].is_currency


# for compatibilty with a previous version with spelling errors
# point incorrectly spelled versions to correct versions
# eventually deprecate these
preceeded_by_phrase = preceded_by_phrase
preceeded_by_pos = preceded_by_pos
preceeded_by_dep = preceded_by_dep