import numpy as np
import os


class ModelLoader:
    """Loads 3D models from various file formats."""
    
    @staticmethod
    def load(path: str) -> dict:
        """Load a 3D model and return mesh data.
        
        Returns:
            dict with keys: 'vertices', 'indices', 'normals', 'uvs'
            All as numpy arrays with appropriate dtypes.
        """
        if not os.path.exists(path):
            raise FileNotFoundError(f"Model file not found: {path}")
        
        _, ext = os.path.splitext(path.lower())
        
        if ext == '.obj':
            return ModelLoader._load_obj(path)
        elif ext in ['.gltf', '.glb']:
            # For now, raise not implemented - could add trimesh later
            raise NotImplementedError(f"Format {ext} not yet implemented")
        else:
            raise ValueError(f"Unsupported model format: {ext}")
    
    @staticmethod
    def _load_obj(filepath: str) -> dict:
        """Load Wavefront .obj file.
        
        Supports vertices (v), texture vt, normals vn, and faces f.
        Assumes faces are triangles and use format: v/vt/vn
        """
        vertices = []
        normals = []
        uvs = []
        faces = []  # Will store tuples of (v_idx, vt_idx, vn_idx)
        
        with open(filepath, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                parts = line.split()
                if not parts:
                    continue
                
                if parts[0] == 'v':  # Vertex
                    vertices.append([float(parts[1]), float(parts[2]), float(parts[3])])
                elif parts[0] == 'vt':  # Texture coordinate
                    u = float(parts[1])
                    v = float(parts[2]) if len(parts) > 2 else 0.0
                    uvs.append([u, v])
                elif parts[0] == 'vn':  # Normal
                    normals.append([float(parts[1]), float(parts[2]), float(parts[3])])
                elif parts[0] == 'f':  # Face
                    # Process triangular faces (assume triangulated)
                    face_verts = []
                    for part in parts[1:]:
                        # Handle v/vt/vn format
                        vals = part.split('/')
                        v_idx = int(vals[0]) - 1  # OBJ is 1-indexed
                        vt_idx = int(vals[1]) - 1 if len(vals) > 1 and vals[1] else 0
                        vn_idx = int(vals[2]) - 1 if len(vals) > 2 and vals[2] else 0
                        face_verts.append((v_idx, vt_idx, vn_idx))
                    
                    # Triangulate if needed (simple fan triangulation for convex polygons)
                    if len(face_verts) > 3:
                        # Create triangles from first vertex
                        for i in range(1, len(face_verts) - 1):
                            faces.append([face_verts[0], face_verts[i], face_verts[i+1]])
                    elif len(face_verts) == 3:
                        faces.append(face_verts)
        
        # Convert to arrays
        vertices = np.array(vertices, dtype=np.float32) if vertices else np.zeros((0, 3), dtype=np.float32)
        normals = np.array(normals, dtype=np.float32) if normals else np.zeros((0, 3), dtype=np.float32)
        uvs = np.array(uvs, dtype=np.float32) if uvs else np.zeros((0, 2), dtype=np.float32)
        
        # Flatten faces to indices
        if faces:
            # We need to expand our vertex arrays to account for separate v/vt/vn indices
            # For simplicity in this initial implementation, we'll just use vertex positions
            # and duplicate vertices for different normal/uv combinations
            expanded_vertices = []
            expanded_normals = []
            expanded_uvs = []
            indices = []
            
            # Map from (v_idx, vt_idx, vn_idx) to expanded vertex index
            vertex_map = {}
            next_index = 0
            
            for face in faces:
                face_indices = []
                for v_idx, vt_idx, vn_idx in face:
                    key = (v_idx, vt_idx, vn_idx)
                    if key not in vertex_map:
                        vertex_map[key] = next_index
                        # Get vertex data
                        expanded_vertices.append(vertices[v_idx])
                        
                        # Get normal if available, otherwise compute or use default
                        if vn_idx < len(normals):
                            expanded_normals.append(normals[vn_idx])
                        else:
                            # If no normal data, we'll compute later or use [0,0,1]
                            expanded_normals.append([0.0, 0.0, 1.0])
                        
                        # Get UV if available
                        if vt_idx < len(uvs):
                            expanded_uvs.append(uvs[vt_idx])
                        else:
                            expanded_uvs.append([0.0, 0.0])
                        
                        next_index += 1
                    
                    face_indices.append(vertex_map[key])
                
                # Add triangle indices
                if len(face_indices) == 3:
                    indices.append(face_indices)
            
            vertices = np.array(expanded_vertices, dtype=np.float32)
            normals = np.array(expanded_normals, dtype=np.float32)
            uvs = np.array(expanded_uvs, dtype=np.float32)
            indices = np.array(indices, dtype=np.uint32)
        else:
            indices = np.zeros((0, 3), dtype=np.uint32)
        
        return {
            'vertices': vertices,
            'indices': indices,
            'normals': normals,
            'uvs': uvs
        }


def load_model(path: str) -> dict:
    """Convenience function to load a model.
    
    Args:
        path: Path to the model file
        
    Returns:
        dict with keys: 'vertices', 'indices', 'normals', 'uvs'
    """
    return ModelLoader.load(path)