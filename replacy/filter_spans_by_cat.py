from typing import List

from replacy import ESpan
from spacy.util import filter_spans


def filter_spans_by_cat(spans: List[ESpan]) -> List[ESpan]:
    if len(spans):
        subcats = set(map(lambda c: c.subcategory, spans))
        grouped_spans = [[y for y in spans if y.subcategory == c] for c in subcats]
        filtered_spans = []
        for group in grouped_spans:
            filtered_spans += filter_spans(group)
        return filtered_spans
    return spans
