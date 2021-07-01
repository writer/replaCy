import warnings
from typing import Any, Callable, Dict, List, Union

import spacy
from functional import seq
from jsonschema import validate
from spacy.tokens import Doc

from replacy.db import get_match_dict_schema


def set_known_extensions(span_class):
    known_string_extensions = ["match_name"]
    known_list_extensions = ["suggestions"]
    for ext in known_list_extensions:
        span_class.set_extension(ext, default=[], force=True)
    for ext in known_string_extensions:
        span_class.set_extension(ext, default="", force=True)
    expected_properties = (
            ["patterns", "match_hook", "test"]
            + known_list_extensions
            + known_string_extensions
    )
    return expected_properties


# set custom extensions for any unexpected keys found in the match_dict
def get_novel_prop_defaults(match_dict, span_class, expected_properties):
    """
    Also mutates the ~global Span~ passed `span_class` to add any needed extensions
    """
    novel_properties = (
        seq(match_dict.values())
            .flat_map(lambda x: x.keys())
            .distinct()
            .difference(expected_properties)
    )
    novel_prop_defaults: Dict[str, Any] = {}
    for x in match_dict.values():
        for k, v in x.items():
            if k in novel_properties and k not in novel_prop_defaults.keys():
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
        span_class.set_extension(prop, default=default, force=True)
    return novel_prop_defaults


def validate_match_dict(match_dict):
    match_dict_schema = get_match_dict_schema()
    validate(instance=match_dict, schema=match_dict_schema)


def equal_except_nth_place(list1, list2, n):
    # compares two lists, skips nth place

    # if empty:
    if not len(list1) * len(list2):
        return False

    # if suggestions come from different suggestions:
    if list1[0].id != list2[0].id:
        return False

    # if different length - not equal
    if len(list1) != len(list2):
        return False

    for i in range(len(list1)):
        if i != n:
            if list1[i].text != list2[i].text:
                return False
    return True


def eliminate_options(elem, chosen, rest):
    # use elem to eliminate elements above the max_count limits
    for i, item in enumerate(elem):
        # item with no max count
        max_count = item.max_count
        elem_text = item.text
        if max_count is None:
            continue
        # item is exclusive (= max count 1)
        elif max_count == 1:
            # eliminate equal except i from rest
            rest = [r for r in rest if not equal_except_nth_place(elem, r, i)]
        # item has a custom max count
        else:
            # get hom many times this item has been used so far
            # it this very context
            current_count = [r for r in chosen if equal_except_nth_place(elem, r, i)]
            # it this is max (with elem), eliminate other options from rest
            if len(current_count) >= max_count:
                rest = [r for r in rest if not equal_except_nth_place(elem, r, i)]
    return rest


def get_predicates(
        match_hooks, default_match_hooks, custom_match_hooks
) -> List[Callable]:
    predicates = []
    for hook in match_hooks:
        # template - ex. succeeded_by_phrase
        try:
            template = getattr(default_match_hooks, hook["name"])
        except AttributeError:
            # if the hook isn't in custom_match_hooks, this will still
            # raise an exception. I think that is the correct behavior
            template = getattr(custom_match_hooks, hook["name"])

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


def make_doc_if_not_doc(text_or_doc: Union[str, Doc], nlp) -> Doc:
    if hasattr(text_or_doc, "text"):
        doc = text_or_doc
    else:
        doc = nlp(text_or_doc)
    return doc


def at_most_one_is_not_none(*args) -> bool:
    return len(list(filter(bool, [x is not None for x in args]))) <= 1


def attach_debug_hook(matches: Dict[str, Dict]) -> Dict[str, Dict]:
    new_matches = {}
    for match_name, match_dict in matches.items():
        new_dict = match_dict
        hooks = match_dict.get("match_hook", [])
        hooks.append(
            {
                "name": "debug_hook",
                "args": match_name,
                "match_if_predicate_is": True,
            }
        )
        new_dict["match_hook"] = hooks
        new_matches[match_name] = new_dict
    return new_matches


def spacy_version() -> int:
    return int(spacy.__version__.split('.')[0])
