import numpy as np
import os


def _compute_normals(vertices, indices):
    """Compute per-vertex normals from triangle mesh."""
    normals = np.zeros_like(vertices)
    for i in range(0, len(indices), 3):
        v0 = vertices[indices[i]]
        v1 = vertices[indices[i + 1]]
        v2 = vertices[indices[i + 2]]
        edge1 = v1 - v0
        edge2 = v2 - v0
        face_normal = np.cross(edge1, edge2)
        norm = np.linalg.norm(face_normal)
        if norm > 1e-8:
            face_normal /= norm
        normals[indices[i]] += face_normal
        normals[indices[i + 1]] += face_normal
        normals[indices[i + 2]] += face_normal
    
    # Normalize
    lengths = np.linalg.norm(normals, axis=1, keepdims=True)
    lengths = np.where(lengths > 1e-8, lengths, 1.0)
    normals /= lengths
    return normals


class ModelLoader:
    """Loads 3D models from various file formats."""
    
    @staticmethod
    def load(path: str) -> dict:
        """Load a 3D model and return mesh data.
        
        Returns:
            dict with keys: 'vertices', 'indices', 'normals', 'uvs'
        """
        if not os.path.exists(path):
            raise FileNotFoundError(f"Model file not found: {path}")
        
        _, ext = os.path.splitext(path.lower())
        
        if ext == '.obj':
            return ModelLoader._load_obj(path)
        else:
            raise ValueError(f"Unsupported model format: {ext}")
    
    @staticmethod
    def _load_obj(filepath: str) -> dict:
        """Load Wavefront .obj file."""
        vertices = []
        normals = []
        uvs = []
        faces = []
        
        with open(filepath, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                parts = line.split()
                if not parts:
                    continue
                
                if parts[0] == 'v':
                    vertices.append([float(parts[1]), float(parts[2]), float(parts[3])])
                elif parts[0] == 'vt':
                    u = float(parts[1])
                    v = float(parts[2]) if len(parts) > 2 else 0.0
                    uvs.append([u, v])
                elif parts[0] == 'vn':
                    normals.append([float(parts[1]), float(parts[2]), float(parts[3])])
                elif parts[0] == 'f':
                    face_verts = []
                    for part in parts[1:]:
                        vals = part.split('/')
                        v_idx = int(vals[0]) - 1
                        vt_idx = int(vals[1]) - 1 if len(vals) > 1 and vals[1] else 0
                        vn_idx = int(vals[2]) - 1 if len(vals) > 2 and vals[2] else -1
                        face_verts.append((v_idx, vt_idx, vn_idx))
                    
                    if len(face_verts) > 3:
                        for i in range(1, len(face_verts) - 1):
                            faces.append([face_verts[0], face_verts[i], face_verts[i+1]])
                    elif len(face_verts) == 3:
                        faces.append(face_verts)
        
        vertices = np.array(vertices, dtype=np.float32) if vertices else np.zeros((0, 3), dtype=np.float32)
        normals = np.array(normals, dtype=np.float32) if normals else np.zeros((0, 3), dtype=np.float32)
        uvs = np.array(uvs, dtype=np.float32) if uvs else np.zeros((0, 2), dtype=np.float32)
        
        if faces:
            expanded_vertices = []
            expanded_normals = []
            expanded_uvs = []
            indices = []
            
            vertex_map = {}
            next_index = 0
            
            for face in faces:
                face_indices = []
                for v_idx, vt_idx, vn_idx in face:
                    key = (v_idx, vt_idx, vn_idx)
                    if key not in vertex_map:
                        vertex_map[key] = next_index
                        expanded_vertices.append(vertices[v_idx])
                        
                        # Handle normals
                        if vn_idx >= 0 and vn_idx < len(normals):
                            expanded_normals.append(normals[vn_idx])
                        else:
                            expanded_normals.append([0.0, 0.0, 1.0])
                        
                        if vt_idx < len(uvs):
                            expanded_uvs.append(uvs[vt_idx])
                        else:
                            expanded_uvs.append([0.0, 0.0])
                        
                        next_index += 1
                    
                    face_indices.append(vertex_map[key])
                
                if len(face_indices) == 3:
                    indices.append(face_indices)
            
            vertices = np.array(expanded_vertices, dtype=np.float32)
            normals = np.array(expanded_normals, dtype=np.float32)
            uvs = np.array(expanded_uvs, dtype=np.float32)
            indices = np.array(indices, dtype=np.uint32)
            
            # Compute normals if model didn't have them
            if len(normals) > 0 and np.all(normals == [0.0, 0.0, 1.0]):
                normals = _compute_normals(vertices, indices)
        else:
            indices = np.zeros((0, 3), dtype=np.uint32)
        
        return {
            'vertices': vertices,
            'indices': indices,
            'normals': normals,
            'uvs': uvs
        }


def create_example_cube() -> dict:
    """Create a simple unit cube mesh for testing."""
    vertices = np.array([
        # Front face
        [-0.5, -0.5,  0.5], [ 0.5, -0.5,  0.5], [ 0.5,  0.5,  0.5], [-0.5,  0.5,  0.5],
        # Back face
        [ 0.5, -0.5, -0.5], [-0.5, -0.5, -0.5], [-0.5,  0.5, -0.5], [ 0.5,  0.5, -0.5],
    ], dtype=np.float32)
    
    normals = np.array([
        # Front
        [0, 0, 1], [0, 0, 1], [0, 0, 1], [0, 0, 1],
        # Back
        [0, 0, -1], [0, 0, -1], [0, 0, -1], [0, 0, -1],
    ], dtype=np.float32)
    
    uvs = np.array([
        [0, 0], [1, 0], [1, 1], [0, 1],
        [0, 0], [1, 0], [1, 1], [0, 1],
    ], dtype=np.float32)
    
    indices = np.array([
        # Front
        [0, 1, 2], [0, 2, 3],
        # Back
        [4, 5, 6], [4, 6, 7],
        # Top
        [3, 2, 6], [3, 6, 7],
        # Bottom
        [0, 4, 5], [0, 5, 1],
        # Right
        [1, 5, 6], [1, 6, 2],
        # Left
        [0, 3, 7], [0, 7, 4],
    ], dtype=np.uint32)
    
    return {
        'vertices': vertices,
        'indices': indices,
        'normals': normals,
        'uvs': uvs
    }


def load_model(path: str) -> dict:
    """Convenience function to load a model."""
    return ModelLoader.load(path)
