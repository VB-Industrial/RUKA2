from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition, UnlessCondition
from launch.substitutions import Command, FindExecutable, LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    use_joint_state_gui = LaunchConfiguration("use_joint_state_gui")
    use_end_effector = LaunchConfiguration("use_end_effector")
    end_effector_type = LaunchConfiguration("end_effector_type")
    model = PathJoinSubstitution(
        [FindPackageShare("ruka2_description"), "urdf", "ruka2.urdf.xacro"]
    )
    rviz_config = PathJoinSubstitution(
        [FindPackageShare("ruka2_description"), "rviz", "display.rviz"]
    )
    robot_description = {
        "robot_description": ParameterValue(
            Command(
                [
                    FindExecutable(name="xacro"),
                    " ",
                    model,
                    " use_end_effector:=",
                    use_end_effector,
                    " end_effector_type:=",
                    end_effector_type,
                ]
            ),
            value_type=str,
        )
    }

    return LaunchDescription(
        [
            DeclareLaunchArgument("use_joint_state_gui", default_value="true"),
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
            Node(
                package="robot_state_publisher",
                executable="robot_state_publisher",
                parameters=[robot_description],
                output="screen",
            ),
            Node(
                package="joint_state_publisher_gui",
                executable="joint_state_publisher_gui",
                condition=IfCondition(use_joint_state_gui),
            ),
            Node(
                package="joint_state_publisher",
                executable="joint_state_publisher",
                condition=UnlessCondition(use_joint_state_gui),
            ),
            Node(
                package="rviz2",
                executable="rviz2",
                arguments=["-d", rviz_config],
                output="screen",
            ),
        ]
    )
