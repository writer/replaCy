import re
import warnings

from functional import seq

from replacy.inflector import Inflector
from replacy.ref_matcher import RefMatcher
from replacy.util import spacy_version


class SuggestionGenerator:
    def __init__(self, nlp, forms_lookup=None, filter_suggestions=False, default_max_count=None):
        self.forms_lookup = forms_lookup
        self.inflector = Inflector(nlp=nlp, forms_lookup=self.forms_lookup)
        self.ref_matcher = RefMatcher(nlp)
        self.filter_suggestions = filter_suggestions
        self.default_max_count = default_max_count

    @staticmethod
    def get_options(item, doc, start, end, pattern, pattern_ref):
        item_options = []
        # set
        if "TEXT" in item:
            if isinstance(item["TEXT"], dict):
                item_options = item["TEXT"].get("IN", [])
            elif isinstance(item["TEXT"], str):
                item_options = [item["TEXT"]]
        # copy
        elif "PATTERN_REF" in item:
            ref = int(item["PATTERN_REF"])
            if ref >= 0:
                try:
                    refd_tokens = pattern_ref[ref]
                    if len(refd_tokens):
                        min_i = start + min(refd_tokens)
                        max_i = start + max(refd_tokens)
                        refd_text = doc[min_i: max_i + 1].text
                    else:
                        refd_text = None
                except:
                    warnings.warn(
                        f"Ref matcher failed for span {doc[start:end]} and {pattern_ref}."
                    )
                    refd_text = doc[start + ref].text
            else:
                # this is confusing. Example:
                # doc = nlp("I like apples, blood oranges, and bananas")
                # start = 2, end = 9 gives doc[start:end] == "apples, blood oranges, and bananas"
                # but doc[9] != "bananas", it is an IndexError, the last token is end-1
                # so, per python conventions, PATTERN_REF = -1 would mean the last matched token
                # so we can just add ref and end if ref is negative
                # to do: match again to get multi-token
                try:
                    # map ref to positive
                    ref = len(pattern_ref) + ref
                    refd_tokens = pattern_ref[ref]
                    if len(refd_tokens):
                        min_i = start + min(refd_tokens)
                        max_i = start + max(refd_tokens)
                        refd_text = doc[min_i: max_i + 1].text
                    else:
                        refd_text = None
                except:
                    warnings.warn(
                        f"Ref matcher failed for span {doc[start:end]} and {pattern_ref}."
                    )
                    refd_text = doc[end + ref].text

            if refd_text:
                if "REGEX" in item:
                    regex_p = pattern[item["PATTERN_REF"]]
                    # regex is with ignore case flag
                    # so having this line to avoid exception when LOWER isn't in the pattern
                    # if at any point needed to be specific or use case sensitive
                    # we should add "REGEX_KEY" (TEXT or LOWER) in suggestions
                    regex_pattern = regex_p["LOWER"]["REGEX"] if "LOWER" in regex_p else regex_p["TEXT"]["REGEX"]
                    regex_replace = item["REGEX"]
                    refd_text = re.sub(regex_pattern, regex_replace, refd_text, flags=re.IGNORECASE)

                if "SUFFIX" in item:
                    refd_text += item['SUFFIX']

                item_options = [refd_text]
            else:
                item_options = []

        return item_options

    def get_item_max_count(self, item, item_options):

        # max count can be hard set in match_dict
        max_count = item.get("MAX_COUNT", None)
        if max_count:
            return max_count

        # can be soft set by default
        # but no more than possible - ex. list len
        # or maximal ie. list len
        if self.default_max_count:
            max_count = min(self.default_max_count, len(item_options))
        else:
            max_count = len(item_options)

        # if we don't want to guess max count
        # to eliminate grammatical variants
        # end here
        if not self.filter_suggestions:
            return max_count

        # if max count is not hard set
        # try to lower max count in special cases (A - G)
        # to eliminate non grammatical suggestions

        # A. empty
        # ex. []
        if not len(item_options):
            return 1

        # B. contains non letters
        # ex. ["", ","]
        if not all([o.isalpha() for o in item_options]):
            return 1

        # C. is multi token
        # ex. ["in a", "for"]
        if max([len(o.split()) for o in item_options]) > 1:
            return 1

        # D. if inflection is set to tag - good
        # other options - will always return many
        if "INFLECTION" in item:
            inflection = item.get("INFLECTION")
            inflection_type = self.inflector.get_inflection_type(inflection)
            if inflection_type != "tag":
                return 1

        # contains many options
        # ex. ["eat", "walk"]
        if len(item_options) > 1:

            # E. contains words of the same lemma
            # ex. [slow, slowly]
            lemmas = set([])
            for option in item_options:
                option_lemmas = set(self.inflector.get_lemmas(option))
                if len(lemmas & option_lemmas):
                    return 1
                lemmas |= option_lemmas

            # F. det:
            # ex. ["a", "an"]
            if any([article in item_options for article in ["a", "an", "the"]]):
                return 1

            # G. irregular plurals - only 2 detected so hardcoded
            # person / people
            # ox / oxen
            if all([el in item_options for el in ["person", "people"]]) or all(
                    [el in item_options for el in ["ox", "oxen"]]
            ):
                return 1

        return max_count

    def inflect(self, item, item_options, pattern, pattern_ref, doc, start, end):
        # set
        if "INFLECTION" in item:
            inflection_value = item["INFLECTION"]
            inflection_type = self.inflector.get_inflection_type(inflection_value)
            if inflection_type == "pos":
                # set by pos
                item_options = (
                    seq(item_options)
                        .map(
                        lambda x: self.inflector.inflect_or_lookup(
                            x, pos=inflection_value
                        )
                    )
                        .flatten()
                        .list()
                )
            elif inflection_type == "tag":
                # set by tag
                item_options = (
                    seq(item_options)
                        .map(
                        lambda x: self.inflector.inflect_or_lookup(
                            x, tag=inflection_value
                        )
                    )
                        .flatten()
                        .list()
                )
            else:
                # get all forms
                item_options = (
                    seq(item_options)
                        .map(lambda x: self.inflector.inflect_or_lookup(x, pos=None))
                        .flatten()
                        .list()
                )
        # copy
        elif "FROM_TEMPLATE_ID" in item:
            template_id = int(item["FROM_TEMPLATE_ID"])
            index = None
            for i, token in enumerate(pattern):
                if "TEMPLATE_ID" in token and token["TEMPLATE_ID"] == template_id:
                    index = i
                    break

            # use token <-> pattern mapping
            # given pattern index, find doc index:
            doc_indices = pattern_ref[index]
            if len(doc_indices) == 0:
                # fallback to direct mapping:
                warnings.warn(
                    f"Ref matcher failed for span {doc[start:end]} and {pattern_ref}."
                )
                doc_index = index
            elif len(doc_indices) >= 1:
                # == 1 good case
                # >1 more tokens found, fallback to the first token
                doc_index = doc_indices[0]

            if doc_index is not None:
                item_options = (
                    seq(item_options)
                        .map(
                        lambda x: self.inflector.auto_inflect(doc, x, start + doc_index)
                    )
                        .flatten()
                        .list()
                )
        return item_options

    def case(self, item, item_options):
        # This should probably be a list of ops
        # and we should have a parser class
        if "REPLACY_OP" in item:
            op = item["REPLACY_OP"]
            if op == "LOWER":
                item_options = [t.lower() for t in item_options]
            if op == "TITLE":
                item_options = [t.title() for t in item_options]
            if op == "UPPER":
                item_options = [t.upper() for t in item_options]
        return item_options

    def __call__(self, pre_suggestion, doc, start, end, pattern, pre_suggestion_id):
        """
        Suggestion text:
            - set: "TEXT": "cat"
            - choose one from: "TEXT": {"IN": ["a", "b"]}
            - copy from pattern: "PATTERN_REF": 3 (copy from 3rd pattern match)
        Set suggestion text inflection:
            - set by tag: "INFLECTION": "VBG" (returns one)
            - set by pos: "INFLECTION": "NOUN" (returns many. ex. NNS, NN)
            - get all: "INFLECTION": "ALL" (returns a lot, use infrequently)
            - copy from pattern: "FROM_TEMPLATE_ID": 2 (copy from token with "TEMPLATE_ID":2)
        Suggestions case matching:
            - lowercase: "REPLACY_OP: "LOWER"
            - title: "REPLACY_OP: "TITLE"
            - upper: "REPLACY_OP: "UPPER"
        Suggestions item max count:
            - set by tag: "MAX_COUNT": n (int) (take best n words from options)
            - implied MAX_COUNT = 1 if words share the same lemma or are mutually exclusive, ex. a/an
        """
        # get token <-> pattern correspondence
        pattern_obj = pattern[0] if spacy_version() >= 3 else pattern
        pattern_ref = self.ref_matcher(doc[start:end], pattern_obj)

        suggestions = []

        for item in pre_suggestion:
            # get text
            item_options = SuggestionGenerator.get_options(item, doc, start, end, pattern_obj, pattern_ref)

            # guess or read max count count
            max_count = self.get_item_max_count(item, item_options)

            # inflect
            inflected_options = self.inflect(
                item, item_options, pattern_obj, pattern_ref, doc, start, end
            )

            # case
            cased_options = self.case(item, inflected_options)

            # if non empty (can be when matching with OP)
            if len(cased_options):
                suggestion_variant = SuggestionVariants(
                    cased_options, max_count, pre_suggestion_id
                )
                suggestions.append(suggestion_variant)

        return suggestions


class SuggestionVariants:
    def __init__(self, cased_options, max_count, id):
        self.cased_options = cased_options
        self.max_count = max_count
        self.id = id

    def __len__(self):
        return len(self.cased_options)

    def __repr__(self):
        return f'(cased_options={",".join(self.cased_options)}, max_count={self.max_count}, id={self.id})'

    def __iter__(self):
        for option in self.cased_options:
            yield Suggestion(option, self.max_count, self.id)


class Suggestion:
    def __init__(self, text, max_count, id):
        self.text = text
        self.max_count = max_count
        self.id = id

    def __repr__(self):
        return f"(text={self.text}, max_count={self.max_count}, id={self.id})"
