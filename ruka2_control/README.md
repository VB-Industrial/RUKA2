# ruka2_control

Существующий аппаратный интерфейс Cyphal для RUKA2, описание робота для
`ros2_control`, конфигурация контроллеров и запуск системы управления.

По умолчанию используется безопасное mock-оборудование:

```bash
ros2 launch ruka2_control ros2_control.launch.py
```

Значение `end_effector_type` можно установить в `mechanical`, `electromagnetic`
или `none`. По умолчанию выбран механический захват; аргумент
`use_end_effector:=false` сохранён для совместимости. В механическом
mock-профиле `mechanical_gripper_controller` управляет ведущим пальцем, а второй
палец следует за ним через отношение mimic в URDF.

Запуск с плагином реального оборудования без изменения структуры запуска:

```bash
ros2 launch ruka2_control ros2_control.launch.py \
  use_mock_hardware:=false can_interface:=vcan1.0
```

Оба профиля предоставляют шесть суставов руки через `ruka_arm_controller`.
Реальный профиль использует `ruka2_control/Ruka2System` и неизменённый
синхронный транспорт Cyphal. Mock-контроллер захвата в нём не запускается.
