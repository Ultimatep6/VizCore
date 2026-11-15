import os
import moderngl
from vizcore.renderer.shader_manager import ShaderManager
import numpy as np


class Renderer:
    def __init__(self, application, window_size):
        self.application = application
        self.__size = window_size
        self.ctx = application.ctx
        self.shader_manager = ShaderManager(application.ctx)

    def draw(self, program_name:str, buffer_bindings:list, index_buffer=None, **kwargs):
        program = self.shader_manager.get_shader(program_name)
        if program is None:
            raise ValueError(f"Shader program '{program_name}' not found in shader manager cache.")
        
        vao_content = []
        for buf, fmt, *attrs in buffer_bindings:
            vao_content.append((buf, fmt, *attrs))
        
        vao = self.ctx.vertex_array(program, vao_content, index_buffer)
        
        mode_val = kwargs.pop('mode', moderngl.TRIANGLES)
        vao.render(mode=mode_val, **kwargs)


    def set_uniform(self, shader_name, uniform_name, data):
        self.shader_manager.set_uniform(shader_name, uniform_name, data)

    def draw_mesh(self, mesh_name: str, mvp_matrix: np.ndarray = None, 
                  model_matrix: np.ndarray = None):
        """Draw a mesh from the mesh registry.
        
        Args:
            mesh_name: Name of mesh in registry or file path
            mvp_matrix: Model-View-Projection matrix (4x4)
            model_matrix: Model matrix (4x4) - if provided, uses camera's view/projection
        """
        from vizcore.meshes import get_mesh
        
        # Get mesh data
        mesh_data = get_mesh(mesh_name)
        vertices = mesh_data['vertices']
        indices = mesh_data['indices']
        
        # For now, just render without normals/uvs (extend later)
        if vertices.size == 0 or indices.size == 0:
            return
            
        # Create VBOs
        vbo_vertices = self.ctx.buffer(vertices.astype('f4').tobytes())
        ibo = self.ctx.buffer(indices.astype('i4').tobytes())
        
        # Get or create shader
        program = self.shader_manager.get_shader("ui")  # Temporary - use UI shader
        if program is None:
            # Fallback - create simple shader if needed
            vbo_vertices.release()
            ibo.release()
            return
            
        # Create VAO
        vao = self.ctx.vertex_array(
            program, 
            [(vbo_vertices, "3f", "in_position")],
            ibo
        )
        
        # Set uniforms
        if mvp_matrix is not None:
            self.set_uniform("ui", "mvp", mvp_matrix.astype('f4').T.tobytes())
        elif model_matrix is not None and self.application:
            # Use camera's view and projection
            view = np.eye(4, dtype='f4')
            projection = np.eye(4, dtype='f4')
            mvp = projection @ view @ model_matrix
            self.set_uniform("ui", "mvp", mvp.astype('f4').T.tobytes())
        
        # Render
        vao.render(moderngl.TRIANGLES)
        
        # Cleanup
        vao.release()
        vbo_vertices.release()
        ibo.release()

    def draw_instanced(self, mesh_name: str, transform_matrices: list,
                       mvp_matrix: np.ndarray = None):
        """Draw multiple instances of a mesh with different transforms.
        
        Args:
            mesh_name: Name of mesh in registry or file path
            transform_matrices: List of 4x4 transformation matrices
            mvp_matrix: Optional base MVP to combine with each transform
        """
        if not transform_matrices:
            return
            
        from vizcore.meshes import get_mesh
        
        # Get mesh data
        mesh_data = get_mesh(mesh_name)
        vertices = mesh_data['vertices']
        indices = mesh_data['indices']
        
        if vertices.size == 0 or indices.size == 0:
            return
            
        # Create VBOs
        vbo_vertices = self.ctx.buffer(vertices.astype('f4').tobytes())
        ibo = self.ctx.buffer(indices.astype('i4').tobytes())
        
        # For instancing, we'd need to create a buffer for the transform matrices
        # This is a simplified version - full instancing would require more setup
        # For now, just draw each instance separately (less efficient but works)
        for transform in transform_matrices:
            if mvp_matrix is not None:
                final_mvp = mvp_matrix @ transform
            else:
                final_mvp = transform
                
            self.draw_mesh(mesh_name, mvp_matrix=final_mvp)
            
        # Cleanup
        vbo_vertices.release()
        ibo.release()

    