"""Replace text with lorem ipsum, keeping what the parse rules need.

A line is split into tokens at whitespace. The part of a token inside a kept span (a
heading marker, a clause number, a defined term, a cross-reference…) is kept as it is,
along with its punctuation and a possessive 's. Everything else keeps its punctuation and
capitalisation, but its letters become a lorem ipsum word of about the same length and its
digits become zeros. So "2.1 Words
importing one gender;" might become "2.1 Lorem ipsum dolor sitam;": the number, the
sentence breaks and the shape of the line survive, and the words don't.
"""
from __future__ import annotations

import re
from collections import defaultdict

LOREM = (
    "lorem ipsum dolor sit amet consectetur adipiscing elit sed do eiusmod tempor "
    "incididunt ut labore et dolore magna aliqua enim ad minim veniam quis nostrud "
    "exercitation ullamco laboris nisi aliquip ex ea commodo consequat duis aute irure in "
    "reprehenderit voluptate velit esse cillum fugiat nulla pariatur excepteur sint "
    "occaecat cupidatat non proident sunt culpa qui officia deserunt mollit anim id est "
    "laborum curabitur pretium tincidunt lacus nunc pulvinar sapien ligula ornare massa "
    "vestibulum sollicitudin condimentum fermentum habitant morbi tristique senectus netus "
    "malesuada fames turpis egestas"
).split()

# Numbering at the start of a line: "2.1", "12.", "(3)", "(iv)", "A1".
NUMBERING = r"^\s*(?:\d{1,3}(?:\.\d+)*\.?|\((?:\d{1,3}|[a-z]{1,2}|[ivxl]{1,6})\)|[A-D]\d{1,2})(?=\s|$)"
TOKEN = re.compile(r"\S+")
CORE = re.compile(r"[^\W_](?:.*[^\W_])?", re.S)  # first to last letter or digit


class Redactor:
    def __init__(self, keep: list[str] = (), terms: list[str] = ()):
        self.patterns = [re.compile(NUMBERING)] + [re.compile(p) for p in keep]
        terms = sorted({t for t in terms if t.strip()}, key=len, reverse=True)
        if terms:
            self.patterns.append(re.compile(r"(?<!\w)(?:" + "|".join(map(re.escape, terms)) + r")(?!\w)"))
        self._by_length: dict[int, list[str]] = defaultdict(list)
        for word in LOREM:
            self._by_length[len(word)].append(word)
        self._counter = 0

    def kept(self, text: str) -> list[bool]:
        mask = [False] * len(text)
        for pattern in self.patterns:
            for m in pattern.finditer(text):
                for i in range(m.start(), m.end()):
                    mask[i] = True
        return mask

    def word(self, original: str) -> str:
        """A lorem word shaped like the original: same case, about the same length."""
        if not re.search(r"[^\W\d_]", original):
            return re.sub(r"\d", "0", original)  # numbers, dates and amounts: zeros
        length = len(original)
        for delta in (0, 1, -1, 2, -2, 3, -3, 4, -4, 5, 6, 7):
            candidates = self._by_length.get(length + delta)
            if candidates:
                break
        else:
            candidates = [max(LOREM, key=len)]
        self._counter += 1
        word = candidates[self._counter % len(candidates)]
        while len(word) < length - 3:  # a long word: join lorem words to about its length
            self._counter += 1
            word += LOREM[self._counter % len(LOREM)]
        word = word[: max(length + 1, 2)]
        if original.isupper() and len(original) > 1:
            return word.upper()
        if original[0].isupper():
            return word[0].upper() + word[1:]
        return word

    def token(self, token: str) -> str:
        m = CORE.search(token)
        if not m:
            return token  # punctuation only: bullets, dashes, brackets
        return token[: m.start()] + self.word(m.group()) + token[m.end():]

    def partial(self, token: str, mask: list[bool]) -> str:
        """A token with only some characters kept: keep those, replace the rest."""
        if all(mask):
            return token
        if not any(mask):
            return self.token(token)
        out, start = [], 0
        for i in range(1, len(token) + 1):
            if i == len(token) or mask[i] != mask[start]:
                run = token[start:i]
                if mask[start] or not CORE.search(run) or re.fullmatch(r"['’]s\W*", run):
                    out.append(run)  # kept, punctuation, or a possessive after a kept term
                else:
                    out.append(self.token(run))
                start = i
        return "".join(out)

    def spans(self, text: str) -> list[tuple[int, int, str]]:
        """Each token's (start, end, replacement)."""
        mask = self.kept(text)
        return [(m.start(), m.end(), self.partial(m.group(), mask[m.start():m.end()])) for m in TOKEN.finditer(text)]

    def line(self, text: str) -> str:
        pieces, last = [], 0
        for start, end, replacement in self.spans(text):
            pieces += [text[last:start], replacement]
            last = end
        return "".join(pieces) + text[last:]
