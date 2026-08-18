"""Start MoveIt and optional RViz against an existing control stack."""

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
    can_interface = LaunchConfiguration("can_interface")
    use_rviz = LaunchConfiguration("use_rviz")

    moveit_config = (
        MoveItConfigsBuilder("ruka2", package_name="ruka2_moveit_config")
        .robot_description(
            file_path="config/ruka2.urdf.xacro",
            mappings={
                "use_mock_hardware": use_mock_hardware,
                "use_end_effector": use_end_effector,
                "can_interface": can_interface,
            },
        )
        .robot_description_semantic(file_path="config/ruka2.srdf")
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
                default_value="true",
                description="Build the same robot description as the active control profile",
            ),
            DeclareLaunchArgument(
                "use_end_effector",
                default_value="true",
                description="Include the gripper visual and collision geometry",
            ),
            DeclareLaunchArgument(
                "can_interface",
                default_value="vcan1.0",
                description="SocketCAN interface embedded in the real robot description",
            ),
            DeclareLaunchArgument(
                "use_rviz",
                default_value="true",
                description="Start RViz with the MoveIt plugin",
            ),
            move_group,
            rviz,
        ]
    )
