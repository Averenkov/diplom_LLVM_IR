cmake_minimum_required(VERSION 3.13)
project(Top20BiggestFuncs LANGUAGES C CXX)

find_package(LLVM REQUIRED CONFIG)
message(STATUS "Found LLVM ${LLVM_PACKAGE_VERSION}")
message(STATUS "Using LLVMConfig.cmake in: ${LLVM_DIR}")

list(APPEND CMAKE_MODULE_PATH "${LLVM_CMAKE_DIR}")
include(AddLLVM)

add_library(Top20BiggestFuncs MODULE Top20BiggestFuncs.cpp)
set_target_properties(Top20BiggestFuncs PROPERTIES
  CXX_STANDARD 17
  CXX_STANDARD_REQUIRED YES
  PREFIX ""
  SUFFIX ".dylib"
)

target_include_directories(Top20BiggestFuncs PRIVATE ${LLVM_INCLUDE_DIRS})
target_compile_definitions(Top20BiggestFuncs PRIVATE ${LLVM_DEFINITIONS})

target_link_options(Top20BiggestFuncs PRIVATE "-Wl,-undefined,dynamic_lookup")
