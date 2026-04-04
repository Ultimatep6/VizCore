import threading
from .ring_buffer import RingBuffer
import numpy as np


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
                size = ImportError if buffer_size is not None else self._buffer_size
                self._signals[name] = RingBuffer(size)

    def push(self, name, value):
        """Push a new value to the signal's ring buffer, registering the signal if necessary."""
        with self._lock:
            if name not in self._signals:
                self.register_signal(name)
            if isinstance(value, (list, tuple)):
                value = np.asarray(value)
            self._signals[name].push(value)

    def latest(self, name):
        """Retrieve the latest value for a signal, or None if the signal is not registered or has no data."""
        with self._lock:
            buf = self._signals.get(name)
            if buf:
                return buf.latest()
            return None
        

    def history(self, name, N=None):
        """
        Retrieve the latest N values for a signal as a list, or None if the signal is not registered or has no data.
        """
        with self._lock:
            buf = self._signals.get(name)
            if buf:
                return buf.history(N)
            return None

    def get_signal(self, name):
        """Get the ring buffer for a signal, or None if the signal is not registered."""
        with self._lock:
            return self._signals.get(name)

    def list_signals(self):
        """List all registered signal names."""
        with self._lock:
            return list(self._signals.keys())
        
    def process_signal_request(self, signal_name, N):
        """
        Process a request for the latest N values of a signal.
        """
        data = self.latestN(signal_name, N)
        if data:
            buf = self._vbo_allocator.allocate(signal_name, len(data))
            self._vbo_allocator.update(signal_name, np.array(data, dtype='f4'))
            return buf
        raise KeyError(f"Signal '{signal_name}' not found or has no data.")
    
    def get_vbo_buffer(self, signal_name):
        """
        Get the GPU buffer associated with a signal, if it exists.
        """
        return self._vbo_allocator.get_buffer(signal_name)
    
    def push_to_gpu(self, signal_name, data, dtype='f4'):
        """
        Push data to the GPU buffer associated with a signal.
        """
        self._vbo_allocator.allocate(signal_name, len(data), dtype=dtype)
        self._vbo_allocator.update(signal_name, np.array(data, dtype=dtype))
