"""Custom exception hierarchy for fcp-midi."""

from __future__ import annotations


class FcpError(Exception):
    """Base exception for all fcp-midi errors."""


class ValidationError(FcpError, ValueError):
    """Invalid user input (pitch, duration, position, etc.).

    Subclasses both FcpError and ValueError so existing ``except ValueError``
    handlers continue to work during the transition.
    """


class StateError(FcpError):
    """Invalid operation given the current song/session state."""


class SerializationError(FcpError):
    """Error during MIDI file import or export."""
