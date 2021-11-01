import copy

from spacy.matcher import Matcher


class RefMatcher:
    def __call__(self, span, orig_pattern, alignments):
        # not all parameters are needed, adding it to have same signature as RefMatcher
        pattern_indexes = set(alignments)
        return {
            pattern_idx: [
                span_token_idx
                for span_token_idx, pattern_index in enumerate(alignments)
                if pattern_index == pattern_idx
            ]
            for pattern_idx in pattern_indexes
        }
