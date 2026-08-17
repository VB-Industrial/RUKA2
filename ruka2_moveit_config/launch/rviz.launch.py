import os

import yaml
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import Command, FindExecutable, LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare


def load_text(package_name, relative_path):
    path = os.path.join(get_package_share_directory(package_name), relative_path)
    with open(path, "r", encoding="utf-8") as source:
        return source.read()


def load_yaml(package_name, relative_path):
    path = os.path.join(get_package_share_directory(package_name), relative_path)
    with open(path, "r", encoding="utf-8") as source:
        return yaml.safe_load(source)


def generate_launch_description():
    use_mock_hardware = LaunchConfiguration("use_mock_hardware")
    can_interface = LaunchConfiguration("can_interface")
    description_file = PathJoinSubstitution(
        [FindPackageShare("ruka2_control"), "urdf", "ruka2_control.urdf.xacro"]
    )
    robot_description = {
        "robot_description": ParameterValue(
            Command(
                [FindExecutable(name="xacro"), " ", description_file,
                 " use_mock_hardware:=", use_mock_hardware,
                 " can_interface:=", can_interface]
            ),
            value_type=str,
        )
    }
    rviz_config = PathJoinSubstitution(
        [FindPackageShare("ruka2_moveit_config"), "rviz", "moveit.rviz"]
    )

    return LaunchDescription(
        [
            DeclareLaunchArgument("use_mock_hardware", default_value="true"),
            DeclareLaunchArgument("can_interface", default_value="vcan1.0"),
            Node(
                package="rviz2",
                executable="rviz2",
                name="rviz2",
                arguments=["-d", rviz_config],
                output="screen",
                parameters=[
                    robot_description,
                    {
                        "robot_description_semantic": load_text(
                            "ruka2_moveit_config", "config/ruka2.srdf"
                        )
                    },
                    {
                        "robot_description_kinematics": load_yaml(
                            "ruka2_moveit_config", "config/kinematics.yaml"
                        )
                    },
                    {
                        "robot_description_planning": load_yaml(
                            "ruka2_moveit_config", "config/joint_limits.yaml"
                        )
                    },
                    {
                        "planning_pipelines": ["ompl"],
                        "default_planning_pipeline": "ompl",
                        "ompl": load_yaml("ruka2_moveit_config", "config/ompl_planning.yaml"),
                    },
                ],
            ),
        ]
    )
