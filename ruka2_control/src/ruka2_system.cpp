#include "ruka2_control/ruka2_system.hpp"

#include <algorithm>
#include <array>
#include <atomic>
#include <chrono>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <exception>
#include <memory>
#include <net/if.h>
#include <sstream>
#include <string>
#include <utility>
#include <vector>

#include "diagnostic_msgs/msg/diagnostic_array.hpp"
#include "diagnostic_msgs/msg/diagnostic_status.hpp"
#include "diagnostic_msgs/msg/key_value.hpp"
#include "hardware_interface/types/hardware_interface_type_values.hpp"
#include "pluginlib/class_list_macros.hpp"
#include "rclcpp/rclcpp.hpp"
#include "ruka2_control/cyphal_contract.hpp"

#include "cyphal/allocators/o1/o1_allocator.h"
#include "cyphal/cyphal.h"
#include "cyphal/providers/LinuxCAN.h"
#include "cyphal/subscriptions/subscription.h"
#include "reg/udral/physics/kinematics/rotation/Planar_0_1.h"
#include "uavcan/node/Heartbeat_1_0.h"
#include "uavcan/node/Health_1_0.h"
#include "uavcan/node/Mode_1_0.h"

TYPE_ALIAS(HeartbeatMessage, uavcan_node_Heartbeat_1_0)
TYPE_ALIAS(JointMessage, reg_udral_physics_kinematics_rotation_Planar_0_1)

namespace
{

using SteadyClock = std::chrono::steady_clock;

std::atomic<bool> g_transport_error{false};

std::uint64_t steady_microseconds()
{
  return static_cast<std::uint64_t>(
    std::chrono::duration_cast<std::chrono::microseconds>(
      SteadyClock::now().time_since_epoch()).count());
}

void transport_error_handler()
{
  g_transport_error.store(true);
}

UtilityConfig g_utilities(steady_microseconds, transport_error_handler);

std::string string_parameter(
  const hardware_interface::HardwareInfo & info, const std::string & key,
  const std::string & default_value)
{
  const auto it = info.hardware_parameters.find(key);
  return it == info.hardware_parameters.end() ? default_value : it->second;
}

template<typename T>
T numeric_parameter(
  const hardware_interface::HardwareInfo & info, const std::string & key, T default_value)
{
  const auto it = info.hardware_parameters.find(key);
  if (it == info.hardware_parameters.end()) {
    return default_value;
  }
  try {
    if constexpr (std::is_integral_v<T>) {
      return static_cast<T>(std::stoull(it->second));
    } else {
      return static_cast<T>(std::stod(it->second));
    }
  } catch (const std::exception &) {
    return default_value;
  }
}

bool bool_parameter(
  const hardware_interface::HardwareInfo & info, const std::string & key, bool default_value)
{
  std::string value = string_parameter(info, key, default_value ? "true" : "false");
  std::transform(value.begin(), value.end(), value.begin(), [](unsigned char c) {
    return static_cast<char>(std::tolower(c));
  });
  if (value == "true" || value == "1" || value == "yes") {
    return true;
  }
  if (value == "false" || value == "0" || value == "no") {
    return false;
  }
  return default_value;
}

bool has_interfaces(
  const std::vector<hardware_interface::InterfaceInfo> & interfaces,
  const std::vector<std::string> & expected)
{
  if (interfaces.size() != expected.size()) {
    return false;
  }
  for (const auto & name : expected) {
    if (std::none_of(interfaces.begin(), interfaces.end(), [&name](const auto & item) {
        return item.name == name;
      }))
    {
      return false;
    }
  }
  return true;
}

diagnostic_msgs::msg::KeyValue diagnostic_value(std::string key, std::string value)
{
  diagnostic_msgs::msg::KeyValue result;
  result.key = std::move(key);
  result.value = std::move(value);
  return result;
}

double age_seconds(std::uint64_t now_us, std::uint64_t timestamp_us)
{
  if (timestamp_us == 0U || timestamp_us > now_us) {
    return std::numeric_limits<double>::infinity();
  }
  return static_cast<double>(now_us - timestamp_us) / 1.0e6;
}

}  // namespace

namespace ruka2_control::detail
{

class FeedbackReader;
class HeartbeatReader;

struct CyphalRuntime
{
  std::shared_ptr<CyphalInterface> interface;
  std::unique_ptr<FeedbackReader> feedback_reader;
  std::unique_ptr<HeartbeatReader> heartbeat_reader;
  std::array<std::atomic<float>, kJointCount> position{};
  std::array<std::atomic<float>, kJointCount> velocity{};
  std::array<std::atomic<std::uint64_t>, kJointCount> feedback_time_us{};
  std::array<std::atomic<std::uint64_t>, kJointCount> heartbeat_time_us{};
  std::array<std::atomic<std::uint8_t>, kJointCount> health{};
  std::array<std::atomic<std::uint8_t>, kJointCount> mode{};
  std::array<std::atomic<std::uint8_t>, kJointCount> vendor_status{};
  std::array<CanardTransferID, kJointCount> command_transfer_ids{};
  CanardTransferID heartbeat_transfer_id{0};
  std::uint64_t transport_start_us{0};
  std::uint64_t activation_time_us{0};
  std::uint64_t last_heartbeat_tx_us{0};
  std::uint64_t last_diagnostics_tx_us{0};
  rclcpp::Node::SharedPtr diagnostics_node;
  rclcpp::Publisher<diagnostic_msgs::msg::DiagnosticArray>::SharedPtr diagnostics_publisher;
};

class FeedbackReader : public AbstractSubscription<JointMessage>
{
public:
  FeedbackReader(const InterfacePtr & interface, CyphalRuntime * runtime)
  : AbstractSubscription<JointMessage>(interface, kFeedbackSubjectId), runtime_(runtime)
  {
  }

  void handler(
    const reg_udral_physics_kinematics_rotation_Planar_0_1 & message,
    CanardRxTransfer * transfer) override
  {
    if (runtime_ == nullptr || transfer == nullptr) {
      return;
    }
    const auto source = transfer->metadata.remote_node_id;
    if (source < kFirstJointNodeId || source >= kFirstJointNodeId + kJointCount) {
      return;
    }
    const auto index = static_cast<std::size_t>(source - kFirstJointNodeId);
    runtime_->position[index].store(message.angular_position.radian);
    runtime_->velocity[index].store(message.angular_velocity.radian_per_second);
    runtime_->feedback_time_us[index].store(steady_microseconds());
  }

private:
  CyphalRuntime * runtime_;
};

class HeartbeatReader : public AbstractSubscription<HeartbeatMessage>
{
public:
  HeartbeatReader(const InterfacePtr & interface, CyphalRuntime * runtime)
  : AbstractSubscription<HeartbeatMessage>(interface, kHeartbeatSubjectId), runtime_(runtime)
  {
  }

  void handler(const uavcan_node_Heartbeat_1_0 & message, CanardRxTransfer * transfer) override
  {
    if (runtime_ == nullptr || transfer == nullptr) {
      return;
    }
    const auto source = transfer->metadata.remote_node_id;
    if (source < kFirstJointNodeId || source >= kFirstJointNodeId + kJointCount) {
      return;
    }
    const auto index = static_cast<std::size_t>(source - kFirstJointNodeId);
    runtime_->health[index].store(message.health.value);
    runtime_->mode[index].store(message.mode.value);
    runtime_->vendor_status[index].store(message.vendor_specific_status_code);
    runtime_->heartbeat_time_us[index].store(steady_microseconds());
  }

private:
  CyphalRuntime * runtime_;
};

}  // namespace ruka2_control::detail

namespace ruka2_control
{

Ruka2System::~Ruka2System()
{
  stop_transport();
}

CallbackReturn Ruka2System::on_init(const hardware_interface::HardwareInfo & hardware_info)
{
  if (hardware_interface::SystemInterface::on_init(hardware_info) != CallbackReturn::SUCCESS) {
    return CallbackReturn::ERROR;
  }
  if (info_.joints.size() != kJointCount) {
    RCLCPP_ERROR(get_logger(), "Expected %zu arm joints, got %zu", kJointCount, info_.joints.size());
    return CallbackReturn::ERROR;
  }

  const std::vector<std::string> expected_commands = {
    hardware_interface::HW_IF_POSITION, hardware_interface::HW_IF_VELOCITY};
  const std::vector<std::string> expected_states = {
    hardware_interface::HW_IF_POSITION, hardware_interface::HW_IF_VELOCITY};
  for (std::size_t index = 0; index < kJointCount; ++index) {
    const auto & joint = info_.joints[index];
    if (joint.name != kJointNames[index] ||
      !has_interfaces(joint.command_interfaces, expected_commands) ||
      !has_interfaces(joint.state_interfaces, expected_states))
    {
      RCLCPP_ERROR(
        get_logger(),
        "Joint %zu must be named '%s' and export position/velocity commands plus position/velocity states",
        index + 1U, kJointNames[index]);
      return CallbackReturn::ERROR;
    }
  }

  can_interface_ = string_parameter(info_, "can_interface", "vcan1.0");
  node_id_ = numeric_parameter<std::uint16_t>(info_, "node_id", kControllerNodeId);
  queue_length_ = numeric_parameter<std::size_t>(info_, "queue_length", 1000U);
  feedback_timeout_s_ = numeric_parameter<double>(info_, "feedback_timeout", 0.25);
  heartbeat_timeout_s_ = numeric_parameter<double>(info_, "heartbeat_timeout", 2.5);
  activation_timeout_s_ = numeric_parameter<double>(info_, "activation_timeout", 5.0);
  startup_grace_s_ = numeric_parameter<double>(info_, "startup_grace", 1.0);
  maximum_servo_velocity_ = numeric_parameter<double>(info_, "maximum_servo_velocity", 0.1);
  servo_acceleration_ = numeric_parameter<double>(info_, "servo_acceleration", 1.0);
  require_all_joints_on_activate_ =
    bool_parameter(info_, "require_all_joints_on_activate", true);

  if (node_id_ != kControllerNodeId || queue_length_ == 0U || feedback_timeout_s_ <= 0.0 ||
    heartbeat_timeout_s_ <= 0.0 || activation_timeout_s_ < 0.0 || startup_grace_s_ < 0.0 ||
    !std::isfinite(maximum_servo_velocity_) || maximum_servo_velocity_ <= 0.0 ||
    !std::isfinite(servo_acceleration_) || servo_acceleration_ <= 0.0)
  {
    RCLCPP_ERROR(get_logger(), "Invalid RUKA2 hardware parameters");
    return CallbackReturn::ERROR;
  }

  joint_position_command_.assign(kJointCount, 0.0);
  joint_velocity_command_.assign(kJointCount, 0.0);
  joint_position_state_.assign(kJointCount, 0.0);
  joint_velocity_state_.assign(kJointCount, 0.0);
  active_ = false;
  return CallbackReturn::SUCCESS;
}

CallbackReturn Ruka2System::start_transport()
{
  stop_transport();
  g_transport_error.store(false);
  if (if_nametoindex(can_interface_.c_str()) == 0U) {
    RCLCPP_ERROR(
      get_logger(), "SocketCAN interface '%s' does not exist", can_interface_.c_str());
    return CallbackReturn::ERROR;
  }
  try {
    runtime_ = std::make_unique<detail::CyphalRuntime>();
    runtime_->transport_start_us = steady_microseconds();
    runtime_->interface = CyphalInterface::create_heap<LinuxCAN, O1Allocator>(
      node_id_, can_interface_, queue_length_, g_utilities);
    if (!runtime_->interface || !runtime_->interface->is_up()) {
      throw std::runtime_error("Cyphal interface is not up");
    }
    runtime_->feedback_reader =
      std::make_unique<detail::FeedbackReader>(runtime_->interface, runtime_.get());
    runtime_->heartbeat_reader =
      std::make_unique<detail::HeartbeatReader>(runtime_->interface, runtime_.get());
    runtime_->diagnostics_node = rclcpp::Node::make_shared("ruka2_hardware_diagnostics");
    runtime_->diagnostics_publisher =
      runtime_->diagnostics_node->create_publisher<diagnostic_msgs::msg::DiagnosticArray>(
      "/diagnostics", rclcpp::QoS(10));
  } catch (const std::exception & error) {
    RCLCPP_ERROR(
      get_logger(), "Cannot open Cyphal transport on '%s': %s",
      can_interface_.c_str(), error.what());
    stop_transport();
    return CallbackReturn::ERROR;
  }
  RCLCPP_INFO(
    get_logger(), "Cyphal transport ready: interface=%s controller_node=%u",
    can_interface_.c_str(), node_id_);
  return CallbackReturn::SUCCESS;
}

void Ruka2System::stop_transport()
{
  active_ = false;
  if (!runtime_) {
    return;
  }
  runtime_->feedback_reader.reset();
  runtime_->heartbeat_reader.reset();
  runtime_->interface.reset();
  runtime_.reset();
}

CallbackReturn Ruka2System::on_configure(const rclcpp_lifecycle::State &)
{
  return start_transport();
}

CallbackReturn Ruka2System::on_activate(const rclcpp_lifecycle::State &)
{
  if (!runtime_ || !runtime_->interface) {
    return CallbackReturn::ERROR;
  }
  runtime_->activation_time_us = steady_microseconds();
  runtime_->last_heartbeat_tx_us = 0U;
  const auto deadline = SteadyClock::now() + std::chrono::duration<double>(activation_timeout_s_);
  std::string reason;
  do {
    runtime_->interface->loop();
    const auto now_us = steady_microseconds();
    if (runtime_->last_heartbeat_tx_us == 0U ||
      now_us - runtime_->last_heartbeat_tx_us >= 1000000U)
    {
      send_heartbeat();
    }
    if (all_joints_fresh(now_us, &reason)) {
      for (std::size_t index = 0; index < kJointCount; ++index) {
        joint_position_state_[index] = runtime_->position[index].load();
        joint_velocity_state_[index] = runtime_->velocity[index].load();
        joint_position_command_[index] = joint_position_state_[index];
        joint_velocity_command_[index] = 0.0;
      }
      active_ = true;
      publish_diagnostics(now_us, true);
      RCLCPP_INFO(get_logger(), "All six RUKA2 joint nodes are online; hardware activated");
      return CallbackReturn::SUCCESS;
    }
    if (!require_all_joints_on_activate_) {
      active_ = true;
      RCLCPP_WARN(get_logger(), "Hardware activated without all joint nodes: %s", reason.c_str());
      return CallbackReturn::SUCCESS;
    }
  } while (SteadyClock::now() < deadline);

  publish_diagnostics(steady_microseconds(), true);
  RCLCPP_ERROR(get_logger(), "Hardware activation timed out: %s", reason.c_str());
  return CallbackReturn::ERROR;
}

CallbackReturn Ruka2System::on_deactivate(const rclcpp_lifecycle::State &)
{
  if (active_) {
    send_hold_commands();
  }
  active_ = false;
  publish_diagnostics(steady_microseconds(), true);
  return CallbackReturn::SUCCESS;
}

CallbackReturn Ruka2System::on_cleanup(const rclcpp_lifecycle::State &)
{
  stop_transport();
  return CallbackReturn::SUCCESS;
}

CallbackReturn Ruka2System::on_shutdown(const rclcpp_lifecycle::State &)
{
  if (active_) {
    send_hold_commands();
  }
  stop_transport();
  return CallbackReturn::SUCCESS;
}

CallbackReturn Ruka2System::on_error(const rclcpp_lifecycle::State &)
{
  if (active_) {
    send_hold_commands();
  }
  stop_transport();
  return CallbackReturn::SUCCESS;
}

std::vector<hardware_interface::StateInterface> Ruka2System::export_state_interfaces()
{
  std::vector<hardware_interface::StateInterface> interfaces;
  interfaces.reserve(kJointCount * 2U);
  for (std::size_t index = 0; index < kJointCount; ++index) {
    interfaces.emplace_back(kJointNames[index], hardware_interface::HW_IF_POSITION,
      &joint_position_state_[index]);
    interfaces.emplace_back(kJointNames[index], hardware_interface::HW_IF_VELOCITY,
      &joint_velocity_state_[index]);
  }
  return interfaces;
}

std::vector<hardware_interface::CommandInterface> Ruka2System::export_command_interfaces()
{
  std::vector<hardware_interface::CommandInterface> interfaces;
  interfaces.reserve(kJointCount * 2U);
  for (std::size_t index = 0; index < kJointCount; ++index) {
    interfaces.emplace_back(kJointNames[index], hardware_interface::HW_IF_POSITION,
      &joint_position_command_[index]);
    interfaces.emplace_back(kJointNames[index], hardware_interface::HW_IF_VELOCITY,
      &joint_velocity_command_[index]);
  }
  return interfaces;
}

void Ruka2System::send_heartbeat()
{
  if (!runtime_ || !runtime_->interface) {
    return;
  }
  const auto now_us = steady_microseconds();
  uavcan_node_Heartbeat_1_0 message{};
  message.uptime = static_cast<std::uint32_t>((now_us - runtime_->transport_start_us) / 1000000U);
  message.health.value = uavcan_node_Health_1_0_NOMINAL;
  message.mode.value = uavcan_node_Mode_1_0_OPERATIONAL;
  message.vendor_specific_status_code = 0U;
  runtime_->interface->send_msg<HeartbeatMessage>(
    &message, kHeartbeatSubjectId, &runtime_->heartbeat_transfer_id);
  runtime_->last_heartbeat_tx_us = now_us;
}

void Ruka2System::send_joint_command(
  std::size_t joint_index, float position, float velocity, float acceleration)
{
  if (!runtime_ || !runtime_->interface || joint_index >= kJointCount) {
    return;
  }
  reg_udral_physics_kinematics_rotation_Planar_0_1 message{};
  message.angular_position.radian = position;
  message.angular_velocity.radian_per_second = velocity;
  message.angular_acceleration.radian_per_second_per_second = acceleration;
  runtime_->interface->send_msg<JointMessage>(
    &message, kServoCommandSubjectIds[joint_index],
    &runtime_->command_transfer_ids[joint_index]);
}

void Ruka2System::send_hold_commands()
{
  if (!runtime_ || !runtime_->interface) {
    return;
  }
  for (std::size_t index = 0; index < kJointCount; ++index) {
    send_joint_command(
      index, static_cast<float>(joint_position_state_[index]), 0.0F,
      static_cast<float>(servo_acceleration_));
  }
  runtime_->interface->process_tx_once();
}

bool Ruka2System::all_joints_fresh(std::uint64_t now_us, std::string * reason) const
{
  if (!runtime_) {
    if (reason) {
      *reason = "transport is not configured";
    }
    return false;
  }
  for (std::size_t index = 0; index < kJointCount; ++index) {
    const auto feedback_age = age_seconds(now_us, runtime_->feedback_time_us[index].load());
    const auto heartbeat_age = age_seconds(now_us, runtime_->heartbeat_time_us[index].load());
    const auto health = runtime_->health[index].load();
    if (feedback_age > feedback_timeout_s_) {
      if (reason) {
        *reason = std::string(kJointNames[index]) + " feedback is stale";
      }
      return false;
    }
    if (heartbeat_age > heartbeat_timeout_s_) {
      if (reason) {
        *reason = std::string(kJointNames[index]) + " heartbeat is stale";
      }
      return false;
    }
    if (health >= uavcan_node_Health_1_0_CAUTION) {
      if (reason) {
        *reason = std::string(kJointNames[index]) + " reports unsafe health=" +
          std::to_string(health);
      }
      return false;
    }
  }
  return true;
}

void Ruka2System::publish_diagnostics(std::uint64_t now_us, bool force)
{
  if (!runtime_ || !runtime_->diagnostics_publisher) {
    return;
  }
  if (!force && runtime_->last_diagnostics_tx_us != 0U &&
    now_us - runtime_->last_diagnostics_tx_us < 1000000U)
  {
    return;
  }

  diagnostic_msgs::msg::DiagnosticArray array;
  array.header.stamp = runtime_->diagnostics_node->now();
  std::string reason;
  const bool fresh = all_joints_fresh(now_us, &reason);
  diagnostic_msgs::msg::DiagnosticStatus aggregate;
  aggregate.name = "RUKA2/Cyphal transport";
  aggregate.hardware_id = can_interface_;
  aggregate.level = fresh ? diagnostic_msgs::msg::DiagnosticStatus::OK :
    diagnostic_msgs::msg::DiagnosticStatus::ERROR;
  aggregate.message = fresh ? "all arm joints online" : reason;
  aggregate.values.push_back(diagnostic_value("controller_node_id", std::to_string(node_id_)));
  aggregate.values.push_back(diagnostic_value("active", active_ ? "true" : "false"));
  aggregate.values.push_back(diagnostic_value(
    "tx_queue_size", runtime_->interface ? std::to_string(runtime_->interface->queue_size()) : "n/a"));
  array.status.push_back(std::move(aggregate));

  for (std::size_t index = 0; index < kJointCount; ++index) {
    const auto feedback_age = age_seconds(now_us, runtime_->feedback_time_us[index].load());
    const auto heartbeat_age = age_seconds(now_us, runtime_->heartbeat_time_us[index].load());
    const auto health = runtime_->health[index].load();
    const auto mode = runtime_->mode[index].load();
    const auto vendor = runtime_->vendor_status[index].load();
    diagnostic_msgs::msg::DiagnosticStatus status;
    status.name = std::string("RUKA2/") + kJointNames[index];
    status.hardware_id = "Cyphal node " + std::to_string(kFirstJointNodeId + index);
    if (feedback_age > feedback_timeout_s_ || heartbeat_age > heartbeat_timeout_s_) {
      status.level = diagnostic_msgs::msg::DiagnosticStatus::ERROR;
      status.message = "communication stale";
    } else if (health != uavcan_node_Health_1_0_NOMINAL || vendor != 0U) {
      status.level = health >= uavcan_node_Health_1_0_CAUTION ?
        diagnostic_msgs::msg::DiagnosticStatus::ERROR :
        diagnostic_msgs::msg::DiagnosticStatus::WARN;
      status.message = "firmware reports degraded health";
    } else {
      status.level = diagnostic_msgs::msg::DiagnosticStatus::OK;
      status.message = "online";
    }
    status.values.push_back(diagnostic_value("feedback_age_s", std::to_string(feedback_age)));
    status.values.push_back(diagnostic_value("heartbeat_age_s", std::to_string(heartbeat_age)));
    status.values.push_back(diagnostic_value("health", std::to_string(health)));
    status.values.push_back(diagnostic_value("mode", std::to_string(mode)));
    status.values.push_back(diagnostic_value("fault_bits_0_7", std::to_string(vendor)));
    status.values.push_back(diagnostic_value("position_rad", std::to_string(joint_position_state_[index])));
    status.values.push_back(diagnostic_value("velocity_rad_s", std::to_string(joint_velocity_state_[index])));
    array.status.push_back(std::move(status));
  }
  runtime_->diagnostics_publisher->publish(array);
  runtime_->last_diagnostics_tx_us = now_us;
}

hardware_interface::return_type Ruka2System::read(const rclcpp::Time &, const rclcpp::Duration &)
{
  if (!runtime_ || !runtime_->interface || g_transport_error.load()) {
    return hardware_interface::return_type::ERROR;
  }
  runtime_->interface->loop();
  const auto now_us = steady_microseconds();
  for (std::size_t index = 0; index < kJointCount; ++index) {
    joint_position_state_[index] = runtime_->position[index].load();
    joint_velocity_state_[index] = runtime_->velocity[index].load();
  }
  publish_diagnostics(now_us);
  if (active_ && now_us - runtime_->activation_time_us >=
    static_cast<std::uint64_t>(startup_grace_s_ * 1.0e6))
  {
    std::string reason;
    if (!all_joints_fresh(now_us, &reason)) {
      RCLCPP_ERROR_THROTTLE(get_logger(), *get_clock(), 1000, "%s", reason.c_str());
      return hardware_interface::return_type::ERROR;
    }
  }
  return hardware_interface::return_type::OK;
}

hardware_interface::return_type Ruka2System::write(const rclcpp::Time &, const rclcpp::Duration &)
{
  if (!active_) {
    return hardware_interface::return_type::OK;
  }
  if (!runtime_ || !runtime_->interface || g_transport_error.load()) {
    return hardware_interface::return_type::ERROR;
  }
  const auto now_us = steady_microseconds();
  if (runtime_->last_heartbeat_tx_us == 0U ||
    now_us - runtime_->last_heartbeat_tx_us >= 1000000U)
  {
    send_heartbeat();
  }
  for (std::size_t index = 0; index < kJointCount; ++index) {
    if (!std::isfinite(joint_position_command_[index]) ||
      !std::isfinite(joint_velocity_command_[index]))
    {
      RCLCPP_ERROR_THROTTLE(
        get_logger(), *get_clock(), 1000, "Non-finite command for %s", kJointNames[index]);
      return hardware_interface::return_type::ERROR;
    }
    const auto velocity = static_cast<float>(std::min(
      std::fabs(joint_velocity_command_[index]), maximum_servo_velocity_));
    send_joint_command(
      index, static_cast<float>(joint_position_command_[index]), velocity,
      static_cast<float>(servo_acceleration_));
  }
  runtime_->interface->loop();
  return hardware_interface::return_type::OK;
}

}  // namespace ruka2_control

PLUGINLIB_EXPORT_CLASS(ruka2_control::Ruka2System, hardware_interface::SystemInterface)
