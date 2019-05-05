#!/usr/bin/python3

# @begin:license
#
# Copyright (c) 2015-2019, Benjamin Niemann <pink@odahoda.de>
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
import functools
import inspect
import logging
import os.path
import uuid
from typing import Any, Dict

from PyQt5 import QtWidgets
import asynctest

from noisicaa.constants import TEST_OPTS
from noisicaa import runtime_settings as runtime_settings_lib
from noisicaa import audioproc
from noisicaa import core
from noisicaa import lv2
from noisicaa import music
from noisicaa import node_db
from noisicaa import editor_main_pb2
from noisicaa.ui import selection_set
from noisicaa.ui import ui_base
from . import qttest
from . import unittest_mixins

logger = logging.getLogger(__name__)


class TestContext(object):
    def __init__(self, *, testcase: 'UITestCase') -> None:
        self.__testcase = testcase

    @property
    def app(self):
        return self.__testcase.app

    @property
    def audioproc_client(self):
        return self.__testcase.app.audioproc_client

    @property
    def window(self):
        return self.__testcase.window

    @property
    def event_loop(self):
        return self.__testcase.loop

    @property
    def project_connection(self):
        return self.__testcase.project_connection

    @property
    def project(self):
        return self.__testcase.project

    @property
    def project_client(self):
        return self.__testcase.project_client

    @property
    def selection_set(self):
        return self.__testcase.selection_set

    def call_async(self, coroutine, callback=None):
        task = self.event_loop.create_task(coroutine)
        task.add_done_callback(
            functools.partial(self.__call_async_cb, callback=callback))

    def __call_async_cb(self, task, callback):
        if task.exception() is not None:
            raise task.exception()
        if callback is not None:
            callback(task.result())

    def set_session_value(self, key, value):
        self.__testcase.session_data[key] = value

    def set_session_values(self, data):
        self.__testcase.session_data.update(data)

    def get_session_value(self, key, default):
        return self.__testcase.session_data.get(key, default)

    def add_session_listener(self, key, listener):
        raise NotImplementedError


class MockAudioProcClient(audioproc.AbstractAudioProcClient):  # pylint: disable=abstract-method
    def __init__(self):
        super().__init__()
        self.node_messages = core.CallbackMap[str, Dict[str, Any]]()
        self.node_state_changed = core.CallbackMap[str, audioproc.NodeStateChange]()


class MockSettings(object):
    def __init__(self):
        self.__data = {}  # type: Dict[str, Any]
        self.__grp = None  # type: str

    def value(self, key, default=None):
        if self.__grp:
            key = self.__grp + '/' + key
        return self.__data.get(key, default)

    def setValue(self, key, value):
        if self.__grp:
            key = self.__grp + '/' + key
        self.__data[key] = value

    def allKeys(self):
        assert self.__grp is None
        return list(self.__data.keys())

    def sync(self):
        pass

    def beginGroup(self, grp):
        assert self.__grp is None
        self.__grp = grp

    def endGroup(self):
        assert self.__grp is not None
        self.__grp = None


class MockProcess(core.ProcessBase):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.project = None


class MockApp(ui_base.AbstractEditorApp):
    def __init__(self):
        self.win = None  # type: AbstractEditorWindow
        self.audioproc_client = None  # type: audioproc.AbstractAudioProcClient
        self.process = None  # type: core.ProcessBase
        self.settings = None  # type: QtCore.QSettings
        self.pipeline_perf_monitor = None  # type: AbstractPipelinePerfMonitor
        self.stat_monitor = None  # type: AbstractStatMonitor
        self.runtime_settings = None  # type: runtime_settings_lib.RuntimeSettings
        self.show_edit_areas_action = None  # type: QtWidgets.QAction
        self.node_db = None  # type: node_db_lib.NodeDBClient
        self.instrument_db = None  # type: instrument_db_lib.InstrumentDBClient
        self.default_style = None  # type: str
        self.qt_app = None  # type: QtWidgets.QApplication


class UITestCase(unittest_mixins.ProcessManagerMixin, qttest.QtTestCase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.process = None
        self.node_db_address = None
        self.node_db_client = None
        self.app = None
        self.context = None

    async def setup_testcase(self):
        self.setup_node_db_process(inline=True)
        self.setup_urid_mapper_process(inline=True)
        self.setup_instrument_db_process(inline=True)

        self.process = MockProcess(
            name='ui',
            manager=self.process_manager_client,
            event_loop=self.loop,
            tmp_dir=TEST_OPTS.TMP_DIR)
        await self.process.setup()

        create_node_db_response = editor_main_pb2.CreateProcessResponse()
        await self.process_manager_client.call(
            'CREATE_NODE_DB_PROCESS', None, create_node_db_response)
        self.node_db_address = create_node_db_response.address

        self.node_db_client = node_db.NodeDBClient(self.loop, self.process.server)
        await self.node_db_client.setup()
        await self.node_db_client.connect(self.node_db_address)

        self.selection_set = selection_set.SelectionSet()

        self.app = MockApp()
        self.app.qt_app = self.qt_app
        self.app.process = self.process
        self.app.runtime_settings = runtime_settings_lib.RuntimeSettings()
        self.app.settings = MockSettings()
        self.app.node_db = self.node_db_client
        self.app.audioproc_client = MockAudioProcClient()
        self.app.node_messages = core.CallbackMap()

        self.session_data = {}  # type: Dict[str, Any]

        self.context = TestContext(testcase=self)

    async def cleanup_testcase(self):
        if self.node_db_client is not None:
            await self.node_db_client.disconnect()
            await self.node_db_client.cleanup()

        if self.node_db_address is not None:
            await self.process_manager_client.call(
                'SHUTDOWN_PROCESS',
                editor_main_pb2.ShutdownProcessRequest(
                    address=self.node_db_address))

        if self.process is not None:
            await self.process.cleanup()


class ProjectMixin(
        unittest_mixins.ServerMixin,
        unittest_mixins.URIDMapperMixin,
        UITestCase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.project_client = None
        self.project = None

    async def setup_testcase(self):
        self.setup_writer_process(inline=True)

        self.project_client = music.ProjectClient(
            event_loop=self.loop,
            server=self.server,
            node_db=self.node_db_client,
            urid_mapper=self.urid_mapper,
            manager=self.process_manager_client,
            tmp_dir=TEST_OPTS.TMP_DIR)
        await self.project_client.setup()

        path = os.path.join(TEST_OPTS.TMP_DIR, 'test-project-%s' % uuid.uuid4().hex)
        await self.project_client.create(path)

        self.project = self.project_client.project

    async def cleanup_testcase(self):
        if self.project_client is not None:
            await self.project_client.cleanup()
