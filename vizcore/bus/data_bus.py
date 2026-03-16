import threading
from .ring_buffer import RingBuffer

class DataBus:
    """
    Central telemetry registry for signal management.

    Responsibilities:
        - Register signals and allocate ring buffers for each.
        - Store and update signal values in a thread-safe manner.
        - Provide fast lookup for signal buffers and their data.
        - Support retrieval of latest value and full history window per signal.

    Thread safety:
        All access and mutation operations are protected by a reentrant lock.
    """
    def __init__(self, buffer_size=1024):
        self._signals = {}
        self._lock = threading.RLock()
        self._buffer_size = buffer_size

    def register_signal(self, name):
        with self._lock:
            if name not in self._signals:
                self._signals[name] = RingBuffer(self._buffer_size)

    def push(self, name, value):
        with self._lock:
            if name not in self._signals:
                self.register_signal(name)
            self._signals[name].push(value)

    def latest(self, name):
        with self._lock:
            buf = self._signals.get(name)
            if buf:
                return buf.latest()
            return None

    def history(self, name):
        with self._lock:
            buf = self._signals.get(name)
            if buf:
                return buf.history()
            return []

    def get_signal(self, name):
        with self._lock:
            return self._signals.get(name)

    def list_signals(self):
        with self._lock:
            return list(self._signals.keys())
