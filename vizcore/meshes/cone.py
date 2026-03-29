import numpy as np

def generate_cone(radius=0.5, height=1.0, segments=32, include_base=True, z_offset=0.0):
    vertices = []
    indices = []

    # Base circle at z = z_offset
    for i in range(segments):
        angle = 2 * np.pi * i / segments
        vertices.append([radius * np.cos(angle), radius * np.sin(angle), z_offset])

    # Tip at z = z_offset + height
    tip_index = len(vertices)
    vertices.append([0.0, 0.0, z_offset + height])

    # Side triangles (CCW from outside)
    for i in range(segments):
        next_i = (i + 1) % segments
        indices.append([i, tip_index, next_i])

    # Base cap
    if include_base:
        base_center_index = len(vertices)
        vertices.append([0.0, 0.0, z_offset])
        for i in range(segments):
            next_i = (i + 1) % segments
            indices.append([base_center_index, i, next_i])

    return np.array(vertices, dtype=np.float32), np.array(indices, dtype=np.int32)