import numpy as np
from vizcore.utils import (
    combine_meshes,
    get_rot_matrix,
    transform_vertices,
    colorize_vertices,
    X_AXIS,
    Y_AXIS,
    Z_AXIS,
)
from vizcore.meshes.cone import generate_cone
from vizcore.meshes.cylinder import generate_cylinder


def build_arrow3D(shaft_radius, shaft_height, head_radius, head_height, segments=32):
    """Builds an arrow along +Z, base at origin."""
    cyl_verts, cyl_inds = generate_cylinder(shaft_radius, shaft_height, segments)
    cone_verts, cone_inds = generate_cone(head_radius, head_height, segments)

    # Shift cone up to sit on top of the cylinder
    cone_verts = cone_verts.copy()
    cone_verts[:, 2] += shaft_height

    return combine_meshes(cyl_verts, cyl_inds, cone_verts, cone_inds)


def build_axis_arrow(shaft_radius, shaft_height, head_radius, head_height, segments=16):
    """Build an arrow mesh for axis visualization (shaft along +Z).

    Args:
        shaft_radius: Radius of the arrow shaft
        shaft_height: Height of the arrow shaft
        head_radius: Radius of the arrow head
        head_height: Height of the arrow head
        segments: Number of segments for cylinder/cone

    Returns:
        Tuple of (vertices, indices)
    """
    cyl_verts, cyl_inds = generate_cylinder(shaft_radius, shaft_height, segments)
    cone_verts, cone_inds = generate_cone(head_radius, head_height, segments)
    cone_verts = cone_verts.copy()
    cone_verts[:, 2] += shaft_height
    return combine_meshes(cyl_verts, cyl_inds, cone_verts, cone_inds)


def build_axis(
    shaft_radius=0.02,
    shaft_height=1.0,
    head_radius=0.05,
    head_height=0.2,
    segments=16,
    colors=None,
):
    """Build a complete 3-axis coordinate system with three arrows.

    Args:
        shaft_radius: Radius of arrow shafts
        shaft_height: Height of arrow shafts
        head_radius: Radius of arrow heads
        head_height: Height of arrow heads
        segments: Number of segments for cylinder/cone
        colors: Optional dict with 'x', 'y', 'z' colors. Default: RED, GREEN, BLUE

    Returns:
        Tuple of (vertices, indices, colors) where vertices and indices are concatenated
        for all three axes. colors is the color array for each vertex.
    """
    if colors is None:
        colors = {
            "x": np.array([1.0, 0.0, 0.0, 1.0], dtype=np.float32),
            "y": np.array([0.0, 1.0, 0.0, 1.0], dtype=np.float32),
            "z": np.array([0.0, 0.0, 1.0, 1.0], dtype=np.float32),
        }

    arrow_verts, arrow_inds = build_axis_arrow(
        shaft_radius, shaft_height, head_radius, head_height, segments
    )

    x_verts = transform_vertices(arrow_verts, get_rot_matrix(np.pi / 2, Y_AXIS))
    y_verts = transform_vertices(arrow_verts, get_rot_matrix(-np.pi / 2, X_AXIS))
    z_verts = arrow_verts.copy()

    x_colored = colorize_vertices(x_verts, colors["x"][:3])
    y_colored = colorize_vertices(y_verts, colors["y"][:3])
    z_colored = colorize_vertices(z_verts, colors["z"][:3])

    n_verts = len(arrow_verts)
    all_verts = np.concatenate([x_colored, y_colored, z_colored], axis=0)
    all_inds = np.concatenate(
        [arrow_inds, arrow_inds + n_verts, arrow_inds + 2 * n_verts], axis=0
    )

    return all_verts, all_inds


def build_arrow2D(
    shaft_width, shaft_height, head_width, head_height, head_segments=12, as_3d=False
):
    """Builds an arrow along +Y in the Y/X plane, base at the origin.

    Args:
        as_3d: If True, returns 4D homogeneous coordinates (x, y, 0.0, 1.0).
               If False, returns 2D coordinates (x, y).
    """
    if head_segments % 3 != 0:
        raise ValueError("head_segements must be a multiple of 3")

    half_shaft_width = shaft_width / 2.0
    half_head_width = head_width / 2.0
    n_triangles = head_segments / 3.0

    shaft_vertices = np.array(
        [
            -half_shaft_width,
            0.0,
            half_shaft_width,
            0.0,
            -half_shaft_width,
            shaft_height,
            half_shaft_width,
            shaft_height,
        ]
    )

    head_vertices = np.array(
        [
            0.0,
            shaft_height + head_height,
            -half_head_width,
            shaft_height,
            half_head_width,
            shaft_height,
        ]
    )

    vertices = np.concatenate([shaft_vertices, head_vertices])
    vertices = vertices.reshape(-1, 2)

    shaft_indices = np.array([0, 1, 2, 1, 2, 3], dtype=np.int32)
    head_indices = np.array([5, 4, 6])
    indices = np.concatenate([shaft_indices, head_indices])

    if as_3d:
        vertices_3d = np.zeros((len(vertices), 4), dtype=np.float32)
        vertices_3d[:, 0] = vertices[:, 0]
        vertices_3d[:, 1] = vertices[:, 1]
        vertices_3d[:, 2] = 0.0
        vertices_3d[:, 3] = 1.0
        return vertices_3d, indices

    return vertices, indices
