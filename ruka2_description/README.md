# ruka2_description

Canonical RUKA2 URDF/Xacro, meshes, collision geometry, inertials, frames, and
standalone RViz viewer.

The package contains the canonical RUKA2 geometry baseline. The six arm axes
are named `joint_1` through `joint_6`. Gripper and finger geometry is retained
for future integration, but its joints are not part of the arm controller.

```bash
ros2 launch ruka2_description display.launch.py
```
