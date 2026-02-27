"""Semantic model for MIDI compositions.

All timing is stored as absolute ticks. Conversion to/from seconds and
measure.beat positions is handled by the timing module.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field


def _id() -> str:
    return uuid.uuid4().hex[:8]


@dataclass
class Pitch:
    name: str  # "C", "D", ..., "B"
    accidental: str  # "", "#", "b", "##", "bb"
    octave: int  # 4 = middle C octave
    midi_number: int  # 0-127, computed from name+accidental+octave


@dataclass
class Note:
    id: str
    track_id: str
    pitch: Pitch
    absolute_tick: int
    duration_ticks: int
    velocity: int  # 1-127
    channel: int  # 0-15


@dataclass
class ControlChange:
    id: str
    track_id: str
    absolute_tick: int
    controller: int  # 0-127
    value: int  # 0-127
    channel: int


@dataclass
class PitchBend:
    id: str
    track_id: str
    absolute_tick: int
    value: int  # -8192 to 8191
    channel: int


@dataclass
class TempoChange:
    absolute_tick: int
    bpm: float


@dataclass
class TimeSignature:
    absolute_tick: int
    numerator: int
    denominator: int  # actual value (4, not power-of-2)


@dataclass
class KeySignature:
    absolute_tick: int
    key: str  # "C", "G", "Bb", etc.
    mode: str  # "major" or "minor"


@dataclass
class Marker:
    absolute_tick: int
    text: str


@dataclass
class Track:
    id: str
    name: str
    channel: int  # default channel (0-15)
    instrument: str | None = None  # GM name
    program: int | None = None  # GM number (0-127)
    bank_msb: int | None = None  # CC#0 Bank Select MSB (0-127)
    bank_lsb: int | None = None  # CC#32 Bank Select LSB (0-127)
    notes: dict[str, Note] = field(default_factory=dict)
    control_changes: dict[str, ControlChange] = field(default_factory=dict)
    pitch_bends: dict[str, PitchBend] = field(default_factory=dict)
    mute: bool = False
    solo: bool = False


@dataclass
class Song:
    id: str
    title: str
    file_path: str | None = None
    format: int = 1  # 0 or 1
    ppqn: int = 480  # ticks per quarter note
    tracks: dict[str, Track] = field(default_factory=dict)
    track_order: list[str] = field(default_factory=list)
    tempo_map: list[TempoChange] = field(default_factory=list)
    time_signatures: list[TimeSignature] = field(default_factory=list)
    key_signatures: list[KeySignature] = field(default_factory=list)
    markers: list[Marker] = field(default_factory=list)

    # --- Factory ---

    @classmethod
    def create(
        cls,
        title: str = "Untitled",
        tempo: float = 120.0,
        time_sig: tuple[int, int] = (4, 4),
        key: str | None = None,
        ppqn: int = 480,
    ) -> Song:
        song = cls(
            id=_id(),
            title=title,
            ppqn=ppqn,
            tempo_map=[TempoChange(absolute_tick=0, bpm=tempo)],
            time_signatures=[
                TimeSignature(
                    absolute_tick=0,
                    numerator=time_sig[0],
                    denominator=time_sig[1],
                )
            ],
        )
        if key:
            parts = key.replace("-", " ").split()
            k = parts[0] if parts else "C"
            mode = parts[1] if len(parts) > 1 else "major"
            song.key_signatures.append(
                KeySignature(absolute_tick=0, key=k, mode=mode)
            )
        return song

    # --- Track CRUD ---

    def add_track(
        self,
        name: str,
        instrument: str | None = None,
        program: int | None = None,
        channel: int | None = None,
    ) -> Track:
        tid = _id()
        if channel is None:
            channel = self._next_channel()
        track = Track(
            id=tid,
            name=name,
            channel=channel,
            instrument=instrument,
            program=program,
        )
        self.tracks[tid] = track
        self.track_order.append(tid)
        return track

    def remove_track(self, track_id: str) -> Track | None:
        track = self.tracks.pop(track_id, None)
        if track and track_id in self.track_order:
            self.track_order.remove(track_id)
        return track

    def get_track_by_name(self, name: str) -> Track | None:
        name_lower = name.lower()
        for t in self.tracks.values():
            if t.name.lower() == name_lower:
                return t
        return None

    # --- Note CRUD ---

    def add_note(
        self,
        track_id: str,
        pitch: Pitch,
        absolute_tick: int,
        duration_ticks: int,
        velocity: int = 80,
        channel: int | None = None,
    ) -> Note:
        track = self.tracks[track_id]
        if channel is None:
            channel = track.channel
        nid = _id()
        note = Note(
            id=nid,
            track_id=track_id,
            pitch=pitch,
            absolute_tick=absolute_tick,
            duration_ticks=duration_ticks,
            velocity=velocity,
            channel=channel,
        )
        track.notes[nid] = note
        return note

    def remove_note(self, track_id: str, note_id: str) -> Note | None:
        track = self.tracks.get(track_id)
        if track:
            return track.notes.pop(note_id, None)
        return None

    # --- CC CRUD ---

    def add_cc(
        self,
        track_id: str,
        controller: int,
        value: int,
        absolute_tick: int,
        channel: int | None = None,
    ) -> ControlChange:
        track = self.tracks[track_id]
        if channel is None:
            channel = track.channel
        cid = _id()
        cc = ControlChange(
            id=cid,
            track_id=track_id,
            absolute_tick=absolute_tick,
            controller=controller,
            value=value,
            channel=channel,
        )
        track.control_changes[cid] = cc
        return cc

    # --- PitchBend CRUD ---

    def add_pitch_bend(
        self,
        track_id: str,
        value: int,
        absolute_tick: int,
        channel: int | None = None,
    ) -> PitchBend:
        track = self.tracks[track_id]
        if channel is None:
            channel = track.channel
        pid = _id()
        pb = PitchBend(
            id=pid,
            track_id=track_id,
            absolute_tick=absolute_tick,
            value=value,
            channel=channel,
        )
        track.pitch_bends[pid] = pb
        return pb

    # --- Meta ---

    def add_tempo(self, bpm: float, absolute_tick: int = 0) -> None:
        self.tempo_map.append(TempoChange(absolute_tick=absolute_tick, bpm=bpm))
        self.tempo_map.sort(key=lambda t: t.absolute_tick)

    def add_time_signature(
        self, numerator: int, denominator: int, absolute_tick: int = 0
    ) -> None:
        self.time_signatures.append(
            TimeSignature(
                absolute_tick=absolute_tick,
                numerator=numerator,
                denominator=denominator,
            )
        )
        self.time_signatures.sort(key=lambda t: t.absolute_tick)

    def add_key_signature(
        self, key: str, mode: str, absolute_tick: int = 0
    ) -> None:
        self.key_signatures.append(
            KeySignature(absolute_tick=absolute_tick, key=key, mode=mode)
        )
        self.key_signatures.sort(key=lambda t: t.absolute_tick)

    def add_marker(self, text: str, absolute_tick: int = 0) -> None:
        self.markers.append(Marker(absolute_tick=absolute_tick, text=text))
        self.markers.sort(key=lambda m: m.absolute_tick)

    # --- Helpers ---

    def _next_channel(self) -> int:
        """Auto-assign next available channel (skip 9 = drums)."""
        used = {t.channel for t in self.tracks.values()}
        for ch in [0, 1, 2, 3, 4, 5, 6, 7, 8, 10, 11, 12, 13, 14, 15]:
            if ch not in used:
                return ch
        return 0  # fallback

    def get_digest(self) -> str:
        """Compact state fingerprint appended to every mutation response."""
        n_tracks = len(self.tracks)
        n_events = sum(
            len(t.notes) + len(t.control_changes) + len(t.pitch_bends)
            for t in self.tracks.values()
        )
        tempo = self.tempo_map[0].bpm if self.tempo_map else 120
        ts = self.time_signatures[0] if self.time_signatures else None
        ts_str = f"{ts.numerator}/{ts.denominator}" if ts else "4/4"
        ks = self.key_signatures[0] if self.key_signatures else None
        ks_str = f"{ks.key}-{ks.mode}" if ks else ""

        # Estimate total measures
        if self.tracks:
            max_tick = 0
            for t in self.tracks.values():
                for n in t.notes.values():
                    end = n.absolute_tick + n.duration_ticks
                    if end > max_tick:
                        max_tick = end
            if ts:
                ticks_per_measure = (
                    self.ppqn * 4 * ts.numerator // ts.denominator
                )
                measures = max_tick // ticks_per_measure if ticks_per_measure else 0
            else:
                measures = max_tick // (self.ppqn * 4)
        else:
            measures = 0

        parts = [
            f"{n_tracks}t",
            f"{n_events}e",
            f"tempo:{tempo:.0f}",
            ts_str,
        ]
        if ks_str:
            parts.append(ks_str)
        if measures:
            parts.append(f"{measures}bars")
        return f"[{' '.join(parts)}]"
