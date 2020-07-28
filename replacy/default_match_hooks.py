"""
This module contains predicates which influence what counts as a match
If the predicate (function) returns True, the match will be ignored
"""
import operator
from typing import Callable, List, Union

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
            bools = [doc[:start].text.lower().endswith(p.lower()) for p in phrase_list]
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


def succeeded_by_lemma(lemma) -> SpacyMatchPredicate:
    if isinstance(lemma, list):
        lemma_list = lemma

        def _succeeded_by_lemma(doc, start, end):
            bools = [doc[end].lemma_ == l for l in lemma_list]
            return any(bools)

        return _succeeded_by_lemma
    elif isinstance(lemma, str):
        return lambda doc, start, end: doc[end].lemma_ == lemma
    else:
        raise ValueError(
            "args of succeeded_by_lemma should be a string or list of strings"
        )


def preceded_by_lemma(lemma, distance=1) -> SpacyMatchPredicate:
    if isinstance(lemma, list):
        lemma_list = lemma

        def _preceded_by_lemma(doc, start, end):
            bools = [doc[start - distance].lemma_ == l for l in lemma_list]
            return any(bools)

        return _preceded_by_lemma
    elif isinstance(lemma, str):
        return lambda doc, start, end: doc[start - distance].lemma_ == lemma
    else:
        raise ValueError(
            "args of preceded_by_lemma should be a string or list of strings"
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


def sentence_has(phrase) -> SpacyMatchPredicate:
    if isinstance(phrase, list):
        phrase_list = phrase

        def _sentence_has(doc, start, end):
            sents = list(doc.sents)
            totalnum = 0
            sentnum = 0
            for sent in sents:
                totalnum += len(sent)
                if start > totalnum - 1:
                    sentnum += 1
            bools = [p in sents[sentnum].text.lower() for p in phrase_list]
            return any(bools)

        return _sentence_has
    elif isinstance(phrase, str):

        def _sentence_has(doc, start, end):
            sents = list(doc.sents)
            totalnum = 0
            sentnum = 0
            for sent in sents:
                totalnum += len(sent)
                if start > totalnum - 1:
                    sentnum += 1
            return phrase in sents[sentnum].text.lower()

        return _sentence_has
    else:
        raise ValueError("args of sentence_has should be a string or list of strings")


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
            preceeds = doc.text.lower()[: doc[start:end].start_char].endswith(firstpart)
            follows = doc.text.lower()[doc[start:end].end_char :].startswith(secondpart)
            if preceeds and follows:
                return True
        return False

    return _part_of_phrase


def succeeded_by_num() -> SpacyMatchPredicate:
    return (
        lambda doc, start, end: doc[end].like_num
        or doc[end].pos_ == "NUM"
        or doc[end].is_digit
    )


def succeeded_by_currency() -> SpacyMatchPredicate:
    return lambda doc, start, end: doc[end].is_currency


# for compatibilty with a previous version with spelling errors
# point incorrectly spelled versions to correct versions
# eventually deprecate these
preceeded_by_phrase = preceded_by_phrase
preceeded_by_pos = preceded_by_pos
preceeded_by_dep = preceded_by_dep
