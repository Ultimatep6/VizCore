import numpy as np
import os
from .loader import load_model


class MeshRegistry:
    """Central registry for mesh loaders and generators."""
    
    _generators = {}
    _loaders = {}
    _cache = {}  # Cache loaded meshes to avoid reloading
    
    @classmethod
    def register_generator(cls, name: str, generator_func):
        """Register a procedural mesh generator.
        
        Args:
            name: Name to register the generator under
            generator_func: Function that returns (vertices, indices) tuple
        """
        cls._generators[name] = generator_func
    
    @classmethod
    def register_loader(cls, extension: str, loader_func):
        """Register a file format loader.
        
        Args:
            extension: File extension (e.g., '.obj', '.gltf')
            loader_func: Function that takes path and returns mesh dict
        """
        cls._loaders[extension.lower()] = loader_func
    
    @classmethod
    def get_mesh(cls, source):
        """Get mesh data from generator name or file path.
        
        Args:
            source: Either a string name for a registered generator,
                   or a file path to load
                   
        Returns:
            dict with keys: 'vertices', 'indices', 'normals', 'uvs'
            For procedural meshes, normals and uvs may be empty arrays
        """
        # Check cache first
        if source in cls._cache:
            return cls._cache[source]
        
        # Check if it's a registered generator name
        if source in cls._generators:
            vertices, indices = cls._generators[source]()
            # Convert to standard format
            mesh_data = {
                'vertices': vertices.astype(np.float32),
                'indices': indices.astype(np.uint32),
                'normals': np.zeros((len(vertices), 3), dtype=np.float32),  # Placeholder
                'uvs': np.zeros((len(vertices), 2), dtype=np.float32)       # Placeholder
            }
            cls._cache[source] = mesh_data
            return mesh_data
        
        # Check if it's a file path
        if isinstance(source, str) and os.path.exists(source):
            mesh_data = load_model(source)
            cls._cache[source] = mesh_data
            return mesh_data
        
        # Try to find a loader for the extension
        if isinstance(source, str):
            _, ext = os.path.splitext(source.lower())
            if ext in cls._loaders:
                mesh_data = cls._loaders[ext](source)
                cls._cache[source] = mesh_data
                return mesh_data
        
        raise ValueError(f"Mesh source not found or not supported: {source}")
    
    @classmethod
    def clear_cache(cls):
        """Clear the mesh cache."""
        cls._cache.clear()
    
    @classmethod
    def is_cached(cls, source):
        """Check if a mesh is already cached."""
        return source in cls._cache


# Register default procedural mesh generators
def _register_defaults():
    """Register the default procedural mesh generators."""
    # Import here to avoid circular dependencies
    from .arrow import build_arrow
    from .cylinder import generate_cylinder
    from .cone import generate_cone
    from ..utils import combine_meshes
    
    MeshRegistry.register_generator('arrow', 
        lambda: build_arrow(shaft_radius=0.04, shaft_height=0.6, 
                           head_radius=0.10, head_height=0.2))
    
    MeshRegistry.register_generator('cylinder', 
        lambda: generate_cylinder(radius=0.5, height=1.0, segments=32))
    
    MeshRegistry.register_generator('cone', 
        lambda: generate_cone(radius=0.5, height=1.0, segments=32))
    
    # Register OBJ loader
    MeshRegistry.register_loader('.obj', lambda p: ModelLoader._load_obj(p))


# Auto-register defaults when module is imported
_register_defaults()


def load_mesh(source) -> dict:
    """Convenience function to get mesh data.
    
    Args:
        source: Generator name or file path
        
    Returns:
        dict with mesh data
    """
    return MeshRegistry.get_mesh(source)