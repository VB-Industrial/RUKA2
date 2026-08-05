#ifndef RUKA2_CONTROL__CYPHAL_CONTRACT_HPP_
#define RUKA2_CONTROL__CYPHAL_CONTRACT_HPP_

#include <array>
#include <cstddef>
#include <cstdint>

namespace ruka2_control
{

inline constexpr std::size_t kJointCount = 6;
inline constexpr std::uint16_t kControllerNodeId = 100;
inline constexpr std::uint16_t kFirstJointNodeId = 21;
inline constexpr std::uint16_t kFeedbackSubjectId = 1001;
inline constexpr std::uint16_t kHeartbeatSubjectId = 7509;

inline constexpr std::array<std::uint16_t, kJointCount> kServoCommandSubjectIds = {
  1121, 1122, 1123, 1124, 1125, 1126};
inline constexpr std::array<std::uint16_t, kJointCount> kDirectCommandSubjectIds = {
  1131, 1132, 1133, 1134, 1135, 1136};

inline constexpr std::array<const char *, kJointCount> kJointNames = {
  "joint_1", "joint_2", "joint_3", "joint_4", "joint_5", "joint_6"};

}  // namespace ruka2_control

#endif  // RUKA2_CONTROL__CYPHAL_CONTRACT_HPP_
