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

    def load_shader(self, name:str, vertex_path, fragment_path):
        """
        Docstring for load_shader
        
        :param name: String that holds the name of the render package
        :param vertex_path: String that holds the path to the render package vertex shader
        :param fragment_path: String that holds the path to the render package fragment shader
        """
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
    
    def set_uniform(self, shader_name, uniform_name, value):
        """
        Set a uniform value for a shader program.
        
        :param shader_name: Name of the shader program to set the uniform for
        :param uniform_name: Name of the uniform variable in the shader
        :param value: Value to set for the uniform (can be int, float, tuple, list, or numpy array)
        """
        program = self.get_shader(shader_name)
        if program is None:
            raise ValueError(f"Shader '{shader_name}' not found in cache.")
        if uniform_name not in program:
            raise ValueError(f"Uniform '{uniform_name}' not found in shader '{shader_name}'.")
        
        if isinstance(value, bytes):
            program[uniform_name].write(value)
        else:
            program[uniform_name].value = value

    def get_shader(self, name):
        return self._cache.get(name)