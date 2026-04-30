#!/bin/bash
# Build colorize-ncnn for Android arm64-v8a
# Called from GitHub Actions after 3rdparty libs are ready

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BUILD_DIR="$SCRIPT_DIR/build-android"

cmake -S "$SCRIPT_DIR" -B "$BUILD_DIR" \
    -DCMAKE_TOOLCHAIN_FILE="$ANDROID_NDK/build/cmake/android.toolchain.cmake" \
    -DANDROID_ABI=arm64-v8a \
    -DANDROID_PLATFORM=android-21 \
    -DANDROID_STL=c++_static \
    -DCMAKE_BUILD_TYPE=Release

cmake --build "$BUILD_DIR" --config Release -j$(nproc)

echo "Built: $BUILD_DIR/colorize-ncnn"
