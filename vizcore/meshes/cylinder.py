import numpy as np

def generate_cylinder(radius=0.5, height=1.0, segments=32):
    vertices = []
    indices = []

    # Bottom circle vertices (z = 0)
    for i in range(segments):
        angle = 2 * np.pi * i / segments
        vertices.append([radius * np.cos(angle), radius * np.sin(angle), 0.0])

    # Top circle vertices (z = height)
    for i in range(segments):
        angle = 2 * np.pi * i / segments
        vertices.append([radius * np.cos(angle), radius * np.sin(angle), height])

    # Side triangles (two triangles per quad, CCW from outside)
    for i in range(segments):
        next_i = (i + 1) % segments
        bot_curr = i
        bot_next = next_i
        top_curr = i + segments
        top_next = next_i + segments

        # First triangle of quad
        indices.append([bot_curr, top_curr, bot_next])
        # Second triangle of quad
        indices.append([bot_next, top_curr, top_next])

    # Bottom cap
    bot_center = len(vertices)
    vertices.append([0.0, 0.0, 0.0])
    for i in range(segments):
        next_i = (i + 1) % segments
        indices.append([bot_center, next_i, i])   # CW from below = CCW from outside

    # Top cap
    top_center = len(vertices)
    vertices.append([0.0, 0.0, height])
    for i in range(segments):
        next_i = (i + 1) % segments
        indices.append([top_center, i, next_i])   # CCW from above = CCW from outside

    return np.array(vertices, dtype=np.float32), np.array(indices, dtype=np.int32)