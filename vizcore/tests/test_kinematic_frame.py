"""
Simple test script for KinematicFrame widget.
Tests basic functionality without rendering.
"""
import unittest
import numpy as np
from vizcore.bus.data_bus import DataBus
from vizcore.components.visualization.kinematicFrame import KinematicFrame
from vizcore.renderer.renderer import Renderer

import moderngl


class TestKinematicFrame(unittest.TestCase):
    """Test suite for KinematicFrame widget."""

    def setUp(self):
        """Set up test fixtures."""
        self.data_bus = DataBus(buffer_size=256)
        self.ctx = moderngl.create_standalone_context()
        self.app = type('App', (object,), {'ctx': self.ctx})()
        self.renderer = Renderer(self.app, (800, 600))

    def tearDown(self):
        """Clean up after tests."""
        self.ctx.release()

    def _make_frame(self, signals=("force",)):
        """Build a frame with bound signals and static geometry."""
        frame = KinematicFrame(channels=len(signals), renderer=self.renderer, text_renderer=None)
        frame.bind_renderer(self.renderer)
        frame.bind_external_signal(self.data_bus, list(signals))
        frame._build_verts()
        return frame

    def _push_euler(self, x, y, z):
        """Push Euler angles into the data bus."""
        self.data_bus.push("eulerian_x", float(x))
        self.data_bus.push("eulerian_y", float(y))
        self.data_bus.push("eulerian_z", float(z))

    def test_kinematic_frame_basic(self):
        """Test basic KinematicFrame initialization and data binding."""
        frame = KinematicFrame(
            shaft_radius=0.04,
            shaft_height=0.6,
            head_radius=0.10,
            head_height=0.2,
            segments=32,
            channels=2,
            text_renderer=None,
            renderer=self.renderer
        )

        frame.bind_renderer(self.renderer)
        frame.bind_external_signal(self.data_bus, ['velocity', 'acceleration'])

        for i in range(10):
            self.data_bus.push('eulerian_x', 0.1 * i)
            self.data_bus.push('eulerian_y', 0.05 * i)
            self.data_bus.push('eulerian_z', 0.02 * i)
            self.data_bus.push('velocity', [1.0 + 0.1*i, 2.0 - 0.1*i, 0.5])
            self.data_bus.push('acceleration', [0.1, -0.05, 0.02])

        frame.update()

        self.assertIsNotNone(frame.signal_buffer)
        self.assertEqual(frame.signal_buffer.shape, (2, 3))
        self.assertIsNotNone(frame.eulerian_buffer)
        self.assertEqual(frame.eulerian_buffer.shape, (3,))
        self.assertGreater(frame._local['velocity'].count, 0)
        self.assertGreater(frame._local['acceleration'].count, 0)
        self.assertGreater(frame._local['eulerian_x'].count, 0)

    def test_kinematic_frame_multiple_updates(self):
        """Test KinematicFrame with multiple update cycles."""
        frame = KinematicFrame(channels=1)
        frame.bind_renderer(self.renderer)
        frame.bind_external_signal(self.data_bus, ['force'])

        for frame_num in range(5):
            self.data_bus.push('eulerian_x', 0.01 * frame_num)
            self.data_bus.push('eulerian_y', 0.02 * frame_num)
            self.data_bus.push('eulerian_z', 0.03 * frame_num)
            self.data_bus.push('force', [1.0, 2.0, 3.0])

            frame.update()

            latest_force = frame._local['force'].latest()
            self.assertIsNotNone(latest_force)
            self.assertTrue(np.allclose(latest_force, [1.0, 2.0, 3.0]))

    def test_kinematic_frame_history(self):
        """Test that history is properly maintained in local buffers."""
        frame = KinematicFrame(channels=1)
        frame.bind_renderer(self.renderer)
        frame.bind_external_signal(self.data_bus, ['torque'])

        test_vectors = [
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
        ]

        for vec in test_vectors:
            self.data_bus.push('eulerian_x', 0.0)
            self.data_bus.push('eulerian_y', 0.0)
            self.data_bus.push('eulerian_z', 0.0)
            self.data_bus.push('torque', vec)
            frame.update()

        history = frame._local['torque'].history()
        self.assertEqual(len(history), 3)
        self.assertTrue(np.allclose(history[0], test_vectors[0]))
        self.assertTrue(np.allclose(history[-1], test_vectors[-1]))

    def test_update_writes_dynamic_buffers(self):
        """Update should refresh signal and Euler buffers from the data bus."""
        frame = self._make_frame(("force", "torque"))

        self._push_euler(0.1, 0.2, 0.3)
        self.data_bus.push("force", np.array([1.0, 2.0, 3.0], dtype="f4"))
        self.data_bus.push("torque", np.array([4.0, 5.0, 6.0], dtype="f4"))

        frame.update()

        self.assertTrue(np.allclose(frame.signal_buffer[0], [1.0, 2.0, 3.0]))
        self.assertTrue(np.allclose(frame.signal_buffer[1], [4.0, 5.0, 6.0]))
        self.assertTrue(np.allclose(frame.eulerian_buffer, [0.1, 0.2, 0.3]))

        self.assertGreater(frame._local["force"].count, 0)
        self.assertGreater(frame._local["torque"].count, 0)
        self.assertGreater(frame._local["eulerian_x"].count, 0)

    def test_update_does_not_modify_read_only_geometry_buffers(self):
        """Static geometry buffers must remain unchanged after update."""
        frame = self._make_frame(("force",))

        basis_verts_before = frame._vbos["basisVerts"].read()
        basis_idx_before = frame._vbos["basisIdx"].read()
        signal_verts_before = frame._vbos["signalVerts"].read()
        signal_idx_before = frame._vbos["signalIdx"].read()

        self._push_euler(0.4, 0.5, 0.6)
        self.data_bus.push("force", np.array([7.0, 8.0, 9.0], dtype="f4"))
        frame.update()

        self.assertEqual(frame._vbos["basisVerts"].read(), basis_verts_before)
        self.assertEqual(frame._vbos["basisIdx"].read(), basis_idx_before)
        self.assertEqual(frame._vbos["signalVerts"].read(), signal_verts_before)
        self.assertEqual(frame._vbos["signalIdx"].read(), signal_idx_before)

    def test_update_maintains_history_across_multiple_calls(self):
        """Repeated updates should append to local history without mutating static buffers."""
        frame = self._make_frame(("torque",))

        # Check geometry after building verts
        basis_verts_before = frame._vbos["basisVerts"].read()

        samples = [
            np.array([1.0, 0.0, 0.0], dtype="f4"),
            np.array([0.0, 1.0, 0.0], dtype="f4"),
            np.array([0.0, 0.0, 1.0], dtype="f4"),
        ]

        for i, sample in enumerate(samples):
            self._push_euler(0.01 * i, 0.02 * i, 0.03 * i)
            self.data_bus.push("torque", sample)
            frame.update()

        history = frame._local["torque"].history()
        self.assertEqual(len(history), len(samples))
        self.assertTrue(np.allclose(history[0], samples[0]))
        self.assertTrue(np.allclose(history[-1], samples[-1]))
        self.assertEqual(frame._vbos["basisVerts"].read(), basis_verts_before)


if __name__ == "__main__":
    unittest.main()
