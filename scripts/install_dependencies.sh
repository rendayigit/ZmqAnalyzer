#!/bin/bash

# wxWidgets Installation Script for Ubuntu/Debian
# This script installs all dependencies needed for the wxWidgets C++ GUI template

set -e  # Exit on any error

echo "=== wxWidgets C++ Template Dependency Installation ==="
echo

# Check if running on Ubuntu/Debian
if ! command -v apt &> /dev/null; then
    echo "Error: This script is designed for Ubuntu/Debian systems with apt package manager."
    echo "Please refer to the README.md for installation instructions for your system."
    exit 1
fi

# Update package lists
echo "Updating package lists..."
sudo apt update

echo "Installing core build tools..."
sudo apt install -y \
    build-essential \
    cmake \
    gdb \
    clangd \
    clang-format

echo "Installing wxWidgets development libraries..."
sudo apt install -y \
    libwxgtk3.0-gtk3-dev \
    wx3.0-headers \
    wx-common

echo
echo "=== Installation Complete ==="
echo
echo "Dependencies installed successfully!"
echo "You can now build the project using:"
echo "  ./scripts/build.sh"
echo "  ./scripts/run.sh"
echo
echo "Or using CMake directly:"
echo "  mkdir -p build && cd build"
echo "  cmake .."
echo "  make -j\$(nproc)"
echo "  ../bin/app"
