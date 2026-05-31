import moderngl


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
