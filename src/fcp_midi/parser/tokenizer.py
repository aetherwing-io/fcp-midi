"""Quote-aware tokenizer for op strings.

Splits on whitespace but respects quoted strings (single and double quotes).
Provides helpers for key:value token detection and parsing.
"""

from __future__ import annotations

import shlex


def tokenize(op_string: str) -> list[str]:
    """Split *op_string* on whitespace, respecting quoted substrings.

    Examples
    --------
    >>> tokenize('note Piano "My Track" at:1.1')
    ['note', 'Piano', 'My Track', 'at:1.1']
    >>> tokenize("note Piano 'My Track' at:1.1")
    ['note', 'Piano', 'My Track', 'at:1.1']
    """
    lexer = shlex.shlex(op_string, posix=True)
    lexer.whitespace_split = True
    lexer.whitespace = " \t\n\r"
    tokens: list[str] = list(lexer)
    return tokens


def is_key_value(token: str) -> bool:
    """Return True if *token* is a ``key:value`` pair.

    A key:value token contains ``:``, does NOT start with ``@``
    (that is a selector), and is not an arrow (``->``).
    """
    if token.startswith("@"):
        return False
    if "->" in token:
        return False
    return ":" in token


def parse_key_value(token: str) -> tuple[str, str]:
    """Split *token* on the first ``:`` and return ``(key, value)``."""
    key, _, value = token.partition(":")
    return key, value
