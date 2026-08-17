# RUKA2

RUKA2 is the ROS 2 and embedded software monorepository for the second-generation
VB-Industrial manipulator.

Target platform:

- Ubuntu 24.04
- ROS 2 Jazzy
- Raspberry Pi, with Ethernet-CAN exposed to ROS as SocketCAN `vcan` interfaces
- STM32G474 joint firmware using Cyphal over CAN FD

## Repository layout

- `ruka2_description` — canonical robot description, meshes, and RViz viewer
- `ruka2_control` — `ros2_control` hardware interface and controller bringup
- `ruka2_moveit_config` — MoveIt configuration and visualization
- `firmware/ruka2_firmware` — standalone firmware Git submodule
- `third_party/libcxxcanard` — VB-Industrial `libcxxcanard` Git submodule for the ROS host
- `interfaces` — documented firmware/host communication contract
- `deploy/raspberry_pi` — Raspberry Pi provisioning and runtime assets

The firmware subtree is intentionally excluded from `colcon` discovery by
`firmware/COLCON_IGNORE`. It is built using its own CMake presets.

## Clone

```bash
git clone --recurse-submodules https://github.com/VB-Industrial/RUKA2.git
cd RUKA2
```

For an existing clone:

```bash
git submodule update --init --recursive
```

## ROS build

```bash
source /opt/ros/jazzy/setup.bash
rosdep install --from-paths . --ignore-src -r -y
colcon build --symlink-install
source install/setup.bash
colcon test
colcon test-result --verbose
```

The repository includes the canonical RUKA2 geometry baseline and a working
six-axis mock control/MoveIt path. Gripper geometry is retained for later work,
but only the arm is currently planned and controlled.

Model viewer:

```bash
ros2 launch ruka2_description display.launch.py
```

Mock `ros2_control`:

```bash
ros2 launch ruka2_control mock.launch.py
```

Mock control, MoveIt, and RViz:

```bash
ros2 launch ruka2_moveit_config demo.launch.py
```

MoveIt can also run against a controller manager on another ROS 2 host:

```bash
ros2 launch ruka2_moveit_config demo.launch.py \
  start_control:=false use_mock_hardware:=false
```

For headless operation and split workstation deployments, the package also
provides separate `move_group.launch.py` and `rviz.launch.py` entry points.
The end effector remains deferred; the current arm planning chain ends at
`link_06` while the finger geometry is retained in the model.

The real hardware-interface implementation follows the current firmware
communication contract.

See [the architecture contract](docs/architecture-contract.md) for current
decisions and deferred inputs.
