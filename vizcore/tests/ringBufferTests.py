import unittest
from vizcore.bus.ring_buffer import RingBuffer

# vizcore/bus/test_ring_buffer.py

class TestRingBufferPush(unittest.TestCase):
        def test_push_single_value(self):
            buffer = RingBuffer(size=3)
            buffer.push(1)
            self.assertEqual(buffer.history(), [1])
            buffer.push(2)
            self.assertEqual(buffer.history(), [1, 2])
            buffer.push(3)
            self.assertEqual(buffer.history(), [1, 2, 3])
            buffer.push(4)  # Overwrites oldest
            self.assertEqual(buffer.history(), [2, 3, 4])

        def test_push_list_of_values(self):
            buffer = RingBuffer(size=4)
            buffer.push([10, 20])
            self.assertEqual(buffer.history(), [10, 20])
            buffer.push([30, 40, 50])
            self.assertEqual(buffer.history(), [20, 30, 40, 50])
            buffer.push([60])
            self.assertEqual(buffer.history(), [30, 40, 50, 60])


class TestRingBufferHistory(unittest.TestCase):
    def test_push_single_value(self):
        buffer = RingBuffer(size=3)
        buffer.push(1)
        self.assertEqual(buffer.history(), [1])
        buffer.push(2)
        self.assertEqual(buffer.history(), [1, 2])
        buffer.push(3)
        self.assertEqual(buffer.history(), [1, 2, 3])
        buffer.push(4)  # Overwrites oldest
        self.assertEqual(buffer.history(), [2, 3, 4])

    def test_push_list_of_values(self):
        buffer = RingBuffer(size=4)
        buffer.push([10, 20])
        self.assertEqual(buffer.history(), [10, 20])
        buffer.push([30, 40, 50])
        self.assertEqual(buffer.history(), [20, 30, 40, 50])
        buffer.push([60])
        self.assertEqual(buffer.history(), [30, 40, 50, 60])
        
    def test_history_empty_buffer(self):
        buffer = RingBuffer(size=5)
        self.assertEqual(buffer.history(), [])
        self.assertEqual(buffer.history(3), [])

    def test_history_partial_fill(self):
        buffer = RingBuffer(size=5)
        buffer.push(1)
        buffer.push(2)
        self.assertEqual(buffer.history(), [1, 2])
        self.assertEqual(buffer.history(1), [2])
        self.assertEqual(buffer.history(3), [1, 2])

    def test_history_full_buffer(self):
        buffer = RingBuffer(size=3)
        buffer.push(1)
        buffer.push(2)
        buffer.push(3)
        self.assertEqual(buffer.history(), [1, 2, 3])
        self.assertEqual(buffer.history(2), [2, 3])
        self.assertEqual(buffer.history(5), [1, 2, 3])  # Requesting more than available

    def test_history_overwrite(self):
        buffer = RingBuffer(size=3)
        buffer.push(1)
        buffer.push(2)
        buffer.push(3)
        buffer.push(4)  # Overwrites the oldest value (1)
        self.assertEqual(buffer.history(), [2, 3, 4])
        self.assertEqual(buffer.history(2), [3, 4])
        self.assertEqual(buffer.history(1), [4])

    def test_history_after_clear(self):
        buffer = RingBuffer(size=3)
        buffer.push(1)
        buffer.push(2)
        buffer.clear()
        self.assertEqual(buffer.history(), [])
        buffer.push(3)
        self.assertEqual(buffer.history(), [3])

    def test_history_after_resize_smaller(self):
        buffer = RingBuffer(size=5)
        buffer.push(1)
        buffer.push(2)
        buffer.push(3)
        buffer.push(4)
        buffer.push(5)
        buffer.resize(3)  # Resize to smaller size
        self.assertEqual(buffer.history(), [3, 4, 5])

    def test_history_after_resize_larger(self):
        buffer = RingBuffer(size=3)
        buffer.push(1)
        buffer.push(2)
        buffer.push(3)
        buffer.resize(5)  # Resize to larger size
        self.assertEqual(buffer.history(), [1, 2, 3])
        buffer.push(4)
        buffer.push(5)
        self.assertEqual(buffer.history(), [1, 2, 3, 4, 5])

if __name__ == "__main__":
    unittest.main()