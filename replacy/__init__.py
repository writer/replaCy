import copy
import itertools
import warnings
from types import ModuleType
from typing import Any, Callable, Dict, List, Optional

from functional import seq
from jsonschema import validate
from spacy.matcher import Matcher
from spacy.tokens import Span

from replacy import default_match_hooks
from replacy.db import get_forms_lookup, get_match_dict, get_match_dict_schema, load_lm
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
        max_suggestions_count=1000,
        lm_path=None,
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
        self.inflector = Inflector(nlp=self.nlp, forms_lookup=self.forms_lookup)
        self.max_suggestions_count = max_suggestions_count
        # The following is not ideal
        # we probably want to have a Scorer interface, that different LMs can adhere to
        # and then have a Default Scorer which applies the identity function,
        # rather than using null
        if lm_path:
            from replacy.scorer import KenLMScorer

            self.scorer: Optional[KenLMScorer] = KenLMScorer(
                nlp=self.nlp, model=load_lm(lm_path)
            )
        else:
            self.scorer = None

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
                warnings.warn(
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

    def get_item(self, item, doc, start, end):

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
                refd_token = doc[start + ref]
            else:
                # this is confusing. Example:
                # doc = nlp("I like apples, blood oranges, and bananas")
                # start = 2, end = 9 gives doc[start:end] == "apples, blood oranges, and bananas"
                # but doc[9] != "bananas", it is an IndexError, the last token is end-1
                # so, per python conventions, PATTERN_REF = -1 would mean the last matched token
                # so we can just add ref and end if ref is negative
                # to do: match again to get multi-token
                refd_token = doc[end + ref]
            item_options = [refd_token.text]

        return item_options

    def inflect_item(self, item_options, item, doc, start, end, match_name):
        # set
        if "INFLECTION" in item:
            inflection_value = item["INFLECTION"]
            inflection_type = Inflector.get_inflection_type(inflection_value)
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
            for i, token in enumerate(self.match_dict[match_name]["patterns"]):
                if "TEMPLATE_ID" in token and token["TEMPLATE_ID"] == template_id:
                    index = i
                    break
            if index is not None:
                item_options = (
                    seq(item_options)
                    .map(lambda x: self.inflector.auto_inflect(doc, x, start + index))
                    .flatten()
                    .list()
                )
        return item_options

    def case_item(self, item_options, item):
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

    def process_suggestions(self, pre_suggestion, doc, start, end, match_name):
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
        """
        options = []
        for item in pre_suggestion:

            item_options = self.get_item(item, doc, start, end)
            inflected_options = self.inflect_item(
                item_options, item, doc, start, end, match_name
            )
            cased_options = self.case_item(inflected_options, item)
            options.append(cased_options)

        # assert there aren't more than max_suggestions_count
        # otherwise raise warning and return []
        suggestions_count = (
            seq(options).map(lambda x: len(x)).reduce(lambda x, y: x * y)
        )

        if suggestions_count > self.max_suggestions_count:
            warnings.warn(
                f"Got {suggestions_count} suggestions, max is {self.max_suggestions_count}. \
                Will fallback to empty suggestions."
            )
            opt_text = []
        else:
            opt_combinations = list(itertools.product(*options))
            opt_text = [" ".join(list(o)) for o in opt_combinations]

        return opt_text

    def score_suggestion(self, doc, span, suggestion):
        text = " ".join([doc[: span.start].text, suggestion, doc[span.end :].text])
        return self.scorer(text)

    def sort_suggestions(self, doc, spans):
        for span in spans:
            if len(span._.suggestions) > 1:
                span._.suggestions = sorted(
                    span._.suggestions,
                    key=lambda x: self.score_suggestion(doc, span, x),
                )
        return spans

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

            span._.suggestions = []

            for x in pre_suggestions:
                span._.suggestions += self.process_suggestions(
                    x, doc, start, end, match_name
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

        if self.scorer:
            self.spans = self.sort_suggestions(sent, self.spans)

        return self.spans
