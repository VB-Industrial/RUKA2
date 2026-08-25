from pathlib import Path
import xml.etree.ElementTree as ET

import xacro


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
ROBOT_XACRO = PACKAGE_ROOT / "config" / "ruka.urdf.xacro"


def joint_5(end_effector_type: str):
    document = xacro.process_file(
        str(ROBOT_XACRO),
        mappings={"end_effector_type": end_effector_type},
    )
    robot = ET.fromstring(document.toxml())
    return robot.find("./joint[@name='joint_5']")


def test_mechanical_gripper_limits_positive_joint_5_travel_to_75_degrees():
    joint = joint_5("mechanical")

    assert joint.find("limit").attrib == {
        "effort": "1000.0",
        "lower": "-2.39",
        "upper": "1.308996939",
        "velocity": "1.0",
    }
    safety = joint.find("safety_controller")
    assert safety.attrib["soft_lower_limit"] == "-2.313300981"
    assert safety.attrib["soft_upper_limit"] == "1.308996939"


def test_other_end_effectors_keep_the_existing_joint_5_limits():
    for end_effector_type in ("none", "electromagnetic"):
        joint = joint_5(end_effector_type)
        assert joint.find("limit").attrib["lower"] == "-2.39"
        assert joint.find("limit").attrib["upper"] == "2.39"
        safety = joint.find("safety_controller")
        assert safety.attrib["soft_lower_limit"] == "-2.313300981"
        assert safety.attrib["soft_upper_limit"] == "2.313300981"
