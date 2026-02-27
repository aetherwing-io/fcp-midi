"""Quote-aware tokenizer — re-exported from fcp_core.

This module is a compatibility shim. All tokenizer functionality
now lives in the ``fcp_core.tokenizer`` module.
"""

from fcp_core.tokenizer import (  # noqa: F401
    is_arrow,
    is_key_value,
    is_selector,
    parse_key_value,
    tokenize,
)

__all__ = [
    "tokenize",
    "is_key_value",
    "parse_key_value",
    "is_selector",
    "is_arrow",
]
