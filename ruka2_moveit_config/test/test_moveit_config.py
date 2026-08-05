import xml.etree.ElementTree as ET
from pathlib import Path

import yaml


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
EXPECTED_JOINTS = {f"joint_{index}" for index in range(1, 7)}


def load_yaml(name):
    return yaml.safe_load((PACKAGE_ROOT / "config" / name).read_text(encoding="utf-8"))


def test_srdf_and_controller_contract_are_consistent():
    srdf = ET.parse(PACKAGE_ROOT / "config/ruka2.srdf").getroot()
    group = srdf.find("./group[@name='ruka2_arm']")
    assert group is not None
    chain = group.find("chain")
    assert chain is not None
    assert chain.attrib == {"base_link": "base_link", "tip_link": "link_06"}

    passive_joints = {joint.attrib["name"] for joint in srdf.findall("passive_joint")}
    assert passive_joints == {
        "link_hand_cyl__first_fin",
        "link_hand_cyl__second_fin",
    }

    home = srdf.find("./group_state[@name='home']")
    assert home is not None
    assert {joint.attrib["name"] for joint in home.findall("joint")} == EXPECTED_JOINTS

    limits = load_yaml("joint_limits.yaml")["joint_limits"]
    assert set(limits) == EXPECTED_JOINTS
    assert all(limit["max_velocity"] == 0.1 for limit in limits.values())

    controllers = load_yaml("moveit_controllers.yaml")["moveit_simple_controller_manager"]
    assert controllers["controller_names"] == ["arm_controller"]
    assert set(controllers["arm_controller"]["joints"]) == EXPECTED_JOINTS
