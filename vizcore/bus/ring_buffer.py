class RingBuffer:
    def __init__(self, size):
        self.size = size
        self.buffer = [None] * size
        self.index = 0
        self.count = 0

    def push(self, value):
        self.buffer[self.index] = value
        self.index = (self.index + 1) % self.size
        self.count = min(self.count + 1, self.size)

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