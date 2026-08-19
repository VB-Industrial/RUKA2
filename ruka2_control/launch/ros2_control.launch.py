"""Запуск описания робота RUKA2 и стека ros2_control."""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import (
    Command,
    FindExecutable,
    LaunchConfiguration,
    PythonExpression,
)
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    use_mock_hardware = LaunchConfiguration("use_mock_hardware")
    use_end_effector = LaunchConfiguration("use_end_effector")
    end_effector_type = LaunchConfiguration("end_effector_type")
    can_interface = LaunchConfiguration("can_interface")

    package_share = get_package_share_directory("ruka2_control")
    description_file = os.path.join(
        package_share, "config", "ruka2_control.urdf.xacro"
    )
    controllers_file = os.path.join(
        package_share, "config", "ros2_controllers.yaml"
    )
    robot_description = {
        "robot_description": ParameterValue(
            Command(
                [
                    FindExecutable(name="xacro"),
                    " ",
                    description_file,
                    " use_mock_hardware:=",
                    use_mock_hardware,
                    " use_end_effector:=",
                    use_end_effector,
                    " end_effector_type:=",
                    end_effector_type,
                    " can_interface:=",
                    can_interface,
                ]
            ),
            value_type=str,
        )
    }

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "use_mock_hardware",
                default_value="true",
                description=(
                    "Использовать ros2_control GenericSystem вместо реального оборудования RUKA2"
                ),
            ),
            DeclareLaunchArgument(
                "use_end_effector",
                default_value="true",
                description="Добавить визуальную и коллизионную геометрию захвата",
            ),
            DeclareLaunchArgument(
                "end_effector_type",
                default_value="mechanical",
                choices=["mechanical", "electromagnetic", "none"],
                description="Выбрать тип установленного захвата",
            ),
            DeclareLaunchArgument(
                "can_interface",
                default_value="vcan1.0",
                description="Интерфейс SocketCAN для плагина реального оборудования",
            ),
            Node(
                package="tf2_ros",
                executable="static_transform_publisher",
                name="world_to_base_link",
                arguments=[
                    "--x", "0.0",
                    "--y", "0.0",
                    "--z", "0.0",
                    "--roll", "0.0",
                    "--pitch", "0.0",
                    "--yaw", "0.0",
                    "--frame-id", "world",
                    "--child-frame-id", "base_link",
                ],
                output="log",
            ),
            Node(
                package="robot_state_publisher",
                executable="robot_state_publisher",
                parameters=[robot_description],
                output="both",
            ),
            Node(
                package="controller_manager",
                executable="ros2_control_node",
                parameters=[controllers_file],
                remappings=[
                    ("/controller_manager/robot_description", "/robot_description"),
                ],
                output="screen",
            ),
            Node(
                package="controller_manager",
                executable="spawner",
                arguments=[
                    "joint_state_broadcaster",
                    "--controller-manager",
                    "/controller_manager",
                ],
            ),
            Node(
                package="controller_manager",
                executable="spawner",
                arguments=[
                    "ruka_arm_controller",
                    "--controller-manager",
                    "/controller_manager",
                ],
            ),
            Node(
                package="controller_manager",
                executable="spawner",
                arguments=[
                    "mechanical_gripper_controller",
                    "--controller-manager",
                    "/controller_manager",
                ],
                condition=IfCondition(
                    PythonExpression(
                        [
                            "'",
                            use_mock_hardware,
                            "'.lower() in ['true', '1', 'yes'] and '",
                            end_effector_type,
                            "'.lower() == 'mechanical'",
                        ]
                    )
                ),
            ),
        ]
    )
