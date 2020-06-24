import copy
from types import ModuleType
from typing import Any, Callable, Dict, List, Optional

from functional import seq
from jsonschema import validate
from spacy.matcher import Matcher
from spacy.tokens import Span

from replacy import default_match_hooks
from replacy.db import get_forms_lookup, get_match_dict, get_match_dict_schema
from replacy.inflector import Inflector
from replacy.version import __version__


# set known extensions:
known_string_extensions = ["description", "match_name", "category", "comment"]
known_list_extensions = ["suggestions"]
for ext in known_list_extensions:
    Span.set_extension(ext, default=[], force=True)
for ext in known_string_extensions:
    Span.set_extension(ext, default="", force=True)

expected_properties = (
    ["patterns", "match_hook", "test"] + known_list_extensions + known_string_extensions
)


class ReplaceMatcher:
    """
    The main unit of functionality. Instantiate with `nlp`, (an instance of spaCy) and a match dict.
    Usage example, including a module of custom match hooks:

    ```python
        from replacy import ReplaceMatcher
        from replacy.db import load_json
        import spacy

        import my.custom_hooks as ch  # suppose this suggests `excepts=>accepts` under some conditions


        nlp = spacy.load("en_core_web_sm")
        rmatch_dict = load_json("./resources/match_dict.json")
        rmatcher = ReplaceMatcher(nlp, rmatch_dict, custom_match_hooks=ch)
        span = rmatcher("She excepts her fate.")[0]
        span._.suggestions
        # >>> ['acccepts']
    ```
    """

    def __init__(
        self,
        nlp,
        match_dict=None,
        forms_lookup=None,
        custom_match_hooks: Optional[ModuleType] = None,
        allow_multiple_whitespaces=False,
        lemmatizer="pyInflect",
    ):
        self.default_match_hooks = default_match_hooks
        self.custom_match_hooks = custom_match_hooks
        self.nlp = nlp
        self.match_dict = match_dict if match_dict else get_match_dict()
        self.forms_lookup = forms_lookup if forms_lookup else get_forms_lookup()
        self.allow_multiple_whitespaces = allow_multiple_whitespaces

        self.matcher = Matcher(self.nlp.vocab)
        self._init_matcher()
        self.spans: List[Span] = []
        self.inflector = Inflector(
            nlp=self.nlp, forms_lookup=self.forms_lookup, lemmatizer=lemmatizer
        )

        # set custom extensions for any unexpected keys found in the match_dict
        novel_properites = (
            seq(self.match_dict.values())
            .flat_map(lambda x: x.keys())
            .distinct()
            .difference(expected_properties)
        )
        novel_prop_defaults: Dict[str, Any] = {}
        for x in self.match_dict.values():
            for k, v in x.items():
                if k in novel_properites and k not in novel_prop_defaults.keys():
                    if isinstance(v, str):
                        novel_prop_defaults[k] = ""
                    elif isinstance(v, list):
                        novel_prop_defaults[k] = []
                    elif isinstance(v, dict):
                        novel_prop_defaults[k] = {}
                    elif isinstance(v, int):
                        novel_prop_defaults[k] = 0
                    elif isinstance(v, float):
                        novel_prop_defaults[k] = 0.0
                    elif isinstance(v, bool):
                        novel_prop_defaults[k] = False
                    else:
                        # just default to whatever value we find
                        print(k, v)
                        novel_prop_defaults[k] = v

        for prop, default in novel_prop_defaults.items():
            Span.set_extension(prop, default=default, force=True)
        self.novel_prop_defaults = novel_prop_defaults

    @staticmethod
    def validate_match_dict(match_dict):
        match_dict_schema = get_match_dict_schema()
        validate(instance=match_dict, schema=match_dict_schema)

    def get_predicates(self, match_hooks) -> List[Callable]:
        predicates = []
        for hook in match_hooks:
            # template - ex. succeeded_by_phrase
            try:
                template = getattr(self.default_match_hooks, hook["name"])
            except AttributeError:
                # if the hook isn't in custom_match_hooks, this will still
                # raise an exception. I think that is the correct behavior
                template = getattr(self.custom_match_hooks, hook["name"])

            # predicate - filled template ex. succeeded_by_word("to")
            # will match "in addition to..." but not "in addition, ..."
            args = hook.get("args", None)
            kwargs = hook.get("kwargs", None)
            if args is None:
                if kwargs is None:
                    # the match_hook is nullary
                    pred = template()
                else:
                    pred = template(**kwargs)
            elif type(args) == dict:
                # should we force them to use kwargs?
                print(
                    f"WARNING: dict passed as sole args argument. Calling {hook['name']} "
                    f"with single argument {args}. If you want to call with keyword arguments, use kwargs"
                )
                pred = template(args)
            else:
                # oops, bad design, we assume non-dicts are called directly
                pred = template(args)

            # to confuse people for centuries to come ...
            # negate, since positive breaks matching
            # see cb in get_callback
            if bool(hook.get("match_if_predicate_is", False)):
                # neg flips the boolean value of a predicate
                pred = default_match_hooks.neg(pred)
            predicates.append(pred)
        return predicates

    def process_suggestions(self, pre_suggestion, doc, start, end, match_name):
        """
        Perform inflection and replace references to the matched token
        example of pattern and pre_suggestion
        pattern: "LEMMA": "chock", "TEMPLATE_ID": 1
        pre_suggestion: "TEXT": "chalk", "FROM_TEMPLATE_ID": 1
        inflect suggestion "chalk" according to form of "cholk" from patterns
        """
        text_list = []
        for item in pre_suggestion:
            try:
                text = item["TEXT"]
            except KeyError:
                ref = int(item["PATTERN_REF"])
                if ref >= 0:
                    refd_token = doc[start + ref]
                else:
                    # this is confusing. Example:
                    # doc = nlp("I like apples, blood oranges, and bananas")
                    # start = 2, end = 9 gives doc[start:end] == "apples, blood oranges, and bananas"
                    # but doc[9] != "bananas", it is an IndexError, the last token is end-1
                    # so, per python conventions, PATTERN_REF = -1 would mean the last matched token
                    # so we can just add ref and end if ref is negative
                    refd_token = doc[end + ref]
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
                    changed_text = self.inflector.auto_inflect(doc, text, start + index)
            elif "PATTERN_REF" in item:
                if "INFLECTION" in item:
                    form = item["INFLECTION"]
                    changed_text = self.inflector.inflect_or_lookup(refd_token, form)
                else:
                    changed_text = refd_token.text

                # This should probably be a list of ops
                # and we should have a parser class
                if "REPLACY_OP" in item:
                    op = item["REPLACY_OP"]
                    if op == "LOWER":
                        changed_text = changed_text.lower()
                    if op == "TITLE":
                        changed_text = changed_text.title()
                    if op == "UPPER":
                        changed_text = changed_text.upper()
            if changed_text:
                text_list.append(changed_text)
            elif len(text):
                text_list.append(text)
        return " ".join(text_list)

    def get_callback(self, match_name, match_hooks):
        """
        Most matches have the same logic to be executed each time a match is found
        Some matches have extra logic, defined in match_hooks
        """
        # Get predicates once, callback is returned in a closure with this information
        predicates = self.get_predicates(match_hooks)

        def cb(matcher, doc, i, matches):
            match_id, start, end = matches[i]

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

            span._.suggestions = [
                self.process_suggestions(x, doc, start, end, match_name)
                for x in pre_suggestions
            ]

            span._.description = self.match_dict[match_name].get("description", "")
            span._.category = self.match_dict[match_name].get("category", "")
            for novel_prop, default_value in self.novel_prop_defaults.items():
                setattr(
                    span._,
                    novel_prop,
                    self.match_dict[match_name].get(novel_prop, default_value),
                )
            self.spans.append(span)

        return cb

    def _init_matcher(self):
        for match_name, ps in self.match_dict.items():
            patterns = copy.deepcopy(ps["patterns"])

            """
            allow matching tokens separated by multiple whitespaces
            they may appear after normalizing nonstandard whitespaces
            ex. "Here␣is␣a\u180E\u200Bproblem." -> "Here␣is␣a␣␣problem."
            pattern can be preceded and followed by whitespace tokens
            to keep preceded_by... with and succeeded_by... with match hooks working
            """
            if self.allow_multiple_whitespaces:

                white_pattern = {"IS_SPACE": True, "OP": "?"}

                normalized_patterns = [white_pattern]
                for p in patterns:
                    normalized_patterns += [p, white_pattern]
                patterns = normalized_patterns

            # remove custom attributes not supported by spaCy Matcher
            for p in patterns:
                if "TEMPLATE_ID" in p:
                    del p["TEMPLATE_ID"]

            match_hooks = ps.get("match_hook", [])
            callback = self.get_callback(match_name, match_hooks)
            self.matcher.add(match_name, callback, patterns)

    def __call__(self, sent):
        # self.spans must be cleared - global
        self.spans = []
        try:
            sent.text
        except AttributeError:
            sent = self.nlp(sent)

        # this fills up self.spans
        matches = self.matcher(sent)

        return self.spans
