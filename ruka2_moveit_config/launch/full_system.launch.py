"""Запуск полной системы управления, планирования и визуализации RUKA2."""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    use_mock_hardware = LaunchConfiguration("use_mock_hardware")
    use_end_effector = LaunchConfiguration("use_end_effector")
    end_effector_type = LaunchConfiguration("end_effector_type")
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
            "end_effector_type": end_effector_type,
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
            "end_effector_type": end_effector_type,
            "can_interface": can_interface,
            "use_rviz": use_rviz,
        }.items(),
    )

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "use_mock_hardware",
                default_value="true",
                description=(
                    "Использовать локальное mock-оборудование; для запуска всей "
                    "системы на манипуляторе укажите false"
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
            DeclareLaunchArgument(
                "use_rviz",
                default_value="true",
                description="Запустить RViz с плагином MoveIt",
            ),
            control,
            moveit,
        ]
    )
