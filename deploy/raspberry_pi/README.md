# Raspberry Pi deployment

Target: Ubuntu 24.04 on Raspberry Pi with ROS 2 Jazzy.

Two runtime profiles are planned:

- `server`: Ethernet-CAN, `ruka2_control`, controller manager, state publisher,
  diagnostics;
- `workstation`: the server profile plus desktop environment, MoveIt, RViz, and
  local visualization.

The Ethernet-CAN host software creates SocketCAN-compatible `vcan1.x`
interfaces. RUKA2 initially targets `vcan1.0` for the arm. Host IP, board
hostname/IP, selected bus, and CAN FD bitrates must be supplied for a real
deployment.

Provisioning scripts and systemd units will be added after the target host is
audited and the networking values are known.

The initial machine handoff prompt is stored in
[`docs/raspberry-pi-handoff-prompt.md`](../../docs/raspberry-pi-handoff-prompt.md).

Upstream documentation:

- https://github.com/VBCores/ethernet-can
