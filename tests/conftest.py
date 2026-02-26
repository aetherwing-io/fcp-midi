"""Shared test fixtures for MIDI FCP integration tests."""

from __future__ import annotations

import pytest

from fcp_midi.server.intent import IntentLayer


@pytest.fixture
def intent() -> IntentLayer:
    """Provide a fresh IntentLayer instance."""
    return IntentLayer()


@pytest.fixture
def intent_with_song(intent: IntentLayer) -> IntentLayer:
    """Provide an IntentLayer with a song already created."""
    result = intent.execute_session('new "Test Song" tempo:120 time-sig:4/4 key:C-major')
    assert result.startswith("+")
    return intent


@pytest.fixture
def intent_with_piano(intent_with_song: IntentLayer) -> IntentLayer:
    """Provide an IntentLayer with a song and a Piano track."""
    results = intent_with_song.execute_ops(
        ["track add Piano instrument:acoustic-grand-piano"]
    )
    assert any(r.startswith("+") for r in results)
    return intent_with_song
