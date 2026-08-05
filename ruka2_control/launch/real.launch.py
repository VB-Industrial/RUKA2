from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import Command, FindExecutable, LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    can_interface = LaunchConfiguration("can_interface")
    description_file = PathJoinSubstitution(
        [FindPackageShare("ruka2_control"), "urdf", "ruka2_control.urdf.xacro"]
    )
    controllers_file = PathJoinSubstitution(
        [FindPackageShare("ruka2_control"), "config", "controllers.yaml"]
    )
    robot_description = {
        "robot_description": ParameterValue(
            Command(
                [
                    FindExecutable(name="xacro"),
                    " ",
                    description_file,
                    " use_mock_hardware:=false can_interface:=",
                    can_interface,
                ]
            ),
            value_type=str,
        )
    }

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "can_interface",
                default_value="vcan1.0",
                description="SocketCAN interface supplied by the Ethernet-CAN bridge",
            ),
            Node(
                package="robot_state_publisher",
                executable="robot_state_publisher",
                parameters=[robot_description],
                output="screen",
            ),
            Node(
                package="controller_manager",
                executable="ros2_control_node",
                parameters=[robot_description, controllers_file],
                output="screen",
            ),
            Node(
                package="controller_manager",
                executable="spawner",
                arguments=["joint_state_broadcaster", "--controller-manager", "/controller_manager"],
                output="screen",
            ),
            Node(
                package="controller_manager",
                executable="spawner",
                arguments=["arm_controller", "--controller-manager", "/controller_manager"],
                output="screen",
            ),
        ]
    )
