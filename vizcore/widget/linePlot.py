import numpy as np

from vizcore.widget.baseWidget import BaseWidget

class LinePlot(BaseWidget):
    """
    A simple line plot for visualizing 1D data.
    Expected signal format: A 1D array of numeric values.

    Usage:
        line_plot = LinePlot()
        frame.render()
    """

    def __init__(self, rect=None,
                 channels=1,
                 text_renderer=None,):
        super().__init__(rect)

        self.channels = channels

        self.signal_names = []
        self._local = {}
        self._vbos = {}

        self._text_renderer = text_renderer
        self._renderer = None
        
    def accepts_signal(self, data_bus, signal_name):
        # Line plot only accepts 1D signals -- For now
        latest_val = data_bus.latest(signal_name)
        if latest_val is not None:
            arr_val = np.asarray(latest_val)
            if arr_val.shape == (3,):
                return True
        return False
    
    def bind_external_signal(self, data_bus, signal: list):
        if not hasattr(self, 'signal_names'):
            raise ValueError("LinePlot widget missing 'signal_names' attribute. Ensure to call super().__init__() in your constructor.")
        
        for signal_name in signal:
            if self.accepts_signal(data_bus, signal_name):
                self.signal_names.append(signal_name)
                self._local[signal_name] = data_bus.get_signal(signal_name)

    