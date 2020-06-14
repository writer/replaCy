import spacy
from replacy.db import get_forms_lookup


class Inflector:
    def __init__(self, nlp=None, forms_lookup=None, lemmatizer="pyInflect"):

        if lemmatizer == "pyInflect":
            import pyinflect
        elif lemmatizer == "lemmInflect":
            import lemminflect
        else:
            raise NotImplementedError

        self.nlp = nlp
        if not self.nlp:
            self.nlp = spacy.load("en_core_web_sm")

        self.forms_lookup = forms_lookup
        if not self.forms_lookup:
            self.forms_lookup = get_forms_lookup()

    def get_dict_form(self, verb, verb_form):
        for k in self.forms_lookup:
            if (
                verb in self.forms_lookup[k].values()
                and verb_form in self.forms_lookup[k].keys()
            ):
                return self.forms_lookup[k][verb_form]
        return None

    def auto_inflect(self, doc, suggestion, index):
        """
        Inflect the suggestion using token at position 'index' as template.
        ex. (washed, eat) => ate
        Returns inflected suggestion as text.
        If the inflection is not supported, check verb_forms.json
        if not found - returns None.
        """

        try:
            doc.text
        except AttributeError:
            doc = self.nlp(doc)

        sentence = doc.text

        token = doc[index]
        token_start = token.idx
        token_end = token_start + len(token)

        changed_sentence = "".join(
            [sentence[:token_start], suggestion, sentence[token_end:]]
        )

        changed_doc = self.nlp(changed_sentence)
        changed_token = changed_doc[index]

        return self.inflect_or_lookup(changed_token, token.tag_)

    def inflect_or_lookup(
        self, token: spacy.tokens.token.Token, form: str
    ) -> str:
        inflected_token = token._.inflect(form)

        # dictionary check
        if not inflected_token:
            inflected_token = self.get_dict_form(token.text, form)

        return inflected_token

    def insert(self, doc, suggestion: str, index: int):
        """
        Returns the sentence with inserted inflected token.
        If inflection is not supported - returns the original sentence.
        ex. She washed her eggs. -> She ate her eggs.
        """

        # if string passed, conversion to doc
        try:
            doc.text
        except AttributeError:
            doc = self.nlp(doc)

        infl_token = self.auto_inflect(doc, suggestion, index)

        if infl_token:
            token = doc[index]
            changed_sent = "".join(
                [
                    doc.text[: token.idx],
                    infl_token,
                    doc.text[token.idx + len(token) :],
                ]
            )
            return changed_sent
        else:
            return doc.text
