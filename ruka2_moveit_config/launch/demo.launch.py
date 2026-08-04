import os

import yaml
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
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
    start_control = LaunchConfiguration("start_control")
    use_rviz = LaunchConfiguration("use_rviz")
    description_file = PathJoinSubstitution(
        [FindPackageShare("ruka2_control"), "urdf", "ruka2_control.urdf.xacro"]
    )
    robot_description = {
        "robot_description": ParameterValue(
            Command([FindExecutable(name="xacro"), " ", description_file]), value_type=str
        )
    }
    robot_description_semantic = {
        "robot_description_semantic": load_text(
            "ruka2_moveit_config", "config/ruka2.srdf"
        )
    }
    robot_description_kinematics = {
        "robot_description_kinematics": load_yaml(
            "ruka2_moveit_config", "config/kinematics.yaml"
        )
    }
    robot_description_planning = {
        "robot_description_planning": load_yaml(
            "ruka2_moveit_config", "config/joint_limits.yaml"
        )
    }
    ompl = load_yaml("ruka2_moveit_config", "config/ompl_planning.yaml")
    planning_pipeline = {
        "planning_pipelines": ["ompl"],
        "default_planning_pipeline": "ompl",
        "ompl": ompl,
    }
    moveit_controllers = load_yaml(
        "ruka2_moveit_config", "config/moveit_controllers.yaml"
    )
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
    rviz_config = PathJoinSubstitution(
        [FindPackageShare("ruka2_moveit_config"), "rviz", "moveit.rviz"]
    )

    return LaunchDescription(
        [
            DeclareLaunchArgument("start_control", default_value="true"),
            DeclareLaunchArgument("use_rviz", default_value="true"),
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    PathJoinSubstitution(
                        [FindPackageShare("ruka2_control"), "launch", "mock.launch.py"]
                    )
                ),
                launch_arguments={"use_rviz": "false"}.items(),
                condition=IfCondition(start_control),
            ),
            Node(
                package="tf2_ros",
                executable="static_transform_publisher",
                arguments=[
                    "--x", "0", "--y", "0", "--z", "0",
                    "--roll", "0", "--pitch", "0", "--yaw", "0",
                    "--frame-id", "world", "--child-frame-id", "base_link",
                ],
                output="screen",
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
                    moveit_controllers,
                    trajectory_execution,
                    planning_scene_monitor,
                    {"use_sim_time": False},
                ],
            ),
            Node(
                package="rviz2",
                executable="rviz2",
                name="rviz2",
                arguments=["-d", rviz_config],
                output="screen",
                condition=IfCondition(use_rviz),
                parameters=[
                    robot_description,
                    robot_description_semantic,
                    robot_description_kinematics,
                    robot_description_planning,
                    planning_pipeline,
                ],
            ),
        ]
    )
