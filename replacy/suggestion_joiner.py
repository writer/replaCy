from typing import List

from spacy.tokens import Span


def join_suggestions(spans: List[Span]) -> List[Span]:
    for span in spans:
        suggestions_separator = span.suggestions_separator if span.has_extension('suggestions_separator') else " "
        suggestions: List[str] = []
        for s in span._.suggestions:
            # in case of two exactly overlapping spans
            # some of suggestions could be already processed
            # this could cause problems
            # this should be handled by early span filtering
            try:
                suggestions += [suggestions_separator.join([t.text for t in s])]
            except AttributeError:
                suggestions.append(s)

        span._.suggestions = suggestions
    return spans
