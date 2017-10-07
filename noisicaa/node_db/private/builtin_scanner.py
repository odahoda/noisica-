#!/usr/bin/python3

# @begin:license
#
# Copyright (c) 2015-2017, Benjamin Niemann <pink@odahoda.de>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#
# @end:license

import logging
import textwrap

from noisicaa import constants
from noisicaa import node_db

from . import scanner

logger = logging.getLogger(__name__)


TrackMixerDescription = node_db.ProcessorDescription(
    display_name='Mixer',
    processor_name='track_mixer',
    ports=[
        node_db.AudioPortDescription(
            name='in:left',
            direction=node_db.PortDirection.Input),
        node_db.AudioPortDescription(
            name='in:right',
            direction=node_db.PortDirection.Input),
        node_db.AudioPortDescription(
            name='out:left',
            direction=node_db.PortDirection.Output),
        node_db.AudioPortDescription(
            name='out:right',
            direction=node_db.PortDirection.Output),
        node_db.KRateControlPortDescription(
            name='gain',
            direction=node_db.PortDirection.Input),
        node_db.KRateControlPortDescription(
            name='muted',
            direction=node_db.PortDirection.Input),
        node_db.KRateControlPortDescription(
            name='pan',
            direction=node_db.PortDirection.Input),
    ])

IPCDescription = node_db.ProcessorDescription(
    display_name='IPC',
    processor_name='ipc',
    ports=[
        node_db.AudioPortDescription(
            name='out:left',
            direction=node_db.PortDirection.Output),
        node_db.AudioPortDescription(
            name='out:right',
            direction=node_db.PortDirection.Output),
    ],
    parameters=[
        node_db.StringParameterDescription(
            name='ipc_address', hidden=True)
    ])

AudioSourceDescription = node_db.UserNodeDescription(
    display_name='Audio',
    node_cls='track_audio_source',
    ports=[
        node_db.AudioPortDescription(
            name='out:left',
            direction=node_db.PortDirection.Output),
        node_db.AudioPortDescription(
            name='out:right',
            direction=node_db.PortDirection.Output),
    ])

EventSourceDescription = node_db.UserNodeDescription(
    display_name='Events',
    node_cls='track_event_source',
    ports=[
        node_db.EventPortDescription(
            name='out',
            direction=node_db.PortDirection.Output),
    ])

ControlSourceDescription = node_db.UserNodeDescription(
    display_name='Control',
    node_cls='track_control_source',
    ports=[
        node_db.ARateControlPortDescription(
            name='out',
            direction=node_db.PortDirection.Output),
    ])

SinkDescription = node_db.ProcessorDescription(
    display_name='Audio Out',
    processor_name='sink',
    ports=[
        node_db.AudioPortDescription(
            name='in:left',
            direction=node_db.PortDirection.Input),
        node_db.AudioPortDescription(
            name='in:right',
            direction=node_db.PortDirection.Input),
    ])

FluidSynthDescription = node_db.ProcessorDescription(
    display_name='FluidSynth',
    processor_name='fluidsynth',
    ports=[
        node_db.EventPortDescription(
            name='in',
            direction=node_db.PortDirection.Input),
        node_db.AudioPortDescription(
            name='out:left',
            direction=node_db.PortDirection.Output),
        node_db.AudioPortDescription(
            name='out:right',
            direction=node_db.PortDirection.Output),
    ],
    parameters=[
        node_db.IntParameterDescription(
            name='bank', hidden=True, min=0, max=127),
        node_db.IntParameterDescription(
            name='preset', hidden=True, min=0, max=127),
        node_db.StringParameterDescription(
            name='soundfont_path', hidden=True),
    ])

SamplePlayerDescription = node_db.ProcessorDescription(
    display_name='Sampler',
    processor_name='sample_player',
    ports=[
        node_db.EventPortDescription(
            name='in',
            direction=node_db.PortDirection.Input),
        node_db.AudioPortDescription(
            name='out:left',
            direction=node_db.PortDirection.Output),
        node_db.AudioPortDescription(
            name='out:right',
            direction=node_db.PortDirection.Output),
    ],
    parameters=[
        node_db.StringParameterDescription(
            name='sample_path',
            hidden=True,
            display_name='Path'),
    ])

SoundFileDescription = node_db.ProcessorDescription(
    display_name='Sound Player',
    processor_name='sound_file',
    ports=[
        node_db.AudioPortDescription(
            name='out:left',
            direction=node_db.PortDirection.Output),
        node_db.AudioPortDescription(
            name='out:right',
            direction=node_db.PortDirection.Output),
    ],
    parameters=[
        node_db.StringParameterDescription(
            name='sound_file_path',
            hidden=True,
            display_name='Path'),
    ])

CustomCSoundDescription = node_db.ProcessorDescription(
    display_name='Custom CSound',
    processor_name='custom_csound',
    ports=[
        node_db.AudioPortDescription(
            name='in:left',
            direction=node_db.PortDirection.Input),
        node_db.AudioPortDescription(
            name='in:right',
            direction=node_db.PortDirection.Input),
        node_db.ARateControlPortDescription(
            name='ctrl',
            direction=node_db.PortDirection.Input),
        node_db.EventPortDescription(
            name='ev',
            direction=node_db.PortDirection.Input),
        node_db.AudioPortDescription(
            name='out:left',
            direction=node_db.PortDirection.Output),
        node_db.AudioPortDescription(
            name='out:right',
            direction=node_db.PortDirection.Output),
    ],
    parameters=[
        node_db.TextParameterDescription(
            name='csound_orchestra',
            display_name='Orchestra Code',
            content_type='text/csound-orchestra',
            default=textwrap.dedent("""\
                instr 2
                    gaOutLeft = gaInLeft
                    gaOutRight = gaInRight
                endin
            """)),
        node_db.TextParameterDescription(
            name='csound_score',
            display_name='Score',
            content_type='text/csound-score',
            default='i2 0 -1'),
    ])


class BuiltinScanner(scanner.Scanner):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def scan(self):
        yield ('builtin://track_mixer', TrackMixerDescription)
        yield ('builtin://ipc', IPCDescription)
        yield ('builtin://audio_source', AudioSourceDescription)
        yield ('builtin://event_source', EventSourceDescription)
        yield ('builtin://control_source', ControlSourceDescription)
        yield ('builtin://sink', SinkDescription)
        yield ('builtin://fluidsynth', FluidSynthDescription)
        yield ('builtin://sample_player', SamplePlayerDescription)
        yield ('builtin://custom_csound', CustomCSoundDescription)
        yield ('builtin://sound_file', SoundFileDescription)
