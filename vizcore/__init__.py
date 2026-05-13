"""VizCore - Real-time 3D visualization for robotics and kinematic simulation.

Core Conventions:
-----------------
- **Matrix Layout:** All matrices within Vizcore, especially for transformations (model, view, projection),
  are handled in **column-major** format. This aligns with OpenGL and GLSL standards.
- **Coordinate System:** Follows the right-handed coordinate system standard in OpenGL,
  where +X is right, +Y is up, and -Z is forward (into the screen).
"""

# Core exports
from .bus.data_bus import DataBus

# from .bus.ring_buffer import RingBuffer
# from .widget.baseWidget import BaseWidget
# from .widget.kinematicFrame import KinematicFrame
# from .widget.linePlot import LinePlot
# from .widget.dataTree import DataTree
# from .widget.logConsole import LogConsole
# from .widget.scalarGauge import ScalarGauge
# from .window.window import Window
# from .renderer.renderer import Renderer
# from .renderer.camera import Camera
# from .text.fontAtlas import FontAtlas
# from .text.texture_manager import TextureManager
# from .simulation.simulation import AttitudeControlSim
# from .simulation.simulation import Signal
# from .utils import combine_meshes, rotation_x, rotation_y, rotation_z, rotation_matrix_from_vectors
#
## Mesh loading capabilities (Phase 1)
# from .meshes import (
#    MeshRegistry,
#    load_mesh,
#    load_model,
#    ModelLoader,
#    build_arrow,
#    generate_cylinder,
#    generate_cone,
# )
#
# __version__ = "0.1.0"
# __author__ = "VizCore Team"
#
# __all__ = [
#    # Core
#    'DataBus',
#    'RingBuffer',
#    'Signal',
#    'AttitudeControlSim',
#    'BaseWidget',
#    'KinematicFrame',
#    'LinePlot',
#    'DataTree',
#    'LogConsole',
#    'ScalarGauge',
#    'Window',
#    'Renderer',
#    'Camera',
#    'FontAtlas',
#    'TextureManager',
#    'combine_meshes',
#    'rotation_x',
#    'rotation_y',
#    'rotation_z',
#    'rotation_matrix_from_vectors',
#
#    # Mesh loading (Phase 1)
#    'MeshRegistry',
#    'load_mesh',
#    'load_model',
#    'ModelLoader',
#    'build_arrow',
#    'generate_cylinder',
#    'generate_cone',
# ]
