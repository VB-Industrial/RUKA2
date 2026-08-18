# ruka2_moveit_config

MoveIt configuration for the six-axis RUKA2 arm. The planning group and the
trajectory controller are both named `ruka_arm_controller`, as in the original
`ruka_end_eff` package.

Start the complete mock environment:

```bash
ros2 launch ruka2_moveit_config full_system.launch.py
```

Omit the gripper from visualization and collision planning while keeping the
same controller contract:

```bash
ros2 launch ruka2_moveit_config full_system.launch.py use_end_effector:=false
```

Start it with the existing real hardware interface:

```bash
ros2 launch ruka2_moveit_config full_system.launch.py \
  use_mock_hardware:=false can_interface:=vcan1.0
```

If `ruka2_control/ros2_control.launch.py` is already running on this or another
ROS 2 host, start only MoveIt and RViz:

```bash
ros2 launch ruka2_moveit_config moveit.launch.py \
  use_mock_hardware:=false
```

Use `use_rviz:=false` for headless operation. The current planning chain ends
at `link_06`; the retained finger joints are passive because the lower-level
gripper interface is not part of the current hardware contract.
