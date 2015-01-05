cmake_minimum_required(VERSION 2.8)

project(schema-validator CXX)

# Find Boost.
set(Boost_USE_STATIC_LIBS ON)
set(Boost_USE_MULTITHREADED ON)
set(Boost_USE_STATIC_RUNTIME OFF)
find_package(Boost REQUIRED COMPONENTS system filesystem regex)

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

# Find libxml2.
find_package(LibXml2 REQUIRED)

# Adjust compiler options.
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -std=c++11")
if (CMAKE_CXX_COMPILER_ID STREQUAL Clang)
    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -stdlib=libc++")
endif()

add_definitions("-DBOOST_FILESYSTEM_NO_DEPRECATED -DLIBXML2_DEFINITIONS")
include_directories(${Boost_INCLUDE_DIRS} ${XERCESC_INCLUDE_DIR} ${LIBXML2_INCLUDE_DIR})
add_executable(${PROJECT_NAME} ${PROJECT_NAME}.cpp)
target_link_libraries(${PROJECT_NAME} ${Boost_SYSTEM_LIBRARY} ${Boost_FILESYSTEM_LIBRARY} ${Boost_REGEX_LIBRARY} ${XERCESC_LIBRARY} ${LIBXML2_LIBRARIES})
