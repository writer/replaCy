import copy
import itertools
import logging
import spacy
import warnings
from functional import seq
from spacy.matcher import Matcher
from spacy.tokens import Span
from spacy.tokens.underscore import get_ext_args
from types import ModuleType
from typing import Callable, List, Optional, Tuple

from replacy import default_match_hooks
from replacy.db import get_forms_lookup, get_match_dict, load_lm
from replacy.default_scorer import Scorer
from replacy.suggestion import SuggestionGenerator
from replacy.suggestion_joiner import join_suggestions
from replacy.util import (
    at_most_one_is_not_none,
    eliminate_options,
    get_novel_prop_defaults,
    get_predicates,
    make_doc_if_not_doc,
    set_known_extensions,
    validate_match_dict,
    spacy_version
)
from replacy.version import __version__

logging.basicConfig(level=logging.INFO)

PipelineComponent = Callable[[List[Span]], List[Span]]


class ESpan(Span):
    """
    dangerous version of Span class
    intentionally bypass the _ attribute so that the class itself has all the properties
    this can result in name collisions, etc

    Why use it? there are cases where overlapping spans cause problems for the built in spacy.tokens.Span
    but for some reason this works
    """

    def __getattribute__(self, name):
        """
        when python attempts to access to underscore property, don't let it, give it self
        this means that:

        ```python
        >>> doc = nlp("She extracts revenge.")
        >>> es = ESpan(doc, 1, 2)
        >>> e._.comment = "yo metaprogramming"
        >>> e.comment
        'yo metaprogramming'
        ```
        """
        if name == "_":
            return self
        return super().__getattribute__(name)

    @classmethod
    def set_extension(cls, name, **kwargs):
        # if we only want to allow default values, this works:
        default, method, getter, setter = get_ext_args(**kwargs)
        setattr(cls, name, default)
        # if we want to allow getters and setters or methods for dynamic props, we have to implement that
        # I think it is doable using the `property` built-in method as shown here
        # https://stackoverflow.com/a/1355444/3518108

    @classmethod
    def has_extension(cls, name):
        return hasattr(cls, name)


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
        # >>> ['accepts']
    ```
    """

    validate_match_dict = validate_match_dict

    def __init__(
            self,
            nlp,
            match_dict=None,
            forms_lookup=None,
            custom_match_hooks: Optional[ModuleType] = None,
            allow_multiple_whitespaces=False,
            max_suggestions_count=1000,
            lm_path=None,
            filter_suggestions=False,
            default_max_count=None,
            debug=False,
            SpanClass=Span,
    ):
        self.debug = debug
        # self.extended_span = extended_span
        self.Span = SpanClass
        self.logger = logging.getLogger("replaCy")
        self.default_match_hooks = default_match_hooks
        self.custom_match_hooks = custom_match_hooks
        self.nlp = nlp
        self.match_dict = match_dict if match_dict else get_match_dict()
        self.allow_multiple_whitespaces = allow_multiple_whitespaces
        self.matcher = Matcher(self.nlp.vocab)
        self._init_matcher()
        self.spans: List[Span] = []
        self.max_suggestions_count = max_suggestions_count
        self.forms_lookup = forms_lookup if forms_lookup else get_forms_lookup()
        self.suggestion_gen = SuggestionGenerator(nlp, forms_lookup, filter_suggestions, default_max_count)
        expected_properties = set_known_extensions(self.Span)
        self.novel_prop_defaults = get_novel_prop_defaults(
            self.match_dict, self.Span, expected_properties
        )
        self._set_scorer(lm_path)
        # Pipeline doesn't include matcher, since doesn't have the signature List[Span] -> None
        self.pipeline: List[Tuple[str, PipelineComponent]] = [
            ("sorter", self.scorer.sort_suggestions),
            ("filter", self.max_count_filter),
            ("joiner", join_suggestions),
        ]

    @classmethod
    def with_espan(cls, *args, **kwargs):
        return cls(*args, **kwargs, SpanClass=ESpan)

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
            callback = self._get_callback(match_name, match_hooks)
            self._add_matcher_rule(match_name, patterns, callback)

    def _add_matcher_rule(self, match_name, patterns, callback):
        if spacy_version() >= 3:
            self.matcher.add(match_name, patterns, on_match=callback, greedy="LONGEST")
        else:
            self.matcher.add(match_name, callback, patterns)

    def _get_callback(self, match_name, match_hooks):
        """
        Most matches have the same logic to be executed each time a match is found
        Some matches have extra logic, defined in match_hooks
        """
        # Get predicates once, callback is returned in a closure with this information
        predicates = get_predicates(
            match_hooks, self.default_match_hooks, self.custom_match_hooks
        )

        def cb(matcher, doc, i, matches):
            match_id, start, end = matches[i]

            for pred in predicates:
                try:
                    if pred(doc, start, end):
                        return None
                except IndexError:
                    break
            match_name = self.nlp.vocab[match_id].text
            span = self.Span(doc, start, end)

            # find in match_dict if needed
            span._.match_name = match_name

            pre_suggestions = self.match_dict[match_name]["suggestions"]

            span._.suggestions = []

            for i, x in enumerate(pre_suggestions):
                span._.suggestions += self.process_suggestions(
                    x, doc, start, end, match_name, i
                )

            for novel_prop, default_value in self.novel_prop_defaults.items():
                setattr(
                    span._,
                    novel_prop,
                    self.match_dict[match_name].get(novel_prop, default_value),
                )
            self.spans.append(span)

        return cb

    def _set_scorer(self, lm_path):
        # The following is not ideal
        # We should update replaCy to accept a Scorer as a parameter
        if lm_path:
            from replacy.scorer import KenLMScorer

            self.scorer: Scorer = KenLMScorer(nlp=self.nlp, model=load_lm(lm_path))
        else:
            self.scorer = Scorer()

    def max_count_filter(self, spans: List[Span]) -> List[Span]:
        # for each span, reduce number of suggestions
        # based on max_count of each suggestion text item
        # assumption - elements are already sorted
        for span in spans:
            suggestions = span._.suggestions
            if len(suggestions):
                rest = suggestions
                chosen = []

                while len(rest):
                    elem = rest[0]
                    rest = rest[1:]

                    # the first element in rest
                    # not eliminated => good
                    chosen.append(elem)
                    rest = eliminate_options(elem, chosen, rest)

                # log matched span and filtered out suggestions
                if self.debug:

                    self.logger.info(
                        f"{span._.match_name} matched '{span.text}' token indices {span.start}:{span.end}"
                    )
                    self.logger.info(f"Accepted suggestions: {chosen}")

                    suggestions_diff = [f for f in suggestions if f not in chosen]
                    if len(suggestions_diff):
                        self.logger.info(f"Ignored suggestions: {suggestions_diff}")

                span._.suggestions = chosen
        return spans

    def process_suggestions(
            self, pre_suggestion, doc, start, end, match_name, pre_suggestion_id
    ):
        # get token <-> pattern correspondence
        pattern = self.match_dict[match_name]["patterns"]

        suggestion_variants = self.suggestion_gen(
            pre_suggestion, doc, start, end, pattern, pre_suggestion_id
        )
        # assert there aren't more than max_suggestions_count
        # otherwise raise warning and return []
        suggestions_count = (
            seq(suggestion_variants).map(lambda x: len(x)).reduce(lambda x, y: x * y, 1)
        )

        if suggestions_count > self.max_suggestions_count:
            warnings.warn(
                f"Got {suggestions_count} suggestions, max is {self.max_suggestions_count}. \
                Will fallback to empty suggestions."
            )
            opt_combinations = []
        else:
            opt_combinations = list(itertools.product(*suggestion_variants))
            opt_combinations = [list(o) for o in opt_combinations]
        return opt_combinations

    @property
    def pipe_names(self):
        return [x[0] for x in self.pipeline]

    def add_pipe(
            self,
            component: PipelineComponent,
            name: str = None,
            before: str = None,
            after: str = None,
            first: bool = None,
            last: bool = None,
    ):
        """
        Add a component to the pipeline
        A component must take one argument, a list of spans, and return None (modify the spans)

        Optionally, you can either specify a component to add it before or after,
        tell replaCy to add it first or last in the pipeline, or define a custom name.
        If no name is set and no name attribute is present on your component, the function/class name is used.
        """
        if not at_most_one_is_not_none(before, after, first, last):
            raise ValueError("Only one of before, after, first, last can be set")
        if name is None:
            if hasattr(component, "name"):
                name = getattr(component, "name")
            else:
                name = component.__name__

        if name in self.pipe_names:
            raise ValueError(
                f"Component {component} has name collision with existing pipeline component. \
            current pipeline: {self.pipeline}"
            )
        pipeline_step = (name, component)

        if last or all([before == None, after == None, first == None, last == None]):
            self.pipeline.append(pipeline_step)
        elif first:
            self.pipeline.insert(0, pipeline_step)
        elif before:
            if before not in self.pipe_names:
                raise ValueError(
                    f"can't insert component before {before}; no component of that name in pipeline"
                )
            reference_component_index = next(
                i for i, tup in enumerate(self.pipeline) if tup[0] == before
            )
            self.pipeline.insert(reference_component_index, pipeline_step)
        elif after:
            if after == "matcher":
                # same as "first"
                self.pipeline.insert(0, pipeline_step)
            if after not in self.pipe_names:
                raise ValueError(
                    f"can't insert component after {after}; no component of that name in pipeline"
                )
            reference_component_index = next(
                i for i, tup in enumerate(self.pipeline) if tup[0] == after
            )
            self.pipeline.insert(reference_component_index + 1, pipeline_step)
        else:
            warnings.warn(
                f"Weird values passes to add_pipe, appending {name} to the end of the pipeline"
            )
            self.pipeline.append(pipeline_step)

    def remove_pipe(self, name):
        pipelines = []
        for p in self.pipeline:
            if p[0] == name:
                continue
            pipelines.append(p)
        self.pipeline = pipelines

    def __call__(self, sent):
        # self.spans must be cleared - global
        self.spans = []
        doc = make_doc_if_not_doc(sent, self.nlp)
        # this fills up self.spans
        self.matcher(doc)
        for _, component in self.pipeline:
            # the default pipeline will:
            # sort suggestions by lm score
            # filter out based on max_count
            # merge lists of words into phrases
            self.spans = component(self.spans)
            # this works because a component's signature is List[Span] -> List[Span]
        return self.spans
