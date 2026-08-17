# RUKA2 architecture contract

Status: active baseline for implementation and hardware integration.

## Product packages

- `ruka2_control`
- `ruka2_firmware` as an external Git submodule
- `ruka2_description`
- `ruka2_moveit_config`

ROS package names are lowercase. The product and repository name is RUKA2.

## Supported platform

- Ubuntu 24.04
- ROS 2 Jazzy
- Raspberry Pi supports two runtime roles:
  - `server`: Ethernet-CAN bridge, `ros2_control`, controller manager, robot
    state publisher, and diagnostics;
  - `workstation`: everything in `server`, plus MoveIt, RViz, and local
    visualization.

The Raspberry Pi host runs Ubuntu 24.04 Desktop on ARM64 while retaining remote
administration and both runtime roles.

## Robot description

The canonical geometry baseline was delivered as `ruka.urdf` and imported into
`ruka2_description`. The delivered source SHA-256 is
`636ee55728b1e7bbe03136b55f579f75608bd8ef5503bfefcdde3c6f466c56f9`.
It is authoritative for:

- joint names and types;
- joint axes and directions;
- zero positions and position limits;
- visual and collision geometry;
- the robot base frame;
- arm joint position and velocity limits.

The six arm joints are normalized to `joint_1` through `joint_6`. The
kinematic chain runs from `base_link` through `link_06`. Gripper and finger
geometry remains present in the description, while gripper control and MoveIt
integration are deferred. Arm-link inertials and a dedicated tool/TCP frame
are also still pending.

`base frame` means the coordinate frame fixed to the robot mounting base and
used as the root for kinematics. `tool frame` means the reference frame at the
working end of the manipulator, normally the flange or tool centre point used
by MoveIt when planning an end-effector pose. Until a dedicated flange/TCP is
defined, MoveIt uses `link_06` as the arm tip.

## Firmware

Firmware source remains in the upstream repository and is consumed here as the
`firmware/ruka2_firmware` Git submodule. Functional fixes must be committed to
that upstream repository and then adopted here by updating the pinned submodule
revision.

Joint selection remains manual through `SR_JOINT_INDEX`. The operator selects
the connected joint, rebuilds, flashes, and then proceeds to the next driver.
No six-image build matrix is required.

The firmware's own embedded dependencies remain controlled by its upstream
repository. The ROS host uses the VB-Industrial `libcxxcanard` submodule at
`third_party/libcxxcanard`.

## Communication baseline

The current firmware is the source of truth. The validated baseline is commit
`e2b37e1847cee153c5d4fee5bee5046bfdcfb399`; the complete host contract is in
`interfaces/cyphal.md`.

The Linux Cyphal transport is deliberately serviced synchronously from the
`ros2_control` update path. No background RX/TX threads are used. This retains
the proven SilverHand execution model and keeps commissioning deterministic.

The Raspberry Pi has no physical SocketCAN adapter. The separate Ethernet-CAN
device transports CAN FD over UDP and the Linux host service exposes board
buses as `vcan1.x` SocketCAN interfaces. Board `ruka1.local` uses the following
mapping on the target Raspberry Pi (`192.168.30.146`):

- bus 0 / `vcan1.0`: arm;
- bus 1 / `vcan1.1`: gripper;
- bus 2 / `vcan1.2`: reserved powerboard transport (no application yet).

All three buses use CAN FD with BRS at 1 Mbit/s nominal and 8 Mbit/s data. The
Ethernet-CAN integration period is 10 ms. Board buses 3 through 5 are disabled.

## Deferred work

- arm-link inertial properties;
- dedicated flange/tool/TCP frames;
- gripper hardware and MoveIt integration;
- final self-collision matrix validation;
- final ROS DDS network parameters.
