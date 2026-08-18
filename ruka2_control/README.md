# ruka2_control

The existing RUKA2 Cyphal hardware interface plus the `ros2_control` robot
description, controller configuration, and bringup.

Mock hardware is the safe default:

```bash
ros2 launch ruka2_control ros2_control.launch.py
```

Use `use_end_effector:=false` to publish the arm without gripper visual and
collision geometry. The controller and hardware joint contract do not change.

Use the real hardware plugin without changing the launch topology:

```bash
ros2 launch ruka2_control ros2_control.launch.py \
  use_mock_hardware:=false can_interface:=vcan1.0
```

Both profiles expose the six arm joints through `ruka_arm_controller`. The
real profile still uses `ruka2_control/Ruka2System` and the unchanged
synchronous Cyphal transport.
