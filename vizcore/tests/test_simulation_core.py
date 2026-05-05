import unittest
import numpy as np
from vizcore.simulation.simulation import SimNode, Signal

class Motor(SimNode):
    rpm = Signal(0.0, units="RPM")
    temp = Signal(25.0, units="C")
    current = Signal(0.0, units="Amps", description="Motor phase current")

class IMU(SimNode):
    accel = Signal(np.array([0.0, 0.0, 0.0]), units="m/s^2")
    gyro = Signal(np.array([0.0, 0.0, 0.0]), units="rad/s")
    mag = Signal(np.array([0.0, 0.0, 0.0]), units="uT")

class Battery(SimNode):
    voltage = Signal(12.6, units="V")
    percentage = Signal(100, units="%")

class Drone(SimNode):
    pos = Signal(np.array([0.0, 0.0, 0.0]), units="m")
    orientation = Signal(np.eye(3), units="matrix", description="3x3 rotation matrix")
    
    def __init__(self, name):
        super().__init__(name)
        # Deeply nested children
        self.motor_fl = Motor("FL")
        self.motor_fr = Motor("FR")
        self.motor_rl = Motor("RL")
        self.motor_rr = Motor("RR")
        
        self.imu = IMU("InternalIMU")
        self.battery = Battery("MainPack")

class Environment(SimNode):
    wind_vector = Signal(np.array([5.0, 0.0, 0.0]), units="m/s")
    ambient_temp = Signal(25.0, units="C")

class World(SimNode):
    gravity = Signal(-9.8, units="m/s^2")
    def __init__(self):
        super().__init__("World")
        # Direct SimNode Children
        self.drone_alpha = Drone("Alpha")
        self.drone_beta = Drone("Beta")
        self.env = Environment("LabEnv")

class TestSimulationCore(unittest.TestCase):
    def test_sim_node_deep_hierarchy(self):
        """Verify that SimNode correctly handles deep nesting across multiple entities."""
        world = World()
        state = world.get_state()
        
        # 1. Check Top-Level (World)
        self.assertIn("gravity", state)
        self.assertIn("drone_alpha", state)
        self.assertIn("drone_beta", state)
        self.assertIn("env", state)
        
        # 2. Check Second-Level (Drone)
        alpha = state["drone_alpha"]
        self.assertIn("pos", alpha)
        self.assertIn("motor_fl", alpha)
        self.assertIn("imu", alpha)
        self.assertIn("battery", alpha)
        
        # 3. Check Third-Level (Components)
        self.assertIn("voltage", alpha["battery"])
        self.assertIn("accel", alpha["imu"])
        self.assertIn("current", alpha["motor_fl"])
        
        # 4. Check Environment Branch
        self.assertEqual(state["env"]["ambient_temp"], 25.0)
        np.testing.assert_array_equal(state["env"]["wind_vector"], [5.0, 0.0, 0.0])
        
        # Verify specific deep values
        self.assertEqual(alpha["motor_fl"]["units_info"]["current"], "Amps") if "units_info" in alpha["motor_fl"] else None # Hypothetical metadata in future
        print("Deep hierarchy check passed")
        print(state)
    def test_sim_node_metadata_inspection(self):
        """Verify that metadata like units and descriptions are captured correctly at the class level."""
        # Test unit extraction
        self.assertEqual(getattr(Motor, "current").units, "Amps")
        self.assertEqual(getattr(IMU, "accel").units, "m/s^2")
        self.assertEqual(getattr(Drone, "orientation").description, "3x3 rotation matrix")
        
        # Verify names match attribute names
        self.assertEqual(Motor.current.name, "current")
        self.assertEqual(IMU.accel.name, "accel")

    def test_multi_instance_isolation(self):
        """Verify that state of different instances (Alpha vs Beta) is completely separate."""
        world = World()
        world.drone_alpha.pos = np.array([10.0, 0.0, 0.0])
        world.drone_beta.pos = np.array([0.0, 0.0, 20.0])
        
        state = world.get_state()
        np.testing.assert_array_equal(state["drone_alpha"]["pos"], [10.0, 0.0, 0.0])
        np.testing.assert_array_equal(state["drone_beta"]["pos"], [0.0, 0.0, 20.0])
        print("Instance isolation check passed")

    def test_signal_numpy_compatibility(self):
        """Verify that Signal descriptor allows native NumPy operations on instances."""
        class Physics(SimNode):
            vel = Signal(np.array([1.0, 2.0, 3.0]))
            pos = Signal(np.array([0.0, 0.0, 0.0]))
            
            def step(self, dt):
                # Test in-place math and operator overloading
                self.pos = self.pos + self.vel * dt
                
        sim = Physics("Phys")
        sim.step(0.5)
        
        expected_pos = np.array([0.5, 1.0, 1.5])
        np.testing.assert_allclose(sim.pos, expected_pos)
        self.assertTrue(isinstance(sim.pos, np.ndarray))

    def test_signal_metadata_access(self):
        """Verify that metadata (units, name) is accessible at the class level."""
        self.assertEqual(Motor.rpm.units, "RPM")
        self.assertEqual(Motor.temp.units, "C")
        self.assertEqual(Drone.pos.units, "m")
        self.assertEqual(World.gravity.units, "m/s^2")
        
        # Check name capture
        self.assertEqual(Motor.rpm.name, "rpm")
        self.assertEqual(Motor.temp.name, "temp")

    def test_sim_node_mutation_reflects_in_state(self):
        """Verify that updating instance variables reflects in the get_state() dictionary."""
        world = World()
        world.gravity = -1.62 # Moon gravity
        world.drone_alpha.pos = np.array([1.0, 0.0, 0.0])
        
        state = world.get_state()
        self.assertEqual(state["gravity"], -1.62)
        np.testing.assert_array_equal(state["drone_alpha"]["pos"], [1.0, 0.0, 0.0])

if __name__ == "__main__":
    unittest.main()
