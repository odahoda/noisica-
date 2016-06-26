#/usr/bin/python3

import fractions

from noisicaa import core
from noisicaa.instr import model as instr_model
from . import pitch
from . import time
from . import clef
from . import key_signature
from . import time_signature

class Measure(core.ObjectBase):
    pass


class Track(core.ObjectBase):
    name = core.Property(str)
    instrument = core.ObjectProperty(cls=instr_model.Instrument)
    measures = core.ObjectListProperty(cls=Measure)

    visible = core.Property(bool, default=True)
    muted = core.Property(bool, default=False)
    volume = core.Property(float, default=100.0)
    transpose_octaves = core.Property(int, default=0)


class Note(core.ObjectBase):
    pitches = core.ListProperty(pitch.Pitch)
    base_duration = core.Property(time.Duration)
    dots = core.Property(int, default=0)
    tuplet = core.Property(int, default=0)

    @property
    def is_rest(self):
        return len(self.pitches) == 1 and self.pitches[0].is_rest

    @property
    def max_allowed_dots(self):
        if self.base_duration <= time.Duration(1, 32):
            return 0
        if self.base_duration <= time.Duration(1, 16):
            return 1
        if self.base_duration <= time.Duration(1, 8):
            return 2
        return 3

    @property
    def duration(self):
        duration = self.base_duration
        for _ in range(self.dots):
            duration *= fractions.Fraction(3, 2)
        if self.tuplet == 3:
            duration *= fractions.Fraction(2, 3)
        elif self.tuplet == 5:
            duration *= fractions.Fraction(4, 5)
        return time.Duration(duration)


class ScoreMeasure(Measure):
    clef = core.Property(clef.Clef, default=clef.Clef.Treble)
    key_signature = core.Property(
        key_signature.KeySignature,
        default=key_signature.KeySignature('C major'))
    notes = core.ObjectListProperty(cls=Note)


class ScoreTrack(Track):
    transpose_octaves = core.Property(int, default=0)


class SheetPropertyMeasure(Measure):
    bpm = core.Property(int, default=120)
    time_signature = core.Property(
        time_signature.TimeSignature,
        default=time_signature.TimeSignature(4, 4))


class SheetPropertyTrack(Track):
    pass


class Sheet(core.ObjectBase):
    name = core.Property(str, default="Sheet")
    tracks = core.ObjectListProperty(Track)
    property_track = core.ObjectProperty(SheetPropertyTrack)


class Metadata(core.ObjectBase):
    author = core.Property(str, allow_none=True)
    license = core.Property(str, allow_none=True)
    copyright = core.Property(str, allow_none=True)
    created = core.Property(int, allow_none=True)


class Project(core.ObjectBase):
    sheets = core.ObjectListProperty(cls=Sheet)
    current_sheet = core.Property(int, default=0)
    metadata = core.ObjectProperty(cls=Metadata)

