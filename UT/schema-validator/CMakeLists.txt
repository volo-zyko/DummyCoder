cmake_minimum_required(VERSION 2.8)

project(schema-validator CXX)

# Find Boost
if (NOT Boost_FILESYSTEM_LIBRARY AND NOT Boost_SYSTEM_LIBRARY)
    find_package(Boost REQUIRED COMPONENTS system filesystem)

    if (Boost_SYSTEM_LIBRARY)
        set(Boost_SYSTEM_LIBRARY ${Boost_SYSTEM_LIBRARY} CACHE STRING "Path to boost system library")
    endif()
    if (Boost_FILESYSTEM_LIBRARY)
        set(Boost_FILESYSTEM_LIBRARY ${Boost_FILESYSTEM_LIBRARY} CACHE STRING "Path to boost filesystem library")
    endif()
endif()

# Find XercesC includes.
find_path(
    XERCESC_INCLUDE_DIR
    xercesc/util/XercesVersion.hpp
    PATHS ${XERCESC_ROOT_DIR}
    PATH_SUFFIXES include
)
if (NOT XERCESC_INCLUDE_DIR)
    message(FATAL_ERROR "XercesC include directory is not found")
endif()

# Find XercesC library.
find_library(
    XERCESC_LIBRARY
    NAMES xerces-c xerces-c_3
    PATHS ${XERCESC_ROOT_DIR}
    PATH_SUFFIXES lib64 lib32 lib
)
if (NOT XERCESC_LIBRARY)
    message(FATAL_ERROR "XercesC library is not found")
endif()

# Adjust compiler options.
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -std=c++11")
if (CMAKE_CXX_COMPILER_ID STREQUAL Clang)
    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -stdlib=libc++")
endif()

include_directories(${XERCESC_INCLUDE_DIR} ${Boost_INCLUDE_DIRS})
add_executable(${PROJECT_NAME} ${PROJECT_NAME}.cpp)
target_link_libraries(${PROJECT_NAME} ${Boost_SYSTEM_LIBRARY} ${Boost_FILESYSTEM_LIBRARY} ${XERCESC_LIBRARY})
