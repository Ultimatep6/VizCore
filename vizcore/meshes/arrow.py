import numpy as np
from vizcore.utils import combine_meshes
from vizcore.meshes.cone import generate_cone
from vizcore.meshes.cylinder import generate_cylinder

def build_arrow(shaft_radius, shaft_height, head_radius, head_height, segments=32):
    """Builds an arrow along +Z, base at origin."""
    cyl_verts, cyl_inds   = generate_cylinder(shaft_radius, shaft_height, segments)
    cone_verts, cone_inds = generate_cone(head_radius, head_height, segments)

    # Shift cone up to sit on top of the cylinder
    cone_verts = cone_verts.copy()
    cone_verts[:, 2] += shaft_height

    return combine_meshes(cyl_verts, cyl_inds, cone_verts, cone_inds)