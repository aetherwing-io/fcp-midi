"""Multi-index lookup registry for Song notes.

Rebuild indexes from scratch via ``rebuild(song)`` whenever the song
mutates, or maintain incrementally in a future revision.
"""

from __future__ import annotations

from collections import defaultdict

from fcp_midi.model.song import Note, Song


class Registry:
    """Indexes notes in a ``Song`` for fast multi-dimensional lookups."""

    def __init__(self) -> None:
        self._by_track: dict[str, list[Note]] = defaultdict(list)
        self._by_pitch: dict[int, list[Note]] = defaultdict(list)
        self._by_channel: dict[int, list[Note]] = defaultdict(list)
        self._all_notes: list[Note] = []

    # -- rebuild -------------------------------------------------------------

    def rebuild(self, song: Song) -> None:
        """Rebuild every index from the current state of *song*."""
        self._by_track = defaultdict(list)
        self._by_pitch = defaultdict(list)
        self._by_channel = defaultdict(list)
        self._all_notes = []

        track_name_map: dict[str, str] = {}
        for track in song.tracks.values():
            track_name_map[track.id] = track.name

        for track in song.tracks.values():
            for note in track.notes.values():
                self._all_notes.append(note)
                self._by_track[track.name].append(note)
                self._by_pitch[note.pitch.midi_number].append(note)
                self._by_channel[note.channel].append(note)

    # -- single-dimension lookups -------------------------------------------

    def by_track(self, track_name: str) -> list[Note]:
        """Return notes belonging to the track with *track_name*."""
        return list(self._by_track.get(track_name, []))

    def by_pitch(self, midi_number: int) -> list[Note]:
        """Return notes matching a specific MIDI pitch number."""
        return list(self._by_pitch.get(midi_number, []))

    def by_range(self, start_tick: int, end_tick: int) -> list[Note]:
        """Return notes whose ``absolute_tick`` falls in [start_tick, end_tick)."""
        return [
            n for n in self._all_notes
            if start_tick <= n.absolute_tick < end_tick
        ]

    def by_channel(self, channel: int) -> list[Note]:
        """Return notes on *channel*."""
        return list(self._by_channel.get(channel, []))

    def by_velocity_range(self, low: int, high: int) -> list[Note]:
        """Return notes with velocity in [low, high] (inclusive)."""
        return [n for n in self._all_notes if low <= n.velocity <= high]

    # -- combined search -----------------------------------------------------

    def search(
        self,
        track: str | None = None,
        pitch: int | None = None,
        range_start: int | None = None,
        range_end: int | None = None,
        channel: int | None = None,
        vel_low: int | None = None,
        vel_high: int | None = None,
    ) -> list[Note]:
        """Intersect multiple optional filters.  ``None`` means 'any'."""
        # Start with candidate sets and narrow down
        candidates: set[str] | None = None  # note ids

        def _intersect(note_list: list[Note]) -> None:
            nonlocal candidates
            ids = {n.id for n in note_list}
            if candidates is None:
                candidates = ids
            else:
                candidates &= ids

        if track is not None:
            _intersect(self.by_track(track))
        if pitch is not None:
            _intersect(self.by_pitch(pitch))
        if channel is not None:
            _intersect(self.by_channel(channel))
        if range_start is not None and range_end is not None:
            _intersect(self.by_range(range_start, range_end))
        if vel_low is not None and vel_high is not None:
            _intersect(self.by_velocity_range(vel_low, vel_high))

        if candidates is None:
            # No filters applied — return everything
            return list(self._all_notes)

        # Build result preserving original note objects
        return [n for n in self._all_notes if n.id in candidates]
