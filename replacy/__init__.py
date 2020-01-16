import copy

from functional import seq
from spacy.matcher import Matcher
from spacy.tokens import Span

import replacy.custom_patterns as custom_patterns
from replacy.inflector import Inflector
from replacy.db import get_forms_lookup, get_match_dict
from replacy.version import __version__

Span.set_extension("suggestions", default=[], force=True)
Span.set_extension("description", default="", force=True)
Span.set_extension("match_name", default="", force=True)


class ReplaceMatcher:
    def __init__(self, nlp, match_dict=None, forms_lookup=None):
        self.nlp = nlp
        self.match_dict = match_dict if match_dict else get_match_dict()
        self.forms_lookup = forms_lookup if forms_lookup else get_forms_lookup()

        self.matcher = Matcher(self.nlp.vocab)
        self._init_matcher()
        self.spans = []
        self.inflector = Inflector(nlp=self.nlp, forms_lookup=self.forms_lookup)

    def get_predicates(self, match_hooks):
        predicates = []
        for hook in match_hooks:
            try:
                # template - ex. succeeded_by_word
                template = getattr(custom_patterns, hook["name"])

                # predicate - filled template ex. succeeded_by_word("to")
                # will match "in addition to..." but not "in addition, ..."
                pred = template(hook["args"])

                # to confuse people for centuries to come ...
                # negate, since positive breaks matching
                # see cb in get_callback
                if bool(hook.get("match_if_predicate_is", False)):
                    pred = getattr(custom_patterns, "neg")(pred)
                predicates.append(pred)
            except:
                print(f"Error loading match_hook {hook}")
        return predicates

    def inflect_suggestion(self, pre_suggestion, doc, start, end, match_name):
        """
        example of pattern and pre_suggestion
        pattern: "LEMMA": "chock", "TEMPLATE_ID": 1
        pre_suggestion: "TEXT": "chalk", "FROM_TEMPLATE_ID": 1
        inflect suggestion "chalk" according to form of "cholk" from patterns
        """
        text_list = []
        for item in pre_suggestion:
            text = item["TEXT"]
            changed_text = None

            # check if inflect
            if "FROM_TEMPLATE_ID" in item:
                template_id = item["FROM_TEMPLATE_ID"]
                index = None
                for i, token in enumerate(self.match_dict[match_name]["patterns"]):
                    if "TEMPLATE_ID" in token and token["TEMPLATE_ID"] == template_id:
                        index = i
                        break
                if index is not None:
                    changed_text = self.inflector.inflect(doc, text, start + index)
            if changed_text:
                text_list.append(changed_text)
            elif len(text):
                text_list.append(text)
        return " ".join(text_list)

    def get_callback(self, match_name, match_hooks):
        """
        Most matches have the same logic to be executed each time a match is found
        Things like adding spans to a list, checking against universal negation conditions
        Some matches have extra logic, defined in match_hooks
        """

        def cb(matcher, doc, i, matches):
            match_id, start, end = matches[i]
            # now check the conditions defined in self.get_predicates

            predicates = self.get_predicates(match_hooks)

            for pred in predicates:
                try:
                    if pred(doc, start, end):
                        return None
                except IndexError:
                    break
            match_name = self.nlp.vocab[match_id].text
            span = Span(doc, start, end)

            # find in match_dict if needed
            span._.match_name = match_name

            pre_suggestions = self.match_dict[match_name]["suggestions"]

            span._.suggestions = (
                seq(pre_suggestions)
                .map(lambda x: self.inflect_suggestion(x, doc, start, end, match_name))
                .list()
            )
            try:
                span._.description = self.match_dict[match_name]["description"]
            except KeyError:
                span._.description = ""
            self.spans.append(span)

        return cb

    def _init_matcher(self):
        for match_name, ps in self.match_dict.items():
            patterns = copy.deepcopy(ps["patterns"])

            # remove custom attributes not supported by spaCy Matcher
            for p in patterns:
                if "TEMPLATE_ID" in p:
                    del p["TEMPLATE_ID"]

            match_hooks = ps.get("match_hook", [])
            callback = self.get_callback(match_name, match_hooks)
            self.matcher.add(match_name, callback, patterns)

    def __call__(self, sent: str):
        # self.spans must be cleared - global
        self.spans = []
        sent_doc = self.nlp(sent)

        # this fills up self.spans
        matches = self.matcher(sent_doc)

        return self.spans
