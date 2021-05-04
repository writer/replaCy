"""
This module contains predicates which influence what counts as a match
If the predicate (function) returns True, the match will be ignored
"""
import operator
import sys
from typing import Callable, List, Union

from spacy.tokens.doc import Doc

SpacyMatchPredicate = Callable[[Doc, int, int], bool]


def _check_args(x):
    """
    get calling function name to give a nice error message
    """
    caller = sys._getframe(1).f_code.co_name
    if not isinstance(x, (list, str)):
        raise ValueError(f"args of {caller} should be a string or list of strings")


def compose(f, g):
    return lambda doc, start, end: f(g(doc, start, end))


def neg(f):
    # function negation, ex. neg(preceded_by_pos(pos))
    return compose(operator.not_, f)


def succeeded_by_phrase(phrases) -> SpacyMatchPredicate:
    _check_args(phrases)
    if not isinstance(phrases, list):
        phrases = [phrases]

    def _succeeded_by_phrase(doc, start, end):
        if end >= len(doc):
            return False
        return any([doc[end:].text.lower().startswith(p.lower()) for p in phrases])

    return _succeeded_by_phrase


def preceded_by_phrase(phrases) -> SpacyMatchPredicate:
    _check_args(phrases)
    if not isinstance(phrases, list):
        phrases = [phrases]

    def _preceded_by_phrase(doc, start, end):
        if start <= 0:
            return False
        return any([doc[:start].text.lower().endswith(p.lower()) for p in phrases])

    return _preceded_by_phrase


def succeeded_by_pos(pos) -> SpacyMatchPredicate:
    _check_args(pos)
    if not isinstance(pos, list):
        pos = [pos]

    def _succeeded_by_pos(doc, start, end):
        if end >= len(doc):
            return False
        bools = [doc[end].pos_ == p for p in pos]
        return any(bools)

    return _succeeded_by_pos


def preceded_by_pos(pos) -> SpacyMatchPredicate:
    _check_args(pos)
    if not isinstance(pos, list):
        pos = [pos]

    def _preceded_by_pos(doc, start, end):
        if start <= 0:
            return False
        bools = [doc[start - 1].pos_ == p for p in pos]
        return any(bools)

    return _preceded_by_pos


def succeeded_by_lemma(lemma) -> SpacyMatchPredicate:
    _check_args(lemma)
    if not isinstance(lemma, list):
        lemma = [lemma]

    def _succeeded_by_lemma(doc, start, end):
        if end >= len(doc):
            return False
        bools = [doc[end].lemma_ == l for l in lemma]
        return any(bools)

    return _succeeded_by_lemma


def preceded_by_lemma(lemma, distance=1) -> SpacyMatchPredicate:
    _check_args(lemma)
    if not isinstance(lemma, list):
        lemma = [lemma]

    def _preceded_by_lemma(doc, start, end):
        if start < distance:
            return False
        bools = [doc[start - distance].lemma_ == l for l in lemma]
        return any(bools)

    return _preceded_by_lemma


def succeeded_by_dep(dep) -> SpacyMatchPredicate:
    _check_args(dep)
    if not isinstance(dep, list):
        dep = [dep]

    def _succeeded_by_dep(doc, start, end):
        if end >= len(doc):
            return False
        bools = [doc[end].dep_ == d for d in dep]
        return any(bools)

    return _succeeded_by_dep


def preceded_by_dep(dep) -> SpacyMatchPredicate:
    _check_args(dep)
    if not isinstance(dep, list):
        dep = [dep]

    def _preceded_by_dep(doc, start, end):
        if start <= 0:
            return False
        bools = [doc[start - 1].dep_ == d for d in dep]
        return any(bools)

    return _preceded_by_dep


def sentence_has(phrases) -> SpacyMatchPredicate:
    _check_args(phrases)
    if not isinstance(phrases, list):
        phrases = [phrases]

    def _sentence_has(doc, start, end):
        sents = list(doc.sents)
        totalnum = 0
        sentnum = 0
        for sent in sents:
            totalnum += len(sent)
            if start > totalnum - 1:
                sentnum += 1
        bools = [p in sents[sentnum].text.lower() for p in phrases]
        return any(bools)

    return _sentence_has


def surrounded_by_phrase(phrase) -> SpacyMatchPredicate:
    def _surrounded_by_hook(doc, start, end):
        if start <= 0 or end >= len(doc):
            return False
        precedes = doc[:start].text.lower().endswith(phrase.lower())
        follows = doc[end:].text.lower().startswith(phrase.lower())
        return precedes and follows

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


def relative_x_is_y(
    children_or_ancestors: str,
    pos_or_dep: str,
    value: str,
    text: Union[str, List] = None,
    lemma: Union[str, List] = None,
) -> SpacyMatchPredicate:
    """
    This is a buggy, half-implementation of a DependencyMatcher, eventually
    replaCy should allow access to spaCy's DependencyMatcher

    Though it's grown, this was originally written because I wanted to
    not match the verb `require` if its subject was clausal
    aka if it had a child with child.dep_ == 'csubj'
    So I will match_if_hook_is: false
    e.g. usage looks like
        {
            "name": "relative_x_is_y",
            "kwargs": {
                "children_or_ancestors": "children",
                "pos_or_dep": "dep",
                "value": "csubj"
            },
            "match_if_predicate_is": false
        }
    And this can be read as "if any children of the matched pattern have
    child.dep_ == csubj, then don't match"
    """

    # asserting that values are acceptable lets us template them in
    assert children_or_ancestors == "children" or children_or_ancestors == "ancestors"
    assert pos_or_dep == "pos" or pos_or_dep == "dep"
    assert text is None or lemma is None

    def _relatives_x_is_y(doc, start, end):
        def _helper(rel, pos_or_dep, value, text, lemma):
            v = getattr(rel, f"{pos_or_dep}_", False)
            if v == value:
                if text == None and lemma == None:
                    return True
                elif text is not None:
                    if type(text) == str:
                        return rel.text == text
                    elif type(text) == list:
                        return any([rel.text == t for t in text])
                elif lemma is not None:
                    if type(lemma) == str:
                        return rel.lemma_ == lemma
                    elif type(lemma) == list:
                        return any([rel.lemma_ == l for l in lemma])
            else:
                return False

        if end - start != 1:
            # This only works if a single Token is matched,
            # not a Span
            print(
                "replaCy match rule relative_x_is_y should only be used "
                "on single token patterns, not for matching spans"
            )
            return False
        matched_token = doc[start]
        relatives = list(getattr(matched_token, children_or_ancestors, []))
        if len(relatives) and children_or_ancestors == "ancestors":
            # with ancestors we really only want the first, the rest are too unrelated
            rel = relatives[0]
            return _helper(rel, pos_or_dep, value, text, lemma)
        else:
            for rel in relatives:
                return any([_helper(rel, pos_or_dep, value, text, lemma)])
        return False

    return _relatives_x_is_y


def part_of_phrase(phrase) -> SpacyMatchPredicate:
    def _part_of_phrase(doc, start, end):
        matched = doc[start:end].text.lower()
        parts = phrase.split(matched)
        for i in range(len(parts) - 1):
            firstpart = ""
            secondpart = ""
            for part in parts[: i - 1]:
                firstpart += part
            for part in parts[i + 1 :]:
                secondpart += part
            precedes = doc.text.lower()[: doc[start:end].start_char].endswith(firstpart)
            follows = doc.text.lower()[doc[start:end].end_char :].startswith(secondpart)
            if precedes and follows:
                return True
        return False

    return _part_of_phrase


def succeeded_by_num() -> SpacyMatchPredicate:
    def _succeeded_by_num(doc, start, end):
        if end >= len(doc):
            return False
        return doc[end].like_num or doc[end].pos_ == "NUM" or doc[end].is_digit

    return _succeeded_by_num


def succeeded_by_currency() -> SpacyMatchPredicate:
    def _succeeded_by_currency(doc, start, end):
        if end >= len(doc):
            return False
        return doc[end].is_currency

    return _succeeded_by_currency


# for compatibility with a previous version with spelling errors
# point incorrectly spelled versions to correct versions
# eventually deprecate these
preceeded_by_phrase = preceded_by_phrase
preceeded_by_pos = preceded_by_pos
preceeded_by_dep = preceded_by_dep
