from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution, PythonExpression
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    start_control = LaunchConfiguration("start_control")
    use_mock_hardware = LaunchConfiguration("use_mock_hardware")
    can_interface = LaunchConfiguration("can_interface")
    use_rviz = LaunchConfiguration("use_rviz")

    return LaunchDescription(
        [
            DeclareLaunchArgument("start_control", default_value="true"),
            DeclareLaunchArgument("use_mock_hardware", default_value="true"),
            DeclareLaunchArgument("can_interface", default_value="vcan1.0"),
            DeclareLaunchArgument("use_rviz", default_value="true"),
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    PathJoinSubstitution(
                        [FindPackageShare("ruka2_control"), "launch", "mock.launch.py"]
                    )
                ),
                launch_arguments={"use_rviz": "false"}.items(),
                condition=IfCondition(
                    PythonExpression(
                        ["'", start_control, "' == 'true' and '", use_mock_hardware, "' == 'true'"]
                    )
                ),
            ),
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    PathJoinSubstitution(
                        [FindPackageShare("ruka2_control"), "launch", "real.launch.py"]
                    )
                ),
                launch_arguments={"can_interface": can_interface}.items(),
                condition=IfCondition(
                    PythonExpression(
                        ["'", start_control, "' == 'true' and '", use_mock_hardware, "' != 'true'"]
                    )
                ),
            ),
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    PathJoinSubstitution(
                        [FindPackageShare("ruka2_moveit_config"), "launch", "move_group.launch.py"]
                    )
                ),
                launch_arguments={
                    "use_mock_hardware": use_mock_hardware,
                    "can_interface": can_interface,
                }.items(),
            ),
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    PathJoinSubstitution(
                        [FindPackageShare("ruka2_moveit_config"), "launch", "rviz.launch.py"]
                    )
                ),
                launch_arguments={
                    "use_mock_hardware": use_mock_hardware,
                    "can_interface": can_interface,
                }.items(),
                condition=IfCondition(use_rviz),
            ),
        ]
    )
