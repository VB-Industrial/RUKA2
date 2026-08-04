# RUKA2 architecture contract

Status: agreed baseline for repository scaffolding. Geometry-dependent details
remain deliberately deferred.

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

The initial Raspberry Pi host starts from Ubuntu Server and will be extended
with a supported desktop environment while retaining remote administration.

## Robot description

The canonical RUKA2 URDF is under development. It will be based on the
SilverHand description but will not be copied as the final model.

The future URDF is authoritative for:

- joint names and types;
- joint axes and directions;
- zero positions and position limits;
- visual, collision, and inertial geometry;
- the robot base frame;
- the flange/tool frames;
- optional sensor frames.

`base frame` means the coordinate frame fixed to the robot mounting base and
used as the root for kinematics. `tool frame` means the reference frame at the
working end of the manipulator, normally the flange or tool centre point used
by MoveIt when planning an end-effector pose. Their final names and transforms
are deferred until the canonical URDF arrives.

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

The current firmware is the source of truth. The subject and node table in
`interfaces/cyphal.md` must be revalidated against firmware before the real
hardware interface is declared compatible.

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

- canonical RUKA2 URDF and meshes;
- geometry-dependent `ruka2_description` implementation;
- SRDF, kinematics, collision matrix, and MoveIt configuration;
- final ROS DDS network parameters.
