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

import asyncio

from noisidev import unittest
from noisicaa.core import ipc

from . import process
from . import client


class TestClientImpl(object):
    def __init__(self, event_loop):
        super().__init__()
        self.event_loop = event_loop
        self.server = ipc.Server(self.event_loop, 'client')

    async def setup(self):
        await self.server.setup()

    async def cleanup(self):
        await self.server.cleanup()


class TestClient(client.InstrumentDBClientMixin, TestClientImpl):
    pass


class InstrumentDBClientTest(unittest.AsyncTestCase):
    async def setup_testcase(self):
        self.process = process.InstrumentDBProcess(
            name='instrument_db', event_loop=self.loop, manager=None)
        await self.process.setup()
        self.process_task = self.loop.create_task(
            self.process.run())

        self.client = TestClient(self.loop)
        await self.client.setup()
        await self.client.connect(self.process.server.address)

    async def cleanup_testcase(self):
        await self.client.disconnect(shutdown=True)
        await self.client.cleanup()
        await asyncio.wait_for(self.process_task, None)
        await self.process.cleanup()

    async def test_start_scan(self):
        await self.client.start_scan()
