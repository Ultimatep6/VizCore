import unittest
import numpy as np
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from core.signal_schema import SignalSchema, V
from core.simulation import Signal, SimNode
from core.data_bus import DataBus
from components.base.base_widget import BaseWidget


class TestSignalSchema(unittest.TestCase):
    def test_auto_infer_from_numpy_array(self):
        schema = SignalSchema.infer_from_value(np.array([1.0, 2.0, 3.0]))
        self.assertEqual(schema.shape, (3,))
        self.assertEqual(schema.dtype, np.float64)

    def test_auto_infer_from_list(self):
        schema = SignalSchema.infer_from_value([1.0, 2.0, 3.0])
        self.assertEqual(schema.shape, (3,))
        self.assertEqual(schema.dtype, float)

    def test_auto_infer_from_nested_list(self):
        schema = SignalSchema.infer_from_value(np.eye(3))
        self.assertEqual(schema.shape, (3, 3))
        self.assertEqual(schema.dtype, np.float64)

    def test_auto_infer_from_scalar(self):
        schema = SignalSchema.infer_from_value(42)
        self.assertEqual(schema.shape, (1,))
        self.assertEqual(schema.dtype, int)
        schema2 = SignalSchema.infer_from_value(3.14)
        self.assertEqual(schema2.shape, (1,))
        self.assertEqual(schema2.dtype, float)

    def test_matches_shape_only(self):
        a = SignalSchema(shape=(3,))
        b = SignalSchema(shape=(3,))
        c = SignalSchema(shape=(4,))
        self.assertTrue(a.matches(b))
        self.assertFalse(a.matches(c))

    def test_matches_dtype(self):
        a = SignalSchema(shape=(3,), dtype=np.float32)
        b = SignalSchema(shape=(3,), dtype=np.float32)
        c = SignalSchema(shape=(3,), dtype=float)
        self.assertTrue(a.matches(b))
        self.assertFalse(a.matches(c))

    def test_matches_constraints(self):
        a = SignalSchema(
            shape=(4,), dtype=float, constraints={"normalized": True}
        )
        b = SignalSchema(
            shape=(4,), dtype=float, constraints={"normalized": True}
        )
        c = SignalSchema(
            shape=(4,), dtype=float, constraints={"normalized": False}
        )
        d = SignalSchema(shape=(4,), dtype=float)
        self.assertTrue(a.matches(b))
        self.assertFalse(a.matches(c))
        self.assertFalse(a.matches(d))

    def test_widget_unspecified_dtype_matches_any_dtype(self):
        a = SignalSchema(shape=(3,))
        b = SignalSchema(shape=(3,), dtype=int)
        self.assertTrue(a.matches(b))

    def test_matches_none_skips_check(self):
        a = SignalSchema(shape=None, dtype=None)
        b = SignalSchema(shape=(3,), dtype=float)
        self.assertTrue(a.matches(b))

    def test_matches_validator_keys_require_constraints(self):
        widget = SignalSchema(
            shape=(4,),
            constraints={"normalized": True},
            validators={"normalized": V.normalized()},
        )
        signal_ok = SignalSchema(
            shape=(4,),
            constraints={"normalized": True},
        )
        signal_no_constraint = SignalSchema(shape=(4,))
        signal_missing_key = SignalSchema(
            shape=(4,),
            constraints={"positive": True},
        )
        self.assertTrue(widget.matches(signal_ok))
        self.assertFalse(widget.matches(signal_no_constraint))
        self.assertFalse(widget.matches(signal_missing_key))

    def test_quaternion_normalized(self):
        quat_schema = SignalSchema(
            shape=(4,),
            dtype=float,
            constraints={"normalized": True},
            description="Unit quaternion for orientation",
        )
        valid = SignalSchema(
            shape=(4,),
            dtype=float,
            constraints={"normalized": True},
        )
        invalid = SignalSchema(
            shape=(4,),
            dtype=float,
            constraints={"normalized": False},
        )
        no_constraint = SignalSchema(
            shape=(4,), dtype=float
        )
        self.assertTrue(quat_schema.matches(valid))
        self.assertFalse(quat_schema.matches(invalid))
        self.assertFalse(quat_schema.matches(no_constraint))


class TestSignalWithSchema(unittest.TestCase):
    def test_signal_auto_schema_from_scalar(self):
        sig = Signal(0.0, units="m", description="Position")
        self.assertEqual(sig.schema.shape, (1,))
        self.assertEqual(sig.schema.dtype, float)
        self.assertEqual(sig.schema.units, "m")
        self.assertEqual(sig.schema.description, "Position")

    def test_signal_auto_schema_from_list(self):
        sig = Signal([0.0, 0.0, 0.0], units="m/s")
        self.assertEqual(sig.schema.shape, (3,))
        self.assertEqual(sig.schema.dtype, float)
        self.assertEqual(sig.schema.units, "m/s")

    def test_signal_explicit_schema(self):
        schema = SignalSchema(
            shape=(4,),
            dtype=float,
            constraints={"normalized": True},
            units="quaternion",
            description="Orientation quaternion",
        )
        sig = Signal(
            np.array([1.0, 0.0, 0.0, 0.0]),
            schema=schema,
        )
        self.assertIs(sig.schema, schema)
        self.assertEqual(sig.schema.constraints, {"normalized": True})

    def test_signal_descriptor_set_name(self):
        class TestNode(SimNode):
            x = Signal(0.0)

        self.assertEqual(TestNode.x.name, "x")


class Motor(SimNode):
    rpm = Signal(0.0, units="RPM")
    temp = Signal(25.0, units="C")
    current = Signal(0.0, units="Amps", description="Motor phase current")


class IMU(SimNode):
    accel = Signal(np.array([0.0, 0.0, 0.0]), units="m/s^2")
    gyro = Signal(np.array([0.0, 0.0, 0.0]), units="rad/s")


class Battery(SimNode):
    voltage = Signal(12.6, units="V")


class Drone(SimNode):
    pos = Signal(np.array([0.0, 0.0, 0.0]), units="m")
    orientation = Signal(
        np.array([1.0, 0.0, 0.0, 0.0]),
        units="quaternion",
        description="3x3 rotation matrix",
        schema=SignalSchema(
            shape=(4,),
            dtype=np.float64,
            constraints={"normalized": True},
        ),
    )

    def __init__(self, name):
        super().__init__(name)
        self.motor_fl = Motor("FL")
        self.motor_fr = Motor("FR")
        self.imu = IMU("InternalIMU")
        self.battery = Battery("MainPack")


class World(SimNode):
    gravity = Signal(-9.8, units="m/s^2")

    def __init__(self):
        super().__init__("World")
        self.drone_alpha = Drone("Alpha")
        self.drone_beta = Drone("Beta")


class TestGetSignalSchemas(unittest.TestCase):
    def test_flat_node_schemas(self):
        class FlatNode(SimNode):
            x = Signal(0.0, units="m")
            y = Signal(0.0, units="m")

        node = FlatNode("flat")
        schemas = node.get_signal_schemas()
        self.assertIn("x", schemas)
        self.assertIn("y", schemas)
        self.assertEqual(schemas["x"].units, "m")
        self.assertEqual(schemas["x"].shape, (1,))

    def test_deep_hierarchy_schemas(self):
        world = World()
        schemas = world.get_signal_schemas()

        self.assertIn("gravity", schemas)
        self.assertIn("drone_alpha.pos", schemas)
        self.assertIn("drone_alpha.orientation", schemas)
        self.assertIn("drone_alpha.motor_fl.rpm", schemas)
        self.assertIn("drone_alpha.motor_fl.temp", schemas)
        self.assertIn("drone_alpha.motor_fl.current", schemas)
        self.assertIn("drone_alpha.imu.accel", schemas)
        self.assertIn("drone_alpha.imu.gyro", schemas)
        self.assertIn("drone_alpha.battery.voltage", schemas)

        self.assertEqual(schemas["drone_alpha.pos"].shape, (3,))
        self.assertEqual(schemas["drone_alpha.orientation"].shape, (4,))
        self.assertEqual(
            schemas["drone_alpha.orientation"].constraints, {"normalized": True}
        )
        self.assertEqual(schemas["drone_alpha.motor_fl.rpm"].units, "RPM")

    def test_schema_isolation_between_instances(self):
        world = World()
        schemas = world.get_signal_schemas()
        self.assertIn("drone_alpha.motor_fl.rpm", schemas)
        self.assertEqual(
            schemas["drone_alpha.motor_fl.rpm"].units, "RPM"
        )
        self.assertEqual(
            schemas["drone_beta.motor_fl.rpm"].units, "RPM"
        )


class TestDataBusSchemas(unittest.TestCase):
    def setUp(self):
        self.bus = DataBus(buffer_size=10)
        self.world = World()
        payload = self.world.get_state()
        self.bus.push_payload(payload)
        schemas = self.world.get_signal_schemas()
        self.bus.register_signal_schemas(schemas)

    def test_shape_matching_still_works(self):
        vec3_paths = self.bus.get_signals_by_shape((3,))
        self.assertIn("drone_alpha.pos", vec3_paths)
        self.assertIn("drone_alpha.imu.accel", vec3_paths)

    def test_get_signals_by_schema_shape_only(self):
        schema = SignalSchema(shape=(3,))
        vec3_paths = self.bus.get_signals_by_schema(schema)
        self.assertIn("drone_alpha.pos", vec3_paths)
        self.assertIn("drone_alpha.imu.accel", vec3_paths)

    def test_get_signals_by_schema_normalized(self):
        quat_schema = SignalSchema(
            shape=(4,), dtype=np.float64, constraints={"normalized": True}
        )
        paths = self.bus.get_signals_by_schema(quat_schema)
        self.assertIn("drone_alpha.orientation", paths)
        self.assertEqual(len(paths), 2)
        self.assertIn("drone_beta.orientation", paths)

    def test_get_signals_by_schema_no_match(self):
        schema = SignalSchema(shape=(3, 3))
        paths = self.bus.get_signals_by_schema(schema)
        self.assertEqual(paths, [])

    def test_get_signal_metadata(self):
        meta = self.bus.get_signal_metadata("drone_alpha.orientation")
        self.assertIsNotNone(meta)
        self.assertIn("schema", meta)
        self.assertEqual(meta["schema"].shape, (4,))
        self.assertEqual(meta["schema"].constraints, {"normalized": True})
        self.assertIn("shape", meta)

    def test_get_signal_metadata_missing(self):
        meta = self.bus.get_signal_metadata("nonexistent")
        self.assertIsNone(meta)


class KinematicFrameWidget(BaseWidget):
    @property
    def signal_schemas(self):
        return [
            SignalSchema(
                shape=(3,),
                description="3D direction vector",
            )
        ]


class QuaternionWidget(BaseWidget):
    @property
    def signal_schemas(self):
        return [
            SignalSchema(
                shape=(4,),
                constraints={"normalized": True},
                validators={"normalized": V.normalized()},
                description="Unit quaternion",
            )
        ]


class AnySignalWidget(BaseWidget):
    @property
    def signal_schemas(self):
        return None


class ScalarWidget(BaseWidget):
    @property
    def signal_schemas(self):
        return [
            SignalSchema(
                shape=(1,),
                description="Scalar value",
            )
        ]


class TestBaseWidgetSchemas(unittest.TestCase):
    def setUp(self):
        self.bus = DataBus(buffer_size=10)
        self.world = World()
        payload = self.world.get_state()
        self.bus.push_payload(payload)
        schemas = self.world.get_signal_schemas()
        self.bus.register_signal_schemas(schemas)
        self.bus.push("extra.scalar", 5.0)

    def test_kinematic_frame_accepts_vec3(self):
        widget = KinematicFrameWidget()
        self.assertTrue(
            widget.accepts_signal(self.bus, "drone_alpha.pos")
        )
        self.assertTrue(
            widget.accepts_signal(self.bus, "drone_alpha.imu.accel")
        )

    def test_kinematic_frame_rejects_quaternion(self):
        widget = KinematicFrameWidget()
        self.assertFalse(
            widget.accepts_signal(self.bus, "drone_alpha.orientation")
        )

    def test_kinematic_frame_rejects_scalar(self):
        widget = KinematicFrameWidget()
        self.assertFalse(widget.accepts_signal(self.bus, "drone_alpha.motor_fl.rpm"))

    def test_quaternion_widget_accepts_normalized(self):
        widget = QuaternionWidget()
        self.assertTrue(
            widget.accepts_signal(self.bus, "drone_alpha.orientation")
        )

    def test_quaternion_widget_rejects_vec3(self):
        widget = QuaternionWidget()
        self.assertFalse(widget.accepts_signal(self.bus, "drone_alpha.pos"))

    def test_any_signal_widget_accepts_everything(self):
        widget = AnySignalWidget()
        self.assertTrue(
            widget.accepts_signal(self.bus, "drone_alpha.pos")
        )
        self.assertTrue(
            widget.accepts_signal(self.bus, "drone_alpha.orientation")
        )
        self.assertTrue(
            widget.accepts_signal(self.bus, "drone_alpha.motor_fl.rpm")
        )

    def test_scalar_widget_accepts_scalar(self):
        widget = ScalarWidget()
        self.assertTrue(
            widget.accepts_signal(self.bus, "drone_alpha.motor_fl.rpm")
        )
        self.assertTrue(
            widget.accepts_signal(self.bus, "drone_alpha.motor_fl.temp")
        )

    def test_scalar_widget_rejects_vec3(self):
        widget = ScalarWidget()
        self.assertFalse(widget.accepts_signal(self.bus, "drone_alpha.pos"))

    def test_required_shape_backward_compat(self):
        widget = KinematicFrameWidget()
        self.assertEqual(widget.required_shape, [(3,)])
        widget2 = AnySignalWidget()
        self.assertIsNone(widget2.required_shape)

    def test_dtype_filtering(self):
        class Float64Widget(BaseWidget):
            @property
            def signal_schemas(self):
                return [
                    SignalSchema(
                        shape=(3,),
                        dtype=np.float64,
                    )
                ]

        widget = Float64Widget()
        self.assertTrue(
            widget.accepts_signal(self.bus, "drone_alpha.pos")
        )

        class IntWidget(BaseWidget):
            @property
            def signal_schemas(self):
                return [
                    SignalSchema(
                        shape=(3,),
                        dtype=int,
                    )
                ]

        int_widget = IntWidget()
        self.assertFalse(
            int_widget.accepts_signal(self.bus, "drone_alpha.pos")
        )

    def test_bind_external_signal_respects_schema(self):
        widget = KinematicFrameWidget()
        widget.bind_external_signal(self.bus, ["drone_alpha.pos"])
        self.assertIn("drone_alpha.pos", widget._bound_signals)
        widget.bind_external_signal(self.bus, ["drone_alpha.orientation"])
        self.assertNotIn("drone_alpha.orientation", widget._bound_signals)

    def test_bind_validates_with_validator_passes(self):
        class PositiveScalarWidget(BaseWidget):
            @property
            def signal_schemas(self):
                return [
                    SignalSchema(
                        shape=(1,),
                        constraints={"positive": True},
                        validators={"positive": V.positive()},
                    )
                ]

        widget = PositiveScalarWidget()
        self.bus.push_payload({"test": {"positive": 42.0}})
        self.bus.register_signal_schema(
            "test.positive",
            SignalSchema(shape=(1,), constraints={"positive": True}),
        )
        widget.bind_external_signal(self.bus, ["test.positive"])
        self.assertIn("test.positive", widget._bound_signals)

    def test_bind_validates_with_validator_rejects(self):
        class PositiveScalarWidget(BaseWidget):
            @property
            def signal_schemas(self):
                return [
                    SignalSchema(
                        shape=(1,),
                        constraints={"positive": True},
                        validators={"positive": V.positive()},
                    )
                ]

        widget = PositiveScalarWidget()
        self.bus.push_payload({"test": {"negative": -5.0}})
        self.bus.register_signal_schema(
            "test.negative",
            SignalSchema(shape=(1,)),
        )
        widget.bind_external_signal(self.bus, ["test.negative"])
        self.assertNotIn("test.negative", widget._bound_signals)

    def test_bind_combined_schema_and_validator(self):
        class NonZeroVec3Widget(BaseWidget):
            @property
            def signal_schemas(self):
                return [
                    SignalSchema(
                        shape=(3,),
                        constraints={"non_zero": True},
                        validators={"non_zero": V.non_zero()},
                    )
                ]

        self.world.drone_alpha.pos = np.array([1.0, 2.0, 3.0])
        self.bus.push_payload(self.world.get_state())
        schemas = self.world.get_signal_schemas()
        schemas["drone_alpha.pos"] = SignalSchema(
            shape=(3,), constraints={"non_zero": True}
        )
        self.bus.register_signal_schemas(schemas)
        widget = NonZeroVec3Widget()
        widget.bind_external_signal(self.bus, ["drone_alpha.pos"])
        self.assertIn("drone_alpha.pos", widget._bound_signals)

    def test_validate_signal_value_runtime(self):
        class PositiveScalarWidget(BaseWidget):
            @property
            def signal_schemas(self):
                return [
                    SignalSchema(
                        shape=(1,),
                        constraints={"positive": True},
                        validators={"positive": V.positive()},
                    )
                ]

        widget = PositiveScalarWidget()
        passed, errors = widget.validate_signal_value("test", 10.0)
        self.assertTrue(passed)
        passed, errors = widget.validate_signal_value("test", -1.0)
        self.assertFalse(passed)

    def test_validate_signal_value_no_validators(self):
        widget = KinematicFrameWidget()
        passed, errors = widget.validate_signal_value("test", np.array([1, 2, 3]))
        self.assertTrue(passed)
        self.assertEqual(errors, [])


class TestIntegration(unittest.TestCase):
    def test_full_pipeline(self):
        bus = DataBus(buffer_size=10)
        world = World()
        bus.push_payload(world.get_state())
        bus.register_signal_schemas(world.get_signal_schemas())

        widget = KinematicFrameWidget()
        widget.bind_external_signal(bus, ["drone_alpha.pos"])
        self.assertIn("drone_alpha.pos", widget._bound_signals)

        value = bus.latest("drone_alpha.pos")
        np.testing.assert_array_equal(value, [0.0, 0.0, 0.0])

        world.drone_alpha.pos = np.array([10.0, 20.0, 30.0])
        bus.push_payload(world.get_state())
        updated = bus.latest("drone_alpha.pos")
        np.testing.assert_array_equal(updated, [10.0, 20.0, 30.0])


if __name__ == "__main__":
    unittest.main(verbosity=2)
