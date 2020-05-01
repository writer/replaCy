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
    ):
        self.default_match_hooks = default_match_hooks
        self.custom_match_hooks = custom_match_hooks
        self.nlp = nlp
        self.match_dict = match_dict if match_dict else get_match_dict()
        self.forms_lookup = forms_lookup if forms_lookup else get_forms_lookup()

        self.matcher = Matcher(self.nlp.vocab)
        self._init_matcher()
        self.spans: List[Span] = []
        self.inflector = Inflector(nlp=self.nlp, forms_lookup=self.forms_lookup)

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
            if args is not None:
                # the match_hook needs arguments
                pred = template(hook["args"])
            else:
                # the match_hook is nullary
                pred = template()

            # to confuse people for centuries to come ...
            # negate, since positive breaks matching
            # see cb in get_callback
            if bool(hook.get("match_if_predicate_is", False)):
                # neg flips the boolean value of a predicate
                pred = default_match_hooks.neg(pred)
            predicates.append(pred)
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

            span._.suggestions = (
                seq(pre_suggestions)
                .map(lambda x: self.inflect_suggestion(x, doc, start, end, match_name))
                .list()
            )
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
