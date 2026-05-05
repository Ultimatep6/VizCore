import numpy as np
import unittest
import glm

"""
Unit tests to ensure that all the matrix generation functions are correct.
WE will use ROW-MAJOR convention for all matrices, which is the default in numpy and matches how OpenGL expects data.
Compared against glm to ensure correctness. Note that glm uses COLUMN-MAJOR convention,
     so we will transpose the results from glm for comparison.
"""

X_AXIS = np.array([1.0, 0.0, 0.0])
Y_AXIS = np.array([0.0, 1.0, 0.0])
Z_AXIS = np.array([0.0, 0.0, 1.0])


def get_translation_matrix(tx=0, ty=0, tz=0) -> np.ndarray:
    """
    Returns a 4x4 translation matrix for translating by (tx, ty, tz) in column-major format.

    :param tx: Description
    :param ty: Description
    :param tz: Description
    :return: Description
    :rtype: ndarray[_AnyShape, dtype[Any]]
    """
    return np.array(
        [
            [1, 0, 0, tx],
            [0, 1, 0, ty],
            [0, 0, 1, tz],
            [0, 0, 0, 1],
        ],
        dtype=np.float32,
    )


def get_scale_matrix(sx=1, sy=1, sz=1) -> np.ndarray:
    return np.array(
        [
            [sx, 0, 0, 0],
            [0, sy, 0, 0],
            [0, 0, sz, 0],
            [0, 0, 0, 1],
        ],
        dtype=np.float32,
    )


def get_rot_matrix(angle, axis: np.ndarray) -> np.ndarray:
    c, s = np.cos(angle), np.sin(angle)
    x, y, z = axis
    return np.array(
        [
            [c + x * x * (1 - c), x * y * (1 - c) - z * s, x * z * (1 - c) + y * s, 0],
            [y * x * (1 - c) + z * s, c + y * y * (1 - c), y * z * (1 - c) - x * s, 0],
            [z * x * (1 - c) - y * s, z * y * (1 - c) + x * s, c + z * z * (1 - c), 0],
            [0, 0, 0, 1],
        ],
        dtype=np.float32,
    )


def get_total_rot_matrix(angle_x=0.0, angle_y=0.0, angle_z=0.0) -> np.ndarray:

    rotX = get_rot_matrix(angle_x, X_AXIS)
    rotY = get_rot_matrix(angle_y, Y_AXIS)
    rotZ = get_rot_matrix(angle_z, Z_AXIS)

    rotT = rotZ @ rotY @ rotX
    return rotT


def get_model_matrix(tx=0, ty=0, tz=0, sx=1, sy=1, sz=1, rx=0.0, ry=0.0, rz=0.0):
    T = get_translation_matrix(tx, ty, tz)
    R = get_total_rot_matrix(rx, ry, rz)
    S = get_scale_matrix(sx, sy, sz)
    return T @ R @ S


get_model_matrix()


def normalize(v):
    return v / np.linalg.norm(v) if np.linalg.norm(v) > 1e-8 else v


def normalize_mesh_vertices(vertices: np.ndarray) -> np.ndarray:
    if len(vertices) == 0:
        return vertices

    min_corner = vertices.min(axis=0)
    max_corner = vertices.max(axis=0)
    center = (min_corner + max_corner) * 0.5
    extents = max_corner - min_corner
    max_extent = float(np.max(extents))

    if max_extent <= 1e-8:
        return vertices - center

    # Fit largest side to length 2.0 => model roughly inside [-1, 1]
    scale = 2.0 / max_extent
    return (vertices - center) * scale


def get_view_matrix(eye, target, up=np.array([0, 1, 0], dtype=np.float32)):
    zaxis = normalize(eye - target)
    xaxis = normalize(np.cross(up, zaxis))
    yaxis = np.cross(zaxis, xaxis)

    viewMatrix = np.array(
        [
            [xaxis[0], yaxis[0], zaxis[0], 0],
            [xaxis[1], yaxis[1], zaxis[1], 0],
            [xaxis[2], yaxis[2], zaxis[2], 0],
            [np.dot(-xaxis, eye), np.dot(-yaxis, eye), np.dot(-zaxis, eye), 1],
        ],
        dtype=np.float32,
    )

    return viewMatrix


def get_perspective_matrix(fov_y_deg: float, aspect: float, near: float, far: float):
    """
    Compute a perspective projection matrix (OpenGL-style, column-major layout).

    Args:
        fov_y_deg: Vertical field of view in degrees
        aspect: Aspect ratio (width / height)
        near: Near clipping plane (positive)
        far: Far clipping plane (positive, > near)

    Returns:
        4x4 perspective projection matrix (as numpy array, column-major order)
    """
    fov_rad = np.radians(fov_y_deg)
    f = 1.0 / np.tan(fov_rad / 2.0)

    return np.array(
        [
            [f / aspect, 0, 0, 0],
            [0, f, 0, 0],
            [0, 0, (far + near) / (near - far), (2 * far * near) / (near - far)],
            [0, 0, -1, 0],
        ],
        dtype=np.float32,
    )


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
