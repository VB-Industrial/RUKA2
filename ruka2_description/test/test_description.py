import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
ARM_JOINTS = {f"joint_{index}" for index in range(1, 7)}
FINGER_JOINTS = {
    "link_hand_cyl__first_fin",
    "link_hand_cyl__second_fin",
}


def expand_xacro(relative_path):
    result = subprocess.run(
        ["xacro", str(PACKAGE_ROOT / relative_path)],
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
    assert {"link_hand_cyl", "first_fin", "second_fin"}.issubset(link_names)

    movable_joints = {
        joint.attrib["name"]
        for joint in robot.findall("joint")
        if joint.attrib["type"] != "fixed"
    }
    assert movable_joints == ARM_JOINTS | FINGER_JOINTS


def test_arm_limits_and_meshes_come_from_canonical_model():
    robot = expand_xacro("urdf/ruka2.urdf.xacro")
    expected_limits = {
        "joint_1": ("-2.96", "2.96", "0.75"),
        "joint_2": ("-3.57", "0.05", "0.6"),
        "joint_3": ("-0.035", "5.23", "0.75"),
        "joint_4": ("-2.87", "2.87", "2.0"),
        "joint_5": ("-2.44", "2.44", "2.5"),
        "joint_6": ("-3.14", "3.14", "6.0"),
    }
    joints = {joint.attrib["name"]: joint for joint in robot.findall("joint")}
    for name, expected in expected_limits.items():
        limit = joints[name].find("limit")
        assert limit is not None
        assert (limit.attrib["lower"], limit.attrib["upper"], limit.attrib["velocity"]) == expected

    mesh_uris = {mesh.attrib["filename"] for mesh in robot.findall(".//mesh")}
    assert mesh_uris == {
        "package://ruka2_description/meshes/gripper4310.stl",
        "package://ruka2_description/meshes/finger50mm-S.stl",
        "package://ruka2_description/meshes/finger50mm-S-1.stl",
    }
