"""
Regression tests for DrawingContext lifecycle.

Characterizes GPU resource management BEFORE refactoring:
- Shader/VBO/VAO lifecycle
- Uniform setting in quad()/outline()
- VAO caching behavior
- Class-level resource sharing between instances

Uses headless ModernGL context (same pattern as test_widget_integration.py).
"""

import sys
import os
import unittest
from types import SimpleNamespace

# ------------------------------------------------------------------
# Path setup
# ------------------------------------------------------------------
_WORKSPACE_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_TEST_FOLDER = os.path.join(_WORKSPACE_ROOT, "test_folder")

if _WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, _WORKSPACE_ROOT)
if _TEST_FOLDER not in sys.path:
    sys.path.insert(0, _TEST_FOLDER)

import moderngl

from widgets.widget_base import DrawingContext


class MockRenderer:
    """Minimal renderer stand-in providing ctx and wnd."""

    def __init__(self, ctx):
        self.ctx = ctx
        self.wnd = SimpleNamespace(size=(1280, 720), width=1280, height=720)


class TestDrawingContextInit(unittest.TestCase):
    """Test DrawingContext.__init__() creates GPU resources."""

    @classmethod
    def setUpClass(cls):
        """Create a single headless ModernGL context shared across tests."""
        cls._headless_ctx = moderngl.create_standalone_context()
        # Ensure we have a valid viewport
        cls._headless_ctx.viewport = (0, 0, 1280, 720)

    def setUp(self):
        """Reset class-level shared state before each test."""
        # Force re-initialization for isolated tests
        DrawingContext._initialized = False
        DrawingContext._ui_program = None
        DrawingContext._quad_vbo = None
        DrawingContext._outline_vbo = None
        DrawingContext._quad_vao = None
        DrawingContext._outline_vao = None

        self.renderer = MockRenderer(self._headless_ctx)

    def test_init_creates_shader_program(self):
        """DrawingContext.__init__() creates the UI shader program."""
        ctx = DrawingContext(self.renderer, 400, 300)

        self.assertIsNotNone(DrawingContext._ui_program)
        self.assertIsInstance(DrawingContext._ui_program, moderngl.Program)

    def test_init_creates_vbos(self):
        """DrawingContext.__init__() creates quad and outline VBOs."""
        ctx = DrawingContext(self.renderer, 400, 300)

        self.assertIsNotNone(DrawingContext._quad_vbo)
        self.assertIsNotNone(DrawingContext._outline_vbo)
        self.assertIsInstance(DrawingContext._quad_vbo, moderngl.Buffer)
        self.assertIsInstance(DrawingContext._outline_vbo, moderngl.Buffer)

    def test_init_creates_vaos(self):
        """DrawingContext.__init__() creates quad and outline VAOs."""
        ctx = DrawingContext(self.renderer, 400, 300)

        self.assertIsNotNone(DrawingContext._quad_vao)
        self.assertIsNotNone(DrawingContext._outline_vao)
        self.assertIsInstance(DrawingContext._quad_vao, moderngl.VertexArray)
        self.assertIsInstance(DrawingContext._outline_vao, moderngl.VertexArray)

    def test_init_only_once_despite_multiple_instances(self):
        """_init_shared() runs only once (guarded by _initialized flag)."""
        ctx1 = DrawingContext(self.renderer, 400, 300)
        original_program = DrawingContext._ui_program
        original_quad_vbo = DrawingContext._quad_vbo

        ctx2 = DrawingContext(self.renderer, 400, 300)

        # Resources should be the same object (not re-created)
        self.assertIs(DrawingContext._ui_program, original_program)
        self.assertIs(DrawingContext._quad_vbo, original_quad_vbo)


class TestDrawingContextSharedResources(unittest.TestCase):
    """Test class-level resource sharing between DrawingContext instances."""

    @classmethod
    def setUpClass(cls):
        cls._headless_ctx = moderngl.create_standalone_context()
        cls._headless_ctx.viewport = (0, 0, 1280, 720)

    def setUp(self):
        DrawingContext._initialized = False
        DrawingContext._ui_program = None
        DrawingContext._quad_vbo = None
        DrawingContext._outline_vbo = None
        DrawingContext._quad_vao = None
        DrawingContext._outline_vao = None

    def test_multiple_instances_share_shader_program(self):
        """Multiple DrawingContext instances share the same shader program (class-level)."""
        renderer1 = MockRenderer(self._headless_ctx)
        renderer2 = MockRenderer(self._headless_ctx)

        ctx1 = DrawingContext(renderer1, 400, 300)
        ctx2 = DrawingContext(renderer2, 400, 300)

        self.assertIs(DrawingContext._ui_program, ctx1._ui_program)
        self.assertIs(DrawingContext._ui_program, ctx2._ui_program)
        self.assertIs(ctx1._ui_program, ctx2._ui_program)

    def test_multiple_instances_share_vbos(self):
        """Multiple DrawingContext instances share the same VBOs."""
        renderer1 = MockRenderer(self._headless_ctx)
        renderer2 = MockRenderer(self._headless_ctx)

        ctx1 = DrawingContext(renderer1, 400, 300)
        ctx2 = DrawingContext(renderer2, 400, 300)

        self.assertIs(DrawingContext._quad_vbo, ctx1._quad_vbo)
        self.assertIs(DrawingContext._quad_vbo, ctx2._quad_vbo)

    def test_multiple_instances_share_vaos(self):
        """Multiple DrawingContext instances share the same VAOs."""
        renderer1 = MockRenderer(self._headless_ctx)
        renderer2 = MockRenderer(self._headless_ctx)

        ctx1 = DrawingContext(renderer1, 400, 300)
        ctx2 = DrawingContext(renderer2, 400, 300)

        self.assertIs(DrawingContext._quad_vao, ctx1._quad_vao)
        self.assertIs(DrawingContext._quad_vao, ctx2._quad_vao)


class TestDrawingContextVAOCaching(unittest.TestCase):
    """Test VAO caching: VAOs should be created once, not per call."""

    @classmethod
    def setUpClass(cls):
        cls._headless_ctx = moderngl.create_standalone_context()
        cls._headless_ctx.viewport = (0, 0, 1280, 720)

    def setUp(self):
        DrawingContext._initialized = False
        DrawingContext._ui_program = None
        DrawingContext._quad_vbo = None
        DrawingContext._outline_vbo = None
        DrawingContext._quad_vao = None
        DrawingContext._outline_vao = None

        self.renderer = MockRenderer(self._headless_ctx)
        self.ctx = DrawingContext(self.renderer, 400, 300)

    def test_vaos_not_recreated_on_second_init(self):
        """_init_shared() does not recreate VAOs when called again."""
        quad_vao_before = DrawingContext._quad_vao
        outline_vao_before = DrawingContext._outline_vao

        # Simulate second init attempt (should be no-op due to _initialized flag)
        DrawingContext._init_shared(self._headless_ctx)

        self.assertIs(DrawingContext._quad_vao, quad_vao_before)
        self.assertIs(DrawingContext._outline_vao, outline_vao_before)

    def test_vao_identity_preserved_after_quad_calls(self):
        """The same VAO object is used across multiple quad() calls."""
        quad_vao_before = DrawingContext._quad_vao

        # Call quad() multiple times
        self.ctx.quad(10, 20, 100, 50, color=(1, 0, 0))
        self.ctx.quad(50, 60, 80, 40, color=(0, 1, 0))
        self.ctx.quad(200, 150, 60, 30, color=(0, 0, 1))

        self.assertIs(DrawingContext._quad_vao, quad_vao_before)


class TestDrawingContextUniformSetting(unittest.TestCase):
    """Test that quad() sets all uniforms correctly before rendering."""

    @classmethod
    def setUpClass(cls):
        cls._headless_ctx = moderngl.create_standalone_context()
        cls._headless_ctx.viewport = (0, 0, 1280, 720)

    def setUp(self):
        DrawingContext._initialized = False
        DrawingContext._ui_program = None
        DrawingContext._quad_vbo = None
        DrawingContext._outline_vbo = None
        DrawingContext._quad_vao = None
        DrawingContext._outline_vao = None

        self.renderer = MockRenderer(self._headless_ctx)
        self.ctx = DrawingContext(self.renderer, 400, 300)

    def test_quad_sets_u_resolution(self):
        """quad() sets u_resolution uniform to widget dimensions."""
        self.ctx.quad(0, 0, 100, 50)

        prog = DrawingContext._ui_program
        u_res = prog["u_resolution"].value
        self.assertEqual(u_res, (400, 300))

    def test_quad_sets_u_pos_with_offset(self):
        """quad() sets u_pos incorporating offset_x and offset_y."""
        ctx_with_offset = DrawingContext(self.renderer, 400, 300, offset_x=10, offset_y=20)
        ctx_with_offset.quad(5, 5, 50, 50)

        prog = DrawingContext._ui_program
        u_pos = prog["u_pos"].value
        # Should include the offset: 10 + 5 = 15, 20 + 5 = 25
        self.assertEqual(u_pos, (15, 25))

    def test_quad_sets_u_size(self):
        """quad() sets u_size to the rectangle dimensions."""
        self.ctx.quad(10, 20, 150, 75)

        prog = DrawingContext._ui_program
        u_size = prog["u_size"].value
        self.assertEqual(u_size, (150, 75))

    def test_quad_sets_u_color_with_alpha(self):
        """quad() sets u_color including alpha channel."""
        self.ctx.quad(0, 0, 100, 50, color=(0.25, 0.5, 0.75), alpha=0.8)

        prog = DrawingContext._ui_program
        u_color = prog["u_color"].value
        self.assertAlmostEqual(u_color[0], 0.25, places=5)
        self.assertAlmostEqual(u_color[1], 0.5, places=5)
        self.assertAlmostEqual(u_color[2], 0.75, places=5)
        self.assertAlmostEqual(u_color[3], 0.8, places=5)


class TestDrawingContextUniformIsolation(unittest.TestCase):
    """Test that uniform values don't leak between consecutive quad() calls."""

    @classmethod
    def setUpClass(cls):
        cls._headless_ctx = moderngl.create_standalone_context()
        cls._headless_ctx.viewport = (0, 0, 1280, 720)

    def setUp(self):
        DrawingContext._initialized = False
        DrawingContext._ui_program = None
        DrawingContext._quad_vbo = None
        DrawingContext._outline_vbo = None
        DrawingContext._quad_vao = None
        DrawingContext._outline_vao = None

        self.renderer = MockRenderer(self._headless_ctx)
        self.ctx = DrawingContext(self.renderer, 400, 300)

    def test_consecutive_quad_calls_set_different_positions(self):
        """Each quad() call overwrites u_pos with new values."""
        self.ctx.quad(10, 20, 50, 50, color=(1, 0, 0))
        prog = DrawingContext._ui_program
        pos_after_first = prog["u_pos"].value

        self.ctx.quad(100, 200, 50, 50, color=(0, 1, 0))
        pos_after_second = prog["u_pos"].value

        self.assertEqual(pos_after_first, (10, 20))
        self.assertEqual(pos_after_second, (100, 200))

    def test_consecutive_quad_calls_set_different_sizes(self):
        """Each quad() call overwrites u_size with new values."""
        self.ctx.quad(0, 0, 50, 50)
        prog = DrawingContext._ui_program
        size_after_first = prog["u_size"].value

        self.ctx.quad(0, 0, 200, 100)
        size_after_second = prog["u_size"].value

        self.assertEqual(size_after_first, (50, 50))
        self.assertEqual(size_after_second, (200, 100))

    def test_consecutive_quad_calls_set_different_colors(self):
        """Each quad() call overwrites u_color with new values."""
        self.ctx.quad(0, 0, 50, 50, color=(1, 0, 0), alpha=1.0)
        prog = DrawingContext._ui_program
        color_after_first = prog["u_color"].value

        self.ctx.quad(0, 0, 50, 50, color=(0, 1, 0), alpha=0.5)
        color_after_second = prog["u_color"].value

        self.assertEqual(color_after_first, (1.0, 0.0, 0.0, 1.0))
        self.assertEqual(color_after_second, (0.0, 1.0, 0.0, 0.5))


class TestDrawingContextOutlineUniforms(unittest.TestCase):
    """Test that outline() sets uniforms correctly."""

    @classmethod
    def setUpClass(cls):
        cls._headless_ctx = moderngl.create_standalone_context()
        cls._headless_ctx.viewport = (0, 0, 1280, 720)

    def setUp(self):
        DrawingContext._initialized = False
        DrawingContext._ui_program = None
        DrawingContext._quad_vbo = None
        DrawingContext._outline_vbo = None
        DrawingContext._quad_vao = None
        DrawingContext._outline_vao = None

        self.renderer = MockRenderer(self._headless_ctx)
        self.ctx = DrawingContext(self.renderer, 400, 300)

    def test_outline_sets_all_required_uniforms(self):
        """outline() sets u_resolution, u_pos, u_size, u_color before rendering."""
        self.ctx.outline(10, 20, 150, 75, color=(0.5, 0.5, 0.5), alpha=0.9)

        prog = DrawingContext._ui_program
        self.assertEqual(prog["u_resolution"].value, (400, 300))
        self.assertEqual(prog["u_pos"].value, (10, 20))
        self.assertEqual(prog["u_size"].value, (150, 75))
        u_color = prog["u_color"].value
        self.assertAlmostEqual(u_color[0], 0.5, places=5)
        self.assertAlmostEqual(u_color[1], 0.5, places=5)
        self.assertAlmostEqual(u_color[2], 0.5, places=5)
        self.assertAlmostEqual(u_color[3], 0.9, places=5)


class TestDrawingContextSetOffset(unittest.TestCase):
    """Test set_offset() method for dynamic offset updates."""

    @classmethod
    def setUpClass(cls):
        cls._headless_ctx = moderngl.create_standalone_context()
        cls._headless_ctx.viewport = (0, 0, 1280, 720)

    def setUp(self):
        DrawingContext._initialized = False
        DrawingContext._ui_program = None
        DrawingContext._quad_vbo = None
        DrawingContext._outline_vbo = None
        DrawingContext._quad_vao = None
        DrawingContext._outline_vao = None

        self.renderer = MockRenderer(self._headless_ctx)
        self.ctx = DrawingContext(self.renderer, 400, 300)

    def test_set_offset_updates_internal_state(self):
        """set_offset() updates _ox and _oy fields."""
        self.ctx.set_offset(50, 100)
        self.assertEqual(self.ctx._ox, 50)
        self.assertEqual(self.ctx._oy, 100)

    def test_set_offset_affects_quad_position(self):
        """quad() uses offset values set via set_offset()."""
        self.ctx.set_offset(10, 20)
        self.ctx.quad(5, 5, 50, 50)

        prog = DrawingContext._ui_program
        u_pos = prog["u_pos"].value
        # Should be offset + position: (10+5, 20+5) = (15, 25)
        self.assertEqual(u_pos, (15, 25))

    def test_set_offset_overrides_constructor_offset(self):
        """set_offset() can change offset that was set at construction."""
        ctx_with_initial = DrawingContext(self.renderer, 400, 300, offset_x=100, offset_y=200)
        ctx_with_initial.set_offset(5, 10)
        ctx_with_initial.quad(0, 0, 50, 50)

        prog = DrawingContext._ui_program
        u_pos = prog["u_pos"].value
        # Should reflect the new offset, not the initial one
        self.assertEqual(u_pos, (5, 10))


if __name__ == "__main__":
    unittest.main(verbosity=2)