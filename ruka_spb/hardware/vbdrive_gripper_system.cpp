#include "ruka_spb/vbdrive_gripper_system.hpp"

#include <algorithm>
#include <atomic>
#include <chrono>
#include <cmath>
#include <cstddef>
#include <cerrno>
#include <cstring>
#include <cstdlib>
#include <exception>
#include <fcntl.h>
#include <linux/can.h>
#include <linux/can/raw.h>
#include <memory>
#include <net/if.h>
#include <sys/socket.h>
#include <string>
#include <thread>
#include <type_traits>
#include <unistd.h>
#include <utility>
#include <vector>

#include "hardware_interface/types/hardware_interface_type_values.hpp"
#include "pluginlib/class_list_macros.hpp"
#include "rclcpp/rclcpp.hpp"
#include "libcanard/canard.h"
#include "voltbro/foc/command_1_0.h"
#include "voltbro/foc/state_simple_1_0.h"

namespace
{
using SteadyClock = std::chrono::steady_clock;

std::uint64_t steady_microseconds()
{
  return static_cast<std::uint64_t>(std::chrono::duration_cast<std::chrono::microseconds>(
    SteadyClock::now().time_since_epoch()).count());
}

void * canard_allocate(CanardInstance *, const std::size_t amount)
{
  return std::malloc(amount);
}

void canard_free(CanardInstance *, void * const pointer)
{
  std::free(pointer);
}

std::string string_parameter(
  const hardware_interface::HardwareInfo & info, const std::string & key,
  const std::string & fallback)
{
  const auto it = info.hardware_parameters.find(key);
  return it == info.hardware_parameters.end() ? fallback : it->second;
}

template<typename T>
T number_parameter(
  const hardware_interface::HardwareInfo & info, const std::string & key, T fallback)
{
  const auto it = info.hardware_parameters.find(key);
  if (it == info.hardware_parameters.end()) {return fallback;}
  try {
    if constexpr (std::is_integral_v<T>) {
      return static_cast<T>(std::stoull(it->second));
    }
    return static_cast<T>(std::stod(it->second));
  } catch (const std::exception &) {
    return fallback;
  }
}
}  // namespace

namespace ruka_spb::detail
{
struct GripperCyphalRuntime
{
  explicit GripperCyphalRuntime(const std::size_t queue_capacity)
  : canard(canardInit(canard_allocate, canard_free)),
    tx_queue(canardTxInit(queue_capacity, CANARD_MTU_CAN_FD))
  {
  }

  int socket_fd{-1};
  CanardInstance canard;
  CanardRxSubscription feedback_subscription{};
  CanardTxQueue tx_queue;
  std::atomic<float> motor_angle{0.0F};
  std::atomic<float> motor_velocity{0.0F};
  std::atomic<float> motor_torque{0.0F};
  std::atomic<bool> has_fault{false};
  std::atomic<std::uint64_t> feedback_time_us{0U};
  CanardTransferID command_transfer_id{0U};
};
}  // namespace ruka_spb::detail

namespace ruka_spb
{
VBDriveGripperSystem::~VBDriveGripperSystem() {stop_transport();}

GripperCallbackReturn VBDriveGripperSystem::on_init(
  const hardware_interface::HardwareInfo & info)
{
  if (hardware_interface::SystemInterface::on_init(info) != GripperCallbackReturn::SUCCESS) {
    return GripperCallbackReturn::ERROR;
  }
  if (info_.joints.size() != 1U ||
    info_.joints[0].name != "link_hand_cyl__first_fin" ||
    info_.joints[0].command_interfaces.size() != 2U ||
    info_.joints[0].command_interfaces[0].name != hardware_interface::HW_IF_POSITION ||
    info_.joints[0].command_interfaces[1].name != hardware_interface::HW_IF_EFFORT)
  {
    RCLCPP_ERROR(
      get_logger(), "VBDrive gripper requires one joint with position and effort commands");
    return GripperCallbackReturn::ERROR;
  }
  can_interface_ = string_parameter(info_, "can_interface", can_interface_);
  controller_node_id_ = number_parameter(info_, "controller_node_id", controller_node_id_);
  drive_node_id_ = number_parameter(info_, "drive_node_id", drive_node_id_);
  feedback_subject_id_ = number_parameter(info_, "feedback_subject_id", feedback_subject_id_);
  command_subject_id_ = number_parameter(info_, "command_subject_id", command_subject_id_);
  queue_length_ = number_parameter(info_, "queue_length", queue_length_);
  feedback_timeout_s_ = number_parameter(info_, "feedback_timeout", feedback_timeout_s_);
  heartbeat_timeout_s_ = number_parameter(info_, "heartbeat_timeout", heartbeat_timeout_s_);
  activation_timeout_s_ = number_parameter(info_, "activation_timeout", activation_timeout_s_);
  joint_closed_position_ = number_parameter(info_, "joint_closed_position", joint_closed_position_);
  joint_open_position_ = number_parameter(info_, "joint_open_position", joint_open_position_);
  motor_closed_angle_ = number_parameter(info_, "motor_closed_angle", motor_closed_angle_);
  motor_open_angle_ = number_parameter(info_, "motor_open_angle", motor_open_angle_);
  maximum_motor_velocity_ = number_parameter(
    info_, "maximum_motor_velocity", maximum_motor_velocity_);
  maximum_motor_torque_ = number_parameter(
    info_, "maximum_motor_torque", maximum_motor_torque_);
  warning_motor_torque_ = number_parameter(
    info_, "warning_motor_torque", warning_motor_torque_);
  maximum_joint_force_ = number_parameter(
    info_, "maximum_joint_force", maximum_joint_force_);
  default_opening_force_ = number_parameter(
    info_, "default_opening_force", default_opening_force_);
  default_closing_force_ = number_parameter(
    info_, "default_closing_force", default_closing_force_);
  angle_kp_ = number_parameter(info_, "angle_kp", angle_kp_);
  velocity_kp_ = number_parameter(info_, "velocity_kp", velocity_kp_);
  current_kp_ = number_parameter(info_, "current_kp", current_kp_);
  current_ki_ = number_parameter(info_, "current_ki", current_ki_);
  command_refresh_period_s_ = number_parameter(
    info_, "command_refresh_period", command_refresh_period_s_);
  position_command_deadband_ = number_parameter(
    info_, "position_command_deadband", position_command_deadband_);
  effort_slew_rate_ = number_parameter(info_, "effort_slew_rate", effort_slew_rate_);
  if (queue_length_ == 0U || feedback_timeout_s_ <= 0.0 || heartbeat_timeout_s_ <= 0.0 ||
    activation_timeout_s_ < 0.0 ||
    !std::isfinite(motor_closed_angle_) || !std::isfinite(motor_open_angle_) ||
    std::fabs(motor_open_angle_ - motor_closed_angle_) < 1.0e-9 ||
    maximum_motor_velocity_ <= 0.0 || maximum_motor_torque_ <= 0.0 ||
    warning_motor_torque_ <= 0.0 || warning_motor_torque_ > maximum_motor_torque_ ||
    maximum_joint_force_ <= 0.0 || angle_kp_ < 0.0 || velocity_kp_ != 0.0 ||
    current_kp_ < 0.0 || current_ki_ < 0.0 || command_refresh_period_s_ <= 0.0 ||
    position_command_deadband_ <= 0.0 ||
    effort_slew_rate_ <= 0.0 ||
    !(joint_open_position_ > joint_closed_position_))
  {
    RCLCPP_ERROR(get_logger(), "Invalid VBDrive gripper parameters");
    return GripperCallbackReturn::ERROR;
  }
  return GripperCallbackReturn::SUCCESS;
}

GripperCallbackReturn VBDriveGripperSystem::start_transport()
{
  stop_transport();
  const auto interface_index = if_nametoindex(can_interface_.c_str());
  if (interface_index == 0U) {
    RCLCPP_ERROR(get_logger(), "SocketCAN interface '%s' does not exist", can_interface_.c_str());
    return GripperCallbackReturn::ERROR;
  }
  runtime_ = std::make_unique<detail::GripperCyphalRuntime>(queue_length_);
  runtime_->canard.node_id = static_cast<CanardNodeID>(controller_node_id_);
  if (canardRxSubscribe(
      &runtime_->canard, CanardTransferKindMessage,
      static_cast<CanardPortID>(feedback_subject_id_),
      voltbro_foc_state_simple_1_0_EXTENT_BYTES_,
      CANARD_DEFAULT_TRANSFER_ID_TIMEOUT_USEC,
      &runtime_->feedback_subscription) < 0)
  {
    RCLCPP_ERROR(get_logger(), "Cannot create Cyphal feedback subscription");
    stop_transport();
    return GripperCallbackReturn::ERROR;
  }
  runtime_->socket_fd = socket(PF_CAN, SOCK_RAW | SOCK_NONBLOCK, CAN_RAW);
  if (runtime_->socket_fd < 0) {
    RCLCPP_ERROR(get_logger(), "Cannot create raw CAN socket: %s", std::strerror(errno));
    stop_transport();
    return GripperCallbackReturn::ERROR;
  }
  const int enable_can_fd = 1;
  if (setsockopt(
      runtime_->socket_fd, SOL_CAN_RAW, CAN_RAW_FD_FRAMES,
      &enable_can_fd, sizeof(enable_can_fd)) < 0)
  {
    RCLCPP_ERROR(get_logger(), "Cannot enable CAN FD: %s", std::strerror(errno));
    stop_transport();
    return GripperCallbackReturn::ERROR;
  }
  sockaddr_can address{};
  address.can_family = AF_CAN;
  address.can_ifindex = static_cast<int>(interface_index);
  if (bind(runtime_->socket_fd, reinterpret_cast<sockaddr *>(&address), sizeof(address)) < 0) {
    RCLCPP_ERROR(get_logger(), "Cannot bind raw CAN socket: %s", std::strerror(errno));
    stop_transport();
    return GripperCallbackReturn::ERROR;
  }
  RCLCPP_INFO(
    get_logger(), "VBDrive gripper ready: iface=%s drive=%u feedback=%u command=%u",
    can_interface_.c_str(), drive_node_id_, feedback_subject_id_, command_subject_id_);
  return GripperCallbackReturn::SUCCESS;
}

void VBDriveGripperSystem::stop_transport()
{
  active_ = false;
  command_initialized_ = false;
  if (runtime_) {
    (void)canardRxUnsubscribe(
      &runtime_->canard, CanardTransferKindMessage,
      static_cast<CanardPortID>(feedback_subject_id_));
    while (const auto * item = canardTxPeek(&runtime_->tx_queue)) {
      auto * owned = canardTxPop(&runtime_->tx_queue, item);
      runtime_->canard.memory_free(&runtime_->canard, owned);
    }
    if (runtime_->socket_fd >= 0) {
      close(runtime_->socket_fd);
      runtime_->socket_fd = -1;
    }
    runtime_.reset();
  }
}

GripperCallbackReturn VBDriveGripperSystem::on_configure(const rclcpp_lifecycle::State &)
{return start_transport();}

GripperCallbackReturn VBDriveGripperSystem::on_activate(const rclcpp_lifecycle::State &)
{
  if (!runtime_ || runtime_->socket_fd < 0) {return GripperCallbackReturn::ERROR;}
  const auto deadline = SteadyClock::now() + std::chrono::duration<double>(activation_timeout_s_);
  while (SteadyClock::now() < deadline && runtime_->feedback_time_us.load() == 0U) {
    read(rclcpp::Time{}, rclcpp::Duration::from_seconds(0.0));
    std::this_thread::sleep_for(std::chrono::milliseconds(2));
  }
  if (runtime_->feedback_time_us.load() == 0U || runtime_->has_fault.load())
  {
    RCLCPP_ERROR(get_logger(), "VBDrive feedback unavailable or drive reports a fault");
    return GripperCallbackReturn::ERROR;
  }
  joint_position_ = motor_to_joint(runtime_->motor_angle.load());
  joint_velocity_ = runtime_->motor_velocity.load() *
    ((joint_open_position_ - joint_closed_position_) /
    (motor_open_angle_ - motor_closed_angle_));
  joint_effort_ = motor_torque_to_joint_force(runtime_->motor_torque.load());
  joint_position_command_ = joint_position_;
  joint_effort_command_ = std::numeric_limits<double>::quiet_NaN();
  last_received_position_command_ = joint_position_;
  automatic_force_command_ = 0.0;
  last_sent_motor_angle_ = runtime_->motor_angle.load();
  last_sent_motor_torque_ = 0.0;
  last_command_time_us_ = 0U;
  command_initialized_ = true;
  active_ = true;
  return GripperCallbackReturn::SUCCESS;
}

GripperCallbackReturn VBDriveGripperSystem::on_deactivate(const rclcpp_lifecycle::State &)
{
  if (active_ && runtime_) {
    joint_position_command_ = motor_to_joint(runtime_->motor_angle.load());
    joint_effort_command_ = 0.0;
    automatic_force_command_ = 0.0;
    (void)write(rclcpp::Time{}, rclcpp::Duration::from_seconds(1.0));
  }
  active_ = false;
  return GripperCallbackReturn::SUCCESS;
}
GripperCallbackReturn VBDriveGripperSystem::on_cleanup(const rclcpp_lifecycle::State &)
{stop_transport(); return GripperCallbackReturn::SUCCESS;}
GripperCallbackReturn VBDriveGripperSystem::on_shutdown(const rclcpp_lifecycle::State &)
{stop_transport(); return GripperCallbackReturn::SUCCESS;}
GripperCallbackReturn VBDriveGripperSystem::on_error(const rclcpp_lifecycle::State &)
{stop_transport(); return GripperCallbackReturn::SUCCESS;}

std::vector<hardware_interface::StateInterface>
VBDriveGripperSystem::export_state_interfaces()
{
  std::vector<hardware_interface::StateInterface> interfaces;
  interfaces.emplace_back(
    info_.joints[0].name, hardware_interface::HW_IF_POSITION, &joint_position_);
  interfaces.emplace_back(
    info_.joints[0].name, hardware_interface::HW_IF_VELOCITY, &joint_velocity_);
  interfaces.emplace_back(
    info_.joints[0].name, hardware_interface::HW_IF_EFFORT, &joint_effort_);
  return interfaces;
}

std::vector<hardware_interface::CommandInterface>
VBDriveGripperSystem::export_command_interfaces()
{
  std::vector<hardware_interface::CommandInterface> interfaces;
  interfaces.emplace_back(
    info_.joints[0].name, hardware_interface::HW_IF_POSITION, &joint_position_command_);
  interfaces.emplace_back(
    info_.joints[0].name, hardware_interface::HW_IF_EFFORT, &joint_effort_command_);
  return interfaces;
}

double VBDriveGripperSystem::motor_to_joint(const double motor_angle) const
{
  const double ratio = (motor_angle - motor_closed_angle_) /
    (motor_open_angle_ - motor_closed_angle_);
  return std::clamp(
    joint_closed_position_ + ratio * (joint_open_position_ - joint_closed_position_),
    joint_closed_position_, joint_open_position_);
}

double VBDriveGripperSystem::joint_to_motor(const double joint_position) const
{
  const double position = std::clamp(
    joint_position, joint_closed_position_, joint_open_position_);
  const double ratio = (position - joint_closed_position_) /
    (joint_open_position_ - joint_closed_position_);
  return motor_closed_angle_ + ratio * (motor_open_angle_ - motor_closed_angle_);
}

double VBDriveGripperSystem::motor_torque_to_joint_force(const double motor_torque) const
{
  const double aperture_meters_per_radian =
    (joint_open_position_ - joint_closed_position_) /
    (motor_open_angle_ - motor_closed_angle_);
  return motor_torque / aperture_meters_per_radian;
}

double VBDriveGripperSystem::joint_force_to_motor_torque(const double joint_force) const
{
  const double aperture_meters_per_radian =
    (joint_open_position_ - joint_closed_position_) /
    (motor_open_angle_ - motor_closed_angle_);
  return joint_force * aperture_meters_per_radian;
}

hardware_interface::return_type VBDriveGripperSystem::read(
  const rclcpp::Time &, const rclcpp::Duration &)
{
  if (!runtime_ || runtime_->socket_fd < 0) {
    return hardware_interface::return_type::ERROR;
  }
  canfd_frame frame{};
  while (true) {
    const auto received = ::read(runtime_->socket_fd, &frame, CANFD_MTU);
    if (received < 0) {
      if (errno == EAGAIN || errno == EWOULDBLOCK) {break;}
      RCLCPP_ERROR_THROTTLE(
        get_logger(), *get_clock(), 1000, "VBDrive CAN read failed: %s", std::strerror(errno));
      return hardware_interface::return_type::ERROR;
    }
    const bool valid_socketcan_frame = received == CAN_MTU || received == CANFD_MTU;
    if (!valid_socketcan_frame || (frame.can_id & CAN_EFF_FLAG) == 0U || frame.len < 2U) {
      continue;
    }
    const CanardFrame cyphal_frame{
      frame.can_id & CAN_EFF_MASK,
      static_cast<std::size_t>(frame.len),
      frame.data};
    CanardRxTransfer transfer{};
    CanardRxSubscription * accepted_subscription = nullptr;
    const auto accept_result = canardRxAccept(
      &runtime_->canard, steady_microseconds(), &cyphal_frame, 0U,
      &transfer, &accepted_subscription);
    if (accept_result < 0) {
      RCLCPP_ERROR_THROTTLE(
        get_logger(), *get_clock(), 1000, "VBDrive Cyphal RX error: %d", accept_result);
      return hardware_interface::return_type::ERROR;
    }
    if (accept_result == 0 || accepted_subscription != &runtime_->feedback_subscription) {
      continue;
    }
    if (transfer.metadata.remote_node_id != drive_node_id_) {
      runtime_->canard.memory_free(&runtime_->canard, transfer.payload);
      continue;
    }
    voltbro_foc_state_simple_1_0 message{};
    std::size_t payload_size = transfer.payload_size;
    if (voltbro_foc_state_simple_1_0_deserialize_(
        &message, static_cast<const std::uint8_t *>(transfer.payload), &payload_size) < 0)
    {
      runtime_->canard.memory_free(&runtime_->canard, transfer.payload);
      continue;
    }
    runtime_->canard.memory_free(&runtime_->canard, transfer.payload);
    runtime_->motor_angle.store(message.angle.radian);
    runtime_->motor_velocity.store(message.velocity.radian_per_second);
    runtime_->motor_torque.store(message._torque.newton_meter);
    runtime_->has_fault.store(message.has_fault.value != 0U);
    runtime_->feedback_time_us.store(steady_microseconds());
  }
  const auto feedback_time = runtime_->feedback_time_us.load();
  const auto feedback_age = feedback_time == 0U ? feedback_timeout_s_ + 1.0 :
    static_cast<double>(steady_microseconds() - feedback_time) / 1.0e6;
  const bool feedback_stale = feedback_age > feedback_timeout_s_;
  const bool drive_faulted = runtime_->has_fault.load();
  if (active_ && (feedback_stale || drive_faulted)) {
    if (drive_faulted) {
      RCLCPP_ERROR_THROTTLE(
        get_logger(), *get_clock(), 5000,
        "VBDrive reports fault; holding last gripper state (feedback_age=%.3f)",
        feedback_age);
    } else {
      RCLCPP_WARN_THROTTLE(
        get_logger(), *get_clock(), 5000,
        "VBDrive feedback stale; holding last gripper state (feedback_age=%.3f)",
        feedback_age);
    }
    joint_position_command_ = motor_to_joint(runtime_->motor_angle.load());
    joint_effort_command_ = 0.0;
    automatic_force_command_ = 0.0;
  }
  joint_position_ = motor_to_joint(runtime_->motor_angle.load());
  joint_velocity_ = runtime_->motor_velocity.load() *
    ((joint_open_position_ - joint_closed_position_) /
    (motor_open_angle_ - motor_closed_angle_));
  joint_effort_ = motor_torque_to_joint_force(runtime_->motor_torque.load());
  return hardware_interface::return_type::OK;
}

hardware_interface::return_type VBDriveGripperSystem::write(
  const rclcpp::Time &, const rclcpp::Duration & period)
{
  if (!active_ || !command_initialized_) {return hardware_interface::return_type::OK;}
  if (!runtime_ || runtime_->socket_fd < 0 || !std::isfinite(joint_position_command_)) {
    return hardware_interface::return_type::ERROR;
  }
  const double measured_motor_torque = runtime_->motor_torque.load();
  const double measured_motor_angle = runtime_->motor_angle.load();
  if (std::fabs(measured_motor_torque) > warning_motor_torque_) {
    RCLCPP_WARN_THROTTLE(
      get_logger(), *get_clock(), 1000, "VBDrive high motor torque: %.4f Nm",
      measured_motor_torque);
  }
  const bool torque_limit_exceeded =
    std::fabs(measured_motor_torque) > maximum_motor_torque_ * 1.10;
  if (std::fabs(measured_motor_torque) > maximum_motor_torque_ * 1.10) {
    RCLCPP_ERROR_THROTTLE(
      get_logger(), *get_clock(), 1000, "VBDrive motor torque safety limit exceeded: %.4f Nm",
      measured_motor_torque);
    joint_position_command_ = motor_to_joint(measured_motor_angle);
    joint_effort_command_ = 0.0;
    automatic_force_command_ = 0.0;
  }
  const double target_motor_angle = joint_to_motor(joint_position_command_);
  const double maximum_step = maximum_motor_velocity_ * std::max(0.0, period.seconds());
  const double rate_limited_motor_angle = std::clamp(
    target_motor_angle, last_sent_motor_angle_ - maximum_step,
    last_sent_motor_angle_ + maximum_step);
  const auto now_us = steady_microseconds();
  const bool refresh_due = last_command_time_us_ == 0U ||
    static_cast<double>(now_us - last_command_time_us_) / 1.0e6 >= command_refresh_period_s_;

  double requested_force = joint_effort_command_;
  // JointTrajectory points without effort are represented as zero by JTC.
  // Keep that as zero feed-forward force; a non-zero effort is an explicit
  // force command in newtons.
  if (!std::isfinite(requested_force) || std::fabs(requested_force) < 1.0e-6) {
    automatic_force_command_ = 0.0;
    requested_force = automatic_force_command_;
  }
  requested_force = std::clamp(
    requested_force, -maximum_joint_force_, maximum_joint_force_);
  double motor_torque = std::clamp(
    joint_force_to_motor_torque(requested_force),
    -maximum_motor_torque_, maximum_motor_torque_);
  const double maximum_effort_step = effort_slew_rate_ * std::max(0.0, period.seconds());
  motor_torque = std::clamp(
    motor_torque, last_sent_motor_torque_ - maximum_effort_step,
    last_sent_motor_torque_ + maximum_effort_step);
  motor_torque = std::clamp(motor_torque, -maximum_motor_torque_, maximum_motor_torque_);
  if (torque_limit_exceeded) {
    motor_torque = 0.0;
  }

  const double motor_angle =
    torque_limit_exceeded ? measured_motor_angle : rate_limited_motor_angle;
  const bool position_changed = std::fabs(motor_angle - last_sent_motor_angle_) >= 1.0e-6;
  const bool effort_changed = std::fabs(motor_torque - last_sent_motor_torque_) >= 1.0e-5;
  if (!position_changed && !effort_changed && !refresh_due) {
    return hardware_interface::return_type::OK;
  }
  voltbro_foc_command_1_0 command{};
  command._torque.newton_meter = static_cast<float>(motor_torque);
  command.angle.radian = static_cast<float>(motor_angle);
  command.velocity.radian_per_second = 0.0F;
  command.angle_kp.value = static_cast<float>(angle_kp_);
  command.velocity_kp.value = 0.0F;
  command.I_kp.value = static_cast<float>(current_kp_);
  command.I_ki.value = static_cast<float>(current_ki_);
  std::uint8_t payload[voltbro_foc_command_1_0_SERIALIZATION_BUFFER_SIZE_BYTES_]{};
  std::size_t payload_size = voltbro_foc_command_1_0_SERIALIZATION_BUFFER_SIZE_BYTES_;
  if (voltbro_foc_command_1_0_serialize_(
      &command, payload, &payload_size) < 0)
  {
    return hardware_interface::return_type::ERROR;
  }
  CanardTransferMetadata metadata{};
  metadata.priority = CanardPriorityNominal;
  metadata.transfer_kind = CanardTransferKindMessage;
  metadata.port_id = static_cast<CanardPortID>(command_subject_id_);
  metadata.remote_node_id = CANARD_NODE_ID_UNSET;
  metadata.transfer_id = runtime_->command_transfer_id++;
  const auto push_result = canardTxPush(
    &runtime_->tx_queue, &runtime_->canard, now_us + 1000000U,
    &metadata, payload_size, payload);
  if (push_result < 0) {
    RCLCPP_ERROR_THROTTLE(
      get_logger(), *get_clock(), 1000, "VBDrive Cyphal TX enqueue error: %d", push_result);
    return hardware_interface::return_type::ERROR;
  }
  while (const auto * item = canardTxPeek(&runtime_->tx_queue)) {
    canfd_frame frame{};
    frame.can_id = CAN_EFF_FLAG | item->frame.extended_can_id;
    frame.len = static_cast<__u8>(item->frame.payload_size);
    frame.flags = CANFD_BRS;
    std::memcpy(frame.data, item->frame.payload, item->frame.payload_size);
    const auto written = ::write(runtime_->socket_fd, &frame, CANFD_MTU);
    if (written != CANFD_MTU) {
      if (written < 0 && (errno == EAGAIN || errno == EWOULDBLOCK)) {
        break;
      }
      RCLCPP_ERROR_THROTTLE(
        get_logger(), *get_clock(), 1000, "VBDrive CAN write failed: %s", std::strerror(errno));
      return hardware_interface::return_type::ERROR;
    }
    auto * owned = canardTxPop(&runtime_->tx_queue, item);
    runtime_->canard.memory_free(&runtime_->canard, owned);
  }
  last_sent_motor_angle_ = motor_angle;
  last_sent_motor_torque_ = motor_torque;
  last_command_time_us_ = now_us;
  return hardware_interface::return_type::OK;
}
}  // namespace ruka_spb

PLUGINLIB_EXPORT_CLASS(ruka_spb::VBDriveGripperSystem, hardware_interface::SystemInterface)
