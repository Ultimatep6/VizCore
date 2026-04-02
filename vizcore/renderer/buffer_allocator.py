import moderngl
import numpy as np
import threading

from vizcore.bus.data_bus import DataBus

class BufferAllocate:
    """
    Manages GPU buffers.

    Responsibilities:
        - Allocate vertex buffers
        - Reuse buffers when possible
        - Manage GPU memory lifecycle

    Important requirement:
        Buffers must support high-frequency updates without reallocation.
    """
    def __init__(self, ctx: moderngl.Context):
        self.ctx = ctx
        self._buffers = {}
        self._lock = threading.RLock()

    def allocate(self, name, size, dtype='f4'):
        """
        Allocate a new buffer or reuse an existing one.
        """
        self._lock.acquire()
        try:
            if name in self._buffers:
                buf = self._buffers[name]
                if buf.size >= size:
                    return buf
                else:
                    buf.release()
            data = np.zeros(size, dtype=dtype)
            buf = self.ctx.buffer(data.tobytes())
            self._buffers[name] = buf
            return buf
        finally:
            self._lock.release()

    def update(self, name, data):
        """
        Update buffer contents without reallocating.
        """
        self._lock.acquire()
        try:
            buf = self._buffers.get(name)
            if buf:
                buf.write(data.tobytes())
            else:
                raise KeyError(f"Buffer '{name}' not allocated.")
        finally:
            self._lock.release()
        
    def release(self, name):
        """
        Release a buffer from GPU memory.
        """
        buf = self._buffers.pop(name, None)
        if buf:
            buf.release()

    def release_all(self):
        """
        Release all managed buffers.
        """
        for buf in self._buffers.values():
            buf.release()
        self._buffers.clear()

    def get_buffer(self, name):
        """
        Retrieve a buffer by name.
        """
        return self._buffers.get(name)

    
        

    

        
    