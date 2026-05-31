import numpy as np
import moderngl



def generate_sphere_geometry(radius, sectors=32, rings=16):
    vertices, normals = [], []
    for r in range(rings + 1):
        theta = r * np.pi / rings
        for s in range(sectors + 1):
            phi = s * 2.0 * np.pi / sectors
            x = radius * np.sin(theta) * np.cos(phi)
            y = radius * np.cos(theta)
            z = radius * np.sin(theta) * np.sin(phi)
            vertices.append((x, y, z))
            normals.append((x / radius, y / radius, z / radius))
    indices = []
    for r in range(rings):
        for s in range(sectors):
            first = r * (sectors + 1) + s
            second = first + sectors + 1
            indices += [first, second, first + 1, second, second + 1, first + 1]
    return (
        np.array(vertices, dtype=np.float32),
        np.array(normals, dtype=np.float32),
        np.array(indices, dtype=np.int32),
    )


def render_nodes(ctx, vp, program, vao, instance_buf, positions, radius, color):
    if not len(positions):
        return
    ctx.enable(moderngl.DEPTH_TEST)
    program["u_vp"].write(vp.astype("f4").T.tobytes())
    program["u_radius"].value = radius
    program["u_color"].write(np.array(color, dtype="f4").tobytes())
    count = min(len(positions), 64)
    instance_buf.write(np.array(positions[:count], dtype="f4").tobytes())
    vao.render(moderngl.TRIANGLES, instances=count)
    ctx.disable(moderngl.DEPTH_TEST)


def render_indicators(ctx, vp, program, vao, positions, radius, color):
    count = len(positions)
    if not count:
        return
    ctx.enable(moderngl.DEPTH_TEST)
    program["u_color"].write(np.array(color, dtype="f4").tobytes())
    program["R"].value = radius
    for pos in positions:
        t = np.eye(4, dtype=np.float32)
        t[0:3, 3] = [pos[0], 0.0, pos[2]]
        mvp = vp @ t
        program["mvp"].write(mvp.astype("f4").T.tobytes())
        vao.render(moderngl.TRIANGLE_STRIP, 4)
    ctx.disable(moderngl.DEPTH_TEST)


def render_cylinders(ctx, vp, program, vao, positions, radius, color, max_instances=16):
    count = len(positions)
    if not count:
        return
    count = min(count, max_instances)
    ctx.enable(moderngl.DEPTH_TEST)
    matrices = np.tile(np.eye(4, dtype=np.float32), (count, 1, 1))
    colors = np.zeros((count, 3), dtype=np.float32)
    for i in range(count):
        pos = positions[i]
        h = pos[1]
        if h >= 0:
            matrices[i, 1, 3] = 0.0
            matrices[i, 1, 1] = h
        else:
            matrices[i, 1, 3] = h
            matrices[i, 1, 1] = -h
        matrices[i, 0, 0] = radius
        matrices[i, 2, 2] = radius
        matrices[i, 0, 3] = pos[0]
        matrices[i, 2, 3] = pos[2]
        colors[i] = color
    program["u_vp"].write(vp.astype("f4").T.tobytes())
    program["u_models"].write(
        matrices.transpose(0, 2, 1).ravel().astype("f4").tobytes()
    )
    program["u_colors"].write(colors.astype("f4").tobytes())
    vao.render(moderngl.TRIANGLES, 24 * 6, instances=count)
    ctx.disable(moderngl.DEPTH_TEST)


def render_tiles(ctx, tile_manager):
    if not ctx:
        return
    ctx.disable(moderngl.DEPTH_TEST)
    tile_manager.render()
    ctx.enable(moderngl.DEPTH_TEST)


def render_gui(ctx, gui_manager):
    if not ctx:
        return
    ctx.disable(moderngl.DEPTH_TEST)
    gui_manager.render()
    ctx.enable(moderngl.DEPTH_TEST)
