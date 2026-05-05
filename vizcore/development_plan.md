# VizCore Development Plan

## Overview

VizCore is a real-time 3D visualization library for robotics/kinematic simulation telemetry. It decouples the simulation from visualization - the simulation runs independently and pushes data to VizCore via a DataBus. VizCore provides an empty window where users build their grid, add widgets, and attach signals dynamically.

## Current State

- ✅ Simulation runs independently, pushes data to VizCore via DataBus
- ✅ Window boots empty, user builds grid dynamically
- ✅ Signal auto-registration via `Signal` class in simulation
- ✅ Widget declares `required_shape`, GUI filters compatible signals
- ✅ `BaseWidget` as extension template

## Priorities

1. **Develop flexible base** - Create templates, classes, methods that smoothen development
2. **Build more widgets** - Simulation room for 3D models
3. **Reduce complexity** - Clean up and organize code
4. **Documentation** - Usage guides and API docs

---

## Phase 1: Flexible Base & Code Templates

**Goal:** Create a foundation that simplifies extending VizCore and supports 3D model loading.

### 1.1 Model Loader System

Create `vizcore/meshes/loader.py` with a `ModelLoader` class:

- Support formats: `.obj`, `.gltf`, `.glb` (using `trimesh` or built-in loaders)
- Method signature: `load_model(path) -> (vertices, indices, normals, uvs)`
- Fallback to existing procedural meshes (cylinder, cone, arrow)

```python
class ModelLoader:
    """Loads 3D models from various file formats."""
    
    @staticmethod
    def load(path: str) -> dict:
        """Load a 3D model and return mesh data."""
        pass
    
    @staticmethod
    def load_obj(path: str) -> tuple:
        """Load Wavefront .obj file."""
        pass
    
    @staticmethod
    def load_gltf(path: str) -> tuple:
        """Load GLTF/GLB file."""
        pass
```

### 1.2 Refactor BaseWidget

Add lifecycle methods for better widget development:

```python
class BaseWidget:
    # Existing:
    # - update()      # Called every frame BEFORE drawing
    # - draw(renderer) # Called every frame to push graphics
    # - bind_renderer(renderer)
    # - bind_camera(camera)
    # - bind_external_signal(data_bus, signal_list)
    # - required_shape
    
    # Add:
    # - on_resize(new_width, new_height)  # Called when tile is resized
    # - on_attach_signal(signal_name)     # Called when signal is bound
    # - on_detach_signal(signal_name)     # Called when signal is removed
    # - get_context_menu(x, y)            # Already exists - good
    # - on_context_menu(action)            # Already exists - good
```

### 1.3 Mesh Abstraction Layer

Create `vizcore/meshes/registry.py` - a registry for mesh factories:

```python
class MeshRegistry:
    """Central registry for mesh loaders and generators."""
    
    _generators = {}
    _loaders = {}
    
    @classmethod
    def register_generator(cls, name: str, generator_func):
        """Register a procedural mesh generator."""
        cls._generators[name] = generator_func
    
    @classmethod
    def register_loader(cls, extension: str, loader_func):
        """Register a file format loader."""
        cls._loaders[extension] = loader_func
    
    @classmethod
    def get_mesh(cls, source):
        """Get mesh data from generator name or file path."""
        pass
```

Allows widgets to request "arrow" mesh without knowing if it's procedural or loaded:
```python
verts, inds = MeshRegistry.get_mesh("arrow")
verts, inds = MeshRegistry.get_mesh("models/drone.obj")
```

### 1.4 Renderer Abstraction

Add helper methods to `Renderer` class:

```python
class Renderer:
    # Existing methods...
    
    # Add:
    def draw_mesh(self, mesh_name: str, transform: np.ndarray, **kwargs):
        """Draw a mesh with a transformation matrix."""
        pass
    
    def draw_instanced(self, mesh_name: str, transforms: list, **kwargs):
        """Draw multiple instances of a mesh."""
        pass
    
    def set_light(self, direction: tuple, color: tuple):
        """Set directional light for 3D rendering."""
        pass
```

---

## Phase 2: Simulation Room Widget

**Goal:** A widget that displays imported 3D models moving in 3D space based on simulation data.

### 2.1 SimulationRoom Widget

```python
class SimulationRoom(BaseWidget):
    """
    A 3D scene widget for displaying moving models.
    
    Features:
    - Load 3D models (.obj, .gltf, .glb)
    - Track position/rotation signals for each model
    - Support multiple objects in scene
    - Basic lighting (directional + ambient)
    - Camera controls (orbit, pan, zoom)
    """
    
    def __init__(self, max_objects: int = 10, **kwargs):
        super().__init__(**kwargs)
        self.objects = []
        self.max_objects = max_objects
    
    def load_model(self, name: str, path: str):
        """Load a 3D model into the scene."""
        pass
    
    def bind_signal(self, object_name: str, position_signal: str, rotation_signal: str = None):
        """Bind signals to control object transform."""
        pass
    
    @property
    def required_shape(self):
        return [(3,)]  # Accepts 3D position vectors
```

### 2.2 Scene Graph System

Create `vizcore/scene/scene.py`:

```python
class SceneObject:
    """A single object in the 3D scene."""
    
    def __init__(self, name: str, mesh_data: dict):
        self.name = name
        self.mesh = mesh_data
        self.position = np.array([0, 0, 0], dtype='f4')
        self.rotation = np.array([0, 0, 0], dtype='f4')  # Euler angles
        self.scale = np.array([1, 1, 1], dtype='f4')
        self.color = np.array([1, 1, 1], dtype='f4')
        self.parent = None
        self.children = []
    
    def update_transform(self):
        """Calculate world transform from local transform."""
        pass


class Scene:
    """Manages a collection of SceneObjects."""
    
    def __init__(self):
        self.objects = {}  # name -> SceneObject
    
    def add_object(self, obj: SceneObject):
        """Add an object to the scene."""
        pass
    
    def remove_object(self, name: str):
        """Remove an object from the scene."""
        pass
    
    def get_object(self, name: str) -> SceneObject:
        """Get an object by name."""
        pass
    
    def update(self, data_bus):
        """Update all objects from data bus signals."""
        pass
```

### 2.3 Signal Binding for Objects

Each model binds to position/rotation signals:
- `drone.position` → vec3 position
- `drone.rotation` → vec3 euler angles
- Auto-detect object name from signal path

```python
# In simulation, signals are pushed:
sim.position = [1.0, 2.0, 3.0]
sim.rotation = [0.1, 0.2, 0.0]

# In VizCore, binds to SimulationRoom:
room.bind_signal("drone", "position", "rotation")
```

### 2.4 Interactive Object Placement

Support for drag-and-drop in editor mode:

```python
class SimulationRoom:
    def on_mouse_drag(self, x, y, dx, dy, buttons, modifiers):
        """Handle object selection and movement in editor mode."""
        pass
    
    def set_edit_mode(self, enabled: bool):
        """Enable/disable object placement mode."""
        pass
    
    def add_placement_object(self, name: str, path: str):
        """Add an object that can be placed (e.g., gate, ring)."""
        pass
```

---

## Phase 3: Simplified Rendering Pipeline

**Goal:** Create a simple, standalone rendering approach that works reliably before adding complexity.

### 3.1 Simple OBJ Viewer

Create a minimal implementation that:
- Opens a ModernGL window directly (not through the complex Window class)
- Loads an OBJ file using `ModelLoader`
- Renders the mesh with basic camera controls
- Uses left-click drag for orbit rotation
- Uses mouse wheel for zoom

**Target file:** `vizcore/simple_viewer.py`

```python
import moderngl
import pyglet
from vizcore.meshes import load_mesh

# Simple standalone viewer - no complex Window class needed
class SimpleViewer(pyglet.window.Window):
    def __init__(self):
        super().__init__(1024, 768, "Simple OBJ Viewer")
        self.ctx = moderngl.create_context()
        self.ctx.enable(moderngl.DEPTH_TEST)
        
        # Load a model
        self.mesh_data = load_mesh('test_models/test_cube.obj')
        
        # Camera state
        self.camera_orbit_y = 0.0
        self.camera_distance = 5.0
    
    def on_mouse_drag(self, dx, dy, buttons, modifiers):
        # Left click drag to orbit
        if buttons & pyglet.window.mouse.LEFT:
            self.camera_orbit_y += dx * 0.01
    
    def on_mouse_scroll(self, scroll_y):
        # Mouse wheel to zoom
        self.camera_distance -= scroll_y * 0.5
        self.camera_distance = max(1.0, min(20.0, self.camera_distance))
    
    def on_draw(self):
        self.clear()
        # Render mesh with MVP from camera_orbit_y and camera_distance
        ...

if __name__ == '__main__':
    SimpleViewer().run()
```

### 3.2 Why This Approach

- Directly tests the rendering pipeline without Window class overhead
- Simpler debugging - less abstraction between ModernGL and the code
- Can be run standalone: `python -m vizcore.simple_viewer`
- Validates mouse input handling before integrating into widget

### 3.3 Success Criteria

- [ ] Opens window and displays OBJ mesh
- [ ] Left-click drag rotates camera around vertical axis
- [ ] Mouse wheel zooms in/out
- [ ] Works reliably before adding to vizcore package

### 3.4 Later: Integrate into SimulationRoom

Once this works, copy the approach to:
- Make SimulationRoom use this simpler mouse handling pattern
- Add to main vizcore package

---

## Phase 4: Reduce Complexity (Original)

**Goal:** Clean up the codebase, remove duplication, improve readability.

### 3.1 Code Organization

Proposed structure:

```
vizcore/
├── __init__.py              # Main API exports (public classes only)
├── core/                    # Core systems
│   ├── __init__.py
│   ├── data_bus.py
│   ├── signal.py            # Signal descriptor class
│   └── scene.py            # Scene graph (NEW)
├── rendering/
│   ├── __init__.py
│   ├── renderer.py
│   ├── camera.py
│   ├── shader_manager.py
│   ├── buffer_allocator.py
│   ├── meshes/
│   │   ├── __init__.py
│   │   ├── __init__.py      # Exports: generate_cylinder, generate_cone, etc.
│   │   ├── loader.py       # NEW: 3D model loading
│   │   ├── registry.py     # NEW: mesh registry
│   │   ├── arrow.py
│   │   ├── cylinder.py
│   │   └── cone.py
│   └── shaders/
│       ├── ui.vert
│       ├── ui.frag
│       └── ...
├── widgets/
│   ├── __init__.py
│   ├── base.py             # BaseWidget (refactored)
│   ├── kinematic_frame.py
│   ├── line_plot.py
│   ├── data_tree.py
│   ├── log_console.py
│   ├── scalar_gauge.py
│   └── simulation_room.py   # NEW
├── window/
│   ├── __init__.py
│   ├── window.py
│   ├── tile.py
│   └── mainloop.py
└── text/
    ├── __init__.py
    ├── font_atlas.py
    └── texture_manager.py
```

### 3.2 Refactor WidgetManager

Make `WidgetManager` actually useful:

```python
class WidgetManager:
    """Manages multiple widgets, their data buses, and rendering."""
    
    def __init__(self):
        self.widgets = []
        self.data_buses = {}
    
    def add_widget(self, widget, data_bus=None):
        """Add a widget to the manager."""
        self.widgets.append(widget)
        if data_bus:
            self.data_buses[id(widget)] = data_bus
    
    def remove_widget(self, widget):
        """Remove a widget by instance."""
        if widget in self.widgets:
            self.widgets.remove(widget)
    
    def get_widget(self, widget_type):
        """Get first widget of a specific type."""
        for w in self.widgets:
            if isinstance(w, widget_type):
                return w
    
    def find_by_type(self, widget_type):
        """Get all widgets of a specific type."""
        return [w for w in self.widgets if isinstance(w, widget_type)]
    
    def update(self):
        """Update all widgets."""
        for widget in self.widgets:
            if hasattr(widget, 'update'):
                widget.update()
    
    def render(self, renderer):
        """Render all widgets."""
        for widget in self.widgets:
            if hasattr(widget, 'draw'):
                widget.draw(renderer)
```

### 3.3 Shader Standardization

- Standardize vertex shader inputs across 3D widgets
- Create common lighting shader for 3D widgets
- Unify MVP matrix handling

---

## Phase 4: Documentation

### 4.1 API Documentation

Document each public class/method in docstring format (Google/NumPy style).

### 4.2 Usage Guides

Create `docs/` directory:

```
docs/
├── README.md              # Overview
├── getting_started.md     # Basic usage
├── widget_development.md  # Creating custom widgets
├── simulation_integration.md  # Connecting your sim to VizCore
└── api_reference.md      # Auto-generated API docs
```

### 4.3 Examples

Create `examples/` directory:

```
examples/
├── minimal_example.py     # Minimal VizCore usage
├── drone_telemetry.py     # Full drone simulation example
├── custom_widget.py       # Creating a custom widget
└── model_viewer.py        # Loading and viewing 3D models
```

---

## Phase 5: Pip-Installable Package

### 5.1 Package Structure

```
vizcore/
├── pyproject.toml
├── setup.py               # Or use pyproject.toml only
├── README.md
├── LICENSE
├── vizcore/              # Main package
│   └── ...
└── tests/
    └── ...
```

### 5.2 Dependencies

```toml
[project]
name = "vizcore"
version = "0.1.0"
dependencies = [
    "moderngl",
    "pyglet",
    "numpy",
]

[project.optional-dependencies]
all = [
    "trimesh",  # For GLTF/GLB loading
]
```

---

## Implementation Order

1. **Start with Phase 1** (Flexible Base):
   - Model loader system
   - Mesh registry
   - BaseWidget enhancements
   - Renderer helpers

2. **Then Phase 2** (Simulation Room):
   - Scene graph
   - SimulationRoom widget
   - Signal binding
   - Interactive placement

3. **Then Phase 3** (Reduce Complexity):
   - Code reorganization
   - WidgetManager refactor
   - Shader cleanup

4. **Then Phase 4** (Documentation):
   - API docs
   - Usage guides
   - Examples

5. **Finally Phase 5** (Pip Package):
   - Package structure
   - Publish to PyPI

---

## Notes

- **3D Model Formats:** Start with OBJ support (easiest), add GLTF/GLB later
- **Trimesh:** Optional dependency - use built-in OBJ loader for simplicity initially
- **Existing Code:** Keep all current widgets, just reorganize
- **Backwards Compatibility:** Maintain existing API during refactoring