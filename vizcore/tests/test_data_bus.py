import unittest
import numpy as np
from vizcore.bus.data_bus import DataBus

class TestDataBus(unittest.TestCase):
    def setUp(self):
        self.bus = DataBus(buffer_size=10)

    def test_recursive_flattening_and_push(self):
        """Verify that nested payloads are correctly flattened and pushed."""
        payload = {
            "drones": {
                "alpha": {
                    "pos": [1.0, 2.0, 3.0],
                    "battery": 95.0
                },
                "beta": {
                    "pos": np.array([4.0, 5.0, 6.0])
                }
            },
            "world": {
                "gravity": -9.8
            }
        }
        
        self.bus.push_payload(payload)
        
        # Verify flattened paths
        self.assertIn("drones.alpha.pos", self.bus.list_signals())
        self.assertIn("drones.alpha.battery", self.bus.list_signals())
        self.assertIn("drones.beta.pos", self.bus.list_signals())
        self.assertIn("world.gravity", self.bus.list_signals())
        
        # Verify values
        np.testing.assert_array_equal(self.bus.latest("drones.alpha.pos"), [1.0, 2.0, 3.0])
        self.assertEqual(self.bus.latest("world.gravity"), -9.8)

    def test_shape_matching(self):
        """Verify that signals can be filtered by their data shape."""
        payload = {
            "vec3_a": [1, 2, 3],
            "vec3_b": np.zeros(3),
            "scalar_a": 10.0,
            "matrix_a": np.eye(2)
        }
        
        self.bus.push_payload(payload)
        
        # Find 3D vectors
        vec3_signals = self.bus.get_signals_by_shape((3,))
        self.assertEqual(len(vec3_signals), 2)
        self.assertIn("vec3_a", vec3_signals)
        self.assertIn("vec3_b", vec3_signals)
        
        # Find 2x2 matrices
        mat2_signals = self.bus.get_signals_by_shape((2, 2))
        self.assertEqual(len(mat2_signals), 1)
        self.assertIn("matrix_a", mat2_signals)

    def test_repeated_push_payload(self):
        """Verify that repeated pushes update history correctly."""
        for i in range(5):
            payload = {"sensor": {"value": float(i)}}
            self.bus.push_payload(payload)
            
        history = self.bus.history("sensor.value")
        self.assertEqual(len(history), 5)
        self.assertEqual(history[-1], 4.0)

if __name__ == "__main__":
    unittest.main()
