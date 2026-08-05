# RUKA2 Cyphal contract

Status: validated against firmware commit
`95a7985eb131c2e4f3cae9331b51f92c67321301`.

## Nodes and subjects

| Direction | Joint/node mapping | Subject | Type | Purpose |
| --- | --- | --- | --- | --- |
| Controller to joints | controller `100`, joints `21..26` | `1121..1126` | `reg.udral.physics.kinematics.rotation.Planar.0.1` | Servo position, velocity, acceleration |
| Controller to joints | controller `100`, joints `21..26` | `1131..1136` | `uavcan.si.unit.angular_velocity.Scalar.1.0` | Direct joint velocity in rad/s |
| Joints to controller | source nodes `21..26` | `1001` | `reg.udral.physics.kinematics.rotation.Planar.0.1` | Shared position and velocity feedback |
| All nodes | standard heartbeat | `7509` | `uavcan.node.Heartbeat.1.0` | Liveness and health |

Feedback on subject `1001` is associated with a joint using the Cyphal source
node-ID. The real hardware interface must reject unexpected source nodes and
stale feedback.

## Timing and command rules

- Joint feedback is published at 20 Hz.
- Joint heartbeat is published at 1 Hz.
- The controller publishes heartbeat at 1 Hz. Firmware accepts remote motion
  only from controller node `100` and stops it after 2.5 seconds without that
  heartbeat.
- Servo command timeout is 1 second. Repeating the same position changes the
  firmware from feed-forward tracking to its settling/hold logic.
- Maximum servo velocity is `0.1 rad/s` for every joint. The host sends the
  absolute velocity magnitude; firmware selects direction from position error.
- The host sends acceleration as zero, selecting the tested default firmware
  motion profile.
- Each command subject and the heartbeat subject own an independent transfer-ID
  sequence.

The real hardware defaults are feedback timeout `0.25 s`, heartbeat timeout
`2.5 s`, activation timeout `5 s`, and CAN interface `vcan1.0`. Activation
requires fresh feedback and heartbeat from all six nodes.

## Joint mapping

| ROS joint | Node | Servo subject | Direct subject | Firmware direction | Encoder inverted |
| --- | ---: | ---: | ---: | ---: | ---: |
| `joint_1` | 21 | 1121 | 1131 | +1 | yes |
| `joint_2` | 22 | 1122 | 1132 | -1 | no |
| `joint_3` | 23 | 1123 | 1133 | -1 | no |
| `joint_4` | 24 | 1124 | 1134 | +1 | yes |
| `joint_5` | 25 | 1125 | 1135 | -1 | no |
| `joint_6` | 26 | 1126 | 1136 | +1 | yes |

The firmware already converts native motor/encoder coordinates into
manipulator coordinates. The ROS hardware interface must not apply another
direction inversion.

## Diagnostics

Heartbeat health and its low eight firmware fault bits are published on the ROS
`/diagnostics` topic. Current fault mapping is documented in the firmware
README. Fault bits above bit 7 are available through firmware registers but do
not fit into the heartbeat vendor status byte; a ROS register bridge is
deferred.
