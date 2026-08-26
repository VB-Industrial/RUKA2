import math
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

import yaml


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
CLOSED_POSITION = 0.008
OPEN_POSITION = 0.025
CLOSED_ANGLE = -0.3880
OPEN_ANGLE = 2.1824
MAXIMUM_MOTOR_VELOCITY = 2.0
PLANNED_JOINT_VELOCITY = 0.012
MAXIMUM_MOTOR_TORQUE = 0.50
WARNING_MOTOR_TORQUE = 0.35
MAXIMUM_JOINT_FORCE = 30.0
GRIPPER_FEEDBACK_TIMEOUT = 12.0


def expand(use_mock_hardware):
    output = subprocess.run(
        [
            "xacro",
            str(PACKAGE_ROOT / "config/ruka.urdf.xacro"),
            f"use_mock_hardware:={str(use_mock_hardware).lower()}",
            "end_effector_type:=mechanical",
        ],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    return ET.fromstring(output)


def gripper_control(root):
    return next(
        control
        for control in root.findall("ros2_control")
        if control.attrib["name"].endswith("Gripper")
    )


def test_mock_and_real_export_the_same_gripper_interfaces():
    for mock in (True, False):
        control = gripper_control(expand(mock))
        joint = control.find("./joint[@name='link_hand_cyl__first_fin']")
        assert [item.attrib["name"] for item in joint.findall("command_interface")] == [
            "position",
            "effort",
        ]
        assert [item.attrib["name"] for item in joint.findall("state_interface")] == [
            "position",
            "velocity",
            "effort",
        ]


def test_real_gripper_uses_experimentally_verified_contract():
    control = gripper_control(expand(False))
    parameters = {
        item.attrib["name"]: item.text for item in control.findall("hardware/param")
    }
    assert control.findtext("hardware/plugin") == "ruka_spb/VBDriveGripperSystem"
    assert parameters["can_interface"] == "vcan1.2"
    assert parameters["drive_node_id"] == "11"
    assert parameters["feedback_subject_id"] == "3811"
    assert parameters["command_subject_id"] == "2118"
    assert float(parameters["joint_closed_position"]) == CLOSED_POSITION
    assert float(parameters["joint_open_position"]) == OPEN_POSITION
    assert float(parameters["motor_closed_angle"]) == CLOSED_ANGLE
    assert float(parameters["motor_open_angle"]) == OPEN_ANGLE
    assert float(parameters["maximum_motor_velocity"]) == MAXIMUM_MOTOR_VELOCITY
    assert float(parameters["angle_kp"]) == 2.5
    assert float(parameters["velocity_kp"]) == 0.0
    assert float(parameters["maximum_motor_torque"]) == MAXIMUM_MOTOR_TORQUE
    assert float(parameters["warning_motor_torque"]) == WARNING_MOTOR_TORQUE
    assert float(parameters["maximum_joint_force"]) == MAXIMUM_JOINT_FORCE
    assert float(parameters["feedback_timeout"]) == GRIPPER_FEEDBACK_TIMEOUT


def test_force_torque_conversion_matches_virtual_work():
    aperture_meters_per_radian = (OPEN_POSITION - CLOSED_POSITION) / (
        OPEN_ANGLE - CLOSED_ANGLE
    )
    assert math.isclose(aperture_meters_per_radian, 0.0066137566138, rel_tol=1e-9)
    assert math.isclose(0.09 / aperture_meters_per_radian, 13.608, rel_tol=1e-9)
    assert math.isclose(
        MAXIMUM_JOINT_FORCE * aperture_meters_per_radian,
        0.1984126984127,
        rel_tol=1e-9,
    )


def test_explicit_effort_command_stays_inside_motor_torque_limit():
    aperture_meters_per_radian = (OPEN_POSITION - CLOSED_POSITION) / (
        OPEN_ANGLE - CLOSED_ANGLE
    )
    maximum_explicit_torque = MAXIMUM_JOINT_FORCE * aperture_meters_per_radian
    assert maximum_explicit_torque < MAXIMUM_MOTOR_TORQUE


def test_moveit_position_and_force_use_separate_controllers():
    controllers = yaml.safe_load(
        (PACKAGE_ROOT / "config/ros2_controllers.yaml").read_text()
    )
    hand = controllers["ruka_hand_controller"]["ros__parameters"]
    force = controllers["ruka_gripper_effort_controller"]["ros__parameters"]
    assert hand["command_interfaces"] == ["position"]
    assert force["joints"] == ["link_hand_cyl__first_fin"]
    assert force["interface_name"] == "effort"


def test_gripper_planning_speed_matches_hardware_limit():
    root = expand(False)
    for joint_name in (
        "link_hand_cyl__first_fin",
        "link_hand_cyl__second_fin",
    ):
        limit = root.find(f"./joint[@name='{joint_name}']/limit")
        assert limit is not None
        assert float(limit.attrib["velocity"]) == PLANNED_JOINT_VELOCITY

    limits = yaml.safe_load(
        (PACKAGE_ROOT / "config/joint_limits.yaml").read_text()
    )["joint_limits"]
    for joint_name in (
        "link_hand_cyl__first_fin",
        "link_hand_cyl__second_fin",
    ):
        assert limits[joint_name]["max_velocity"] == PLANNED_JOINT_VELOCITY


def test_gripper_controller_allows_for_measured_feedback_period():
    controllers = yaml.safe_load(
        (PACKAGE_ROOT / "config/ros2_controllers.yaml").read_text()
    )
    constraints = controllers["ruka_hand_controller"]["ros__parameters"]["constraints"]
    joint_constraints = constraints["link_hand_cyl__first_fin"]
    assert constraints["goal_time"] >= 3.0
    assert joint_constraints["trajectory"] >= OPEN_POSITION - CLOSED_POSITION
    assert joint_constraints["goal"] == 0.001

    moveit_execution = yaml.safe_load(
        (PACKAGE_ROOT / "config/moveit_controllers.yaml").read_text()
    )["trajectory_execution"]
    assert (
        moveit_execution["allowed_goal_duration_margin"]
        >= constraints["goal_time"]
    )
