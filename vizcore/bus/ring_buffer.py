class RingBuffer:
    def __init__(self, size, gpu_buffer=False):
        self.size = size
        self.buffer = [None] * size
        self.index = 0
        self.count = 0

    def push(self, value):
        self.buffer[self.index] = value
        self.index = (self.index + 1) % self.size
        self.count = min(self.count + 1, self.size)

    def clear(self):
        self.buffer = [None] * self.size
        self.index = 0
        self.count = 0
    
    def resize(self, new_size):
        if new_size < self.count:
            # If the new size is smaller than the current count, we need to drop old data
            self.buffer = self.history()[-new_size:] + [None] * (new_size - self.count)
            self.count = new_size
        else:
            # If the new size is larger, just extend the buffer
            self.buffer += [None] * (new_size - self.size)
        self.size = new_size
        self.index = self.count % self.size  # Reset index to the correct position after resizing

    def latest(self):
        if self.count == 0:
            return None
        return self.buffer[(self.index - 1) % self.size]

    def history(self):
        if self.count == 0:
            return []
        if self.count < self.size:
            return self.buffer[:self.count]
        # Return in correct order: oldest to newest
        return self.buffer[self.index:] + self.buffer[:self.index]
    