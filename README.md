# RUKA2

Рабочее пространство ROS 2 Jazzy и встроенное ПО для манипулятора
VB-Industrial второго поколения.

## Пакеты ROS

- `ruka2_description` — основная модель URDF/Xacro, меши и отдельный запуск
  для просмотра модели;
- `ruka2_control` — существующий аппаратный плагин Cyphal для `ros2_control`,
  mock-профиль, контроллеры и запуск робота;
- `ruka2_moveit_config` — SRDF, настройки планирования, MoveIt и RViz.

Планирование и управление рукой выполняются через `ruka_arm_controller`.
Текущий аппаратный контракт предоставляет шесть суставов руки. Геометрия
захвата отображается и учитывается при проверке коллизий, но управление
захватом на реальном оборудовании будет добавлено после реализации нижнего
уровня. В mock-профиле механическим захватом можно управлять для проверки.

## Сборка

```bash
git submodule update --init --recursive
source /opt/ros/jazzy/setup.bash
rosdep install --from-paths . --ignore-src -r -y
colcon build --symlink-install
source install/setup.bash
```

В дереве прошивки находится `COLCON_IGNORE`, поэтому прошивка не входит в
сборку colcon и собирается отдельно своими пресетами CMake.

## Запуск

Подробное описание launch-файлов и готовые сценарии приведены в
[`docs/launch-guide.md`](docs/launch-guide.md).

Только просмотр модели:

```bash
ros2 launch ruka2_description display.launch.py
```

Публикация состояния робота и `ros2_control`. Этот отдельный запуск по умолчанию
использует реальный аппаратный интерфейс Cyphal/SocketCAN:

```bash
ros2 launch ruka2_control ros2_control.launch.py
```

Полная локальная система для планирования и проверки без оборудования:

```bash
ros2 launch ruka2_moveit_config full_system.launch.py
```

В `full_system.launch.py` mock-профиль выбран по умолчанию. Если вся система
запускается непосредственно на компьютере манипулятора с доступным SocketCAN,
включите реальный профиль явно:

```bash
ros2 launch ruka2_moveit_config full_system.launch.py \
  use_mock_hardware:=false
```

По умолчанию выбран механический захват. Чтобы использовать электромагнитный
захват, укажите его явно:

```bash
ros2 launch ruka2_moveit_config full_system.launch.py \
  end_effector_type:=electromagnetic
```

Запуск без визуальной и коллизионной геометрии захвата:

```bash
ros2 launch ruka2_moveit_config full_system.launch.py end_effector_type:=none
```

Для обратной совместимости также поддерживается аргумент
`use_end_effector:=false`.

Цепочка планирования MoveIt заканчивается в общей системе координат `tool0`.
Для электромагнитного захвата она расположена на внешней плоскости наклонного
цилиндра, для механического — посередине между концами пальцев. Второй палец
механического захвата повторяет первый и не может перемещаться независимо.

При `end_effector_type:=mechanical` в mock-профиле RViz также доступна группа
планирования `mechanical_gripper`. Выберите её в панели MotionPlanning и задайте
единственную координату раскрытия либо используйте именованные состояния `open`
и `closed`. В реальном профиле пальцы зафиксированы, чтобы MoveIt не ожидал
отсутствующее состояние суставов захвата; соответствующий контроллер появится
после реализации интерфейса захвата на нижнем уровне.

Явное указание CAN-интерфейса реальной руки:

```bash
ros2 launch ruka2_moveit_config full_system.launch.py \
  use_mock_hardware:=false \
  can_interface:=vcan1.0
```

MoveIt и RViz при уже запущенном экземпляре `ruka2_control`:

```bash
ros2 launch ruka2_moveit_config moveit.launch.py \
  end_effector_type:=mechanical
```

Для запуска MoveIt без графического интерфейса укажите `use_rviz:=false`.

## Проверка

```bash
colcon test --event-handlers console_direct+
colcon test-result --verbose
```

Интерфейс реального оборудования сохраняет существующий синхронный тракт
Cyphal/SocketCAN и по умолчанию использует `vcan1.0`. Зафиксированный контракт
нижнего уровня описан в
[`docs/architecture-contract.md`](docs/architecture-contract.md) и
[`interfaces/cyphal.md`](interfaces/cyphal.md).
