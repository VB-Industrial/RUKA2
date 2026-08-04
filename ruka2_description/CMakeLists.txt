cmake_minimum_required(VERSION 3.16)
project(ruka2_description)

find_package(ament_cmake REQUIRED)

install(
  DIRECTORY launch meshes rviz urdf
  DESTINATION share/${PROJECT_NAME}
)

if(BUILD_TESTING)
  find_package(ament_cmake_pytest REQUIRED)
  ament_add_pytest_test(test_dummy_description test/test_dummy_description.py)
endif()

ament_package()
