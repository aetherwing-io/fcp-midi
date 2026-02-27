"""Selector parser — extracts @-prefixed selectors from token lists.

Selector types
--------------
- ``@track:NAME``
- ``@channel:N``
- ``@range:M.B-M.B``
- ``@pitch:P``
- ``@velocity:N-M``
- ``@all``
- ``@recent``
- ``@recent:N``
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Selector:
    """A parsed selector from an op string."""

    type: str  # "track", "channel", "range", "pitch", "velocity", "all", "recent"
    value: str  # raw value string
    negated: bool = False  # True when parsed from @not:type:value


def parse_selectors(tokens: list[str]) -> list[Selector]:
    """Extract selectors from a list of tokens.

    Parameters
    ----------
    tokens : list[str]
        Token list (e.g. from :func:`tokenize`). Only tokens starting
        with ``@`` are processed.

    Returns
    -------
    list[Selector]
    """
    selectors: list[Selector] = []
    for token in tokens:
        if not token.startswith("@"):
            continue

        raw = token[1:]  # strip leading @

        # Check for @not:type:value negation prefix
        negated = False
        if raw.startswith("not:"):
            negated = True
            raw = raw[4:]  # strip "not:"

        if ":" in raw:
            sel_type, _, sel_value = raw.partition(":")
        else:
            sel_type = raw
            sel_value = ""

        selectors.append(Selector(type=sel_type, value=sel_value, negated=negated))

    return selectors
