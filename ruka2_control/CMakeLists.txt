cmake_minimum_required(VERSION 3.16)
project(ruka2_control)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(ament_cmake REQUIRED)

install(
  DIRECTORY config launch ros2_control urdf
  DESTINATION share/${PROJECT_NAME}
)

if(BUILD_TESTING)
  find_package(ament_cmake_pytest REQUIRED)
  ament_add_pytest_test(test_mock_description test/test_mock_description.py)
endif()

ament_package()
