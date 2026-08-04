# ruka2_moveit_config

MoveIt SRDF, kinematics, joint limits, planning pipelines, controller mapping,
launch files, and RViz configuration for RUKA2.

The package currently contains an explicitly temporary MoveIt configuration for
the dummy model. It allows infrastructure, controller, planning, and RViz
integration to be tested before the canonical RUKA2 URDF is delivered:

```bash
ros2 launch ruka2_moveit_config demo.launch.py
```

It will support both an external controller manager and a self-contained local
workstation launch on the Raspberry Pi.
