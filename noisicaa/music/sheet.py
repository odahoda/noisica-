#!/usr/bin/python3

import logging

from noisicaa import core

from . import model
from . import state
from . import commands
from . import mutations
from . import score_track
from . import track_group
from . import sheet_property_track

logger = logging.getLogger(__name__)


class AddTrack(commands.Command):
    track_type = core.Property(str)
    parent_group_id = core.Property(str)

    def __init__(self, track_type=None, parent_group_id=None, state=None):
        super().__init__(state=state)
        if state is None:
            self.track_type = track_type
            self.parent_group_id = parent_group_id

    def run(self, sheet):
        assert isinstance(sheet, Sheet)
        project = sheet.root

        parent_group = project.get_object(self.parent_group_id)
        assert parent_group.is_child_of(sheet)
        assert isinstance(parent_group, track_group.TrackGroup)

        if len(parent_group.tracks) > 0:
            num_measures = max(
                len(track.measures)
                for track in parent_group.tracks)
        else:
            num_measures = 1

        track_name = "Track %d" % (len(parent_group.tracks) + 1)
        track_cls_map = {
            'score': score_track.ScoreTrack,
            'group': track_group.TrackGroup,
        }
        track_cls = track_cls_map[self.track_type]
        track = track_cls(name=track_name, num_measures=num_measures)
        parent_group.tracks.append(track)

        track.add_to_pipeline()

        return len(parent_group.tracks) - 1

commands.Command.register_command(AddTrack)


class RemoveTrack(commands.Command):
    track_id = core.Property(str)

    def __init__(self, track_id=None, state=None):
        super().__init__(state=state)
        if state is None:
            self.track_id = track_id

    def run(self, sheet):
        assert isinstance(sheet, Sheet)
        project = sheet.root

        track = project.get_object(self.track_id)
        assert track.is_child_of(sheet)
        parent_group = track.parent

        track.remove_from_pipeline()

        del parent_group.tracks[track.index]

commands.Command.register_command(RemoveTrack)


class MoveTrack(commands.Command):
    track = core.Property(int)
    direction = core.Property(int)

    def __init__(self, track=None, direction=None, state=None):
        super().__init__(state=state)
        if state is None:
            self.track = track
            self.direction = direction

    def run(self, sheet):
        assert isinstance(sheet, Sheet)

        track = sheet.master_group.tracks[self.track]
        assert track.index == self.track

        if self.direction == 0:
            raise ValueError("No direction given.")

        if self.direction < 0:
            if track.index == 0:
                raise ValueError("Can't move first track up.")
            new_pos = track.index - 1
            del sheet.master_group.tracks[track.index]
            sheet.master_group.tracks.insert(new_pos, track)

        elif self.direction > 0:
            if track.index == len(sheet.master_group.tracks) - 1:
                raise ValueError("Can't move last track down.")
            new_pos = track.index + 1
            del sheet.master_group.tracks[track.index]
            sheet.master_group.tracks.insert(new_pos, track)

        return track.index

commands.Command.register_command(MoveTrack)


class InsertMeasure(commands.Command):
    tracks = core.ListProperty(int)
    pos = core.Property(int)

    def __init__(self, tracks=None, pos=None, state=None):
        super().__init__(state=state)
        if state is None:
            self.tracks.extend(tracks)
            self.pos = pos

    def run(self, sheet):
        assert isinstance(sheet, Sheet)

        if not self.tracks:
            sheet.property_track.insert_measure(self.pos)
        else:
            sheet.property_track.append_measure()

        for idx, track in enumerate(sheet.master_group.tracks):
            if not self.tracks or idx in self.tracks:
                track.insert_measure(self.pos)
            else:
                track.append_measure()

commands.Command.register_command(InsertMeasure)


class RemoveMeasure(commands.Command):
    tracks = core.ListProperty(int)
    pos = core.Property(int)

    def __init__(self, tracks=None, pos=None, state=None):
        super().__init__(state=state)
        if state is None:
            self.tracks.extend(tracks)
            self.pos = pos

    def run(self, sheet):
        assert isinstance(sheet, Sheet)

        if not self.tracks:
            sheet.property_track.remove_measure(self.pos)

        for idx, track in enumerate(sheet.master_group.tracks):
            if not self.tracks or idx in self.tracks:
                track.remove_measure(self.pos)
                if self.tracks:
                    track.append_measure()

commands.Command.register_command(RemoveMeasure)


class Sheet(model.Sheet, state.StateBase):
    def __init__(self, name=None, num_tracks=1, state=None):
        super().__init__(state)

        if state is None:
            self.name = name

            self.master_group = track_group.MasterTrackGroup(name="Master")
            self.property_track = sheet_property_track.SheetPropertyTrack(name="Time")

            for i in range(num_tracks):
                self.master_group.tracks.append(
                    score_track.ScoreTrack(name="Track %d" % i))

    @property
    def project(self):
        return self.parent

    @property
    def all_tracks(self):
        return [self.property_track] + list(self.master_group.tracks)

    def clear(self):
        pass

    def equalize_tracks(self, remove_trailing_empty_measures=0):
        if len(self.master_group.tracks) < 1:
            return

        while remove_trailing_empty_measures > 0:
            max_length = max(len(track.measures) for track in self.all_tracks)
            if max_length < 2:
                break

            can_remove = True
            for track in self.all_tracks:
                if len(track.measures) < max_length:
                    continue
                if not track.measures[max_length - 1].empty:
                    can_remove = False
            if not can_remove:
                break

            for track in self.all_tracks:
                if len(track.measures) < max_length:
                    continue
                track.remove_measure(max_length - 1)

            remove_trailing_empty_measures -= 1

        max_length = max(len(track.measures) for track in self.all_tracks)

        for track in self.all_tracks:
            while len(track.measures) < max_length:
                track.append_measure()

    def handle_pipeline_mutation(self, mutation):
        self.listeners.call('pipeline_mutations', mutation)

    def add_to_pipeline(self):
        self.master_group.add_to_pipeline()

    def remove_from_pipeline(self):
        self.master_group.remove_from_pipeline()


state.StateBase.register_class(Sheet)
