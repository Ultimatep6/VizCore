import numpy as np
from vizcore.utils import combine_meshes
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


def build_arrow2D(shaft_width, shaft_height, head_width, head_height, head_segments=12, as_3d=False):
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
            -half_shaft_width, 0.0,
            half_shaft_width, 0.0,
            -half_shaft_width, shaft_height,
            half_shaft_width, shaft_height,
        ]
    )

    head_vertices = np.array(
        [
            0.0, shaft_height + head_height,
            -half_head_width, shaft_height,
            half_head_width, shaft_height,
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
