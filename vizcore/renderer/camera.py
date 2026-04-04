import numpy as np
from vizcore.utils import rotation_x, rotation_y, translation, perspective

class Camera:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.update_projection(width, height)
        camera_tilt  = rotation_x(np.radians(25))
        camera_trans = translation(0, -0.3, -3)
        self.view         = camera_trans @ camera_tilt

    def update_projection(self, width, height):
        self.width = width
        self.height = height
        aspect = width / height if height > 0 else 1.0
        self.projection  = perspective(np.radians(60), aspect, 0.1, 100)