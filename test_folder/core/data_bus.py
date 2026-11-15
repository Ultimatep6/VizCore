import threading
import numpy as np
from core.signal_schema import SignalSchema


class RingBuffer:
    def __init__(self, size=1024):
        self._buffer = []
        self._size = size

    def push(self, value):
        self._buffer.append(value)
        if len(self._buffer) > self._size:
            self._buffer.pop(0)

    def latest(self):
        return self._buffer[-1] if self._buffer else None

    def history(self, N=None):
        if N is None:
            return list(self._buffer)
        return list(self._buffer[-N:])

    def __len__(self):
        return len(self._buffer)


class DataBus:
    def __init__(self, buffer_size=1024):
        self._signals = {}
        self._metadata = {}
        self._lock = threading.RLock()
        self._buffer_size = buffer_size

    def push_payload(self, payload):
        with self._lock:
            self._flatten_and_push("", payload)

    def _flatten_and_push(self, prefix, data):
        for key, val in data.items():
            path = f"{prefix}.{key}" if prefix else key
            if isinstance(val, dict):
                self._flatten_and_push(path, val)
            else:
                self.push(path, val)
                if path not in self._metadata:
                    latest = self.latest(path)
                    if hasattr(latest, "shape"):
                        self._metadata[path] = {"shape": latest.shape}
                    else:
                        self._metadata[path] = {"shape": (1,)}

    def register_signal_schema(self, path, schema):
        with self._lock:
            if path in self._metadata:
                self._metadata[path]["schema"] = schema
                if schema.shape:
                    self._metadata[path]["shape"] = schema.shape

    def register_signal_schemas(self, schema_dict):
        for path, schema in schema_dict.items():
            self.register_signal_schema(path, schema)

    def get_signals_by_shape(self, target_shape):
        with self._lock:
            return [
                path
                for path, meta in self._metadata.items()
                if meta.get("shape") == target_shape
            ]

    def get_signals_by_schema(self, target_schema):
        with self._lock:
            results = []
            for path, meta in self._metadata.items():
                sig_schema = meta.get("schema")
                if sig_schema is not None and target_schema.matches(sig_schema):
                    results.append(path)
            return results

    def get_signal_metadata(self, path):
        with self._lock:
            return self._metadata.get(path)

    def register_signal(self, name, buffer_size=None):
        with self._lock:
            if name not in self._signals:
                size = buffer_size if buffer_size is not None else self._buffer_size
                self._signals[name] = RingBuffer(size)

    def push(self, name, value):
        with self._lock:
            if name not in self._signals:
                self.register_signal(name)
            if isinstance(value, (list, tuple)):
                value = np.asarray(value)
            self._signals[name].push(value)

    def latest(self, name):
        with self._lock:
            buf = self._signals.get(name)
            if buf:
                return buf.latest()
            return None

    def history(self, name, N=None):
        with self._lock:
            buf = self._signals.get(name)
            if buf:
                return buf.history(N)
            return None

    def list_signals(self):
        with self._lock:
            return list(self._signals.keys())
