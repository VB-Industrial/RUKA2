import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, SetEnvironmentVariable
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration, PythonExpression
from launch_ros.actions import Node
from moveit_configs_utils import MoveItConfigsBuilder


def generate_launch_description():
    use_mock_hardware = LaunchConfiguration("use_mock_hardware")
    end_effector_type = LaunchConfiguration("end_effector_type")
    can_interface = LaunchConfiguration("can_interface")
    gripper_can_interface = LaunchConfiguration("gripper_can_interface")
    fastdds_profile = os.path.join(
        get_package_share_directory("ruka_spb"), "config", "fastdds_udp.xml"
    )

    moveit_config = (
        MoveItConfigsBuilder("ruka", package_name="ruka_spb")
        .robot_description(
            file_path="config/ruka.urdf.xacro",
            mappings={
                "use_mock_hardware": use_mock_hardware,
                "end_effector_type": end_effector_type,
                "can_interface": can_interface,
                "gripper_can_interface": gripper_can_interface,
            },
        )
        .robot_description_semantic(
            file_path="config/ruka.srdf",
            mappings={"end_effector_type": end_effector_type},
        )
        .planning_pipelines(pipelines=["ompl"])
        .to_moveit_configs()
    )

    static_tf_node = Node(
        package="tf2_ros",
        executable="static_transform_publisher",
        name="static_transform_publisher",
        output="log",
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
    )

    robot_state_publisher = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        output="both",
        parameters=[moveit_config.robot_description],
    )

    controllers_file = os.path.join(
        get_package_share_directory("ruka_spb"),
        "config",
        "ros2_controllers.yaml",
    )
    ros2_control_node = Node(
        package="controller_manager",
        executable="ros2_control_node",
        parameters=[controllers_file],
        remappings=[
            ("/controller_manager/robot_description", "/robot_description"),
        ],
        output="screen",
    )

    joint_state_broadcaster = Node(
        package="controller_manager",
        executable="spawner",
        arguments=[
            "joint_state_broadcaster",
            "--controller-manager",
            "/controller_manager",
        ],
    )
    arm_controller = Node(
        package="controller_manager",
        executable="spawner",
        arguments=[
            "ruka_arm_controller",
            "--controller-manager",
            "/controller_manager",
        ],
    )
    hand_controller = Node(
        package="controller_manager",
        executable="spawner",
        arguments=[
            "ruka_hand_controller",
            "--controller-manager",
            "/controller_manager",
        ],
        condition=IfCondition(
            PythonExpression(["'", end_effector_type, "' == 'mechanical'"])
        ),
    )

    return LaunchDescription(
        [
            SetEnvironmentVariable("RMW_IMPLEMENTATION", "rmw_fastrtps_cpp"),
            SetEnvironmentVariable("RMW_FASTRTPS_USE_QOS_FROM_XML", "1"),
            SetEnvironmentVariable("FASTDDS_DEFAULT_PROFILES_FILE", fastdds_profile),
            SetEnvironmentVariable("FASTRTPS_DEFAULT_PROFILES_FILE", fastdds_profile),
            DeclareLaunchArgument(
                "use_mock_hardware",
                default_value="true",
                description="Использовать локальную имитацию оборудования вместо приводов RUKA2",
            ),
            DeclareLaunchArgument(
                "end_effector_type",
                default_value="mechanical",
                choices=["mechanical", "electromagnetic", "none"],
                description="Выбрать механический, электромагнитный захват или запуск без захвата",
            ),
            DeclareLaunchArgument(
                "can_interface",
                default_value="vcan1.0",
                description="Интерфейс SocketCAN для реального оборудования RUKA2",
            ),
            DeclareLaunchArgument(
                "gripper_can_interface",
                default_value="vcan1.2",
                description="Интерфейс SocketCAN для механического захвата VBDrive",
            ),
            static_tf_node,
            robot_state_publisher,
            ros2_control_node,
            joint_state_broadcaster,
            arm_controller,
            hand_controller,
        ]
    )
