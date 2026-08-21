#ifndef RUKA_SPB__RUKA2_SYSTEM_HPP_
#define RUKA_SPB__RUKA2_SYSTEM_HPP_

#include <cstddef>
#include <cstdint>
#include <memory>
#include <string>
#include <vector>

#include "hardware_interface/hardware_info.hpp"
#include "hardware_interface/system_interface.hpp"
#include "hardware_interface/types/hardware_interface_return_values.hpp"
#include "rclcpp_lifecycle/node_interfaces/lifecycle_node_interface.hpp"
#include "rclcpp_lifecycle/state.hpp"

namespace ruka_spb
{

using CallbackReturn = rclcpp_lifecycle::node_interfaces::LifecycleNodeInterface::CallbackReturn;

namespace detail
{
struct CyphalRuntime;
}  // namespace detail

class Ruka2System : public hardware_interface::SystemInterface
{
public:
  ~Ruka2System() override;

  CallbackReturn on_init(const hardware_interface::HardwareInfo & hardware_info) override;
  CallbackReturn on_configure(const rclcpp_lifecycle::State & previous_state) override;
  CallbackReturn on_activate(const rclcpp_lifecycle::State & previous_state) override;
  CallbackReturn on_deactivate(const rclcpp_lifecycle::State & previous_state) override;
  CallbackReturn on_cleanup(const rclcpp_lifecycle::State & previous_state) override;
  CallbackReturn on_shutdown(const rclcpp_lifecycle::State & previous_state) override;
  CallbackReturn on_error(const rclcpp_lifecycle::State & previous_state) override;

  std::vector<hardware_interface::StateInterface> export_state_interfaces() override;
  std::vector<hardware_interface::CommandInterface> export_command_interfaces() override;

  hardware_interface::return_type read(
    const rclcpp::Time & time, const rclcpp::Duration & period) override;
  hardware_interface::return_type write(
    const rclcpp::Time & time, const rclcpp::Duration & period) override;

private:
  CallbackReturn start_transport();
  void stop_transport();
  void send_heartbeat();
  void send_hold_commands();
  void send_joint_command(
    std::size_t joint_index, float position, float velocity, float acceleration);
  bool all_joints_fresh(std::uint64_t now_us, std::string * reason = nullptr) const;
  void publish_diagnostics(std::uint64_t now_us, bool force = false);

  std::vector<double> joint_position_command_;
  std::vector<double> joint_velocity_command_;
  std::vector<double> joint_position_state_;
  std::vector<double> joint_velocity_state_;
  std::unique_ptr<detail::CyphalRuntime> runtime_;

  std::string can_interface_{"vcan1.0"};
  std::uint16_t node_id_{100};
  std::size_t queue_length_{1000};
  double feedback_timeout_s_{0.25};
  double heartbeat_timeout_s_{2.5};
  double activation_timeout_s_{5.0};
  double startup_grace_s_{1.0};
  double maximum_servo_velocity_{0.1};
  double servo_acceleration_{1.0};
  bool require_all_joints_on_activate_{true};
  bool active_{false};
};

}  // namespace ruka_spb

#endif  // RUKA_SPB__RUKA2_SYSTEM_HPP_
