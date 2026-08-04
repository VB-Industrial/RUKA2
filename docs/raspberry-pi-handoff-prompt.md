# Prompt: prepare the RUKA2 Raspberry Pi workstation

Ты работаешь непосредственно с управляющей Raspberry Pi проекта RUKA2. Сейчас
на ней установлена серверная Ubuntu. Нужно безопасно превратить её в полноценную
рабочую станцию RUKA2, сохранив серверную роль и удалённый доступ.

## Целевое состояние

- Ubuntu 24.04 arm64 с поддерживаемым desktop-окружением;
- ROS 2 Jazzy;
- полный runtime для `ros2_control`, MoveIt 2, RViz, robot state publisher и
  diagnostics;
- Ethernet-CAN host service из
  `https://github.com/VBCores/ethernet-can`;
- выбранная шина Ethernet-CAN видна как SocketCAN-интерфейс `vcan1.0`;
- два поддерживаемых профиля RUKA2:
  - `server`: Ethernet-CAN, hardware interface, controller manager, state
    publisher, diagnostics;
  - `workstation`: всё из `server` плюс MoveIt, RViz и локальная визуализация;
- на этой Raspberry Pi активным должен стать профиль `workstation`;
- backend должен запускаться системными systemd units, а RViz — внутри
  графической пользовательской сессии;
- после перезагрузки SSH, сеть, Ethernet-CAN и выбранный профиль должны
  восстанавливаться автоматически.

## Правила безопасности

1. Сначала проведи read-only аудит и покажи краткий результат. Проверь:
   архитектуру CPU, модель Raspberry Pi, точную версию Ubuntu, свободное место,
   RAM/swap, текущие apt sources, ROS, desktop/display manager, SSH, hostname,
   пользователей, группы, network interfaces, netplan, firewall, resolver/mDNS,
   текущие workspaces и systemd services.
2. Не переустанавливай ОС и не перезаписывай сетевую конфигурацию вслепую.
   Ubuntu Server нужно дооснастить desktop-пакетами через apt. Если это не
   Ubuntu 24.04 arm64, остановись и сообщи расхождение.
3. Не ломай текущий SSH-доступ. Перед сетевыми изменениями сохрани копии
   затрагиваемых файлов и подготовь понятный откат.
4. Не удаляй существующие ROS workspaces, конфиги или сервисы. Конфликты сначала
   опиши.
5. Не угадывай IP Raspberry Pi, hostname/IP Ethernet-CAN, номер физической шины
   и CAN-FD bitrates. Если их нельзя достоверно определить из текущей системы и
   статуса платы, запроси эти значения у пользователя, а остальную установку
   продолжай.
6. Не делай reboot без предупреждения. До reboot перечисли, что уже проверено
   и как снова подключиться.
7. Не создавай выдуманный RUKA2-код вместо отсутствующего репозитория. Сейчас
   `https://github.com/VB-Industrial/RUKA2.git` может быть пустым; подготовь
   систему, а clone/build выполни, когда в remote появится первый рабочий commit.

## Порядок работы

### 1. Аудит и резервирование

- Зафиксируй вывод релевантных диагностических команд без публикации секретов.
- Сохрани копии изменяемых netplan, systemd, resolved, apt и ROS environment
  файлов в отдельном timestamped каталоге.
- Проверь, что места хватает для desktop, ROS desktop, MoveIt и сборки workspace.
- Проверь текущую возможность входа по SSH и включён ли `ssh.service`.

### 2. Обновление Ubuntu Server до desktop-среды

- Обнови установленные пакеты штатным способом Ubuntu 24.04.
- Установи поддерживаемое desktop-окружение. Предпочти
  `ubuntu-desktop-minimal`, если нет причины ставить полный набор приложений.
- Установи и включи display manager и `graphical.target`, не отключая SSH.
- Проверь локальную графическую сессию, OpenGL renderer и возможность запуска
  простого GUI-приложения.
- Не запускай RViz от root.

### 3. ROS 2 Jazzy

- Проверь или настрой официальный apt-репозиторий ROS 2 для Ubuntu Noble.
- Установи ROS 2 Jazzy Desktop, MoveIt 2, ros2_control, controller manager,
  joint trajectory controller, joint state broadcaster, xacro, URDF, RViz,
  diagnostics, `rosdep`, `colcon`, `vcstool` и необходимые build tools.
- Инициализируй и обнови rosdep, если это ещё не сделано.
- Не добавляй повторяющиеся строки `source` в shell profiles.
- Проверь `ros2 doctor`, доступность RViz и MoveIt executables.

### 4. Ethernet-CAN

- Используй актуальную документацию непосредственно из
  `https://github.com/VBCores/ethernet-can`.
- Установи host-зависимости, клонируй репозиторий с submodules, собери CMake и
  установи штатным `cmake --install`.
- Установи поставляемые `ethernet-can.service` и mDNS/resolved config.
- Предпочитаемый первый сценарий — router/DHCP + host-managed FDCAN config.
- Host JSON должен содержать реальные:
  - `network.host_ip` Raspberry Pi;
  - `network.device_ip` Ethernet-CAN платы;
  - mapping выбранного bus на `vcan1.0`;
  - `fdcan.period_ns`, `nominal_kbit`, `data_kbit`.
- Значения примера upstream `1000/8000 kbit` не считать автоматически
  подтверждёнными для RUKA2.
- Проверь mDNS через `getent hosts`, REST status/config платы, systemd status,
  наличие `vcan1.0`, `ip -details link show vcan1.0` и при возможности
  `candump vcan1.0`.
- Если плата недоступна, сервис и конфиг должны быть подготовлены, а причина
  отсутствия end-to-end проверки явно отмечена.

### 5. Runtime layout RUKA2

- Подготовь отдельного непривилегированного runtime-пользователя либо используй
  согласованного существующего пользователя; не хардкодь `voltbro` без проверки.
- Подготовь `/etc/ruka2/ruka2.env` минимум для:
  `RUKA2_PROFILE`, `RUKA2_CAN_IFACE=vcan1.0`, workspace/install path,
  `ROS_DOMAIN_ID` и выбранного RMW. Не угадывай ROS domain.
- Подготовь versioned release layout, например:
  `/opt/ruka2/releases/<git-commit>` и атомарный symlink `/opt/ruka2/current`.
  Это и есть rollback: предыдущий release не удаляется, а при неуспешном
  health-check symlink и сервис возвращаются на предыдущую версию.
- System services должны запускать backend профиля `server` или `workstation`
  и зависеть от `ethernet-can.service`/готовности `vcan1.0` без фиксированного
  `sleep 30`.
- MoveIt backend может быть частью workstation profile. RViz запускай через
  user systemd unit или desktop autostart после появления graphical session,
  а не из system service без `DISPLAY`/Wayland environment.
- Пока RUKA2 remote пуст, подготовь каталоги и units как disabled templates, но
  не включай несуществующий executable.

### 6. Проверка

После появления RUKA2-кода:

- clone с `--recurse-submodules`;
- `rosdep install --from-paths ... --ignore-src`;
- `colcon build --symlink-install` для development либо release install для
  systemd;
- `colcon test` и `colcon test-result --verbose`;
- проверка обнаружения пакетов;
- Ethernet-CAN и `vcan1.0` smoke test;
- запуск server backend;
- запуск workstation backend, MoveIt и RViz;
- проверка автозапуска после reboot;
- проверка восстановления после временной потери Ethernet-CAN;
- проверка rollback на предыдущий release.

## Итоговый отчёт

В конце сообщи:

- исходное и итоговое состояние ОС;
- какие пакеты установлены;
- какие файлы и services созданы или изменены;
- выбранные desktop/display manager и runtime user;
- Ethernet-CAN IP/hostname, bus mapping и bitrates;
- ROS domain и RMW;
- какие сервисы enabled/active;
- результаты всех health checks;
- что осталось заблокировано отсутствием RUKA2 commit, Ethernet-CAN платы,
  дисплея или неизвестных сетевых значений;
- точные команды отката.

Работай до достигнутого и проверенного результата, регулярно давай короткие
статусные обновления и не маскируй непроверенные пункты как выполненные.
