import xml.etree.ElementTree as ET
from pathlib import Path

import yaml


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PACKAGE_ROOT.parent
EXPECTED_JOINTS = tuple(f"joint_{index}" for index in range(1, 7))


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
    home_positions = {
        joint.attrib["name"]: float(joint.attrib["value"])
        for joint in home.findall("joint")
    }
    assert tuple(home_positions) == EXPECTED_JOINTS

    limits = load_yaml("joint_limits.yaml")["joint_limits"]
    assert tuple(limits) == EXPECTED_JOINTS
    assert all(limit["max_velocity"] == 0.1 for limit in limits.values())

    controllers = load_yaml("moveit_controllers.yaml")["moveit_simple_controller_manager"]
    assert controllers["controller_names"] == ["arm_controller"]
    assert tuple(controllers["arm_controller"]["joints"]) == EXPECTED_JOINTS

    kinematics = load_yaml("kinematics.yaml")
    assert tuple(kinematics) == ("ruka2_arm",)
    assert kinematics["ruka2_arm"]["kinematics_solver"].endswith(
        "/KDLKinematicsPlugin"
    )


def test_srdf_references_and_home_match_the_robot_description():
    model = ET.parse(
        REPOSITORY_ROOT / "ruka2_description/urdf/ruka2_macro.urdf.xacro"
    ).getroot()
    srdf = ET.parse(PACKAGE_ROOT / "config/ruka2.srdf").getroot()

    links = {link.attrib["name"] for link in model.findall(".//link")}
    joints = {joint.attrib["name"]: joint for joint in model.findall(".//joint")}
    assert {"base_link", "link_06"}.issubset(links)
    assert set(EXPECTED_JOINTS).issubset(joints)

    for collision in srdf.findall("disable_collisions"):
        assert collision.attrib["link1"] in links
        assert collision.attrib["link2"] in links

    for passive in srdf.findall("passive_joint"):
        assert passive.attrib["name"] in joints

    home = srdf.find("./group_state[@name='home']")
    for state in home.findall("joint"):
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
        for state in home.findall("joint")
    }
