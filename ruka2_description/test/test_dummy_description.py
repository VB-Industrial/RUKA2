import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[1]


def expand_xacro(relative_path):
    result = subprocess.run(
        ["xacro", str(PACKAGE_ROOT / relative_path)],
        check=True,
        capture_output=True,
        text=True,
    )
    return ET.fromstring(result.stdout)


def test_dummy_description_has_expected_chain():
    robot = expand_xacro("urdf/ruka2.urdf.xacro")
    assert robot.attrib["name"] == "ruka2"

    link_names = {link.attrib["name"] for link in robot.findall("link")}
    assert {"base_link", "tool0"}.issubset(link_names)
    assert {f"link_{index}" for index in range(1, 7)}.issubset(link_names)

    movable_joints = {
        joint.attrib["name"]
        for joint in robot.findall("joint")
        if joint.attrib["type"] != "fixed"
    }
    assert movable_joints == {f"joint_{index}" for index in range(1, 7)}
