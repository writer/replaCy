import pyinflect
import spacy

from replacy.db import get_forms_dict


class Inflector:
    def __init__(self, nlp=None):
        if not nlp:
            nlp = spacy.load("en_core_web_sm")
        self.nlp = nlp
        self.forms_dict = get_forms_dict()

    def get_dict_form(self, verb, verb_form):
        for k in self.forms_dict:
            if (
                verb in self.forms_dict[k].values()
                and verb_form in self.forms_dict[k].keys()
            ):
                return self.forms_dict[k][verb_form]
        return None

    def inflect(self, doc, suggestion, index):
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

        inflected_token = changed_token._.inflect(token.tag_)

        # dictionary check
        if not inflected_token:
            inflected_token = self.get_dict_form(suggestion, token.tag_)

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

        infl_token = self.inflect(doc, suggestion, index)

        if infl_token:
            token = doc[index]
            changed_sent = "".join(
                [doc.text[: token.idx], infl_token, doc.text[token.idx + len(token) :]]
            )
            return changed_sent
        else:
            return doc.text
