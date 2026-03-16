# Visualization Library Specification

## Overview

This document defines the requirements, architecture, and responsibilities of each module in the visualization library designed to support the nCopter simulation ecosystem. The visualization library is intentionally independent from the simulation codebase and communicates only through a telemetry data bus.

The library provides real‑time GPU‑accelerated visualization of telemetry streams such as drone state, controller outputs, and environmental data.

Primary goals:

* Real‑time telemetry visualization
* GPU accelerated rendering
* Modular widget system
* High frequency data ingestion (500–1000 Hz)
* Decoupling from simulation logic

---

# External Dependencies

## Required

### moderngl

Provides the OpenGL abstraction used to manage buffers, shaders, and rendering pipelines.

Responsibilities:

* GPU buffer management
* Shader compilation
* Draw submission

### pyglet

Provides window creation, event loop, and input handling.

Responsibilities:

* OpenGL context creation
* Window management
* Keyboard/mouse input

### numpy

Provides CPU‑side numerical arrays used for staging telemetry data and preparing GPU buffers.

Responsibilities:

* Ring buffer backing storage
* Numeric operations

---

# Top Level Package Structure

```
vizcore/

app/
renderer/
layout/
bus/
widgets/
graphics/
shaders/
text/
utils/
```

Each subsystem has a specific responsibility described below.

---

# app/

Application layer responsible for initializing and running the visualization system.

Files:

## dashboard.py

Main entry point for building dashboards.

Responsibilities:

* Manage widget registration
* Connect to telemetry data bus
* Initialize renderer
* Initialize layout engine
* Start visualization loop

Primary functionality:

* Add widgets to layout
* Bind widgets to telemetry signals
* Control dashboard lifecycle

---

## window.py

Creates and manages the application window.

Responsibilities:

* Create OpenGL window
* Handle resize events
* Dispatch input events

Key behaviors:

* Notify layout engine when window size changes
* Forward input events to widgets

---

## mainloop.py

Controls the render/update loop.

Responsibilities:

* Maintain stable frame rate
* Update widgets
* Submit draw calls

Typical loop responsibilities:

1. Poll window events
2. Update widgets
3. Execute rendering pass

---

# renderer/

Responsible for all GPU operations.

Files:

## renderer.py

Central rendering controller.

Responsibilities:

* Manage render pipeline
* Submit draw calls
* Maintain global GPU state

Capabilities:

* Draw meshes
* Draw line plots
* Draw UI primitives

---

## shader_manager.py

Handles shader compilation and caching.

Responsibilities:

* Load shader files
* Compile shaders
* Cache compiled programs

Ensures shaders are not repeatedly compiled.

---

## buffer_allocator.py

Manages GPU buffers.

Responsibilities:

* Allocate vertex buffers
* Reuse buffers when possible
* Manage GPU memory lifecycle

Important requirement:

Buffers must support high‑frequency updates without reallocation.

---

## camera.py

Implements camera transformations for 3D scenes.

Responsibilities:

* View matrix calculation
* Projection matrix calculation
* Camera movement

Supported modes:

* Orbit camera
* Free camera

---

# layout/

Controls placement of widgets within the window.

Files:

## grid_layout.py

Primary layout engine.

Responsibilities:

* Divide screen into cells
* Assign widgets to cells
* Compute widget rectangles

Requirements:

* Support resizing
* Maintain widget proportions

---

## rect.py

Defines rectangle geometry used by layout system.

Responsibilities:

* Store position and dimensions
* Provide helper geometry operations

---

# bus/

Telemetry communication layer between simulation and visualization.

Files:

## data_bus.py

Central telemetry registry.

Responsibilities:

* Register signals
* Store signal buffers
* Provide signal lookup

Requirements:

* Thread safe access
* Fast signal lookup

---

## ring_buffer.py

Circular buffer used for telemetry storage.

Responsibilities:

* Store recent signal values
* Maintain constant memory footprint

Required functionality:

* Push new value
* Retrieve latest value
* Retrieve full history window

---

# widgets/

Contains all visual components.

All widgets must inherit from a common base class.

Required interface:

* update()
* draw()
* resize()

---

## base_widget.py

Abstract widget class.

Responsibilities:

* Define widget interface
* Store widget rectangle
* Maintain widget state

All widgets must implement:

* update(data)
* draw(renderer)
* resize(rect)

---

# widgets/plots/

Plotting widgets for telemetry signals.

## line_plot.py

Scrolling line plot.

Responsibilities:

* Display time series signals
* Maintain GPU ring buffer

Features:

* Multiple channels
* Automatic scrolling

---

## phase_plot.py

XY scatter plot with fading history.

Responsibilities:

* Display relationship between two signals

Typical use:

* Control input correlation

---

# widgets/indicators/

Telemetry indicators.

## attitude_indicator.py

Displays drone orientation.

Responsibilities:

* Visualize roll, pitch, yaw

Typical implementation:

* Artificial horizon

---

## bar_meter.py

Displays scalar value as vertical or horizontal bar.

Responsibilities:

* Visualize actuator outputs

Features:

* Configurable ranges

---

## numeric_readout.py

Displays numeric telemetry values.

Responsibilities:

* Show precise signal values

Features:

* Configurable precision

---

# widgets/timeline/

## event_timeline.py

Displays discrete events along time axis.

Responsibilities:

* Show button presses
* Show controller state changes

---

# widgets/scene3d/

3D simulation view.

## scene.py

Manages 3D scene rendering.

Responsibilities:

* Render world objects
* Maintain scene graph

---

## drone_mesh.py

Visual representation of drone model.

Responsibilities:

* Load mesh
* Apply pose transforms

---

## trajectory.py

Displays flight path.

Responsibilities:

* Maintain path history
* Render trajectory line

---

# graphics/

Low‑level geometry primitives.

## mesh.py

Mesh representation used by renderer.

Responsibilities:

* Store vertices
* Store indices

---

## geometry.py

Procedural geometry generation.

Examples:

* cubes
* grids
* axes

---

## materials.py

Defines shader material parameters.

Responsibilities:

* Store shader uniforms

---

## primitives.py

Reusable rendering primitives.

Examples:

* lines
* quads

---

# shaders/

Contains GPU shader programs.

Examples:

* line plot shaders
* mesh shaders
* UI shaders

Responsibilities:

* Define vertex transformations
* Define fragment shading

---

# text/

Handles text rendering.

## font_atlas.py

Generates texture atlas for font glyphs.

Responsibilities:

* Pack glyphs
* Provide texture coordinates

---

## text_renderer.py

Renders text using GPU.

Responsibilities:

* Draw characters
* Manage glyph buffers

---

# utils/

Utility helpers used across the library.

## colors.py

Defines color palettes and utilities.

---

## time.py

Provides timing helpers.

Responsibilities:

* Frame timing
* Simulation timestamps

---

## config.py

Handles configuration loading.

Responsibilities:

* Load dashboard layouts
* Parse configuration files

---

# Summary

The visualization library is composed of several independent subsystems:

* Application layer
* Renderer
* Layout system
* Telemetry bus
* Widget library
* Graphics primitives

These components together form a real‑time telemetry visualization platform capable of supporting complex simulation environments such as nCopter.
