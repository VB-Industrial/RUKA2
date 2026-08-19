import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

import yaml


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PACKAGE_ROOT.parent
EXPECTED_JOINTS = tuple(f"joint_{index}" for index in range(1, 7))
GRIPPER_JOINT = "link_hand_cyl__first_fin"


def load_yaml(name):
    return yaml.safe_load((PACKAGE_ROOT / "config" / name).read_text(encoding="utf-8"))


def render_srdf(end_effector_type="mechanical"):
    result = subprocess.run(
        [
            "xacro",
            str(PACKAGE_ROOT / "config/ruka2.srdf"),
            f"end_effector_type:={end_effector_type}",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return ET.fromstring(result.stdout)


def test_srdf_and_controller_contract_are_consistent():
    srdf = render_srdf()
    group = srdf.find("./group[@name='ruka_arm_controller']")
    assert group is not None
    chain = group.find("chain")
    assert chain is not None
    assert chain.attrib == {"base_link": "base_link", "tip_link": "tool0"}

    gripper = srdf.find("./group[@name='mechanical_gripper']")
    assert gripper is not None
    assert [joint.attrib["name"] for joint in gripper.findall("joint")] == [
        GRIPPER_JOINT
    ]
    assert srdf.find("./group_state[@name='closed']").find("joint").attrib == {
        "name": GRIPPER_JOINT,
        "value": "0.0",
    }
    assert srdf.find("./group_state[@name='open']").find("joint").attrib == {
        "name": GRIPPER_JOINT,
        "value": "0.01",
    }

    passive_joints = {joint.attrib["name"] for joint in srdf.findall("passive_joint")}
    assert passive_joints == {"link_hand_cyl__second_fin"}
    assert render_srdf("electromagnetic").find(
        "./group[@name='mechanical_gripper']"
    ) is None

    start = srdf.find("./group_state[@name='start']")
    assert start is not None
    start_positions = {
        joint.attrib["name"]: float(joint.attrib["value"])
        for joint in start.findall("joint")
    }
    assert tuple(start_positions) == EXPECTED_JOINTS

    limits = load_yaml("joint_limits.yaml")["joint_limits"]
    assert tuple(limits) == EXPECTED_JOINTS + (GRIPPER_JOINT,)
    assert all(limits[name]["max_velocity"] == 0.177778 for name in EXPECTED_JOINTS)
    assert all(
        limit["max_acceleration"] == 1.333333
        for name, limit in limits.items()
        if name != "joint_6"
        and name != GRIPPER_JOINT
    )
    assert limits["joint_6"]["max_acceleration"] == 2.666667
    assert limits[GRIPPER_JOINT]["max_velocity"] == 0.2
    assert limits[GRIPPER_JOINT]["max_acceleration"] == 0.4

    controllers = load_yaml("moveit_controllers.yaml")["moveit_simple_controller_manager"]
    assert controllers["controller_names"] == [
        "ruka_arm_controller",
        "mechanical_gripper_controller",
    ]
    assert tuple(controllers["ruka_arm_controller"]["joints"]) == EXPECTED_JOINTS
    assert controllers["mechanical_gripper_controller"]["joints"] == [GRIPPER_JOINT]

    kinematics = load_yaml("kinematics.yaml")
    assert tuple(kinematics) == ("ruka_arm_controller",)
    assert kinematics["ruka_arm_controller"]["kinematics_solver"].endswith(
        "/KDLKinematicsPlugin"
    )

    ros2_controllers = yaml.safe_load(
        (REPOSITORY_ROOT / "ruka2_control/config/ros2_controllers.yaml").read_text(
            encoding="utf-8"
        )
    )
    assert ros2_controllers["controller_manager"]["ros__parameters"]["update_rate"] == 100
    arm_parameters = ros2_controllers["ruka_arm_controller"]["ros__parameters"]
    assert arm_parameters["action_monitor_rate"] == 100.0
    assert arm_parameters["interpolation_method"] == "splines"
    gripper_parameters = ros2_controllers["mechanical_gripper_controller"][
        "ros__parameters"
    ]
    assert gripper_parameters["joints"] == [GRIPPER_JOINT]
    assert gripper_parameters["command_interfaces"] == ["position"]


def test_rviz_uses_a_neutral_goal_state_overlay():
    rviz = load_yaml("moveit.rviz")
    displays = rviz["Visualization Manager"]["Displays"]
    motion_planning = next(
        display
        for display in displays
        if display["Class"] == "moveit_rviz_plugin/MotionPlanning"
    )
    planning_request = motion_planning["Planning Request"]
    assert planning_request["Goal State Color"] == "255; 255; 255"
    assert planning_request["Goal State Alpha"] == 1.0
    assert planning_request["Colliding Link Color"] == "255; 0; 0"

    planned_path = motion_planning["Planned Path"]
    assert planned_path["Loop Animation"] is False
    assert planned_path["State Display Time"] == "0.033 s"
    assert planned_path["Trajectory Topic"] == "display_planned_path"


def test_srdf_references_and_start_match_the_robot_description():
    model = ET.parse(
        REPOSITORY_ROOT / "ruka2_description/urdf/ruka2_macro.urdf.xacro"
    ).getroot()
    srdf = render_srdf()

    links = {link.attrib["name"] for link in model.findall(".//link")}
    joints = {joint.attrib["name"]: joint for joint in model.findall(".//joint")}
    assert {"base_link", "link_06", "tool0"}.issubset(links)
    assert set(EXPECTED_JOINTS).issubset(joints)

    disabled_collisions = srdf.findall("disable_collisions")
    assert len(disabled_collisions) == 51
    for collision in disabled_collisions:
        assert collision.attrib["link1"] in links
        assert collision.attrib["link2"] in links

    disabled_pairs = {
        frozenset((collision.attrib["link1"], collision.attrib["link2"]))
        for collision in disabled_collisions
    }
    assert frozenset(("link_05_red", "link_hand_cyl")) not in disabled_pairs
    assert frozenset(("link_06", "link_hand_cyl")) in disabled_pairs

    for passive in srdf.findall("passive_joint"):
        assert passive.attrib["name"] in joints

    start = srdf.find("./group_state[@name='start']")
    for state in start.findall("joint"):
        limit = joints[state.attrib["name"]].find("limit")
        value = float(state.attrib["value"])
        assert float(limit.attrib["lower"]) <= value <= float(limit.attrib["upper"])

    initial_positions = yaml.safe_load(
        (REPOSITORY_ROOT / "ruka2_control/config/initial_positions.yaml").read_text(
            encoding="utf-8"
        )
    )["initial_positions"]
    assert initial_positions == {
        state.attrib["name"]: float(state.attrib["value"])
        for state in start.findall("joint")
    }
