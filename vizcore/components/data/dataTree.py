import moderngl
import numpy as np
import os
import pyglet

from vizcore.components.base.baseWidget import BaseWidget

class DataTree(BaseWidget):
    """
    A recursive UI tree component to visualize the entire simulation hierarchy
    straight from the DataBus. It displays all nested branches and dynamically 
    renders scalar and vector leaves nicely. 
    """
    def __init__(self, rect=None):
        super().__init__(rect)
        self.channels = 0 
        self.expanded_nodes = set()  # Store node paths that are collapsed (inverted logic)
        self.scroll_y = 0.0
        self.scroll_x = 0.0
        self.zoom = 1.0

        self.base_font_scale = 0.3
        self.base_box_width = 180
        self.base_box_height = 50
        self.base_padding_x = 40
        self.base_padding_y = 80
        
        self.font_scale = self.base_font_scale
        self.box_width = self.base_box_width
        self.box_height = self.base_box_height
        self.padding_x = self.base_padding_x
        self.padding_y = self.base_padding_y
        
        self.colors = {
            "branch": (0.2, 0.2, 0.25, 1.0),
            "leaf": (0.15, 0.15, 0.2, 1.0),
            "border": (0.5, 0.5, 0.6, 1.0),
            "text": (0.9, 0.9, 0.9, 1.0),
            "val": (0.6, 0.9, 0.6, 1.0),
            "line": (0.4, 0.4, 0.5, 1.0)
        }

        self.node_positions = {}  # path -> (x, y, name, is_branch)
        self.node_hitboxes = {}  # path -> (x, y, w, h)
        self.lines_to_draw = []

    @property
    def required_shape(self) -> list:
        return None

    def accepts_signal(self, data_bus, signal_name) -> bool:
        return True

    def bind_external_signal(self, data_bus, signal: list):
        self.data_bus = data_bus

    def bind_renderer(self, renderer):
        self._renderer = renderer
        self._text_renderer = getattr(renderer, 'text_renderer', None)
        
        # Load custom shaders from root shaders folder
        vizcore_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        shader_dir = os.path.join(vizcore_root, 'shaders')
        
        with open(os.path.join(shader_dir, 'datatree_box.vert'), 'r') as f:
            v_src = f.read()
        with open(os.path.join(shader_dir, 'datatree_box.frag'), 'r') as f:
            f_src = f.read()
        self.prog_box = renderer.ctx.program(vertex_shader=v_src, fragment_shader=f_src)
        
        with open(os.path.join(shader_dir, 'datatree_line.vert'), 'r') as f:
            v_src = f.read()
        with open(os.path.join(shader_dir, 'datatree_line.frag'), 'r') as f:
            f_src = f.read()
        self.prog_line = renderer.ctx.program(vertex_shader=v_src, fragment_shader=f_src)

        # Quad VBO for box drawing
        quad = np.array([
            0.0, 0.0,
            1.0, 0.0,
            0.0, 1.0,
            1.0, 1.0
        ], dtype='f4')
        self.vbo_quad = renderer.ctx.buffer(quad)
        self.vao_box = renderer.ctx.simple_vertex_array(self.prog_box, self.vbo_quad, 'in_vert')

    def bind_camera(self, camera):
        self.camera = camera

    @property
    def use_camera(self) -> bool:
        return True

    def get_camera_config(self) -> dict:
        return {
            "eye": np.array([0.0, 0.0, 1.0], dtype=np.float32),
            "target": np.array([0.0, 0.0, 0.0], dtype=np.float32),
            "fov_y_deg": 45,
            "enable_keyboard": False,
            "near": 0.01,
            "far": 100.0,
        }

    def on_mouse_press(self, local_x, local_y, button, modifiers):
        if button == pyglet.window.mouse.LEFT:
            for path, (x, y, w, h) in self.node_hitboxes.items():
                if x <= local_x <= x + w and y <= local_y <= y + h:
                    pos_info = self.node_positions.get(path)
                    if pos_info and pos_info[3]: # is_branch
                        if path in self.expanded_nodes:
                            self.expanded_nodes.remove(path)
                        else:
                            self.expanded_nodes.add(path)
                        break
                    
    def on_mouse_drag(self, local_x, local_y, dx, dy, buttons, modifiers):
        if buttons & pyglet.window.mouse.LEFT:
            self.scroll_x += dx
            self.scroll_y += dy
            
    def on_mouse_scroll(self, local_x, local_y, scroll_x, scroll_y):
        # Adjust zoom factor
        zoom_speed = 1.1
        if scroll_y > 0:
            self.zoom *= zoom_speed
        elif scroll_y < 0:
            self.zoom /= zoom_speed
            
        # Clamp zoom to prevent math errors or blowing up the tree
        self.zoom = max(0.1, min(self.zoom, 5.0))
        
        # Apply scaled geometry parameters
        self.font_scale = self.base_font_scale * self.zoom
        self.box_width = self.base_box_width * self.zoom
        self.box_height = self.base_box_height * self.zoom
        self.padding_x = self.base_padding_x * self.zoom
        self.padding_y = self.base_padding_y * self.zoom

    def update(self):
        pass

    def _build_tree(self):
        """Build hierarchical tree from flat signal names."""
        signals = self.data_bus.list_signals()
        excluded_channels = {"INFO", "WARN", "ERROR", "DEBUG"}
        
        tree = {}
        for sig in sorted(signals):
            if sig in excluded_channels:
                continue
                
            parts = sig.split('.')
            curr = tree
            for part in parts[:-1]:
                if part not in curr:
                    curr[part] = {}
                curr = curr[part]
            curr[parts[-1]] = sig  # Leaf holds the full signal name
        return tree

    def _compute_subtree_layout(self, node, path, depth):
        """
        Recursively compute layout for each subtree.
        Returns (width, layout_info) where layout_info contains positioning data.
        """
        is_collapsed = path in self.expanded_nodes
        is_branch = isinstance(node, dict)
        
        # Base case: leaf or collapsed branch
        if not is_branch or is_collapsed:
            return self.box_width, {
                'path': path,
                'node': node,
                'is_branch': is_branch,
                'depth': depth,
                'x_offset': 0,  # Will be set by parent
                'children': []
            }
        
        # Recursive case: expanded branch
        children_layouts = []
        total_width = 0
        
        for key, child_node in node.items():
            child_path = f"{path}.{key}" if path else key
            child_width, child_layout = self._compute_subtree_layout(child_node, child_path, depth + 1)
            children_layouts.append((key, child_width, child_layout))
            total_width += child_width
        
        # Add padding between children
        if children_layouts:
            total_width += self.padding_x * (len(children_layouts) - 1)
        
        # Parent width is max of own width and children width
        width = max(self.box_width, total_width)
        
        return width, {
            'path': path,
            'node': node,
            'is_branch': is_branch,
            'depth': depth,
            'x_offset': 0,
            'children': children_layouts,
            'total_width': total_width
        }

    def _assign_positions(self, layout_info, base_x, base_y):
        """
        Assign absolute (x, y) positions to all nodes and generate connection lines.
        """
        path = layout_info['path']
        depth = layout_info['depth']
        is_branch = layout_info['is_branch']
        node = layout_info['node']
        
        # Calculate this node's Y position
        y = base_y - depth * (self.box_height + self.padding_y)
        
        # If this node has children, center it above them
        if layout_info['children']:
            total_width = layout_info['total_width']
            # Position this node centered above children
            x = base_x + (total_width - self.box_width) / 2
            
            # Position children left to right
            child_x = base_x
            for key, child_width, child_layout in layout_info['children']:
                # Center child within its allocated width
                child_base_x = child_x + (child_width - self.box_width) / 2
                self._assign_positions(child_layout, child_x, base_y)
                
                # Draw line from this node to child
                child_y = y - (self.box_height + self.padding_y)
                self.lines_to_draw.append((
                    x + self.box_width / 2, y,  # Parent bottom center
                    child_base_x + self.box_width / 2, child_y + self.box_height  # Child top center
                ))
                
                child_x += child_width + self.padding_x
        else:
            # Leaf node or collapsed branch
            x = base_x
        
        # Store position and hitbox
        self.node_positions[path] = (x, y, path.split('.')[-1], is_branch, node)
        self.node_hitboxes[path] = (x, y, self.box_width, self.box_height)

    def draw_lines(self, renderer):
        """Draw connector lines between nodes."""
        pass  # Lines drawn in draw() method with boxes

    def draw_text(self, renderer):
        """Draw text labels on nodes."""
        pass  # Text drawn in draw() method with boxes

    def draw(self, renderer):
        if not hasattr(self, 'data_bus') or not self.data_bus:
            return

        # Build tree structure
        tree = self._build_tree()
        
        # Reset positioning data
        self.node_positions = {}
        self.node_hitboxes = {}
        self.lines_to_draw = []
        
        # Wrap tree in root node
        if not tree:
            return
            
        # Compute layout (single root, no double-wrapping)
        total_width, root_layout = self._compute_subtree_layout(
            tree, "Root", 0
        )
        
        # Calculate starting position (centered horizontally, near top)
        if not self.camera:
            return
            
        start_x = (self.camera.width - total_width) / 2 + self.scroll_x
        start_y = self.camera.height - 50 * self.zoom + self.scroll_y
        
        # Assign absolute positions
        self._assign_positions(root_layout, start_x, start_y)
        
        # Render
        renderer.ctx.disable(moderngl.DEPTH_TEST)
        renderer.ctx.enable(moderngl.BLEND)
        renderer.ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA
        
        self._render_lines(renderer)
        self._render_nodes(renderer)
        self._render_triangles(renderer)
        
        renderer.ctx.disable(moderngl.BLEND)
        renderer.ctx.enable(moderngl.DEPTH_TEST)

    def _ortho_matrix(self):
        """Create orthographic projection matrix for 2D rendering."""
        if not self.camera:
            return np.eye(4, dtype='f4')
            
        w, h = self.camera.width, self.camera.height
        # Transform from pixel coords to NDC
        return np.array([
            [2.0/w, 0, 0, -1.0],
            [0, 2.0/h, 0, -1.0],
            [0, 0, -1.0, 0],
            [0, 0, 0, 1.0]
        ], dtype='f4').T

    def _to_text_space_y(self, world_y_from_bottom):
        """Convert bottom-origin widget Y to TextRenderer top-origin Y."""
        if not self.camera:
            return world_y_from_bottom
        return self.camera.height - world_y_from_bottom
        
    def _render_lines(self, renderer):
        """Render connection lines between nodes."""
        if not self.lines_to_draw: 
            return
        
        # Build line segments with smooth curves
        pts = []
        for x1, y1, x2, y2 in self.lines_to_draw:
            # Vertical line from parent down
            mid_y = (y1 + y2) / 2
            pts.extend([x1, y1, x1, mid_y])
            # Horizontal line across
            pts.extend([x1, mid_y, x2, mid_y])
            # Vertical line to child
            pts.extend([x2, mid_y, x2, y2])
            
        vbo = renderer.ctx.buffer(np.array(pts, dtype='f4'))
        vao = renderer.ctx.simple_vertex_array(self.prog_line, vbo, 'in_vert')
        
        self.prog_line['color'].value = self.colors["line"]
        mvp = self._ortho_matrix()
        self.prog_line['mvp'].write(mvp.tobytes())
        
        vao.render(moderngl.LINES)
        vbo.release()

    def _render_nodes(self, renderer):
        """Render all node boxes and labels."""
        mvp = self._ortho_matrix()
        self.prog_box['mvp'].write(mvp.tobytes())
        self.prog_box['u_size'].value = (self.box_width, self.box_height)
        self.prog_box['u_radius'].value = 8.0
        self.prog_box['u_border_width'].value = 2.0
        self.prog_box['u_border_color'].value = self.colors["border"]
        
        for path, (x, y, name, is_branch, node) in self.node_positions.items():
            # Skip if outside viewport
            if not self.camera:
                continue
            if y + self.box_height < 0 or y > self.camera.height:
                continue
                
            # Draw box background
            model = np.array([
                [1, 0, 0, 0],
                [0, 1, 0, 0],
                [0, 0, 1, 0],
                [x, y, 0, 1]
            ], dtype='f4')
            final_mvp = model @ mvp
            self.prog_box['mvp'].write(final_mvp.tobytes())
            
            self.prog_box['u_color'].value = self.colors["branch"] if is_branch else self.colors["leaf"]
            self.vao_box.render(moderngl.TRIANGLE_STRIP)
            
            # Draw name
            text_x = x + 10 * self.zoom
            
            if is_branch:
                name_world_y = y + self.box_height * 0.58
                text_y = self._to_text_space_y(name_world_y)
                if self._text_renderer:
                    self._text_renderer.render_text(name, text_x, text_y, color=self.colors["text"][:3], scale=self.font_scale)
            else:
                name_world_y = y + self.box_height * 0.72
                text_y = self._to_text_space_y(name_world_y)
                if self._text_renderer:
                    self._text_renderer.render_text(name, text_x, text_y, color=self.colors["text"][:3], scale=self.font_scale)
            
            # Draw value for leaf nodes
            if not is_branch:
                latest = self.data_bus.latest(node)
                if latest is not None:
                    if isinstance(latest, np.ndarray):
                        val_str = np.array2string(latest, precision=2, separator=',', suppress_small=True)
                    elif isinstance(latest, float):
                        val_str = f"{latest:.2f}"
                    else:
                        val_str = str(latest)
                    
                    val_world_y = y + self.box_height * 0.35
                    val_y = self._to_text_space_y(val_world_y)
                    if self._text_renderer:
                        self._text_renderer.render_text(val_str, text_x, val_y, color=self.colors["val"][:3], scale=self.font_scale * 0.8)

    def _render_triangles(self, renderer):
        """Render explicit toggle triangles for branches."""
        pts = []
        for path, (x, y, name, is_branch, node) in self.node_positions.items():
            if not is_branch:
                continue
            
            if not self.camera:
                continue
            if y + self.box_height < 0 or y > self.camera.height:
                continue
                
            is_collapsed = path in self.expanded_nodes
            tx = x + self.box_width - 15 * self.zoom  # 15px from right edge
            ty = y + self.box_height / 2
            
            # Draw a filled triangle using 3 vertices
            s = 6 * self.zoom # Size
            
            if is_collapsed:
                # Right-pointing filled triangle
                pts.extend([
                    tx - s, ty + s,
                    tx - s, ty - s,
                    tx + s, ty
                ])
            else:
                # Down-pointing filled triangle
                pts.extend([
                    tx - s, ty + s,
                    tx + s, ty + s,
                    tx, ty - s
                ])
                
        if not pts:
            return
            
        vbo = renderer.ctx.buffer(np.array(pts, dtype='f4'))
        vao = renderer.ctx.simple_vertex_array(self.prog_line, vbo, 'in_vert')
        
        self.prog_line['color'].value = (0.8, 0.8, 0.8, 1.0)
        mvp = self._ortho_matrix()
        self.prog_line['mvp'].write(mvp.tobytes())
        
        vao.render(moderngl.TRIANGLES)
        vbo.release()

    def resize(self, rect):
        super().resize(rect)