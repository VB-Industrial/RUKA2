# Firmware

`ruka2_firmware` is an external Git submodule tracking:

`https://github.com/VB-Industrial/silverhand_arm_firmware.git`

It is deliberately excluded from ROS/colcon discovery. Build, flash, and debug
it using the instructions and CMake presets in the submodule.

Select `SR_JOINT_INDEX` manually for the currently connected joint before each
build and flash operation. Commit reusable firmware fixes upstream first, then
update the submodule revision in RUKA2.
