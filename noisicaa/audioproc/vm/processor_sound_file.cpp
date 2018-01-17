/*
 * @begin:license
 *
 * Copyright (c) 2015-2018, Benjamin Niemann <pink@odahoda.de>
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

#include <dlfcn.h>
#include <stdint.h>
#include "sndfile.h"
extern "C" {
#include "libswresample/swresample.h"
#include "libavutil/channel_layout.h"
}
#include "noisicaa/core/perf_stats.h"
#include "noisicaa/audioproc/vm/host_data.h"
#include "noisicaa/audioproc/vm/message_queue.h"
#include "noisicaa/audioproc/vm/misc.h"
#include "noisicaa/audioproc/vm/processor_sound_file.h"

namespace noisicaa {

ProcessorSoundFile::ProcessorSoundFile(const string& node_id, HostData* host_data)
  : Processor(node_id, "noisicaa.audioproc.vm.processor.sound_file", host_data) {}

ProcessorSoundFile::~ProcessorSoundFile() {}

Status ProcessorSoundFile::setup(const ProcessorSpec* spec) {
  Status status = Processor::setup(spec);
  RETURN_IF_ERROR(status);

  StatusOr<string> stor_path = get_string_parameter("sound_file_path");
  RETURN_IF_ERROR(stor_path);
  string path = stor_path.result();

  StatusOr<AudioFile*> stor_audio_file = _host_data->audio_file->load_audio_file(path);
  RETURN_IF_ERROR(stor_audio_file);

  _audio_file = stor_audio_file.result();
  _host_data->audio_file->acquire_audio_file(_audio_file);
  _loop = false;
  _playing = true;
  _pos = 0;

  return Status::Ok();
}

void ProcessorSoundFile::cleanup() {
  if (_audio_file != nullptr) {
    _host_data->audio_file->release_audio_file(_audio_file);
    _audio_file = nullptr;
  }

  Processor::cleanup();
}

Status ProcessorSoundFile::connect_port(uint32_t port_idx, BufferPtr buf) {
  if (port_idx > 1) {
    return ERROR_STATUS("Invalid port index %d", port_idx);
  }

  _buf[port_idx] = buf;
  return Status::Ok();
}

Status ProcessorSoundFile::run(BlockContext* ctxt, TimeMapper* time_mapper) {
  PerfTracker tracker(ctxt->perf.get(), "sound_file");

  const float* l_in = _audio_file->channel_data(0);
  const float* r_in = _audio_file->channel_data(1 % _audio_file->num_channels());
  float* l_out = (float*)_buf[0];
  float* r_out = (float*)_buf[1];
  for (uint32_t i = 0 ; i < ctxt->block_size ; ++i) {
    if (_pos >= _audio_file->num_samples()) {
      if (_loop) {
        _pos = 0;
      } else {
        if (_playing) {
          _playing = false;

          SoundFileCompleteMessage msg(node_id());
          ctxt->out_messages->push(&msg);
        }

        *l_out++ = 0.0;
        *r_out++ = 0.0;
        continue;
      }
    }

    *l_out++ = l_in[_pos];
    *r_out++ = r_in[_pos];

    _pos++;
  }

  return Status::Ok();
}

}
