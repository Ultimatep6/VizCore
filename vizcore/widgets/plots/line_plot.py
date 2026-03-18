import numpy as np
from vizcore.widgets.base_widget import BaseWidget
from vizcore.bus.ring_buffer import RingBuffer
from vizcore.layout.rect import Rect


TITLE_BAR_HEIGHT = 40  # pixels reserved at top for title

class LinePlot(BaseWidget):
    """
    Scrolling line plot.

    Responsibilities:
        - Display time series signals
        - Maintain GPU ring buffer

    Features:
        - Multiple channels
        - Automatic scrolling
    """
    def __init__(self, channels=1, buffer_size=512, margin=10, title=None):
        super().__init__()
        self.channels = channels
        self.buffer_size = buffer_size
        self.margin = margin
        self.title = title
        self.buffers = [RingBuffer(buffer_size) for _ in range(channels)]
        self.values = [np.zeros(buffer_size, dtype='f4') for _ in range(channels)]
        self._vbos = {}

    def bind_renderer(self, renderer):
        """Call once after widget is created to pre-allocate GPU buffers."""
        for i in range(self.channels):
            points = np.zeros(self.buffer_size * 2, dtype='f4')  # x,y interleaved
            self._vbos[i] = renderer.ctx.buffer(points.tobytes())


    def update(self, data=None):
        # Pull latest values from the data bus for each signal
        if hasattr(self, 'signal_names') and hasattr(self, 'data_bus'):
            for i, name in enumerate(self.signal_names):
                value = self.data_bus.latest(name)
                if value is not None:
                    self.buffers[i].push(value)
                # Only update self.values if buffer has valid data
                self.values[i] = np.array(self.buffers[i].history(), dtype='f4')

    def draw_lines(self, renderer):
        for i, values in enumerate(self.values):
            if len(values) < 2:
                continue
            x = np.linspace(-1.0, 1.0, len(values))
            v_min, v_max = np.min(values), np.max(values)
            y = 2.0 * (values - v_min) / (v_max - v_min + 1e-6) - 1.0
            points = np.column_stack((x, y)).flatten().astype('f4')

            # Shrink the rect to leave space at top for title
            plot_rect = Rect(
                self.rect.x,
                self.rect.y,
                self.rect.width,
                self.rect.height - (TITLE_BAR_HEIGHT if self.title else 0)
            )

            if i in self._vbos:
                self._vbos[i].write(points.tobytes())
                renderer.draw_line_plot_vbo(
                    self._vbos[i], len(points) // 2,
                    rect=plot_rect, color=(0, 150 + i*50, 255 - i*50, 255),
                    margin=self.margin
                )
            else:
                renderer.draw_line_plot(
                    points, rect=plot_rect,
                    color=(0, 150 + i*50, 255 - i*50, 255),
                    margin=self.margin
                )


    def draw_text(self, renderer):
        if self.title and self.rect:
            cx = self.rect.x + self.rect.width // 2
            y = self.rect.y + self.rect.height - 40
            tw, th = renderer.text_title.measure(self.title)
            pad = 6
            # Dark background box behind title
            renderer.draw_rect(
                cx - tw // 2 - pad, y - pad,
                tw + pad * 2, th + pad * 2,
                color=(0.1, 0.1, 0.1, 1.0)
            )
            renderer.draw_title(self.title, cx, y)



    def draw(self, renderer):
        self.draw_lines(renderer)
        self.draw_text(renderer)


            

    def resize(self, rect):
        super().resize(rect)

    def bind_signal(self, data_bus, signal):
        """
        Bind this plot to one or more signals from the data bus.
        Accepts a single signal name (str) or a list of signal names.
        """
        if isinstance(signal, str):
            self.signal_names = [signal]
        else:
            self.signal_names = list(signal)
        self.data_bus = data_bus