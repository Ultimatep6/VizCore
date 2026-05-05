# Vizcore Project Conventions

This document outlines key technical standards for the Vizcore project to ensure consistency.

---

## 1. Matrix Layout: Column-Major

All transformation matrices (model, view, projection) are handled in **column-major** format.

-   **Why**: This aligns with OpenGL and GLSL, eliminating the need to transpose matrices before they are sent to the GPU.
-   **Transformation Order**: `Projection * View * Model`.
-   **Visual Example**: A transformation matrix is composed of basis vectors (right, up, forward) and a position vector, which form the columns of the matrix.
    $$
    \begin{bmatrix}
    right_x & up_x & forward_x & position_x \\
    right_y & up_y & forward_y & position_y \\
    right_z & up_z & forward_z & position_z \\
    0 & 0 & 0 & 1
    \end{bmatrix}
    $$
-   **Implementation**:
    -   Functions in `vizcore.utils` must return column-major `numpy.ndarray`s.
    -   `PyGLM` is to be used with its default column-major settings.

---

## 2. Coordinate System: Right-Handed

Vizcore uses a **right-handed coordinate system**, the standard for OpenGL.

-   **+X axis:** Points right
-   **+Y axis:** Points up
-   **-Z axis:** Points "into" the screen (away from the camera)

---

## 3. Data Types and Formats

-   **Matrices**:
    -   **Type**: `numpy.ndarray`
    -   **Dimensions**: `4x4`
    -   **Data Type**: `numpy.float32`
    -   **Layout**: Column-major, as specified above.
    -   **Example**:
        ```python
        import numpy as np
        # A 4x4 column-major identity matrix
        identity_matrix = np.identity(4, dtype=np.float32)
        ```

-   **Vectors**:
    -   **Type**: `numpy.ndarray` or `glm.vec` types.
    -   **Dimensions**: `vec3` for positions and directions, `vec4` for homogeneous coordinates.
    -   **Data Type**: `numpy.float32`
    -   **Example**:
        ```python
        import numpy as np
        import glm
        # A 3D position vector
        position_np = np.array([1.0, 2.0, 3.0], dtype=np.float32)
        position_glm = glm.vec3(1.0, 2.0, 3.0)
        ```

