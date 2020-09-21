from typing import List

from spacy.tokens import Span


class Scorer:
    def __init__(self):
        pass

    def __call__(self, text):
        """Please override this"""
        return 0.5

    def score_suggestion(self, doc, span, suggestion):
        """Please override this"""
        text = " ".join([doc[: span.start].text] + suggestion + [doc[span.end :].text])
        return self(text)

    def sort_suggestions(self, spans: List[Span]) -> List[Span]:
        """Please override this"""
        return spans
