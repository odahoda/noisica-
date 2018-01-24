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

import os
import os.path
import uuid
import threading

from noisidev import unittest
from noisicaa.constants import TEST_OPTS
# TODO: pylint has issues with cython modules.
from . import audio_stream  # pylint: disable=no-name-in-module


class TestAudioStream(unittest.TestCase):
    def setup_testcase(self):
        self.address = os.fsencode(
            os.path.join(TEST_OPTS.TMP_DIR, 'test.%s.pipe' % uuid.uuid4().hex))

    def test_client_to_server(self):
        server = audio_stream.AudioStream.create_server(self.address)
        server.setup()

        client = audio_stream.AudioStream.create_client(self.address)
        client.setup()

        def server_thread():
            request = server.receive_bytes()
            server.send_bytes(request)

        thread = threading.Thread(target=server_thread)
        thread.start()

        request = b'123' * 100000
        client.send_bytes(request)
        response = client.receive_bytes()

        self.assertEqual(response, b'123' * 100000)

        client.cleanup()
        server.cleanup()
