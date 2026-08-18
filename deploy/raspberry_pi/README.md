# Raspberry Pi deployment

Target: Ubuntu 24.04 on Raspberry Pi with ROS 2 Jazzy.

Two runtime profiles are planned:

- `server`: Ethernet-CAN, `ruka2_control`, controller manager, state publisher,
  diagnostics;
- `workstation`: the server profile plus desktop environment, MoveIt, RViz, and
  local visualization.

The Ethernet-CAN host software creates SocketCAN-compatible `vcan1.x`
interfaces. The initial board mapping is:

- `bus0` / `vcan1.0`: RUKA2 arm;
- `bus1` / `vcan1.1`: gripper;
- `bus2` / `vcan1.2`: reserved for the future powerboard implementation.

The checked-in host-managed configuration in `ethernet-can/ruka1.json` targets
the Raspberry Pi Ethernet address `192.168.30.146` and the board hostname
`ruka1.local`. Its CAN FD profile is derived from the pinned RUKA2 joint
firmware: 1 Mbit/s nominal, 8 Mbit/s data with BRS. The 10 ms integration
period follows the upstream Ethernet-CAN host-managed example.

The target host has been audited and validated with this configuration. Import
of its generic provisioning scripts and systemd units remains separate from
the board-specific JSON tracked here.

Upstream documentation:

- https://github.com/VBCores/ethernet-can
