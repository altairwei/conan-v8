cmake_minimum_required(VERSION 3.1)
project(PackageTest CXX)

include(${CMAKE_BINARY_DIR}/conanbuildinfo.cmake)
conan_basic_setup()

find_package(Threads REQUIRED)

#set(CMAKE_CXX_STANDARD 14)
#add_definitions(-DV8_COMPRESS_POINTERS)

add_executable(example example.cpp)
target_link_libraries(example ${CONAN_LIBS} Threads::Threads)

if (WIN32)
    #add_definitions(-D_HAS_ITERATOR_DEBUGGING=0)
    #target_link_libraries(example winmm.lib dbghelp.lib)
endif()

# CTest is a testing tool that can be used to test your project.
# enable_testing()
# add_test(NAME example
#          WORKING_DIRECTORY ${CMAKE_BINARY_DIR}/bin
#          COMMAND example)
