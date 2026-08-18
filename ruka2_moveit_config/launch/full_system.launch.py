"""Start the complete RUKA2 control, planning, and visualization system."""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    use_mock_hardware = LaunchConfiguration("use_mock_hardware")
    use_end_effector = LaunchConfiguration("use_end_effector")
    can_interface = LaunchConfiguration("can_interface")
    use_rviz = LaunchConfiguration("use_rviz")

    control = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution(
                [FindPackageShare("ruka2_control"), "launch", "ros2_control.launch.py"]
            )
        ),
        launch_arguments={
            "use_mock_hardware": use_mock_hardware,
            "use_end_effector": use_end_effector,
            "can_interface": can_interface,
        }.items(),
    )
    moveit = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution(
                [
                    FindPackageShare("ruka2_moveit_config"),
                    "launch",
                    "moveit.launch.py",
                ]
            )
        ),
        launch_arguments={
            "use_mock_hardware": use_mock_hardware,
            "use_end_effector": use_end_effector,
            "can_interface": can_interface,
            "use_rviz": use_rviz,
        }.items(),
    )

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "use_mock_hardware",
                default_value="true",
                description="Use mock hardware; set false for the real Cyphal system",
            ),
            DeclareLaunchArgument(
                "use_end_effector",
                default_value="true",
                description="Include the gripper visual and collision geometry",
            ),
            DeclareLaunchArgument(
                "can_interface",
                default_value="vcan1.0",
                description="SocketCAN interface used by the real hardware plugin",
            ),
            DeclareLaunchArgument(
                "use_rviz",
                default_value="true",
                description="Start RViz with the MoveIt plugin",
            ),
            control,
            moveit,
        ]
    )
