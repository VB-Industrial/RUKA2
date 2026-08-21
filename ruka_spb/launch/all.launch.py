import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition, UnlessCondition
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution, PythonExpression
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
from moveit_configs_utils import MoveItConfigsBuilder


def generate_launch_description():
    use_mock_hardware = LaunchConfiguration("use_mock_hardware")
    end_effector_type = LaunchConfiguration("end_effector_type")
    can_interface = LaunchConfiguration("can_interface")

    use_mock_hardware_arg = DeclareLaunchArgument(
        "use_mock_hardware",
        default_value="true",
        description="Использовать локальную имитацию оборудования вместо приводов RUKA2",
    )
    can_interface_arg = DeclareLaunchArgument(
        "can_interface",
        default_value="vcan1.0",
        description="Интерфейс SocketCAN для реального оборудования RUKA2",
    )
    end_effector_type_arg = DeclareLaunchArgument(
        "end_effector_type",
        default_value="mechanical",
        choices=["mechanical", "electromagnetic", "none"],
        description="Выбрать механический, электромагнитный захват или запуск без захвата",
    )
    rviz_config_arg = DeclareLaunchArgument(
        "rviz_config",
        default_value="moveit.rviz",
        description="RViz configuration file",
    )
    db_arg = DeclareLaunchArgument(
        "db",
        default_value="false",
        description="Start the MoveIt warehouse database",
    )

    moveit_config = (
        MoveItConfigsBuilder("ruka", package_name="ruka_spb")
        .robot_description(
            file_path="config/ruka.urdf.xacro",
            mappings={
                "use_mock_hardware": use_mock_hardware,
                "end_effector_type": end_effector_type,
                "can_interface": can_interface,
            },
        )
        .robot_description_semantic(
            file_path="config/ruka.srdf",
            mappings={"end_effector_type": end_effector_type},
        )
        .planning_scene_monitor(
            publish_robot_description=True,
            publish_robot_description_semantic=True,
        )
        .trajectory_execution(file_path="config/moveit_controllers.yaml")
        .planning_pipelines(pipelines=["ompl"])
        .to_moveit_configs()
    )
    arm_only_moveit_config = (
        MoveItConfigsBuilder("ruka", package_name="ruka_spb")
        .robot_description(
            file_path="config/ruka.urdf.xacro",
            mappings={
                "use_mock_hardware": use_mock_hardware,
                "end_effector_type": end_effector_type,
                "can_interface": can_interface,
            },
        )
        .robot_description_semantic(
            file_path="config/ruka.srdf",
            mappings={"end_effector_type": end_effector_type},
        )
        .planning_scene_monitor(
            publish_robot_description=True,
            publish_robot_description_semantic=True,
        )
        .trajectory_execution(file_path="config/moveit_controllers_arm_only.yaml")
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

    move_group_with_gripper = Node(
        package="moveit_ros_move_group",
        executable="move_group",
        output="screen",
        parameters=[moveit_config.to_dict()],
        condition=IfCondition(
            PythonExpression(["'", end_effector_type, "' == 'mechanical'"])
        ),
    )
    move_group_arm_only = Node(
        package="moveit_ros_move_group",
        executable="move_group",
        output="screen",
        parameters=[arm_only_moveit_config.to_dict()],
        condition=UnlessCondition(
            PythonExpression(["'", end_effector_type, "' == 'mechanical'"])
        ),
    )

    rviz_config = PathJoinSubstitution(
        [
            FindPackageShare("ruka_spb"),
            "config",
            LaunchConfiguration("rviz_config"),
        ]
    )
    rviz_node = Node(
        package="rviz2",
        executable="rviz2",
        name="rviz2",
        output="log",
        arguments=["-d", rviz_config],
        parameters=[
            moveit_config.robot_description,
            moveit_config.robot_description_semantic,
            moveit_config.planning_pipelines,
            moveit_config.robot_description_kinematics,
            moveit_config.joint_limits,
        ],
    )

    warehouse_node = Node(
        package="warehouse_ros_mongo",
        executable="mongo_wrapper_ros.py",
        parameters=[
            {"warehouse_port": 33829},
            {"warehouse_host": "localhost"},
            {"warehouse_plugin": "warehouse_ros_mongo::MongoDatabaseConnection"},
        ],
        output="screen",
        condition=IfCondition(LaunchConfiguration("db")),
    )

    return LaunchDescription(
        [
            use_mock_hardware_arg,
            end_effector_type_arg,
            can_interface_arg,
            rviz_config_arg,
            db_arg,
            static_tf_node,
            robot_state_publisher,
            ros2_control_node,
            joint_state_broadcaster,
            arm_controller,
            hand_controller,
            warehouse_node,
            rviz_node,
            move_group_with_gripper,
            move_group_arm_only,
        ]
    )
