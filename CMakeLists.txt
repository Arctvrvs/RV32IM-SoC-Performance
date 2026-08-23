cmake_minimum_required(VERSION 3.16)
project(RV32IM_Performance_Starter LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

option(RV32IM_BUILD_SYSTEMC "Build the optional SystemC clocked runner" ON)

add_library(rv32im_core
    src/CpuModel.cpp
    src/Memory.cpp
    src/PipelineTimingModel.cpp
    src/CacheModel.cpp
    src/IFetchStreamModel.cpp
)

target_include_directories(rv32im_core PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}/include
)

target_compile_options(rv32im_core PRIVATE
    $<$<CXX_COMPILER_ID:GNU,Clang>:-Wall;-Wextra;-Wpedantic>
)

add_executable(rv32im_model main.cpp)
target_link_libraries(rv32im_model PRIVATE rv32im_core)

if(RV32IM_BUILD_SYSTEMC)
    find_path(SYSTEMC_INCLUDE_DIR
        NAMES systemc
        HINTS $ENV{SYSTEMC_HOME}
        PATH_SUFFIXES include
    )

    find_library(SYSTEMC_LIBRARY
        NAMES systemc
        HINTS $ENV{SYSTEMC_HOME}
        PATH_SUFFIXES lib lib64 lib-linux64
    )

    if(SYSTEMC_INCLUDE_DIR AND SYSTEMC_LIBRARY)
        add_executable(rv32im_systemc
            systemc/systemc_main.cpp
            systemc/RV32IMSystemC.cpp
        )
        target_include_directories(rv32im_systemc PRIVATE
            ${SYSTEMC_INCLUDE_DIR}
            ${CMAKE_CURRENT_SOURCE_DIR}/systemc
        )
        target_link_libraries(rv32im_systemc PRIVATE
            rv32im_core
            ${SYSTEMC_LIBRARY}
        )
        message(STATUS "SystemC found: building rv32im_systemc")
    else()
        message(WARNING
            "SystemC was not found. rv32im_model will still build. "
            "Set SYSTEMC_HOME to your SystemC installation to build rv32im_systemc."
        )
    endif()
endif()
