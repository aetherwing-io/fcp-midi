"""Full op-string parser — tokenize, classify, and structure an op string.

Produces a :class:`ParsedOp` on success or a :class:`ParseError` on failure.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from fcp_midi.parser.selector import Selector, parse_selectors
from fcp_midi.parser.tokenizer import is_key_value, parse_key_value, tokenize


@dataclass
class ParsedOp:
    """Successfully parsed operation."""

    verb: str
    raw: str  # original string
    target: str | None = None
    targets: list[str] | None = None
    params: dict[str, str] = field(default_factory=dict)
    selectors: list[Selector] = field(default_factory=list)


@dataclass
class ParseError:
    """Parsing failure."""

    error: str
    raw: str


# Verbs that operate on selectors (no positional target)
_SELECTOR_VERBS = {
    "remove",
    "move",
    "copy",
    "transpose",
    "velocity",
    "quantize",
    "modify",
    "repeat",
    "crescendo",
    "decrescendo",
}

# Verbs that take a track name as first positional arg
_TRACK_TARGET_VERBS = {
    "note",
    "chord",
    "cc",
    "bend",
    "mute",
    "solo",
    "program",
}

# Verbs that take a single value positional arg
_VALUE_VERBS = {
    "tempo",
    "time-sig",
    "key-sig",
    "marker",
    "title",
}


def parse_op(op_string: str) -> ParsedOp | ParseError:
    """Parse an op string into a structured :class:`ParsedOp`.

    Parameters
    ----------
    op_string : str
        The raw op string, e.g. ``'note Piano C4 at:1.1 dur:quarter vel:80'``.

    Returns
    -------
    ParsedOp | ParseError
    """
    raw = op_string.strip()
    if not raw:
        return ParseError(error="Empty op string", raw=raw)

    try:
        tokens = tokenize(raw)
    except ValueError as exc:
        return ParseError(error=f"Tokenization failed: {exc}", raw=raw)

    if not tokens:
        return ParseError(error="No tokens after tokenization", raw=raw)

    verb = tokens[0].lower()
    rest = tokens[1:]

    # Separate selectors, key:value params, and positional args
    selectors = parse_selectors(rest)
    params: dict[str, str] = {}
    positional: list[str] = []

    for token in rest:
        if token.startswith("@"):
            continue  # already captured as selectors
        if is_key_value(token):
            k, v = parse_key_value(token)
            params[k] = v
        else:
            positional.append(token)

    # Dispatch by verb type
    if verb == "track":
        return _parse_track_verb(verb, raw, positional, params, selectors)
    elif verb in _SELECTOR_VERBS:
        return _parse_selector_verb(verb, raw, positional, params, selectors)
    elif verb in _TRACK_TARGET_VERBS:
        return _parse_track_target_verb(verb, raw, positional, params, selectors)
    elif verb in _VALUE_VERBS:
        return _parse_value_verb(verb, raw, positional, params, selectors)
    else:
        # Unknown verb — return a best-effort parse
        target = positional[0] if positional else None
        return ParsedOp(
            verb=verb,
            raw=raw,
            target=target,
            targets=positional if positional else None,
            params=params,
            selectors=selectors,
        )


def _parse_track_verb(
    verb: str,
    raw: str,
    positional: list[str],
    params: dict[str, str],
    selectors: list[Selector],
) -> ParsedOp:
    """Parse ``track add NAME ...`` or ``track remove NAME``."""
    if not positional:
        return ParsedOp(verb=verb, raw=raw, params=params, selectors=selectors)

    sub_command = positional[0]  # "add" or "remove"
    remaining = positional[1:]

    op = ParsedOp(
        verb=verb,
        raw=raw,
        target=sub_command,
        params=params,
        selectors=selectors,
    )

    if remaining:
        op.params["name"] = remaining[0]
        # Additional positional args go into targets
        if len(remaining) > 1:
            op.targets = remaining[1:]

    return op


def _parse_selector_verb(
    verb: str,
    raw: str,
    positional: list[str],
    params: dict[str, str],
    selectors: list[Selector],
) -> ParsedOp:
    """Parse verbs that primarily operate on selectors (remove, move, etc.)."""
    # Positional args for selector verbs are often modifier values like "+5"
    target = positional[0] if positional else None
    return ParsedOp(
        verb=verb,
        raw=raw,
        target=target,
        targets=positional if positional else None,
        params=params,
        selectors=selectors,
    )


def _parse_track_target_verb(
    verb: str,
    raw: str,
    positional: list[str],
    params: dict[str, str],
    selectors: list[Selector],
) -> ParsedOp:
    """Parse verbs that take a track name as the first positional arg.

    Examples: ``note Piano C4``, ``cc Piano volume 100``, ``mute Piano``
    """
    target = positional[0] if positional else None
    remaining = positional[1:]

    op = ParsedOp(
        verb=verb,
        raw=raw,
        target=target,
        params=params,
        selectors=selectors,
    )

    # Store remaining positional args based on verb
    if verb == "note" and remaining:
        op.params.setdefault("pitch", remaining[0])
        if len(remaining) > 1:
            op.targets = remaining[1:]
    elif verb == "chord" and remaining:
        op.params.setdefault("chord", remaining[0])
        if len(remaining) > 1:
            op.targets = remaining[1:]
    elif verb == "cc" and remaining:
        if len(remaining) >= 1:
            op.params.setdefault("cc_name", remaining[0])
        if len(remaining) >= 2:
            op.params.setdefault("cc_value", remaining[1])
        if len(remaining) > 2:
            op.targets = remaining[2:]
    elif verb == "bend" and remaining:
        op.params.setdefault("value", remaining[0])
        if len(remaining) > 1:
            op.targets = remaining[1:]
    elif verb == "program" and remaining:
        op.params.setdefault("instrument", remaining[0])
        if len(remaining) > 1:
            op.targets = remaining[1:]
    elif remaining:
        op.targets = remaining

    return op


def _parse_value_verb(
    verb: str,
    raw: str,
    positional: list[str],
    params: dict[str, str],
    selectors: list[Selector],
) -> ParsedOp:
    """Parse verbs that take a value as the first positional arg.

    Examples: ``tempo 120``, ``time-sig 3/4``, ``title "My Song"``
    """
    target = positional[0] if positional else None
    remaining = positional[1:]

    return ParsedOp(
        verb=verb,
        raw=raw,
        target=target,
        targets=remaining if remaining else None,
        params=params,
        selectors=selectors,
    )
