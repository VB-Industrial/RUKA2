import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
ARM_JOINTS = {f"joint_{index}" for index in range(1, 7)}
PASSIVE_JOINTS = {
    "link_hand_cyl__first_fin",
    "link_hand_cyl__second_fin",
}
END_EFFECTOR_LINKS = {"link_hand_cyl", "first_fin", "second_fin"}


def render_control_description(*arguments):
    result = subprocess.run(
        [
            "xacro",
            str(PACKAGE_ROOT / "config/ruka2_control.urdf.xacro"),
            *arguments,
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return ET.fromstring(result.stdout)


def test_mock_hardware_exports_all_arm_joints():
    robot = render_control_description()
    control = robot.find("ros2_control")
    assert control is not None
    assert control.findtext("hardware/plugin") == "mock_components/GenericSystem"

    control_joints = {joint.attrib["name"] for joint in control.findall("joint")}
    assert control_joints == ARM_JOINTS | PASSIVE_JOINTS
    for joint in control.findall("joint"):
        command_interfaces = [
            item.attrib["name"] for item in joint.findall("command_interface")
        ]
        if joint.attrib["name"] in ARM_JOINTS:
            assert command_interfaces == ["position", "velocity"]
        elif joint.attrib["name"] == "link_hand_cyl__first_fin":
            assert command_interfaces == ["position"]
        else:
            assert command_interfaces == []


def test_real_hardware_exports_only_six_arm_joints():
    robot = render_control_description("use_mock_hardware:=false")
    control = robot.find("ros2_control")
    assert control is not None
    assert control.findtext("hardware/plugin") == "ruka2_control/Ruka2System"
    assert control.findtext("hardware/param[@name='can_interface']") == "vcan1.0"
    assert {joint.attrib["name"] for joint in control.findall("joint")} == ARM_JOINTS


def test_end_effector_geometry_is_optional_without_changing_the_contract():
    mechanical = render_control_description()
    electromagnetic = render_control_description(
        "end_effector_type:=electromagnetic"
    )
    without_end_effector = render_control_description("end_effector_type:=none")

    for link_name in END_EFFECTOR_LINKS:
        visible_link = mechanical.find(f"./link[@name='{link_name}']")
        hidden_link = without_end_effector.find(f"./link[@name='{link_name}']")
        assert visible_link is not None
        assert visible_link.find("visual") is not None
        assert visible_link.find("collision") is not None
        assert hidden_link is not None
        assert hidden_link.find("visual") is None
        assert hidden_link.find("collision") is None

    assert electromagnetic.find("./link[@name='link_hand_cyl']/visual") is not None
    assert electromagnetic.find("./link[@name='tool0']") is not None

    for robot in (mechanical, electromagnetic, without_end_effector):
        control = robot.find("ros2_control")
        assert {joint.attrib["name"] for joint in control.findall("joint")} == (
            ARM_JOINTS | PASSIVE_JOINTS
        )

    for robot in (electromagnetic, without_end_effector):
        for joint_name in PASSIVE_JOINTS:
            joint = robot.find(f"./ros2_control/joint[@name='{joint_name}']")
            assert joint.findall("command_interface") == []
