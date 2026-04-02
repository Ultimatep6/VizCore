import moderngl
import numpy as np

class mainLoop:
    def __init__(self, window):
        self.window = window
        self.bus = self.window.bus

    # on_data_push
    def push_data(self, data, signal_name):
        # Process incoming data and update the data bus
        self.bus.push(signal_name, data)

    def after_loop(self):
        for signal in self.bus.list_signals():
            self._gpu_allocator.update(signal, np.array(self.bus.latest(signal), dtype='f4'))
            


        
        