fbo = ctx.simple_framebuffer((512, 512)) # <--- A buffer that contains 512x512 pixels
fbo.use()
fbo.clear(0.0, 0.0, 0.0, 1.0) # <--- Set the pixels to black with full (1) opacity

vao.render(moderngl.LINE_STRIP) # <--- Render a set of vertices by connecting them up vertex by vertex

vao.render(moderngl.LINE_STRIP)
Image.frombytes('RGB', fbo.size, fbo.read(), 'raw', 'RGB', 0, -1).show()    # read the framebuffer GPU to CPU. Display the image



