# RUKA2 Cyphal contract

Status: baseline copied from firmware commit
`69a5baa1404f26bed4da8b1a8dbdebe23dbb9766`; must be revalidated before real
hardware commissioning.

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

## Items to verify before implementation freeze

- actual current command modes and arbitration rules;
- heartbeat timing and controller-loss behavior;
- feedback rate and stale timeout;
- transfer-ID ownership per subject/session;
- diagnostics and fault status required by ROS;
- Ethernet-CAN bus mapping and CAN FD nominal/data bitrates;
- whether any current firmware register needs a ROS service or diagnostic
  bridge.
