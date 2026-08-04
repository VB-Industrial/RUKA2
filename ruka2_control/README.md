# ruka2_control

RUKA2 `ros2_control` hardware plugin, controller configuration, mock/real
profiles, diagnostics, and bringup.

The package currently provides a working mock `ros2_control` launch around the
temporary model in `ruka2_description`:

```bash
ros2 launch ruka2_control mock.launch.py
```

The real hardware plugin will be derived from the current firmware contract;
SilverHand control code is a reference only.

Initial real transport default: `vcan1.0`, supplied by the Ethernet-CAN host
service on the Raspberry Pi.
