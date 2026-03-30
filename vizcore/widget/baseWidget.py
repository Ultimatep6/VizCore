
class BaseWidget:
    def __init__(self, ctx, text_renderer=None, data_bus=None):
        self.ctx = ctx
        self.data_bus = data_bus