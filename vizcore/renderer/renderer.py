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

        font_atlas_body = FontAtlas(font_path="vizcore/text/data/cmunbi.ttf", font_size=48)
        # temporary
        # self.text       = TextRenderer(window_wrapper, font_atlas_body, window_size)

    def draw(self, program_name:str, buffer_bindings:list, index_buffer=None, **kwargs):
        program = self.shader_manager.get_shader(program_name)
        if program is None:
            raise ValueError(f"Shader program '{program_name}' not found in shader manager cache.")
        
        vao_content = []
        for buf, fmt, *attrs in buffer_bindings:
            vao_content.append((buf, fmt, *attrs))
        
        vao = self.ctx.vertex_array(program, vao_content, index_buffer)
        vao.render(**kwargs)


    def set_uniform(self, shader_name, uniform_name, data):
        self.shader_manager.set_uniform(shader_name, uniform_name, data)

    