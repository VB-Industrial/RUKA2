"""Запуск MoveIt и, при необходимости, RViz с существующим стеком управления."""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
from moveit_configs_utils import MoveItConfigsBuilder


def generate_launch_description():
    use_mock_hardware = LaunchConfiguration("use_mock_hardware")
    use_end_effector = LaunchConfiguration("use_end_effector")
    end_effector_type = LaunchConfiguration("end_effector_type")
    can_interface = LaunchConfiguration("can_interface")
    use_rviz = LaunchConfiguration("use_rviz")

    moveit_config = (
        MoveItConfigsBuilder("ruka2", package_name="ruka2_moveit_config")
        .robot_description(
            file_path="config/ruka2.urdf.xacro",
            mappings={
                "use_mock_hardware": use_mock_hardware,
                "use_end_effector": use_end_effector,
                "end_effector_type": end_effector_type,
                "can_interface": can_interface,
            },
        )
        .robot_description_semantic(
            file_path="config/ruka2.srdf",
            mappings={"end_effector_type": end_effector_type},
        )
        .planning_scene_monitor()
        .trajectory_execution(
            file_path="config/moveit_controllers.yaml",
            moveit_manage_controllers=False,
        )
        .planning_pipelines(default_planning_pipeline="ompl", pipelines=["ompl"])
        .to_moveit_configs()
    )

    move_group = Node(
        package="moveit_ros_move_group",
        executable="move_group",
        output="screen",
        parameters=[moveit_config.to_dict()],
    )

    rviz_config = PathJoinSubstitution(
        [FindPackageShare("ruka2_moveit_config"), "config", "moveit.rviz"]
    )
    rviz = Node(
        package="rviz2",
        executable="rviz2",
        name="rviz2",
        arguments=["-d", rviz_config],
        parameters=[
            moveit_config.robot_description,
            moveit_config.robot_description_semantic,
            moveit_config.planning_pipelines,
            moveit_config.robot_description_kinematics,
            moveit_config.joint_limits,
        ],
        condition=IfCondition(use_rviz),
        output="log",
    )

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "use_mock_hardware",
                default_value="false",
                description="Создать описание робота, соответствующее активному профилю управления",
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
                description="Интерфейс SocketCAN в описании реального робота",
            ),
            DeclareLaunchArgument(
                "use_rviz",
                default_value="true",
                description="Запустить RViz с плагином MoveIt",
            ),
            move_group,
            rviz,
        ]
    )
