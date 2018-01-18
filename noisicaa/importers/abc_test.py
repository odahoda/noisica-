#!/usr/bin/python3

# @begin:license
#
# Copyright (c) 2015-2018, Benjamin Niemann <pink@odahoda.de>
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

import fractions

from noisidev import unittest
from noisicaa import music
from . import abc


class ABCImporterTest(unittest.TestCase):
    def setup_testcase(self):
        self.imp = abc.ABCImporter()

    def test_parse_note(self):
        self.imp.unit_length = fractions.Fraction(1, 4)
        cases = [
            ('A', 'A4/4'),
            ('B', 'B4/4'),
            ('C', 'C4/4'),
            ('D', 'D4/4'),
            ('E', 'E4/4'),
            ('F', 'F4/4'),
            ('G', 'G4/4'),
            ('a', 'A5/4'),
            ('b', 'B5/4'),
            ('c', 'C5/4'),
            ('d', 'D5/4'),
            ('e', 'E5/4'),
            ('f', 'F5/4'),
            ('g', 'G5/4'),
            ('z', 'r/4'),
            ('d,', 'D4/4'),
            ('d,,', 'D3/4'),
            ('d\'', 'D6/4'),
            ('d\'\'', 'D7/4'),
            ('^d', 'D#5/4'),
            ('_d', 'Db5/4'),
            ('=d', 'D5/4'),
            ('d/', 'D5/8'),
            ('d//', 'D5/16'),
            ('d///', 'D5/32'),
            ('d3/2', 'D5;3/8'),
            ('d/2', 'D5/8'),
            ('d2', 'D5/2'),
        ]

        for s, expected_note in cases:
            for expected_remainder in ['', ' bla', '|']:
                note, remainder = self.imp.parse_note(s + expected_remainder)
                self.assertEqual(remainder, expected_remainder)
                self.assertEqual(str(note), expected_note)

    def test_decoration(self):
        self.imp.unit_length = fractions.Fraction(1, 4)
        cases = [
            ('Ta', 'A5/4'),
        ]

        for s, expected_note in cases:
            note, remainder = self.imp.parse_note(s)
            self.assertEqual(remainder, '')
            self.assertEqual(str(note), expected_note)

    def test_grace_note(self):
        self.imp.unit_length = fractions.Fraction(1, 4)
        notes, remainder = self.imp.parse_grace_notes('{ceg}')
        self.assertEqual(remainder, '')
        self.assertEqual(
            [str(n) for n in notes],
            ['C5/4', 'E5/4', 'G5/4'])

    def test_pitch_in_key(self):
        self.imp.unit_length = fractions.Fraction(1, 4)
        self.imp.key = music.KeySignature('G major')
        note, remainder = self.imp.parse_note('f')
        self.assertEqual(str(note), 'F#5/4')

    def test_broken_rhythm(self):
        self.imp.unit_length = fractions.Fraction(1, 4)
        self.imp.parse_music('a>b c<d')
        notes = [str(n) for n in self.imp.notes]
        self.assertEqual(
            [str(n) for n in self.imp.notes],
            ['A5;3/8', 'B5/8', 'C5/8', 'D5;3/8'])

    def test_tempo(self):
        cases = [
            ('110', 110),
            ('1/4=130', 130),
            ('1/2=40', 80),
            ('1/4 3/8 1/4 3/8=40', 200),
            ('', 120),
            ('"Schneller!"', 120),
        ]

        for s, expected_bpm in cases:
            self.assertEqual(self.imp.parse_tempo(s), expected_bpm)

    def test_bach_measure(self):
        self.imp.unit_length = fractions.Fraction(1, 4)
