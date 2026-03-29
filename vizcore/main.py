import moderngl

ctx = moderngl.create_context(standalone=True)

fbo = ctx.simple_framebuffer((100, 100), 4) 
fbo.use()
