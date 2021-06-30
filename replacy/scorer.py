import string
import warnings
from typing import List

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
            doc = self.nlp(segment, disable=self.nlp.pipe_names)
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

        # log10 prob
        score = self.model.score(text, bos=bos, eos=eos)

        if score_type == "log":
            return score

        elif score_type == "perplexity":
            prob = 10.0 ** (score)
            prob = 0.00000000001 if prob == 0 else prob
            return prob ** (-1 / word_count)
        else:
            raise NotImplementedError

    def score_suggestion(self, doc: Doc, span: Span, suggestion: List[str]) -> float:
        """
        between spacy 2.3.2 and 2.3.5 the behavior of slicing docs changed
        so doc[len(doc):] now throws an exception (it just returned the empty span before)

        also, we use arrays of text tokens rather than t.text_with_ws_ because
        Ken wants space-tokenized strings
        """
        if span.start == 0:
            head = []
        else:
            head = [t.text for t in doc[: span.start]]
        if span.end >= len(doc):
            tail = []
        else:
            tail = [t.text for t in doc[span.end :]]
        text = " ".join(head + suggestion + tail)
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
