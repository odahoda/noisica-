// -*- mode: c++ -*-

/*
 * @begin:license
 *
 * Copyright (c) 2015-2017, Benjamin Niemann <pink@odahoda.de>
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 2 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License along
 * with this program; if not, write to the Free Software Foundation, Inc.,
 * 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
 *
 * @end:license
 */

#ifndef _NOISICAA_AUDIOPROC_VM_PROCESSOR_LADSPA_H
#define _NOISICAA_AUDIOPROC_VM_PROCESSOR_LADSPA_H

#include <string>
#include <vector>
#include <stdint.h>
#include "ladspa.h"
#include "noisicaa/core/status.h"
#include "noisicaa/audioproc/vm/buffers.h"
#include "noisicaa/audioproc/vm/processor.h"

namespace noisicaa {

using namespace std;

class HostData;
class BlockContext;

class ProcessorLadspa : public Processor {
public:
  ProcessorLadspa(const string& node_id, HostData* host_data);
  ~ProcessorLadspa() override;

  Status setup(const ProcessorSpec* spec) override;
  void cleanup() override;

  Status connect_port(uint32_t port_idx, BufferPtr buf) override;
  Status run(BlockContext* ctxt, TimeMapper* time_mapper) override;

private:
  void* _library = nullptr;
  const LADSPA_Descriptor*_descriptor = nullptr;
  LADSPA_Handle _instance = nullptr;
};

}  // namespace noisicaa

#endif
