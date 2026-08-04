from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import Command, FindExecutable, LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    use_rviz = LaunchConfiguration("use_rviz")
    description_file = PathJoinSubstitution(
        [FindPackageShare("ruka2_control"), "urdf", "ruka2_control.urdf.xacro"]
    )
    controllers_file = PathJoinSubstitution(
        [FindPackageShare("ruka2_control"), "config", "controllers.yaml"]
    )
    rviz_config = PathJoinSubstitution(
        [FindPackageShare("ruka2_description"), "rviz", "display.rviz"]
    )
    robot_description = {
        "robot_description": ParameterValue(
            Command([FindExecutable(name="xacro"), " ", description_file]), value_type=str
        )
    }

    return LaunchDescription(
        [
            DeclareLaunchArgument("use_rviz", default_value="true"),
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
            Node(
                package="rviz2",
                executable="rviz2",
                arguments=["-d", rviz_config],
                condition=IfCondition(use_rviz),
                output="screen",
            ),
        ]
    )
