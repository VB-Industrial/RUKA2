import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
ARM_JOINTS = {f"joint_{index}" for index in range(1, 7)}
PASSIVE_JOINTS = {
    "link_hand_cyl__first_fin",
    "link_hand_cyl__second_fin",
}


def test_mock_hardware_exports_all_arm_joints():
    result = subprocess.run(
        ["xacro", str(PACKAGE_ROOT / "urdf/ruka2_control.urdf.xacro")],
        check=True,
        capture_output=True,
        text=True,
    )
    robot = ET.fromstring(result.stdout)
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
            assert command_interfaces == ["position"]
        else:
            assert command_interfaces == []
