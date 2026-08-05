# ruka2_control

RUKA2 `ros2_control` hardware plugin, controller configuration, mock/real
profiles, diagnostics, and bringup.

The package provides separate six-axis mock and real profiles around the
canonical geometry in `ruka2_description`:

```bash
ros2 launch ruka2_control mock.launch.py
ros2 launch ruka2_control real.launch.py can_interface:=vcan1.0
```

The real profile loads `ruka2_control/Ruka2System`. It communicates as Cyphal
node 100 with firmware nodes 21 through 26. Activation fails unless all six
nodes provide fresh heartbeat and feedback. Communication and firmware health
are published on `/diagnostics`.

The transport is single-threaded and serviced from the `ros2_control` update
cycle. The default is `vcan1.0`, supplied by the Ethernet-CAN host service on
the Raspberry Pi.
