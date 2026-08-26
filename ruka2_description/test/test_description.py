import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
ARM_JOINTS = {f"joint_{index}" for index in range(1, 7)}
FINGER_JOINTS = {
    "link_hand_cyl__first_fin",
    "link_hand_cyl__second_fin",
}


def expand_xacro(relative_path, *arguments):
    result = subprocess.run(
        ["xacro", str(PACKAGE_ROOT / relative_path), *arguments],
        check=True,
        capture_output=True,
        text=True,
    )
    return ET.fromstring(result.stdout)


def test_description_has_expected_arm_and_retained_gripper():
    robot = expand_xacro("urdf/ruka2.urdf.xacro")
    assert robot.attrib["name"] == "ruka2"

    link_names = {link.attrib["name"] for link in robot.findall("link")}
    assert {"base_link", "link_01", "link_02", "link_03", "link_04", "link_05", "link_06"}.issubset(link_names)
    assert {"link_hand_cyl", "first_fin", "second_fin", "tool0"}.issubset(
        link_names
    )

    movable_joints = {
        joint.attrib["name"]
        for joint in robot.findall("joint")
        if joint.attrib["type"] != "fixed"
    }
    assert movable_joints == ARM_JOINTS | FINGER_JOINTS

    tool0_origin = robot.find("./joint[@name='link_06__tool0']/origin")
    assert tool0_origin.attrib == {"rpy": "0 0.0 0", "xyz": "0.0 0 0.1162"}

    second_finger = robot.find(
        "./joint[@name='link_hand_cyl__second_fin']/mimic"
    )
    assert second_finger.attrib == {
        "joint": "link_hand_cyl__first_fin",
        "multiplier": "1.0",
        "offset": "0.0",
    }


def test_arm_limits_and_meshes_come_from_canonical_model():
    robot = expand_xacro("urdf/ruka2.urdf.xacro")
    expected_limits = {
        "joint_1": ("-2.91", "2.91", "0.75"),
        "joint_2": ("-3.37", "0.02", "0.6"),
        "joint_3": ("0.0", "5.11", "0.75"),
        "joint_4": ("-2.42", "3.20", "2.0"),
        "joint_5": ("-2.39", "2.39", "2.5"),
        "joint_6": ("-2.82", "2.84", "6.0"),
    }
    joints = {joint.attrib["name"]: joint for joint in robot.findall("joint")}
    for name, expected in expected_limits.items():
        limit = joints[name].find("limit")
        assert limit is not None
        assert (limit.attrib["lower"], limit.attrib["upper"], limit.attrib["velocity"]) == expected
        # MoveIt должен использовать калиброванные жёсткие границы из limit.
        # Дополнительный safety_controller сузил бы их и сделал допустимое
        # положение около физического нуля некорректным стартовым состоянием.
        assert joints[name].find("safety_controller") is None

    mesh_uris = {mesh.attrib["filename"] for mesh in robot.findall(".//mesh")}
    assert mesh_uris == {
        "package://ruka2_description/meshes/gripper4310.stl",
        "package://ruka2_description/meshes/finger50mm-S.stl",
        "package://ruka2_description/meshes/finger50mm-S-1.stl",
    }


def test_electromagnetic_gripper_dimensions_and_grasp_frame():
    robot = expand_xacro(
        "urdf/ruka2.urdf.xacro",
        "end_effector_type:=electromagnetic",
    )
    hand = robot.find("./link[@name='link_hand_cyl']")
    assert hand is not None

    visual = hand.find("./visual[@name='electromagnetic_gripper_visual']")
    assert visual.find("origin").attrib == {
        "rpy": "0 0 -1.5707963268",
        "xyz": "-0.02 -0.0150980395 -0.0162865356",
    }
    assert visual.find("geometry/mesh").attrib["filename"] == (
        "package://ruka2_description/meshes/mag-gripper.stl"
    )
    assert visual.find("material").attrib["name"] == "gray"
    assert robot.find("./material[@name='gray']/color").attrib["rgba"] == (
        "0.45 0.45 0.45 1"
    )

    collision = hand.find(
        "./collision[@name='electromagnetic_gripper_collision']"
    )
    assert collision.find("origin").attrib == visual.find("origin").attrib
    assert collision.find("geometry/mesh").attrib == visual.find(
        "geometry/mesh"
    ).attrib

    tool0_joint = robot.find("./joint[@name='link_06__tool0']")
    assert tool0_joint is not None
    assert tool0_joint.find("origin").attrib == {
        "rpy": "0 -0.436332313 0",
        "xyz": "-0.0272404332 0 0.0879375831",
    }
    assert tool0_joint.find("parent").attrib["link"] == "link_06"
    assert tool0_joint.find("child").attrib["link"] == "tool0"
    assert robot.find("./link[@name='tool0']") is not None

    assert [mesh.attrib["filename"] for mesh in robot.findall(".//mesh")] == [
        "package://ruka2_description/meshes/mag-gripper.stl",
        "package://ruka2_description/meshes/mag-gripper.stl",
    ]
    for finger_name in ("first_fin", "second_fin"):
        finger = robot.find(f"./link[@name='{finger_name}']")
        assert finger.find("visual") is None
        assert finger.find("collision") is None


def test_no_end_effector_mode_remains_backward_compatible():
    selections = (
        ("end_effector_type:=none",),
        ("use_end_effector:=false",),
    )
    for arguments in selections:
        robot = expand_xacro("urdf/ruka2.urdf.xacro", *arguments)
        hand = robot.find("./link[@name='link_hand_cyl']")
        assert hand.find("visual") is None
        assert hand.find("collision") is None
        tool0_origin = robot.find("./joint[@name='link_06__tool0']/origin")
        assert tool0_origin.attrib == {"rpy": "0 0.0 0", "xyz": "0.0 0 0.0"}


def test_gripper_joints_can_be_fixed_for_real_hardware():
    for end_effector_type in ("mechanical", "electromagnetic", "none"):
        robot = expand_xacro(
            "urdf/ruka2.urdf.xacro",
            "enable_gripper_motion:=false",
            f"end_effector_type:={end_effector_type}",
        )
        for joint_name in FINGER_JOINTS:
            joint = robot.find(f"./joint[@name='{joint_name}']")
            assert joint.attrib["type"] == "fixed"
            assert joint.find("axis") is None
            assert joint.find("limit") is None
            assert joint.find("mimic") is None
