# ruka2_moveit_config

Конфигурация MoveIt для шестиосевой руки RUKA2. Группа планирования и контроллер
траектории имеют одинаковое имя `ruka_arm_controller`.

Запуск полной локальной системы без реального оборудования:

```bash
ros2 launch ruka2_moveit_config full_system.launch.py
```

В этом launch-файле mock-профиль выбран по умолчанию. Для запуска всей системы
непосредственно на компьютере манипулятора включите реальный профиль явно:

```bash
ros2 launch ruka2_moveit_config full_system.launch.py \
  use_mock_hardware:=false
```

Запуск с электромагнитным захватом:

```bash
ros2 launch ruka2_moveit_config full_system.launch.py \
  end_effector_type:=electromagnetic
```

Запуск без отображения и коллизионной геометрии захвата с сохранением того же
контракта контроллера:

```bash
ros2 launch ruka2_moveit_config full_system.launch.py end_effector_type:=none
```

Явное указание CAN-интерфейса реального оборудования:

```bash
ros2 launch ruka2_moveit_config full_system.launch.py \
  use_mock_hardware:=false \
  can_interface:=vcan1.0
```

Если `ruka2_control/ros2_control.launch.py` уже запущен на этом или другом
хосте ROS 2, можно отдельно запустить только MoveIt и RViz:

```bash
ros2 launch ruka2_moveit_config moveit.launch.py \
  end_effector_type:=mechanical
```

Для работы без графического интерфейса укажите `use_rviz:=false`. Цепочка
планирования заканчивается в общей системе координат `tool0`. В режиме
электромагнитного захвата она находится на рабочей плоскости магнита, в режиме
механического — посередине между концами пальцев. Второй палец повторяет первый,
а интерфейс нижнего уровня для реального захвата пока не входит в действующий
аппаратный контракт.

При запуске механического mock-профиля выберите `mechanical_gripper` в поле
Planning Group интерфейса RViz. У группы одна независимая координата раскрытия
и два именованных состояния: `open` и `closed`. При планировании и выполнении
оба пальца перемещаются автоматически. Для вариантов `electromagnetic` и `none`
эта группа не создаётся.
