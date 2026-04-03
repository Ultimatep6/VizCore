import os
import moderngl
from vizcore.renderer.shader_manager import ShaderManager
from vizcore.text.fontAtlas import FontAtlas, TextRenderer
# from vizcore.utils.config import find_system_font
import numpy as np


class Renderer:
    def __init__(self, application, window_size):
        self.application = application
        self.__size = window_size
        self.ctx = application.ctx
        self.shader_manager = ShaderManager(application.ctx)

        # Initialize Text Rendering
        try:
            font_atlas_body = FontAtlas(font_path="vizcore/text/data/cmunbi.ttf", font_size=48)
            # Create a mock window wrapper for TextRenderer which expects .ctx, .texture and .size
            class WindowWrapper:
                def __init__(self, ctx, app):
                    self.ctx = ctx
                    self.app = app
                    self.texture = None
                
                @property
                def size(self):
                    # Pull dynamic dimensions from the tile/window pipeline
                    return self.app.window.width, self.app.window.height

            self.window_wrapper = WindowWrapper(self.ctx, self.application)
            self.text_renderer = TextRenderer(self.window_wrapper, font_atlas_body)
        except Exception as e:
            print(f"Warning: Failed to initialize TextRenderer: {e}")
            self.text_renderer = None

    def draw(self, program_name:str, buffer_bindings:list, index_buffer=None, **kwargs):
        program = self.shader_manager.get_shader(program_name)
        if program is None:
            raise ValueError(f"Shader program '{program_name}' not found in shader manager cache.")
        
        vao_content = []
        for buf, fmt, *attrs in buffer_bindings:
            vao_content.append((buf, fmt, *attrs))
        
        vao = self.ctx.vertex_array(program, vao_content, index_buffer)
        
        mode_val = kwargs.pop('mode', moderngl.TRIANGLES)
        vao.render(mode=mode_val, **kwargs)


    def set_uniform(self, shader_name, uniform_name, data):
        self.shader_manager.set_uniform(shader_name, uniform_name, data)

    