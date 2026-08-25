#!/usr/bin/env python3

"""Отправка тестовой траектории напрямую в контроллер руки без MoveIt."""

import argparse
import math
import sys
from typing import Dict, List, Optional

import rclpy
from control_msgs.action import FollowJointTrajectory
from rclpy.action import ActionClient
from rclpy.node import Node
from sensor_msgs.msg import JointState
from trajectory_msgs.msg import JointTrajectoryPoint


# Эти значения можно менять прямо в файле на Raspberry Pi.
DEFAULT_JOINT = "joint_2"
DEFAULT_DELTA_DEG = -10.0
DEFAULT_DURATION_SEC = 5.0
DEFAULT_MAX_DELTA_DEG = 20.0

JOINT_NAMES = [f"joint_{index}" for index in range(1, 7)]
JOINT_LIMITS_RAD = {
    "joint_1": (-2.91, 2.91),
    "joint_2": (-3.37, 0.02),
    "joint_3": (0.0, 5.11),
    "joint_4": (-2.42, 3.20),
    "joint_5": (-2.39, 2.39),
    "joint_6": (-2.82, 2.84),
}
ACTION_NAME = "/ruka_arm_controller/follow_joint_trajectory"


class JointGoalClient(Node):
    def __init__(self) -> None:
        super().__init__("ruka_joint_goal_client")
        self.positions: Optional[Dict[str, float]] = None
        self._joint_state_subscription = self.create_subscription(
            JointState,
            "/joint_states",
            self._joint_state_callback,
            10,
        )
        self.action_client = ActionClient(
            self,
            FollowJointTrajectory,
            ACTION_NAME,
        )

    def _joint_state_callback(self, message: JointState) -> None:
        positions = dict(zip(message.name, message.position))
        if all(name in positions for name in JOINT_NAMES):
            self.positions = {name: positions[name] for name in JOINT_NAMES}


def wait_for_current_positions(
    node: JointGoalClient,
    timeout_sec: float,
) -> Optional[Dict[str, float]]:
    deadline_ns = node.get_clock().now().nanoseconds + int(timeout_sec * 1e9)
    while rclpy.ok() and node.positions is None:
        if node.get_clock().now().nanoseconds >= deadline_ns:
            return None
        rclpy.spin_once(node, timeout_sec=0.1)
    return node.positions


def print_pose(title: str, positions: List[float]) -> None:
    print(title)
    for name, position in zip(JOINT_NAMES, positions):
        print(f"  {name}: {math.degrees(position):8.3f} deg ({position: .6f} rad)")


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Отправить одну точку траектории напрямую в ruka_arm_controller. "
            "Без флага --send выполняется только безопасная предварительная проверка."
        )
    )
    parser.add_argument(
        "--joint",
        choices=JOINT_NAMES,
        default=DEFAULT_JOINT,
        help=f"Изменяемый сустав (по умолчанию {DEFAULT_JOINT})",
    )
    target = parser.add_mutually_exclusive_group()
    target.add_argument(
        "--delta-deg",
        type=float,
        help=(
            "Относительное смещение в градусах. Если цель не задана, "
            f"используется {DEFAULT_DELTA_DEG:+g} град."
        ),
    )
    target.add_argument(
        "--absolute-deg",
        type=float,
        help="Абсолютное целевое положение в градусах",
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=DEFAULT_DURATION_SEC,
        help=f"Время движения в секундах (по умолчанию {DEFAULT_DURATION_SEC:g})",
    )
    parser.add_argument(
        "--max-delta-deg",
        type=float,
        default=DEFAULT_MAX_DELTA_DEG,
        help=(
            "Защитное ограничение одного перемещения в градусах "
            f"(по умолчанию {DEFAULT_MAX_DELTA_DEG:g})"
        ),
    )
    parser.add_argument(
        "--state-timeout",
        type=float,
        default=3.0,
        help="Время ожидания /joint_states в секундах",
    )
    parser.add_argument(
        "--server-timeout",
        type=float,
        default=5.0,
        help="Время ожидания action-сервера в секундах",
    )
    parser.add_argument(
        "--send",
        action="store_true",
        help="Действительно отправить команду; без флага рука не движется",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_arguments()
    if args.duration <= 0.0:
        print("Ошибка: --duration должен быть больше нуля.", file=sys.stderr)
        return 2
    if args.max_delta_deg <= 0.0:
        print("Ошибка: --max-delta-deg должен быть больше нуля.", file=sys.stderr)
        return 2

    rclpy.init()
    node = JointGoalClient()
    try:
        current_map = wait_for_current_positions(node, args.state_timeout)
        if current_map is None:
            node.get_logger().error(
                "Не получено полное состояние шести суставов из /joint_states."
            )
            return 3

        current = [current_map[name] for name in JOINT_NAMES]
        target = list(current)
        joint_index = JOINT_NAMES.index(args.joint)

        if args.absolute_deg is not None:
            target[joint_index] = math.radians(args.absolute_deg)
        else:
            delta_deg = (
                DEFAULT_DELTA_DEG if args.delta_deg is None else args.delta_deg
            )
            target[joint_index] += math.radians(delta_deg)

        actual_delta_deg = math.degrees(target[joint_index] - current[joint_index])
        if abs(actual_delta_deg) > args.max_delta_deg:
            node.get_logger().error(
                f"Запрошено {actual_delta_deg:+.3f} град., что превышает "
                f"защитный предел {args.max_delta_deg:.3f} град."
            )
            return 4

        lower, upper = JOINT_LIMITS_RAD[args.joint]
        if not lower <= target[joint_index] <= upper:
            node.get_logger().error(
                f"Цель {math.degrees(target[joint_index]):.3f} град. выходит "
                f"за пределы {math.degrees(lower):.3f} ... "
                f"{math.degrees(upper):.3f} град."
            )
            return 5

        print_pose("Текущее положение:", current)
        print_pose("Целевое положение:", target)
        print(
            f"Перемещение {args.joint}: {actual_delta_deg:+.3f} град. "
            f"за {args.duration:.3f} с"
        )

        if not args.send:
            print("ПРЕДПРОСМОТР: команда не отправлена. Для движения добавьте --send.")
            return 0

        if not node.action_client.wait_for_server(timeout_sec=args.server_timeout):
            node.get_logger().error(f"Action-сервер {ACTION_NAME} недоступен.")
            return 6

        goal = FollowJointTrajectory.Goal()
        goal.trajectory.joint_names = JOINT_NAMES
        point = JointTrajectoryPoint()
        point.positions = target
        point.velocities = [0.0] * len(JOINT_NAMES)
        point.time_from_start.sec = int(args.duration)
        point.time_from_start.nanosec = int(
            (args.duration - int(args.duration)) * 1e9
        )
        goal.trajectory.points = [point]
        goal.goal_time_tolerance.sec = 2

        node.get_logger().info(f"Отправляю цель в {ACTION_NAME}...")
        send_future = node.action_client.send_goal_async(goal)
        rclpy.spin_until_future_complete(
            node,
            send_future,
            timeout_sec=args.server_timeout,
        )
        if not send_future.done() or send_future.result() is None:
            node.get_logger().error("Не получен ответ на отправку цели.")
            return 7

        goal_handle = send_future.result()
        if not goal_handle.accepted:
            node.get_logger().error("Контроллер отклонил цель.")
            return 8

        node.get_logger().info("Цель принята контроллером.")
        result_future = goal_handle.get_result_async()
        rclpy.spin_until_future_complete(
            node,
            result_future,
            timeout_sec=args.duration + 10.0,
        )
        if not result_future.done() or result_future.result() is None:
            node.get_logger().error("Контроллер не вернул результат вовремя.")
            return 9

        wrapped_result = result_future.result()
        result = wrapped_result.result
        if result.error_code != FollowJointTrajectory.Result.SUCCESSFUL:
            node.get_logger().error(
                f"Траектория завершилась с кодом {result.error_code}: "
                f"{result.error_string}"
            )
            return 10

        node.get_logger().info("Траектория успешно выполнена.")
        return 0
    except KeyboardInterrupt:
        node.get_logger().warning("Остановлено пользователем.")
        return 130
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
