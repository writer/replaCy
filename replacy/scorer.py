from typing import List

import os
import string
import warnings

from kenlm import Model as KenLMModel
from spacy.tokens import Doc, Span, Token


from replacy.default_scorer import Scorer


class KenLMScorer(Scorer):

    name = "kenlm"

    def __init__(self, model=None, path=None, nlp=None, lowercase=True):

        if model:
            self.model = model
        elif path:
            self.model = KenLMModel(path)

        self._check_model()

        if nlp:
            self.nlp = nlp
        else:
            import spacy

            self.nlp = spacy.load("en_core_web_sm")

        self.lowercase = lowercase

    def _check_model(self):
        assert isinstance(self.model, KenLMModel)
        assert self.model.score("testing !") < 0

    def preprocess(self, segment):
        """
        SpaCy tokenize + lowercase. Ignore extra whitespaces.
        - if Doc, Span, Token - retrieve .lower_
        - if string - convert to Doc first
        """
        if isinstance(segment, (Doc, Span, Token)):
            # spaCy tokenizer, ignore whitespaces
            tok = [token.text for token in segment if not token.is_space]
            if self.lowercase:
                tok = [token.lower() for token in tok]

        elif isinstance(segment, str):
            doc = self.nlp(segment, disable=["parser", "tagger", "ner"])
            return self.preprocess(doc)

        return " ".join(tok)

    def __call__(self, segment, score_type="perplexity"):

        text = self.preprocess(segment)
        word_count = len(text.split())

        if word_count < 2:
            warnings.warn(f"Scorer: Received {word_count} tokens, expected >= 2.")
            return float("-inf")

        if isinstance(segment, Doc):
            # if doc - assume bos, eos=True
            bos = True
            eos = True

        if isinstance(segment, (Span, Token)):
            # if span - assume bos, eos=False
            bos = False
            eos = False

        if isinstance(segment, str):
            # string passed - guess:
            bos = text.capitalize() == text
            eos = text[-1] in string.punctuation


        if score_type == "log":
            # log10 prob
            score = self.model.score(text, bos=bos, eos=eos)
            return score
        elif score_type == "perplexity":
            return self.model.perplexity(text)
        else:
            raise NotImplementedError

    def score_suggestion(self, doc, span, suggestion):
        text = " ".join([doc[: span.start].text] + suggestion + [doc[span.end :].text])
        return self(text)

    def sort_suggestions(self, spans: List[Span]) -> List[Span]:
        for span in spans:
            if len(span._.suggestions) > 1:
                span._.suggestions = sorted(
                    span._.suggestions,
                    key=lambda x: self.score_suggestion(
                        span.doc, span, [t.text for t in x]
                    ),
                )
        return spans
