cmake_minimum_required(VERSION 3.21)

project(app LANGUAGES CXX)

# Set C++ standard
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find wxWidgets using wx-config (more reliable for older versions)
find_program(WX_CONFIG wx-config)
if(NOT WX_CONFIG)
    message(FATAL_ERROR "wx-config not found. Please install wxWidgets development packages.")
endif()

# Get wxWidgets version
execute_process(COMMAND ${WX_CONFIG} --version OUTPUT_VARIABLE WX_VERSION OUTPUT_STRIP_TRAILING_WHITESPACE)
message(STATUS "Found wxWidgets version: ${WX_VERSION}")

# Get wxWidgets flags
execute_process(COMMAND ${WX_CONFIG} --cxxflags OUTPUT_VARIABLE WX_CXX_FLAGS OUTPUT_STRIP_TRAILING_WHITESPACE)
execute_process(COMMAND ${WX_CONFIG} --libs OUTPUT_VARIABLE WX_LIBS OUTPUT_STRIP_TRAILING_WHITESPACE)

# Convert space-separated flags to list
separate_arguments(WX_CXX_FLAGS)
separate_arguments(WX_LIBS)

# Set target directory
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${CMAKE_SOURCE_DIR}/bin/)

# Include SourceFiles.cmake to access the SOURCEFILES and INCLUDEDIRS variables
include(${CMAKE_CURRENT_LIST_DIR}/src/SourceFiles.cmake)

add_executable(app ${SOURCEFILES})

# Apply wxWidgets flags
target_compile_options(app PRIVATE ${WX_CXX_FLAGS})
target_link_libraries(app ${WX_LIBS})

target_include_directories(app PUBLIC ${INCLUDEDIRS})