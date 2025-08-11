#!/bin/bash

# wxWidgets Installation Script for Ubuntu/Debian
# This script installs all dependencies needed for the ZmqAnalyzer C++ application
# 
# Supported systems:
# - Ubuntu 22.04 and earlier: Uses wxWidgets 3.0.x packages
# - Ubuntu 24.04 and later: Uses wxWidgets 3.2.x packages
# - Other Debian-based distributions with similar package naming

set -e  # Exit on any error

echo "=== ZmqAnalyzer Dependency Installation ==="
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

echo "Installing additional project dependencies..."
sudo apt install -y \
    libboost-all-dev \
    libzmq3-dev \
    libfmt-dev \
    libspdlog-dev

echo "Installing wxWidgets development libraries..."

# Detect Ubuntu version and install appropriate wxWidgets packages
# Ubuntu 24.04+ uses wxWidgets 3.2.x, while older versions use 3.0.x
UBUNTU_VERSION=$(lsb_release -rs 2>/dev/null || echo "unknown")
echo "Detected Ubuntu/distribution version: $UBUNTU_VERSION"

# Check if wxWidgets 3.2 packages are available (Ubuntu 24.04+)
if apt-cache search libwxgtk3.2-dev | grep -q libwxgtk3.2-dev; then
    echo "Installing wxWidgets 3.2 packages (newer systems)..."
    sudo apt install -y \
        libwxgtk3.2-dev \
        wx3.2-headers \
        wx-common
elif apt-cache search libwxgtk3.0-gtk3-dev | grep -q libwxgtk3.0-gtk3-dev; then
    echo "Installing wxWidgets 3.0 packages (older systems)..."
    sudo apt install -y \
        libwxgtk3.0-gtk3-dev \
        wx3.0-headers \
        wx-common
else
    echo "Error: No compatible wxWidgets development packages found."
    echo "Please install wxWidgets manually or check your package repositories."
    exit 1
fi

echo
echo "=== Installation Complete ==="
echo
echo "All ZmqAnalyzer dependencies installed successfully!"
echo "You can now build and run the project using:"
echo "  ./scripts/build.sh"
echo "  ./scripts/run.sh"
echo
echo "Or using CMake directly:"
echo "  mkdir -p build && cd build"
echo "  cmake .."
echo "  make -j\$(nproc)"
echo "  ../bin/app"
