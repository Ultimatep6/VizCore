# core — Data Bus & Simulation

Thread-safe pub/sub data bus for real-time signal distribution and a simulation example.

## Files

| File | Purpose |
|---|---|
| `data_bus.py` | `DataBus` (signal registry + ring buffers) + `RingBuffer` |
| `signal_schema.py` | `SignalSchema` (type/shape constraints) |
| `simulation.py` | Example `Simulation` thread that pushes payloads |

## Quick Start

```python
from core.data_bus import DataBus

bus = DataBus(buffer_size=1024)

# Push a structured payload (dict is flattened into dot-separated signals):
bus.push_payload({
    "sensor": {
        "imu": {"accel_x": 0.1, "accel_y": -0.02},
        "gps": {"lat": 48.85, "lon": 2.35},
    }
})

# Read latest values:
bus.latest("sensor.imu.accel_x")  # 0.1
bus.latest("sensor.gps.lat")      # 48.85

# Get history:
bus.history("sensor.imu.accel_x", N=50)

# List all registered signals:
bus.list_signals()

# Query by shape:
bus.get_signals_by_shape((1,))
```

## DataBus API

| Method | Description |
|---|---|
| `push_payload(dict)` | Flatten nested dict and push all leaf values |
| `push(name, value)` | Push a single value to a named signal |
| `latest(name)` | Most recent value (or `None`) |
| `history(name, N)` | Last N values; all if `N` is `None` |
| `register_signal_schema(path, schema)` | Attach schema metadata |
| `register_signal_schemas(dict)` | Batch register schemas |
| `get_signals_by_shape(shape)` | List signals matching a NumPy shape |
| `get_signals_by_schema(schema)` | List signals matching a `SignalSchema` |
| `get_signal_metadata(path)` | Schema + shape for a signal |
| `list_signals()` | All registered signal names |

## RingBuffer

Fixed-size buffer (default 1024) — oldest values drop off as new ones arrive.

```python
buf = RingBuffer(512)
buf.push(42)
buf.latest()    # 42
buf.history(10) # last 10 values
```

## SignalSchema

```python
from core.signal_schema import SignalSchema

schema = SignalSchema(
    dtype=np.float32,
    shape=(3,),
    min=-1.0,
    max=1.0,
)
```

## Simulation

`Simulation` runs in a background thread, calling `bus.push_payload(...)` in a loop. Start/stop controlled by `.start()` / `.stop()` / `.running` flag.
