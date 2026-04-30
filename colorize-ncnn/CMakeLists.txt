cmake_minimum_required(VERSION 3.10)
project(colorize-ncnn)

set(CMAKE_CXX_STANDARD 17)

# ncnn
set(ncnn_DIR ${CMAKE_SOURCE_DIR}/../3rdparty/ncnn/${ANDROID_ABI}/lib/cmake/ncnn)
find_package(ncnn REQUIRED)

# OpenCV
set(OpenCV_DIR ${CMAKE_SOURCE_DIR}/../3rdparty/opencv/${ANDROID_ABI}/sdk/native/jni)
find_package(OpenCV REQUIRED core imgproc imgcodecs)

set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -fexceptions -fopenmp -Os")
set(CMAKE_EXE_LINKER_FLAGS "${CMAKE_EXE_LINKER_FLAGS} -static-openmp")

add_executable(colorize-ncnn
    main.cpp
    colorize.cpp
)

# colorize.cpp uses ncnn::Layer subclass — must be -fno-rtti to avoid
# "undefined symbol: typeinfo for ncnn::Layer" from libncnn.a
set_source_files_properties(colorize.cpp PROPERTIES COMPILE_FLAGS "-fno-rtti")

target_link_libraries(colorize-ncnn ncnn ${OpenCV_LIBS})
