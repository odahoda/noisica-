import uuid
import logging
import select
import threading

from noisicaa.core import callbacks
from . import libalsa

logger = logging.getLogger(__name__)


class Error(Exception):
    pass


class MidiHub(object):
    def __init__(self):
        self._seq = None
        self._thread = None
        self._quit_event = None
        self._started = False
        self.listeners = callbacks.CallbackRegistry(self._listener_changed)

        self._connected = None

    def _listener_changed(self, target, listener_id, add_or_remove):
        assert self._started, "MidiHub must be started before adding listeners."

        if add_or_remove:
            refcount = self._connected.setdefault(target, 0)
            if refcount == 0:
                for port_info in self._seq.list_all_ports():
                    if port_info.device_id == target:
                        logger.info("Connecting to %s", port_info)
                        self._seq.connect(port_info)
                        break
                else:
                    raise Error("Device %s not found" % target)

            self._connected[target] += 1

        else:
            assert target in self._connected
            self._connected[target] -= 1

            if self._connected[target] == 0:
                del self._connected[target]

                for port_info in self._seq.list_all_ports():
                    if port_info.device_id == target:
                        logger.info("Disconnecting from %s", port_info)
                        self._seq.disconnect(port_info)
                        break
                else:
                    raise Error("Device %s not found" % target)

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
        return False

    def start(self):
        logger.info("Starting MidiHub...")

        # Do other clients handle non-ASCII names?
        # 'aconnect' seems to work (or just spits out whatever bytes it gets
        # and the console interprets it as UTF-8), 'aconnectgui' shows the
        # encoded bytes.
        self._seq = libalsa.AlsaSequencer('noisicaä')

        self._connected = {}

        #port_info = next(
        #    p for p in self._seq.list_all_ports()
        #    if 'read' in p.capabilities and 'hardware' in p.types)
        #self._seq.connect(port_info)

        self._quit_event = threading.Event()
        self._thread = threading.Thread(target=self._thread_main, name="MidiHub")
        self._thread.start()
        logger.info("MidiHub started.")

        self._started = True

    def stop(self):
        self._started = False

        logger.info("Stopping MidiHub...")
        if self._thread is not None:
            self._quit_event.set()
            self._thread.join()
            self._thread = None
            self._quit_event = None

        if self._seq is not None:
            self._seq.close()
            self._seq = None
        logger.info("MidiHub stopped.")

    def list_devices(self):
        for port_info in self._seq.list_all_ports():
            if 'read' not in port_info.capabilities:
                continue
            if 'midi_generic' not in port_info.types:
                continue
            print(port_info.device_id, port_info)

    def _thread_main(self):
        poller = select.poll()

        # TODO: Can the list of FDs change over time? E.g. when ports are
        # created/removed?
        for fd in self._seq.get_pollin_fds():
            poller.register(fd, select.POLLIN)

        while not self._quit_event.is_set():
            # TODO: Poll w/o timeout and have quit_tread() ping some FD,
            # so this gets unstuck.
            poller.poll(10)
            event = self._seq.get_event()
            if event is not None:
                self.dispatch_midi_event(event)

    def dispatch_midi_event(self, event):
        logger.info("Dispatching MIDI event %s", event)
        self.listeners.call(event.device_id, event)
