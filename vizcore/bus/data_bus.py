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

    def register_signal(self, name, buffer_size=None):
        """Register a new signal with a ring buffer if it doesn't already exist."""
        with self._lock:
            if name not in self._signals:
                size = buffer_size if buffer_size is not None else self._buffer_size
                self._signals[name] = RingBuffer(size)

    def push(self, name, value):
        """Push a new value to the signal's ring buffer, registering the signal if necessary."""
        with self._lock:
            if name not in self._signals:
                self.register_signal(name)
            self._signals[name].push(value)

    def latest(self, name):
        """Retrieve the latest value for a signal, or None if the signal is not registered or has no data."""
        with self._lock:
            buf = self._signals.get(name)
            if buf:
                return buf.latest()
            return None

    def history(self, name):
        """Retrieve the full history of values for a signal, or an empty list if the signal is not registered or has no data."""
        with self._lock:
            buf = self._signals.get(name)
            if buf:
                return buf.history()
            return []

    def get_signal(self, name):
        """Get the ring buffer for a signal, or None if the signal is not registered."""
        with self._lock:
            return self._signals.get(name)

    def list_signals(self):
        """List all registered signal names."""
        with self._lock:
            return list(self._signals.keys())
