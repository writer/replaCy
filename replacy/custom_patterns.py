"""
This module contains predicates which influence what counts as a match
If the predicate (function) returns True, the match will be ignored
"""
import operator


def compose(f, g):
    return lambda doc, start, end: f(g(doc, start, end))


def neg(f):
    # function negatin, ex. neg(preceeded_by_pos(pos))
    return compose(operator.not_, f)


def succeeded_by_phrase(phrase):
    return lambda doc, start, end: doc[end:].text.lower().startswith(phrase.lower())


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
