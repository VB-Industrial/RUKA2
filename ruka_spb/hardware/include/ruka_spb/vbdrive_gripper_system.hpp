#pragma once

#include <cstddef>
#include <cstdint>
#include <memory>
#include <limits>
#include <string>
#include <vector>

#include "hardware_interface/hardware_info.hpp"
#include "hardware_interface/system_interface.hpp"
#include "hardware_interface/types/hardware_interface_return_values.hpp"
#include "rclcpp_lifecycle/node_interfaces/lifecycle_node_interface.hpp"
#include "rclcpp_lifecycle/state.hpp"

namespace ruka_spb
{

using GripperCallbackReturn =
  rclcpp_lifecycle::node_interfaces::LifecycleNodeInterface::CallbackReturn;

namespace detail
{
struct GripperCyphalRuntime;
}

class VBDriveGripperSystem : public hardware_interface::SystemInterface
{
public:
  ~VBDriveGripperSystem() override;

  GripperCallbackReturn on_init(const hardware_interface::HardwareInfo & info) override;
  GripperCallbackReturn on_configure(const rclcpp_lifecycle::State &) override;
  GripperCallbackReturn on_activate(const rclcpp_lifecycle::State &) override;
  GripperCallbackReturn on_deactivate(const rclcpp_lifecycle::State &) override;
  GripperCallbackReturn on_cleanup(const rclcpp_lifecycle::State &) override;
  GripperCallbackReturn on_shutdown(const rclcpp_lifecycle::State &) override;
  GripperCallbackReturn on_error(const rclcpp_lifecycle::State &) override;

  std::vector<hardware_interface::StateInterface> export_state_interfaces() override;
  std::vector<hardware_interface::CommandInterface> export_command_interfaces() override;
  hardware_interface::return_type read(const rclcpp::Time &, const rclcpp::Duration &) override;
  hardware_interface::return_type write(const rclcpp::Time &, const rclcpp::Duration &) override;

private:
  GripperCallbackReturn start_transport();
  void stop_transport();
  double motor_to_joint(double motor_angle) const;
  double joint_to_motor(double joint_position) const;
  double motor_torque_to_joint_force(double motor_torque) const;
  double joint_force_to_motor_torque(double joint_force) const;

  std::unique_ptr<detail::GripperCyphalRuntime> runtime_;
  std::string can_interface_{"vcan1.2"};
  std::uint16_t controller_node_id_{101};
  std::uint16_t drive_node_id_{11};
  std::uint16_t feedback_subject_id_{3811};
  std::uint16_t command_subject_id_{2118};
  std::size_t queue_length_{1000};
  double feedback_timeout_s_{12.0};
  double heartbeat_timeout_s_{2.5};
  double activation_timeout_s_{3.0};
  double joint_closed_position_{0.008};
  double joint_open_position_{0.025};
  double motor_closed_angle_{-0.3880};
  double motor_open_angle_{2.1824};
  double maximum_motor_velocity_{2.0};
  double maximum_motor_torque_{0.50};
  double warning_motor_torque_{0.35};
  double maximum_joint_force_{30.0};
  double default_opening_force_{9.64};
  double default_closing_force_{-9.64};
  double angle_kp_{2.5};
  double velocity_kp_{0.0};
  double current_kp_{4.0};
  double current_ki_{1600.0};
  double command_refresh_period_s_{0.05};
  double position_command_deadband_{0.0001};
  double effort_slew_rate_{1.0};
  double joint_position_{0.0};
  double joint_velocity_{0.0};
  double joint_effort_{0.0};
  double joint_position_command_{0.0};
  double joint_effort_command_{std::numeric_limits<double>::quiet_NaN()};
  double last_received_position_command_{0.0};
  double automatic_force_command_{0.0};
  double last_sent_motor_angle_{0.0};
  double last_sent_motor_torque_{0.0};
  std::uint64_t last_command_time_us_{0U};
  bool active_{false};
  bool command_initialized_{false};
};

}  // namespace ruka_spb
