import numpy as np
import unittest
import glm
from vizcore.utils import (
    get_rot_matrix,
    get_total_rot_matrix,
    get_model_matrix,
    get_perspective_matrix,
    get_scale_matrix,
    get_translation_matrix,
    get_view_matrix,
)

"""
Unit tests to ensure that all the matrix generation functions are correct.
WE will use ROW-MAJOR convention for all matrices, which is the default in numpy and matches how OpenGL expects data.
Compared against glm to ensure correctness. Note that glm uses COLUMN-MAJOR convention,
     so we will transpose the results from glm for comparison.
"""


class TestMatrices(unittest.TestCase):
    def test_translation_matrix(self):
        tx, ty, tz = 1.0, 2.0, 3.0
        expected = get_translation_matrix(tx, ty, tz)
        result = glm.translate((tx, ty, tz))
        np.testing.assert_array_almost_equal(result, expected)

    def test_scale_matrix(self):
        sx, sy, sz = 2.0, 3.0, 4.0
        expected = get_scale_matrix(sx, sy, sz)
        result = glm.scale((sx, sy, sz))
        np.testing.assert_array_almost_equal(result, expected)

    def test_rotation_matrix(self):
        angle_x, angle_y, angle_z = np.radians(30), np.radians(45), np.radians(60)
        expected = get_total_rot_matrix(angle_x, angle_y, angle_z)
        rot_x = glm.rotate(np.rad2deg(angle_x), (1.0, 0.0, 0.0))
        rot_y = glm.rotate(np.rad2deg(angle_y), (0.0, 1.0, 0.0))
        rot_z = glm.rotate(np.rad2deg(angle_z), (0.0, 0.0, 1.0))
        result = rot_z @ rot_y @ rot_x
        np.testing.assert_array_almost_equal(result, expected)

    def test_model_matrix(self):
        tx, ty, tz = 1.0, 2.0, 3.0
        sx, sy, sz = 2.0, 3.0, 4.0
        angle_x, angle_y, angle_z = np.radians(30), np.radians(45), np.radians(60)
        expected = get_model_matrix(
            tx=tx, ty=ty, tz=tz, sx=sx, sy=sy, sz=sz, rx=angle_x, ry=angle_y, rz=angle_z
        )

        T = glm.translate((tx, ty, tz))

        R = (
            glm.rotate(np.rad2deg(angle_z), (0.0, 0.0, 1.0))
            @ glm.rotate(np.rad2deg(angle_y), (0.0, 1.0, 0.0))
            @ glm.rotate(np.rad2deg(angle_x), (1.0, 0.0, 0.0))
        )

        S = glm.scale((sx, sy, sz))

        result = T @ R @ S
        np.testing.assert_array_almost_equal(result, expected)

    def test_view_matrix(self):
        eye = np.array([1.0, 2.0, 3.0])
        target = np.array([4.0, 5.0, 6.0])
        expected = get_view_matrix(eye, target)
        result = glm.lookat(eye, target, (0.0, 1.0, 0.0)).T
        np.testing.assert_array_almost_equal(result, expected)

    def test_perspective_matrix(self):

        fov_y = 45.0
        aspect = 16 / 9
        near = 0.1
        far = 100.0
        expected = get_perspective_matrix(fov_y, aspect, near, far)
        result = glm.perspective(fov_y, aspect, znear=near, zfar=far)

        np.testing.assert_array_almost_equal(result, expected)
