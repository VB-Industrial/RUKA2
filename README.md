# RUKA2

ROS 2 Jazzy workspace and embedded software for the second-generation
VB-Industrial manipulator.

## ROS packages

- `ruka2_description` — the canonical URDF/Xacro, meshes, and a standalone
  model viewer;
- `ruka2_control` — the existing Cyphal `ros2_control` hardware plugin, the
  mock profile, controllers, and robot bringup;
- `ruka2_moveit_config` — SRDF, planning configuration, MoveIt, and RViz.

The arm is planned and controlled through `ruka_arm_controller`, matching the
public name used by the original `ruka_end_eff` package. The current hardware
contract exposes six arm joints. Gripper geometry remains visible, but its
joints are passive until lower-level gripper control is implemented.

## Build

```bash
git submodule update --init --recursive
source /opt/ros/jazzy/setup.bash
rosdep install --from-paths . --ignore-src -r -y
colcon build --symlink-install
source install/setup.bash
```

The firmware subtree contains `COLCON_IGNORE` and is built separately with its
own CMake presets.

## Launch

Display only:

```bash
ros2 launch ruka2_description display.launch.py
```

Robot state publisher and `ros2_control`, using safe mock hardware by default:

```bash
ros2 launch ruka2_control ros2_control.launch.py
```

Complete mock environment (control, MoveIt, and RViz):

```bash
ros2 launch ruka2_moveit_config full_system.launch.py
```

Start the same system without gripper visual and collision geometry:

```bash
ros2 launch ruka2_moveit_config full_system.launch.py use_end_effector:=false
```

Real arm:

```bash
ros2 launch ruka2_moveit_config full_system.launch.py \
  use_mock_hardware:=false can_interface:=vcan1.0
```

MoveIt and RViz against an already running `ruka2_control` instance:

```bash
ros2 launch ruka2_moveit_config moveit.launch.py \
  use_mock_hardware:=false
```

Set `use_rviz:=false` on either MoveIt launch for headless operation.

## Validation

```bash
colcon test --event-handlers console_direct+
colcon test-result --verbose
```

The real hardware interface keeps the established synchronous Cyphal/SocketCAN
path and defaults to `vcan1.0`. See
[`docs/architecture-contract.md`](docs/architecture-contract.md) and
[`interfaces/cyphal.md`](interfaces/cyphal.md) for the frozen lower-level
contract.
