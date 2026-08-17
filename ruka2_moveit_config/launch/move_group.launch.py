import os

import yaml
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
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
    publish_world_tf = LaunchConfiguration("publish_world_tf")
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
    robot_description_semantic = {
        "robot_description_semantic": load_text("ruka2_moveit_config", "config/ruka2.srdf")
    }
    robot_description_kinematics = {
        "robot_description_kinematics": load_yaml("ruka2_moveit_config", "config/kinematics.yaml")
    }
    robot_description_planning = {
        "robot_description_planning": load_yaml("ruka2_moveit_config", "config/joint_limits.yaml")
    }
    planning_pipeline = {
        "planning_pipelines": ["ompl"],
        "default_planning_pipeline": "ompl",
        "ompl": load_yaml("ruka2_moveit_config", "config/ompl_planning.yaml"),
    }
    trajectory_execution = {
        "moveit_manage_controllers": False,
        "trajectory_execution.allowed_execution_duration_scaling": 1.2,
        "trajectory_execution.allowed_goal_duration_margin": 0.5,
        "trajectory_execution.allowed_start_tolerance": 0.01,
    }
    planning_scene_monitor = {
        "publish_planning_scene": True,
        "publish_geometry_updates": True,
        "publish_state_updates": True,
        "publish_transforms_updates": True,
        "publish_robot_description": True,
        "publish_robot_description_semantic": True,
    }

    return LaunchDescription(
        [
            DeclareLaunchArgument("use_mock_hardware", default_value="true"),
            DeclareLaunchArgument("can_interface", default_value="vcan1.0"),
            DeclareLaunchArgument("publish_world_tf", default_value="true"),
            Node(
                package="tf2_ros",
                executable="static_transform_publisher",
                arguments=[
                    "--x", "0", "--y", "0", "--z", "0",
                    "--roll", "0", "--pitch", "0", "--yaw", "0",
                    "--frame-id", "world", "--child-frame-id", "base_link",
                ],
                output="screen",
                condition=IfCondition(publish_world_tf),
            ),
            Node(
                package="moveit_ros_move_group",
                executable="move_group",
                output="screen",
                parameters=[
                    robot_description,
                    robot_description_semantic,
                    robot_description_kinematics,
                    robot_description_planning,
                    planning_pipeline,
                    load_yaml("ruka2_moveit_config", "config/moveit_controllers.yaml"),
                    trajectory_execution,
                    planning_scene_monitor,
                    {"use_sim_time": False},
                ],
            ),
        ]
    )
