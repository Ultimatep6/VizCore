import moderngl
import collections
import itertools
from datetime import datetime

from vizcore.widget.baseWidget import BaseWidget
from vizcore.text.fontAtlas import FontAtlas, TextRenderer

class LogConsole(BaseWidget):
    """
    A widget that displays a scrollable log of text messages, useful for debugging or showing system status.
    It accepts signals containing string messages and renders them in a console-like format.
    The widget maintains a history of messages and supports basic text formatting.
    Must be time-stamped    
    """

    CHANNELS = ("INFO", "WARN", "ERROR", "DEBUG")

    def __init__(self, rect=None, max_history=50000):
        super().__init__(rect)

        self._text_renderer = None
        self._logger_text_renderer = None
        self._renderer = None

        # 1. Data Storage: Deque prevents infinite memory growth
        self.logs = collections.deque(maxlen=max_history)
        
        # 2. Scrolling State
        self.scroll_offset = 0  # Index of the top-most visible log
        self.auto_scroll = True # Snap to bottom when new logs arrive
        self.visible_lines = 1
        self._channel_history_lengths = {level: 0 for level in self.CHANNELS}
        
        # 3. Layout & Typography
        self.font_scale = 0.46
        self.line_height = 28  # Base pixels per line
        self.margin = 36
        self.wrap_chars = 72

        # 4. Styling
        self.level_colors = {
            "INFO": (0.8, 0.8, 0.8, 1.0),    # Light Grey
            "WARN": (0.9, 0.8, 0.2, 1.0),    # Yellow
            "ERROR": (0.9, 0.2, 0.2, 1.0),   # Red
            "DEBUG": (0.1, 0.55, 1.0, 1.0)   # Strong Blue
        }

    @property
    def required_shape(self):
        return None

    def accepts_signal(self, data_bus, signal_name) -> bool:
        return signal_name in self.CHANNELS

    def bind_external_signal(self, data_bus, signal):
        """
        Bind log console to fixed built-in channels only.
        `signal` is ignored intentionally to enforce strict channels.
        """
        self.data_bus = data_bus
        self._channel_history_lengths = {level: 0 for level in self.CHANNELS}

    def _format_timestamp(self, raw_time):
        if raw_time is None:
            return datetime.now().strftime("%H:%M:%S.%f")[:-3]

        if isinstance(raw_time, datetime):
            return raw_time.strftime("%H:%M:%S.%f")[:-3]

        if isinstance(raw_time, (int, float)):
            try:
                return datetime.fromtimestamp(raw_time).strftime("%H:%M:%S.%f")[:-3]
            except Exception:
                return datetime.now().strftime("%H:%M:%S.%f")[:-3]

        return str(raw_time)

    def _normalize_log_entry(self, level, raw_entry):
        if isinstance(raw_entry, dict):
            message = raw_entry.get("message", raw_entry.get("msg", ""))
            raw_time = raw_entry.get("time", raw_entry.get("timestamp"))
        else:
            message = raw_entry
            raw_time = None

        return {
            "time": self._format_timestamp(raw_time),
            "level": level,
            "message": str(message),
        }

    def _wrap_message(self, message, wrap_chars):
        if not message:
            return [""]

        words = str(message).split()
        if not words:
            return [str(message)]

        wrapped_lines = []
        current_line = words[0]

        for word in words[1:]:
            candidate = f"{current_line} {word}"
            if len(candidate) <= wrap_chars:
                current_line = candidate
            else:
                wrapped_lines.append(current_line)
                current_line = word

        wrapped_lines.append(current_line)
        return wrapped_lines

    def bind_renderer(self, renderer):
        self._renderer = renderer
        self._text_renderer = getattr(renderer, 'text_renderer', None)

        if self._logger_text_renderer is None:
            class _LoggerTextWindow:
                def __init__(self, ctx):
                    self.ctx = ctx
                    self.texture = None

            logger_window = _LoggerTextWindow(renderer.ctx)
            hack_atlas = FontAtlas(font_path="vizcore/text/data/Hack-Regular.ttf", font_size=42)
            self._logger_text_renderer = TextRenderer(logger_window, hack_atlas)

        self._text_renderer = self._logger_text_renderer

    def bind_camera(self, camera):
        self.camera = camera

    def update(self):
        """Fetch new logs from DataBus fixed channels (INFO/WARN/ERROR/DEBUG)."""
        if not hasattr(self, 'data_bus') or self.data_bus is None:
            return

        appended_any = False

        for level in self.CHANNELS:
            channel_history = self.data_bus.history(level)
            if channel_history is None:
                channel_history = []

            curr_len = len(channel_history)
            prev_len = self._channel_history_lengths.get(level, 0)

            # Ring buffer rollover safety: if length shrank, consume from start.
            start_idx = 0 if curr_len < prev_len else prev_len

            for raw_entry in channel_history[start_idx:curr_len]:
                self.logs.append(self._normalize_log_entry(level, raw_entry))
                appended_any = True

            self._channel_history_lengths[level] = curr_len

        if appended_any and self.auto_scroll:
            self._snap_to_bottom()

    def _snap_to_bottom(self):
        """Calculates the max scroll offset to show the newest logs."""
        if not self.camera:
            self.visible_lines = 1
            self.scroll_offset = max(0, len(self.logs) - 1)
            return

        ui_scale = self.camera.height / 600.0
        txt_scale = self.font_scale * (0.85 + 0.45 * ui_scale)
        scaled_line_height = max(self.line_height * ui_scale, txt_scale * 54.0)

        # Calculate how many lines fit in the widget's height
        usable_height = max(1.0, self.camera.height - (2 * self.margin))
        self.visible_lines = max(1, int(usable_height / max(1.0, scaled_line_height)))

        # Set offset so the last log is at the bottom
        max_offset = max(0, len(self.logs) - self.visible_lines)
        self.scroll_offset = max_offset

    def on_mouse_scroll(self, x, y, scroll_x, scroll_y):
        """Handle mouse wheel to scroll history."""
        # Disable auto-scroll if the user scrolls up
        if scroll_y > 0:
            self.auto_scroll = False
            
        # Adjust offset (scroll_y is usually 1 or -1)
        self.scroll_offset -= int(scroll_y * 3) # Scroll 3 lines per tick

        max_offset = max(0, len(self.logs) - 1)
        # Clamp scrolling bounds
        self.scroll_offset = max(0, min(self.scroll_offset, max_offset))

        # Re-enable auto-scroll if they hit the bottom (approx visible lines)
        if self.scroll_offset >= max(0, max_offset - max(1, self.visible_lines)):
            self.auto_scroll = True

    def draw(self, renderer):
        """Render only the visible slice of logs (Virtual Scrolling)."""
        if not self._text_renderer:
            return

        # Disable depth testing for UI overlays, just like LinePlot
        renderer.ctx.disable(moderngl.DEPTH_TEST)

        if not self.camera:
            renderer.ctx.enable(moderngl.DEPTH_TEST)
            return

        ui_scale = self.camera.height / 600.0
        txt_scale = self.font_scale * (0.85 + 0.45 * ui_scale)
        scaled_line_height = max(self.line_height * ui_scale, txt_scale * 54.0)

        usable_height = max(1.0, self.camera.height - (2 * self.margin))
        visible_lines = max(1, int(usable_height / max(1.0, scaled_line_height)))
        self.visible_lines = visible_lines
        
        usable_width = max(1.0, self.camera.width - (2 * self.margin))
        char_width = max(1.0, 42.0 * txt_scale * 0.58)  # Approximate character width for monospace Hack font
        dynamic_wrap_chars = max(10, int(usable_width / char_width))

        if not self.logs:
            renderer.ctx.enable(moderngl.DEPTH_TEST)
            return

        draw_items = collections.deque()
        accumulated_height = 0.0

        if self.auto_scroll:
            # Go backwards to ensure the bottom perfectly aligns
            for log in reversed(self.logs):
                text_str = f"[{log['time']}] {log['level']}: {log['message']}"
                wrapped = self._wrap_message(text_str, dynamic_wrap_chars)
                
                log_height = len(wrapped) * scaled_line_height + scaled_line_height * 0.25
                
                draw_items.appendleft((None, scaled_line_height * 0.25))
                for line in reversed(wrapped):
                    draw_items.appendleft((log['level'], line))

                accumulated_height += log_height
                if accumulated_height >= usable_height:
                    break
                    
            if accumulated_height > usable_height:
                current_y = self.margin - (accumulated_height - usable_height)
            else:
                current_y = self.margin
        else:
            # User scrolled up, draw from current offset forward
            self.scroll_offset = max(0, min(self.scroll_offset, len(self.logs) - 1))
            for log in itertools.islice(self.logs, self.scroll_offset, len(self.logs)):
                text_str = f"[{log['time']}] {log['level']}: {log['message']}"
                wrapped = self._wrap_message(text_str, dynamic_wrap_chars)
                
                for line in wrapped:
                    draw_items.append((log['level'], line))
                draw_items.append((None, scaled_line_height * 0.25))

                log_height = len(wrapped) * scaled_line_height + scaled_line_height * 0.25
                accumulated_height += log_height
                if accumulated_height >= usable_height:
                    break
                    
            current_y = self.margin

        for item in draw_items:
            # Stop if we drop below the camera's bottom viewing region
            if current_y > self.camera.height - self.margin:
                break

            if item[0] is not None:
                # Text line: only draw if fully inside the top margin 
                if current_y + scaled_line_height > self.margin:
                    level, text = item
                    color = self.level_colors.get(level, (1.0, 1.0, 1.0, 1.0))
                    self._text_renderer.render_text(
                        text,
                        self.margin,
                        current_y,
                        color=color,
                        scale=txt_scale
                    )
                current_y += scaled_line_height
            else:
                # Spacer gap
                current_y += item[1]

        renderer.ctx.enable(moderngl.DEPTH_TEST)





        
        