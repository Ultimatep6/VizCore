import moderngl

class ShaderManager:
    """
    Handles shader compilation and caching.

    Responsibilities:
        - Load shader files
        - Compile shaders
        - Cache compiled programs
        - Ensure shaders are not repeatedly compiled
    """
    def __init__(self, ctx: moderngl.Context):
        self.ctx = ctx
        self._cache = {}

    def load_shader(self, name, vertex_path, fragment_path):
        if name in self._cache:
            return self._cache[name]
        with open(vertex_path, 'r') as vfile:
            vertex_src = vfile.read()
        with open(fragment_path, 'r') as ffile:
            fragment_src = ffile.read()
        program = self.ctx.program(
            vertex_shader=vertex_src,
            fragment_shader=fragment_src
        )
        self._cache[name] = program
        return program

    def get_shader(self, name):
        return self._cache.get(name)