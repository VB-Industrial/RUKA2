# Запуск RUKA2

В этом документе описано, какой launch-файл использовать в зависимости от
задачи, какие узлы он запускает и какие аргументы ему можно передать.

## Подготовка терминала

После первой загрузки проекта установите зависимости и соберите рабочее
пространство:

```bash
cd ~/RUKA2
git submodule update --init --recursive
source /opt/ros/jazzy/setup.bash
rosdep install --from-paths . --ignore-src -r -y
colcon build --symlink-install
source install/setup.bash
```

В каждом новом терминале перед запуском достаточно выполнить:

```bash
cd ~/RUKA2
source /opt/ros/jazzy/setup.bash
source install/setup.bash
```

После изменения Xacro, конфигурации или launch-файлов повторите сборку:

```bash
colcon build --symlink-install
source install/setup.bash
```

## Какой launch-файл выбрать

| Задача | Launch-файл |
|---|---|
| Запустить всю систему целиком | `ruka2_moveit_config/full_system.launch.py` |
| Запустить только оборудование и контроллеры | `ruka2_control/ros2_control.launch.py` |
| Подключить MoveIt и RViz к уже работающим контроллерам | `ruka2_moveit_config/moveit.launch.py` |
| Только посмотреть URDF и подвигать суставы ползунками | `ruka2_description/display.launch.py` |

Для обычной работы рекомендуется `full_system.launch.py`. Раздельные запуски
нужны, когда управление уже работает на этом или другом компьютере либо MoveIt
требуется перезапустить независимо от оборудования.

> **Внимание:** рабочие launch-файлы по умолчанию используют реальный
> hardware interface `ruka2_control/Ruka2System`. Для запуска без подключённого
> оборудования всегда указывайте `use_mock_hardware:=true`.

## Полная система: `full_system.launch.py`

Команда запускает:

- преобразование `world` → `base_link`;
- `robot_state_publisher`;
- `ros2_control_node` и `joint_state_broadcaster`;
- контроллер руки `ruka_arm_controller`;
- MoveIt (`move_group`);
- RViz с панелью MotionPlanning;
- `mechanical_gripper_controller`, только если выбран механический захват и
  включён mock-профиль.

### Реальная рука

По умолчанию выбираются реальный интерфейс, механический захват и CAN-интерфейс
`vcan1.0`:

```bash
ros2 launch ruka2_moveit_config full_system.launch.py
```

Если рабочий SocketCAN-интерфейс имеет другое имя, укажите его явно:

```bash
ros2 launch ruka2_moveit_config full_system.launch.py \
  can_interface:=can0
```

### Проверка без оборудования

```bash
ros2 launch ruka2_moveit_config full_system.launch.py \
  use_mock_hardware:=true
```

В этом режиме команды выполняет `mock_components/GenericSystem`, поэтому
подключение к CAN и нижнему уровню не требуется.

### Выбор захвата

Механический захват выбран по умолчанию:

```bash
ros2 launch ruka2_moveit_config full_system.launch.py \
  end_effector_type:=mechanical
```

Электромагнитный захват:

```bash
ros2 launch ruka2_moveit_config full_system.launch.py \
  end_effector_type:=electromagnetic
```

Без захвата:

```bash
ros2 launch ruka2_moveit_config full_system.launch.py \
  end_effector_type:=none
```

Аргументы можно объединять. Например, полная mock-система с электромагнитным
захватом:

```bash
ros2 launch ruka2_moveit_config full_system.launch.py \
  use_mock_hardware:=true \
  end_effector_type:=electromagnetic
```

### Запуск без RViz

```bash
ros2 launch ruka2_moveit_config full_system.launch.py \
  use_rviz:=false
```

Такой вариант подходит для запуска без монитора или при использовании другого
клиента MoveIt.

## Только управление: `ros2_control.launch.py`

Этот файл следует запускать отдельно, если нужны только связь с оборудованием,
публикация состояния и контроллеры, а MoveIt будет запущен позднее или на другом
компьютере.

Он запускает:

- преобразование `world` → `base_link`;
- `robot_state_publisher`;
- `ros2_control_node`;
- `joint_state_broadcaster`;
- `ruka_arm_controller`;
- mock-контроллер механического захвата при соответствующем профиле.

Реальное оборудование:

```bash
ros2 launch ruka2_control ros2_control.launch.py
```

Mock-оборудование:

```bash
ros2 launch ruka2_control ros2_control.launch.py \
  use_mock_hardware:=true
```

Этот запуск не открывает RViz и не запускает MoveIt.

## Только планирование: `moveit.launch.py`

Этот файл запускает `move_group` и RViz, но не запускает `ros2_control`,
контроллеры или hardware interface. Перед ним должен быть запущен
`ros2_control.launch.py` либо совместимый внешний стек управления.

### Раздельный запуск реальной системы

Терминал 1 — оборудование и контроллеры:

```bash
cd ~/RUKA2
source /opt/ros/jazzy/setup.bash
source install/setup.bash
ros2 launch ruka2_control ros2_control.launch.py \
  end_effector_type:=electromagnetic
```

Терминал 2 — MoveIt и RViz:

```bash
cd ~/RUKA2
source /opt/ros/jazzy/setup.bash
source install/setup.bash
ros2 launch ruka2_moveit_config moveit.launch.py \
  end_effector_type:=electromagnetic
```

### Раздельный запуск mock-системы

Терминал 1:

```bash
ros2 launch ruka2_control ros2_control.launch.py \
  use_mock_hardware:=true \
  end_effector_type:=mechanical
```

Терминал 2:

```bash
ros2 launch ruka2_moveit_config moveit.launch.py \
  use_mock_hardware:=true \
  end_effector_type:=mechanical
```

При раздельном запуске значения `use_mock_hardware`, `end_effector_type` и
`can_interface` должны совпадать. Иначе MoveIt и `ros2_control` получат разные
описания робота.

Чтобы запустить только `move_group` без RViz:

```bash
ros2 launch ruka2_moveit_config moveit.launch.py use_rviz:=false
```

## Только модель: `display.launch.py`

Этот запуск предназначен для проверки URDF. Он не подключается к оборудованию,
не запускает `ros2_control` и не выполняет планирование.

Механический захват:

```bash
ros2 launch ruka2_description display.launch.py
```

Электромагнитный захват:

```bash
ros2 launch ruka2_description display.launch.py \
  end_effector_type:=electromagnetic
```

Без захвата:

```bash
ros2 launch ruka2_description display.launch.py \
  end_effector_type:=none
```

По умолчанию открывается `joint_state_publisher_gui`, в котором суставы можно
перемещать ползунками. Для просмотра модели без окна ползунков используйте:

```bash
ros2 launch ruka2_description display.launch.py \
  use_joint_state_gui:=false
```

## Аргументы запуска

| Аргумент | Значение по умолчанию | Назначение |
|---|---|---|
| `use_mock_hardware` | `false` | `false` — реальный `Ruka2System`, `true` — тестовый `GenericSystem` |
| `end_effector_type` | `mechanical` | `mechanical`, `electromagnetic` или `none` |
| `can_interface` | `vcan1.0` | Имя SocketCAN-интерфейса реального оборудования |
| `use_rviz` | `true` | Запускать ли RViz вместе с MoveIt |
| `use_joint_state_gui` | `true` | Показывать ли ползунки в `display.launch.py` |

Аргумент `use_end_effector:=false` сохранён для совместимости со старыми
командами. Для нового запуска без захвата используйте
`end_effector_type:=none`.

## Работа в RViz

Для движения руки во всех конфигурациях выбирайте группу планирования
`ruka_arm_controller`. Сфера со стрелками управляет общей системой координат
`tool0`:

- для механического захвата она находится между концами пальцев;
- для электромагнитного — на рабочем конце магнита;
- без захвата — на конце `link_06`.

При `end_effector_type:=mechanical` дополнительно доступна группа
`mechanical_gripper`. У неё одна независимая координата раскрытия и два
именованных состояния: `open` и `closed`. Второй палец движется автоматически.

Выполнение команд механического захвата доступно в mock-профиле. В реальном
профиле движение захвата появится после реализации соответствующего интерфейса
на нижнем уровне. Электромагнитный захват не имеет подвижных суставов, поэтому
для него отдельная группа планирования не создаётся.

Геометрия выбранного захвата входит в collision-модель MoveIt. Планировщик
учитывает её при проверке столкновений с роботом и объектами сцены.

## Быстрая проверка запущенной системы

Список основных узлов:

```bash
ros2 node list
```

Состояние контроллеров:

```bash
ros2 control list_controllers
```

Для рабочей системы контроллеры `joint_state_broadcaster` и
`ruka_arm_controller` должны находиться в состоянии `active`. В механическом
mock-профиле также должен быть активен `mechanical_gripper_controller`.

Текущие положения суставов:

```bash
ros2 topic echo /joint_states
```

Остановить launch-файл можно сочетанием `Ctrl+C` в терминале, из которого он
был запущен.
