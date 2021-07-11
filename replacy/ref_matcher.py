import copy

from spacy.matcher import Matcher

from replacy.util import spacy_version


class RefMatcher:
    def __init__(self, nlp):
        self.nlp = nlp
        self.matcher = Matcher(nlp.vocab)

    def clean_matcher(self):
        # no native method to clean spaCy matcher
        # or retrieve pattern names
        # so always add ints, starting from zero
        # and clean ints from 0 till not found
        i = 0
        while len(self.matcher) > 0 and i < 100:
            if i in self.matcher:
                self.matcher.remove(i)
            i += 1

    @staticmethod
    def is_negative(p):
        if "OP" in p and p["OP"] == "!":
            return True
        return False

    @staticmethod
    def is_droppable(p):
        if "OP" in p and p["OP"] in ["*", "?"]:
            return True
        return False

    @staticmethod
    def is_multitoken(p):
        if "OP" in p and p["OP"] in ["*", "+"]:
            return True
        return False

    def remove_skipped_ops(self, span, pattern):
        skipped_idx = []

        op_tokens = [i for (i, p) in enumerate(pattern) if RefMatcher.is_droppable(p)]

        for op in op_tokens:
            op_pattern = copy.deepcopy(pattern)
            # remove "?" to require 1 instead of 0
            if op_pattern[op]["OP"] == "?":
                if len(op_pattern[op]) == 1:
                    # if no more props,
                    # add dummy string that will never match
                    # since its not 1 token :)
                    op_pattern[op]["TEXT"] = "alice and bob"
                    op_pattern[op]["OP"] = "!"
                del op_pattern[op]["OP"]
            # change "*" to "+", to require 1+ instead of 0+
            elif op_pattern[op]["OP"] == "*":
                op_pattern[op]["OP"] = "+"
            self.matcher.add(op, None, op_pattern)

        # check whether it still matches
        matches = self.matcher(span.as_doc())
        max_matches = [m for (m, s, e) in matches if (s == 0) and (e == len(span))]

        # clean the matcher
        self.clean_matcher()

        non_op_pattern = []
        for i, p in enumerate(pattern):
            # is optional
            if "OP" in p:
                # but not found
                if not i in max_matches and not RefMatcher.is_negative(p):
                    # => to do marked non matched, skip
                    skipped_idx.append(i)
                    continue
                else:
                    if p["OP"] == "+":
                        if len(p) == 1:
                            # if no more props,
                            # add dummy string that will never match
                            # since its not 1 token :)
                            p["TEXT"] = "alice and bob"
                            p["OP"] = "!"
                        else:
                            del p["OP"]
                    elif p["OP"] == "*":
                        p["OP"] = "+"
            non_op_pattern.append(p)

        return non_op_pattern, skipped_idx

    def insert_empty_idx(self, pattern_ref, idx):
        pattern_ref_insert = {}
        for p, v in pattern_ref.items():
            if p >= idx:
                pattern_ref_insert[p + 1] = v
            else:
                pattern_ref_insert[p] = v
        pattern_ref_insert[idx] = []
        return pattern_ref_insert

    def shift_pattern_ref(self, pattern_ref, skipped_idx):
        for idx in skipped_idx:
            pattern_ref = self.insert_empty_idx(pattern_ref, idx)
        return pattern_ref

    def __call__(self, span, orig_pattern):

        pattern = copy.deepcopy(orig_pattern)

        # remove props not supported by SpaCy matcher:
        for p in pattern:
            if "TEMPLATE_ID" in p:
                del p["TEMPLATE_ID"]

        # case I: tokens <-> patterns
        # if lengths match
        # if no OP
        # => everything has been matched
        if len(span) == len(pattern) and not any(["OP" in p for p in pattern]):
            return {k: [k] for k in range(len(pattern))}

        # check which tokens are matched, remove non matched
        non_op_pattern, skipped_idx = self.remove_skipped_ops(span, pattern)

        # case II:
        # if lengths match
        # if no multitoken OPs
        # => everything has been matched
        if len(span) == len(non_op_pattern) and not any(
                [RefMatcher.is_multitoken(p) for p in non_op_pattern]
        ):
            pattern_ref = {k: [k] for k in range(len(non_op_pattern))}
            return self.shift_pattern_ref(pattern_ref, skipped_idx)

        # case III:
        # worst case
        # get shifts for multitokens
        # ie rematching cropped spans and patterns

        # A. get cropped patterns
        for i in range(len(non_op_pattern)):
            if spacy_version() >= 3:
                self.matcher.add(i, [non_op_pattern[i:]])
            else:
                self.matcher.add(i, None, non_op_pattern[i:])

        # B. get cropped spans
        docs = [span[i:].as_doc() for i in range(len(span))]

        # C. rematch
        matches = self.matcher.pipe(docs, batch_size=len(span), return_matches=True)

        # D. get pattern_ref
        pattern_ref = {}

        for i, (d, m) in enumerate(matches):
            # take max span match for doc
            if len(m):
                # len 0 shouldn't happen except weird white spaces
                m_id, m_start, m_end = max(m, key=lambda x: x[2] - x[1])

                # if cropped span matches cropped pattern
                # 1st token of cropped span belongs to 1st cropped pattern item
                if not m_id in pattern_ref:
                    pattern_ref[m_id] = [i]
                else:
                    # no changes in pattern
                    # pattern item had more tokens matched
                    # ex. "very fast ..." & "fast ... "
                    # matched with {"POS": "ADJ", "OP": "+"} ...
                    pattern_ref[m_id].append(i)

        # clean
        self.clean_matcher()

        # shift by skipped ops
        pattern_ref = self.shift_pattern_ref(pattern_ref, skipped_idx)
        return pattern_ref
