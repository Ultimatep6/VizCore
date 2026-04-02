import numpy as np
from vizcore.utils import rotation_x, rotation_y, translation, perspective

class Camera:
    def __init__(self, width, height):
        self.projection  = perspective(np.radians(60), width / height, 0.1, 100)
        camera_tilt  = rotation_x(np.radians(25))
        camera_trans = translation(0, -0.3, -3)
        self.view         = camera_trans @ camera_tilt