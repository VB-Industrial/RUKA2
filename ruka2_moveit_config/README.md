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

It will support both an external controller manager and a self-contained local
workstation launch on the Raspberry Pi.
