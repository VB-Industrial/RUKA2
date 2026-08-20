import ast
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


def launch_argument_default(path, argument_name):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Name):
            continue
        if node.func.id != "DeclareLaunchArgument" or not node.args:
            continue
        if not isinstance(node.args[0], ast.Constant):
            continue
        if node.args[0].value != argument_name:
            continue
        default = next(
            keyword.value
            for keyword in node.keywords
            if keyword.arg == "default_value"
        )
        return default.value
    raise AssertionError(f"Launch argument {argument_name!r} was not found")


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
    robot = render_control_description("use_mock_hardware:=true")
    control = robot.find("ros2_control")
    assert control is not None
    assert control.findtext("hardware/plugin") == "mock_components/GenericSystem"
    assert robot.find("./joint[@name='link_hand_cyl__first_fin']").attrib[
        "type"
    ] == "prismatic"
    assert robot.find("./joint[@name='link_hand_cyl__second_fin']").attrib[
        "type"
    ] == "prismatic"

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


def test_real_hardware_is_default_and_exports_only_six_arm_joints():
    robot = render_control_description()
    control = robot.find("ros2_control")
    assert control is not None
    assert control.findtext("hardware/plugin") == "ruka2_control/Ruka2System"
    assert control.findtext("hardware/param[@name='can_interface']") == "vcan1.0"
    assert {joint.attrib["name"] for joint in control.findall("joint")} == ARM_JOINTS
    for joint_name in PASSIVE_JOINTS:
        joint = robot.find(f"./joint[@name='{joint_name}']")
        assert joint.attrib["type"] == "fixed"
        assert joint.find("axis") is None
        assert joint.find("limit") is None
        assert joint.find("mimic") is None


def test_standalone_control_defaults_to_real_hardware():
    launch_file = PACKAGE_ROOT / "launch/ros2_control.launch.py"
    assert launch_argument_default(launch_file, "use_mock_hardware") == "false"


def test_end_effector_geometry_is_optional_without_changing_the_contract():
    mechanical = render_control_description("use_mock_hardware:=true")
    electromagnetic = render_control_description(
        "use_mock_hardware:=true",
        "end_effector_type:=electromagnetic"
    )
    without_end_effector = render_control_description(
        "use_mock_hardware:=true", "end_effector_type:=none"
    )

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
