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

from libc.stdint cimport uint8_t
from libcpp.string cimport string
from libcpp.memory cimport unique_ptr

import os
import os.path
import sys
import unittest

from noisicaa import constants
from noisicaa.bindings.lv2 cimport atom
from noisicaa.bindings.lv2 import urid
from noisicaa.core.status cimport *
from .block_context cimport *
from .buffers cimport *
from .processor cimport *
from .processor_spec cimport *
from .host_data cimport *
from .message_queue cimport *


class TestProcessorSamplePlayer(unittest.TestCase):
    def test_sample_player(self):
        cdef Status status

        cdef PyHostData host_data = PyHostData()
        host_data.setup()

        cdef StatusOr[Processor*] stor_processor = Processor.create(
            b'test_node', host_data.ptr(), b'sample_player')
        check(stor_processor)
        cdef unique_ptr[Processor] processor_ptr
        processor_ptr.reset(stor_processor.result())

        cdef Processor* processor = processor_ptr.get()

        cdef unique_ptr[ProcessorSpec] spec
        spec.reset(new ProcessorSpec())
        spec.get().add_port(b'in', PortType.atomData, PortDirection.Input)
        spec.get().add_port(b'out:left', PortType.audio, PortDirection.Output)
        spec.get().add_port(b'out:right', PortType.audio, PortDirection.Output)
        spec.get().add_parameter(new StringParameterSpec(
            b'sample_path',
            os.fsencode(os.path.join(constants.ROOT, '..', 'testdata', 'snare.wav'))))

        check(processor.setup(spec.release()))

        cdef PyBlockContext ctxt = PyBlockContext()
        ctxt.block_size = 128

        cdef uint8_t inbuf[10240]
        cdef float outleftbuf[128]
        cdef float outrightbuf[128]

        check(processor.connect_port(0, <BufferPtr>inbuf))
        check(processor.connect_port(1, <BufferPtr>outleftbuf))
        check(processor.connect_port(2, <BufferPtr>outrightbuf))

        # run once empty to give csound some chance to initialize the ftable
        cdef atom.AtomForge forge = atom.AtomForge(urid.static_mapper)
        forge.set_buffer(inbuf, 10240)
        with forge.sequence():
            pass

        check(processor.run(ctxt.get(), NULL))  # TODO: pass time_mapper

        forge = atom.AtomForge(urid.static_mapper)
        forge.set_buffer(inbuf, 10240)
        with forge.sequence():
            forge.write_midi_event(0, bytes([0x90, 60, 100]), 3)
            forge.write_midi_event(64, bytes([0x80, 60, 0]), 3)

        for i in range(128):
            outleftbuf[i] = 0.0
            outrightbuf[i] = 0.0

        check(processor.run(ctxt.get(), NULL))  # TODO: pass time_mapper

        self.assertTrue(any(v != 0.0 for v in outleftbuf))
        self.assertTrue(any(v != 0.0 for v in outrightbuf))

        processor.cleanup()
