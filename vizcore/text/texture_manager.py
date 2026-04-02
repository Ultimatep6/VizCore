import moderngl

class TextureManager:
    def __init__(self, ctx):
        self.ctx = ctx
        self.textures = {}

    def get_texture(self, key):
        return self.textures.get(key)

    def append_texture(self, key, texture):
        self.textures[key] = texture

    def set_texture(self, key):
        self.ctx.texture = self.textures.get(key)
    