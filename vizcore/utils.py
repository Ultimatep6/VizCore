import numpy as np

X_AXIS = np.array([1.0, 0.0, 0.0])
Y_AXIS = np.array([0.0, 1.0, 0.0])
Z_AXIS = np.array([0.0, 0.0, 1.0])


def rotation_matrix_from_vectors(a, b):
    a = a / np.linalg.norm(a)
    b = b / np.linalg.norm(b)
    v = np.cross(a, b)
    c = np.dot(a, b)
    if np.allclose(v, 0):
        return np.eye(3) if c > 0 else -np.eye(3)
    s = np.linalg.norm(v)
    kmat = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
    R = np.eye(3) + kmat + kmat @ kmat * ((1 - c) / (s**2))
    return R.astype("f4")


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


def normalize(v):
    return v / np.linalg.norm(v) if np.linalg.norm(v) > 1e-8 else v


def get_view_matrix(eye, target, up=np.array([0, 1, 0], dtype=np.float32)):
    f = normalize(target - eye)

    # Fallback if forward direction is parallel to up
    if abs(np.dot(f, up)) > 0.999:
        up = np.array([0.0, 0.0, 1.0], dtype=np.float32)

    r = normalize(np.cross(f, up))
    u = np.cross(r, f)

    return np.array(
        [
            [r[0], r[1], r[2], -np.dot(r, eye)],
            [u[0], u[1], u[2], -np.dot(u, eye)],
            [-f[0], -f[1], -f[2], np.dot(f, eye)],
            [0, 0, 0, 1],
        ],
        dtype=np.float32,
    )


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
