# ruka2_moveit_config

MoveIt SRDF, kinematics, joint limits, planning pipelines, controller mapping,
launch files, and RViz configuration for RUKA2.

The package configures the six-axis arm chain from `base_link` through
`link_06`. The retained gripper finger joints are passive and are not part of
the arm planning group or controller:

```bash
ros2 launch ruka2_moveit_config demo.launch.py
```

Use the real arm on the Raspberry Pi with:

```bash
ros2 launch ruka2_moveit_config demo.launch.py \
  use_mock_hardware:=false can_interface:=vcan1.0
```

Set `start_control:=false` when MoveIt/RViz runs on a workstation and the
controller manager is already running on the Raspberry Pi.

The launch files can also be run independently:

```bash
# Planning and trajectory execution, using an external controller manager.
ros2 launch ruka2_moveit_config move_group.launch.py use_mock_hardware:=false

# Visualization connected to an already running move_group.
ros2 launch ruka2_moveit_config rviz.launch.py use_mock_hardware:=false
```

`demo.launch.py` is the all-in-one Raspberry Pi/workstation entry point and
remains the recommended mock smoke test. `move_group.launch.py` publishes the
fixed `world -> base_link` transform by default; set `publish_world_tf:=false`
if another node owns that transform.

The current planning tip is `link_06`. Gripper geometry and passive finger
joints stay in the model, but the end effector is intentionally not configured
for planning or control yet.
